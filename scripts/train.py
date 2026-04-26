# train.py
# Phase 3: Training Pipeline for Dark Pattern Detection Model
#
# Publication-ready training with:
#   - Domain-level train/val/test split (no data leakage)
#   - Class-weighted loss for imbalanced labels
#   - Confidence-weighted training
#   - Early stopping with patience
#   - LR warmup + cosine annealing
#   - Mixed precision (AMP) support
#   - Multi-seed reproducibility
#   - Ablation mode (disable branches)
#   - Enhanced metrics (ROC-AUC, confusion matrix, attention analysis)
#   - Held-out test set evaluation
#
# USAGE:
#   python train.py                                    # Train with defaults
#   python train.py --epochs 30 --batch-size 16        # Custom settings
#   python train.py --disable-branches visual,structural  # Text-only ablation
#   python train.py --seed 123 --amp                   # Different seed + AMP

import sys
import json
import time
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts, LinearLR, SequentialLR
from transformers import RobertaTokenizer

from dataset import (
    create_dataloaders,
    DARK_PATTERN_TYPES,
    SEVERITY_LEVELS,
    NUM_TYPES,
    NUM_SEVERITY,
    NUM_STRUCTURAL_FEATURES,
)
from model import DarkPatternDetector, MultiTaskLoss

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================================
# SEED + CLASS WEIGHTS
# ============================================================================

def set_seed(seed):
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    logger.info(f"Random seed set to {seed}")


def compute_class_weights(train_dataset):
    """
    Compute class weights by reading only label files (not images/text/transforms).
    Deterministic — avoids stochastic counting from WeightedRandomSampler.

    Returns:
        type_pos_weights: Tensor [11] — pos_weight for BCE on type head
        severity_weights: Tensor [4]  — class weight for CE on severity head
    """
    from dataset import extract_labels_from_labeler

    type_counts = torch.zeros(NUM_TYPES)
    severity_counts = torch.zeros(NUM_SEVERITY)
    total = 0

    skipped = 0
    for source, source_idx in train_dataset._index_map:
        if source == "own":
            # Read only the label JSON — skip image/text/structural loading
            sample_info = train_dataset.own_dataset.samples[source_idx]
            try:
                with open(sample_info["label"]) as f:
                    label_data = json.load(f)
                labels = extract_labels_from_labeler(label_data)
                type_counts += torch.tensor(labels["types"])
                severity_counts[labels["severity"]] += 1
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                # Skip corrupt/missing labels — do NOT silently inflate severity class 0.
                logger.warning(
                    f"Skipping corrupt label in class-weight count: "
                    f"{sample_info.get('label')} ({type(e).__name__}: {e})"
                )
                skipped += 1
                continue
        else:
            # Yada: labels already in memory, no I/O needed
            yada_sample = train_dataset.yada_dataset.samples[source_idx]
            type_counts += torch.tensor(yada_sample["types"])
            severity_counts[yada_sample["severity"]] += 1
        total += 1

    # pos_weight: num_negative / num_positive, capped at 10
    type_pos_weights = torch.clamp((total - type_counts) / (type_counts + 1), max=10.0)

    # severity weight: total / (num_classes * count)
    severity_weights = total / (NUM_SEVERITY * (severity_counts + 1))

    logger.info(f"Class-weight computation: counted={total}, skipped_corrupt={skipped}")
    logger.info(f"Type pos_weights: {dict(zip(DARK_PATTERN_TYPES, [f'{w:.2f}' for w in type_pos_weights.tolist()]))}")
    logger.info(f"Severity weights: {dict(zip(SEVERITY_LEVELS, [f'{w:.2f}' for w in severity_weights.tolist()]))}")

    return type_pos_weights, severity_weights


# ============================================================================
# METRICS
# ============================================================================

def compute_metrics(all_preds, all_labels, threshold=0.5, attention_weights=None):
    """
    Compute evaluation metrics for all three tasks.
    Includes ROC-AUC, per-type P/R/F1, severity confusion matrix, attention analysis.
    """
    metrics = {}

    # --- Binary metrics ---
    binary_probs = torch.sigmoid(all_preds["binary"]).cpu()
    binary_pred = (binary_probs >= threshold).float()
    binary_true = all_labels["binary"].cpu()

    tp = ((binary_pred == 1) & (binary_true == 1)).sum().item()
    fp = ((binary_pred == 1) & (binary_true == 0)).sum().item()
    fn = ((binary_pred == 0) & (binary_true == 1)).sum().item()
    tn = ((binary_pred == 0) & (binary_true == 0)).sum().item()

    metrics["binary_accuracy"] = (tp + tn) / max(tp + fp + fn + tn, 1)
    metrics["binary_precision"] = tp / max(tp + fp, 1)
    metrics["binary_recall"] = tp / max(tp + fn, 1)
    metrics["binary_f1"] = (
        2 * metrics["binary_precision"] * metrics["binary_recall"] /
        max(metrics["binary_precision"] + metrics["binary_recall"], 1e-8)
    )

    # ROC-AUC (requires sklearn + at least one sample of each class)
    try:
        from sklearn.metrics import roc_auc_score
    except ImportError:
        logger.warning("sklearn not installed — skipping ROC-AUC metric")
    else:
        if len(set(binary_true.squeeze().tolist())) > 1:
            try:
                metrics["binary_roc_auc"] = roc_auc_score(
                    binary_true.squeeze().numpy(), binary_probs.squeeze().numpy()
                )
            except ValueError as e:
                logger.debug(f"ROC-AUC skipped: {e}")

    # --- Multi-label metrics (per-type P/R/F1) ---
    type_probs = torch.sigmoid(all_preds["types"]).cpu()
    type_pred = (type_probs >= threshold).float()
    type_true = all_labels["types"].cpu()

    type_f1s = []
    for i, type_name in enumerate(DARK_PATTERN_TYPES):
        tp_i = ((type_pred[:, i] == 1) & (type_true[:, i] == 1)).sum().item()
        fp_i = ((type_pred[:, i] == 1) & (type_true[:, i] == 0)).sum().item()
        fn_i = ((type_pred[:, i] == 0) & (type_true[:, i] == 1)).sum().item()

        prec = tp_i / max(tp_i + fp_i, 1)
        rec = tp_i / max(tp_i + fn_i, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-8) if (tp_i + fp_i + fn_i) > 0 else 0.0

        metrics[f"type_{type_name}_precision"] = prec
        metrics[f"type_{type_name}_recall"] = rec
        metrics[f"type_{type_name}_f1"] = f1
        if (tp_i + fp_i + fn_i) > 0:
            type_f1s.append(f1)

    metrics["type_macro_f1"] = sum(type_f1s) / max(len(type_f1s), 1)

    correct_per_sample = (type_pred == type_true).float().mean(dim=1)
    metrics["type_sample_accuracy"] = correct_per_sample.mean().item()

    # --- Severity metrics ---
    severity_pred = all_preds["severity"].cpu().argmax(dim=1)
    severity_true = all_labels["severity"].cpu().squeeze(1)

    metrics["severity_accuracy"] = (severity_pred == severity_true).float().mean().item()

    # Confusion matrix
    confusion = [[0] * NUM_SEVERITY for _ in range(NUM_SEVERITY)]
    for true_i, pred_i in zip(severity_true.tolist(), severity_pred.tolist()):
        confusion[int(true_i)][int(pred_i)] += 1
    metrics["severity_confusion_matrix"] = confusion

    for i, sev_name in enumerate(SEVERITY_LEVELS):
        mask = severity_true == i
        if mask.sum() > 0:
            metrics[f"severity_{sev_name}_acc"] = (severity_pred[mask] == i).float().mean().item()

    # --- Attention weights analysis ---
    if attention_weights is not None:
        try:
            # attention_weights shape varies: [batch, 3, 3] or [batch, heads, 3, 3]
            # Average over all dims except the last two to get [3, 3]
            while attention_weights.dim() > 2:
                attention_weights = attention_weights.mean(dim=0)
            # avg_attn is now [3, 3]: how much each token attends to each other
            modality_importance = attention_weights.sum(dim=0)  # column sum = how much each modality is attended to
            modality_importance = modality_importance / modality_importance.sum()
            metrics["attention_visual"] = modality_importance[0].item()
            metrics["attention_text"] = modality_importance[1].item()
            metrics["attention_structural"] = modality_importance[2].item()
        except Exception:
            pass  # skip attention analysis if shape is unexpected

    return metrics


# ============================================================================
# TRAINING STEP
# ============================================================================

def train_one_epoch(model, train_loader, criterion, optimizer, device, epoch,
                    scaler=None):
    """Run one training epoch. Supports AMP via scaler."""
    model.train()

    total_loss = 0.0
    loss_components = {"binary": 0.0, "types": 0.0, "severity": 0.0}
    num_batches = 0

    for batch_idx, batch in enumerate(train_loader):
        image = batch["image"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        structural = batch["structural"].to(device)
        binary_label = batch["binary_label"].to(device)
        type_labels = batch["type_labels"].to(device)
        severity_label = batch["severity_label"].to(device)
        confidence = batch["confidence"].to(device)

        optimizer.zero_grad()

        if scaler is not None:
            with torch.amp.autocast("cuda"):
                outputs = model(image, input_ids, attention_mask, structural)
                loss, loss_dict = criterion(
                    outputs["binary_logits"], outputs["type_logits"],
                    outputs["severity_logits"],
                    binary_label, type_labels, severity_label,
                    sample_weights=confidence,
                )
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(image, input_ids, attention_mask, structural)
            loss, loss_dict = criterion(
                outputs["binary_logits"], outputs["type_logits"],
                outputs["severity_logits"],
                binary_label, type_labels, severity_label,
                sample_weights=confidence,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        total_loss += loss_dict["total"]
        loss_components["binary"] += loss_dict["binary"]
        loss_components["types"] += loss_dict["types"]
        loss_components["severity"] += loss_dict["severity"]
        num_batches += 1

        if (batch_idx + 1) % 10 == 0 or (batch_idx + 1) == len(train_loader):
            logger.info(
                f"  Epoch {epoch} [{batch_idx + 1}/{len(train_loader)}] "
                f"loss={loss_dict['total']:.4f} "
                f"(bin={loss_dict['binary']:.3f} "
                f"type={loss_dict['types']:.3f} "
                f"sev={loss_dict['severity']:.3f})"
            )

    avg_loss = total_loss / max(num_batches, 1)
    avg_components = {k: v / max(num_batches, 1) for k, v in loss_components.items()}

    return avg_loss, avg_components


# ============================================================================
# VALIDATION STEP
# ============================================================================

@torch.no_grad()
def validate(model, val_loader, criterion, device, use_amp=None):
    """Run validation and compute metrics including attention analysis.

    use_amp: None = auto (enable on CUDA); True/False = force.
    """
    model.eval()

    if use_amp is None:
        use_amp = (device.type == "cuda")

    total_loss = 0.0
    num_batches = 0

    all_preds = {"binary": [], "types": [], "severity": []}
    all_labels = {"binary": [], "types": [], "severity": []}
    all_attention = []

    for batch in val_loader:
        image = batch["image"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        structural = batch["structural"].to(device)
        binary_label = batch["binary_label"].to(device)
        type_labels = batch["type_labels"].to(device)
        severity_label = batch["severity_label"].to(device)

        with torch.amp.autocast(device_type=device.type, enabled=use_amp):
            outputs = model(image, input_ids, attention_mask, structural)

            # No confidence weighting during validation — unbiased evaluation
            loss, loss_dict = criterion(
                outputs["binary_logits"], outputs["type_logits"],
                outputs["severity_logits"],
                binary_label, type_labels, severity_label,
            )

        total_loss += loss_dict["total"]
        num_batches += 1

        all_preds["binary"].append(outputs["binary_logits"])
        all_preds["types"].append(outputs["type_logits"])
        all_preds["severity"].append(outputs["severity_logits"])

        all_labels["binary"].append(binary_label)
        all_labels["types"].append(type_labels)
        all_labels["severity"].append(severity_label)

        if outputs.get("attention_weights") is not None:
            all_attention.append(outputs["attention_weights"].cpu())

    for key in all_preds:
        all_preds[key] = torch.cat(all_preds[key], dim=0)
        all_labels[key] = torch.cat(all_labels[key], dim=0)

    attn = torch.cat(all_attention, dim=0) if all_attention else None

    avg_loss = total_loss / max(num_batches, 1)
    metrics = compute_metrics(all_preds, all_labels, attention_weights=attn)

    return avg_loss, metrics


# ============================================================================
# CHECKPOINT
# ============================================================================

def save_checkpoint(model, optimizer, scheduler, criterion, epoch, metrics, path):
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "criterion_state_dict": criterion.state_dict(),
        "metrics": {k: v for k, v in metrics.items() if not isinstance(v, list)},
        "timestamp": datetime.now().isoformat(),
    }
    torch.save(checkpoint, path)
    logger.info(f"  Checkpoint saved: {path}")


def load_checkpoint(path, model, optimizer=None, scheduler=None, criterion=None):
    # weights_only=True blocks arbitrary code execution via crafted checkpoints.
    # Our saved state contains only tensors + plain python containers (safe).
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    if scheduler and checkpoint.get("scheduler_state_dict"):
        scheduler.load_state_dict(checkpoint["scheduler_state_dict"])
    if criterion and "criterion_state_dict" in checkpoint:
        criterion.load_state_dict(checkpoint["criterion_state_dict"])
    logger.info(f"Checkpoint loaded from epoch {checkpoint['epoch']}")
    return checkpoint["epoch"]


# ============================================================================
# MAIN TRAINING LOOP
# ============================================================================

def train(args):
    """Full training pipeline with early stopping, warmup, AMP, multi-seed."""

    # --- Seed ---
    set_seed(args.seed)

    # --- Device ---
    device = torch.device("cuda" if torch.cuda.is_available() else
                          "mps" if torch.backends.mps.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Output directory includes seed
    output_dir = Path(args.output_dir) / f"seed_{args.seed}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Tokenizer ---
    logger.info("Loading RoBERTa tokenizer...")
    tokenizer = RobertaTokenizer.from_pretrained("roberta-base")

    # --- Data ---
    logger.info("Creating dataloaders...")
    train_loader, val_loader, test_loader, dataset_info = create_dataloaders(
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        data_dir=args.data_dir,
        label_dir=args.label_dir,
        use_yada=not args.no_yada,
        seed=args.seed,
    )

    if dataset_info["num_train"] == 0:
        logger.error("No training data found. Exiting.")
        sys.exit(1)

    # --- Class weights (computed from dataset directly, not stochastic sampler) ---
    logger.info("Computing class weights from training data...")
    type_pos_weights, severity_weights = compute_class_weights(train_loader.dataset)
    type_pos_weights = type_pos_weights.to(device)
    severity_weights = severity_weights.to(device)

    # --- Parse disable_branches ---
    disable_branches = []
    if args.disable_branches:
        disable_branches = [b.strip() for b in args.disable_branches.split(",")]
        logger.info(f"Ablation mode: disabled branches = {disable_branches}")

    # --- Model ---
    logger.info("Building model...")
    model = DarkPatternDetector(
        num_structural_features=NUM_STRUCTURAL_FEATURES,
        num_types=NUM_TYPES,
        num_severity=NUM_SEVERITY,
        freeze_backbone_layers=args.freeze_layers,
        dropout=args.dropout,
        disable_branches=disable_branches,
    )

    param_info = model.get_trainable_params()
    logger.info(f"Parameters: {param_info['total']:,} total, "
                f"{param_info['trainable']:,} trainable ({param_info['trainable_pct']}%)")

    model = model.to(device)

    # --- Loss ---
    criterion = MultiTaskLoss(
        type_pos_weights=type_pos_weights,
        severity_weights=severity_weights,
    ).to(device)

    # --- Optimizer ---
    param_groups = model.get_param_groups(
        lr_backbone=args.lr_backbone,
        lr_new=args.lr_new,
    )
    param_groups.append({"params": criterion.parameters(), "lr": args.lr_new})
    optimizer = AdamW(param_groups, weight_decay=args.weight_decay)

    # --- Scheduler with warmup ---
    warmup_epochs = 2
    warmup_scheduler = LinearLR(
        optimizer, start_factor=0.1, end_factor=1.0, total_iters=warmup_epochs
    )
    cosine_scheduler = CosineAnnealingWarmRestarts(
        optimizer,
        T_0=max(args.epochs // 3, 1),
        T_mult=2,
        eta_min=1e-7,
    )
    scheduler = SequentialLR(
        optimizer,
        schedulers=[warmup_scheduler, cosine_scheduler],
        milestones=[warmup_epochs],
    )

    # --- AMP ---
    scaler = None
    if args.amp and device.type == "cuda":
        scaler = torch.amp.GradScaler("cuda")
        logger.info("Mixed precision (AMP) enabled")

    # --- Resume ---
    start_epoch = 0
    if args.resume:
        start_epoch = load_checkpoint(
            args.resume, model, optimizer, scheduler, criterion
        ) + 1

    # --- Training state ---
    training_log = {
        "args": vars(args),
        "dataset": dataset_info,
        "params": param_info,
        "device": str(device),
        "disable_branches": disable_branches,
        "epochs": [],
    }

    best_val_f1 = 0.0
    patience_counter = 0
    last_epoch = start_epoch
    val_metrics = {}

    # --- Training loop ---
    logger.info(f"\nTraining for up to {args.epochs} epochs (patience={args.patience})...")
    logger.info(f"Train: {dataset_info['num_train']} | Val: {dataset_info['num_val']} | "
                f"Test: {dataset_info['num_test']}")

    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()

        logger.info(f"Epoch {epoch + 1}/{args.epochs}")
        train_loss, train_components = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch + 1,
            scaler=scaler,
        )

        val_loss, val_metrics = validate(model, val_loader, criterion, device)

        scheduler.step()
        # Convention: checkpoint["epoch"] = number of COMPLETED epochs (1-indexed count).
        # On resume, start_epoch = checkpoint["epoch"] → loop restarts at next index.
        completed_epochs = epoch + 1
        last_epoch = completed_epochs

        epoch_time = time.time() - epoch_start

        # Log
        logger.info(
            f"  Train loss: {train_loss:.4f} | Val loss: {val_loss:.4f} | "
            f"Time: {epoch_time:.1f}s"
        )
        logger.info(
            f"  Binary: acc={val_metrics['binary_accuracy']:.3f} "
            f"f1={val_metrics['binary_f1']:.3f} "
            f"p={val_metrics['binary_precision']:.3f} "
            f"r={val_metrics['binary_recall']:.3f}"
            + (f" auc={val_metrics['binary_roc_auc']:.3f}" if "binary_roc_auc" in val_metrics else "")
        )
        logger.info(
            f"  Types:  macro_f1={val_metrics['type_macro_f1']:.3f} "
            f"sample_acc={val_metrics['type_sample_accuracy']:.3f}"
        )
        logger.info(f"  Severity: acc={val_metrics['severity_accuracy']:.3f}")
        if "attention_visual" in val_metrics:
            logger.info(
                f"  Attention: visual={val_metrics['attention_visual']:.3f} "
                f"text={val_metrics['attention_text']:.3f} "
                f"structural={val_metrics['attention_structural']:.3f}"
            )

        epoch_log = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "train_components": train_components,
            "val_loss": val_loss,
            "val_metrics": {k: v for k, v in val_metrics.items()
                           if not isinstance(v, list)},
            "epoch_time": epoch_time,
            "lr": optimizer.param_groups[0]["lr"],
        }
        training_log["epochs"].append(epoch_log)

        # Best model + early stopping
        current_f1 = val_metrics["binary_f1"]
        if current_f1 > best_val_f1:
            best_val_f1 = current_f1
            patience_counter = 0
            save_checkpoint(
                model, optimizer, scheduler, criterion, completed_epochs,
                val_metrics, output_dir / "best_model.pt"
            )
            logger.info(f"  New best! Binary F1: {best_val_f1:.4f}")
        else:
            patience_counter += 1
            logger.info(f"  No improvement ({patience_counter}/{args.patience})")
            if patience_counter >= args.patience:
                logger.info(f"  Early stopping at epoch {epoch + 1}")
                break

        if completed_epochs % args.save_every == 0:
            save_checkpoint(
                model, optimizer, scheduler, criterion, completed_epochs,
                val_metrics, output_dir / f"checkpoint_epoch{completed_epochs}.pt"
            )

    # --- Final save ---
    if val_metrics:
        save_checkpoint(
            model, optimizer, scheduler, criterion, last_epoch,
            val_metrics, output_dir / "final_model.pt"
        )

    log_path = output_dir / "training_log.json"
    with open(log_path, "w") as f:
        json.dump(training_log, f, indent=2, default=str)

    # --- Test evaluation ---
    if test_loader is not None and len(test_loader) > 0:
        logger.info("\nEvaluating on held-out test set...")
        best_ckpt = output_dir / "best_model.pt"
        if best_ckpt.exists():
            load_checkpoint(best_ckpt, model)
        test_loss, test_metrics = validate(model, test_loader, criterion, device)
        logger.info(f"TEST Binary F1: {test_metrics['binary_f1']:.4f} | "
                    f"Type Macro F1: {test_metrics['type_macro_f1']:.4f} | "
                    f"Severity Acc: {test_metrics['severity_accuracy']:.4f}")
        test_results = {
            "test_loss": test_loss,
            "test_metrics": test_metrics,
            "best_val_f1": best_val_f1,
        }
        with open(output_dir / "test_results.json", "w") as f:
            json.dump(test_results, f, indent=2, default=str)

    logger.info("\n" + "=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info(f"Best Val Binary F1: {best_val_f1:.4f}")
    logger.info(f"Models saved to: {output_dir}")
    logger.info("=" * 60)

    return model


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_training_logging():
    named_logger = logging.getLogger("darksite")
    named_logger.setLevel(logging.INFO)
    if not named_logger.handlers:
        log_dir = PROJECT_ROOT / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh = logging.FileHandler(str(log_dir / "training.log"))
        fh.setFormatter(fmt)
        named_logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        named_logger.addHandler(sh)
    return named_logger


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Train dark pattern detection model")

    # Data
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--label-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str,
                        default=str(PROJECT_ROOT / "models"))

    # External datasets
    parser.add_argument("--no-yada", action="store_true",
                        help="Exclude Yada text dataset")

    # Ablation
    parser.add_argument("--disable-branches", type=str, default=None,
                        help="Comma-separated branches to disable: visual,text,structural")

    # Training
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr-backbone", type=float, default=1e-5)
    parser.add_argument("--lr-new", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--freeze-layers", type=int, default=8)
    parser.add_argument("--patience", type=int, default=7,
                        help="Early stopping patience (epochs)")
    parser.add_argument("--seed", type=int, default=42)

    # System
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--save-every", type=int, default=5)
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument("--amp", action="store_true",
                        help="Enable mixed precision training")

    args = parser.parse_args()

    setup_training_logging()

    logger.info("=" * 60)
    logger.info("DARK PATTERN DETECTION — MODEL TRAINING")
    logger.info("=" * 60)
    logger.info(f"Config: epochs={args.epochs}, batch={args.batch_size}, "
                f"lr_backbone={args.lr_backbone}, lr_new={args.lr_new}, seed={args.seed}")
    if args.disable_branches:
        logger.info(f"Ablation: disabled={args.disable_branches}")
    logger.info("")

    train(args)


if __name__ == "__main__":
    main()
