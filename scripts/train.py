# train.py
# Phase 3: Training Pipeline for Dark Pattern Detection Model
#
# Trains the multi-modal model (ViT + RoBERTa + MLP + attention fusion)
# with multi-task outputs (binary + multi-label + severity).
#
# SETUP:
#   pip install torch torchvision transformers scikit-learn Pillow
#
# USAGE:
#   python train.py                          # Train with defaults
#   python train.py --epochs 30 --batch 16   # Custom settings
#   python train.py --resume checkpoint.pt   # Resume from checkpoint
#
# For Google Colab:
#   1. Upload data/ folder to Google Drive
#   2. Mount drive in Colab
#   3. Set --data-dir and --label-dir to your Drive paths
#   4. Run this script

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingWarmRestarts
from transformers import RobertaTokenizer

# Local imports
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
# METRICS
# ============================================================================

def compute_metrics(all_preds, all_labels, threshold=0.5):
    """
    Compute evaluation metrics for all three tasks.

    Args:
        all_preds: dict with binary_logits, type_logits, severity_logits (concatenated tensors)
        all_labels: dict with binary, types, severity (concatenated tensors)
        threshold: Threshold for binary/multi-label predictions

    Returns:
        dict with accuracy, F1, precision, recall per task
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

    # --- Multi-label metrics (per-type and macro-average) ---
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

        metrics[f"type_{type_name}_f1"] = f1
        if (tp_i + fp_i + fn_i) > 0:  # only include types that actually appear
            type_f1s.append(f1)

    metrics["type_macro_f1"] = sum(type_f1s) / max(len(type_f1s), 1)

    # Sample-level metrics for multi-label
    correct_per_sample = (type_pred == type_true).float().mean(dim=1)
    metrics["type_sample_accuracy"] = correct_per_sample.mean().item()

    # --- Severity metrics ---
    severity_pred = all_preds["severity"].cpu().argmax(dim=1)
    severity_true = all_labels["severity"].cpu().squeeze()

    metrics["severity_accuracy"] = (severity_pred == severity_true).float().mean().item()

    # Per-class severity accuracy
    for i, sev_name in enumerate(SEVERITY_LEVELS):
        mask = severity_true == i
        if mask.sum() > 0:
            metrics[f"severity_{sev_name}_acc"] = (severity_pred[mask] == i).float().mean().item()

    return metrics


# ============================================================================
# TRAINING STEP
# ============================================================================

def train_one_epoch(model, train_loader, criterion, optimizer, device, epoch):
    """Run one training epoch."""
    model.train()

    total_loss = 0.0
    loss_components = {"binary": 0.0, "types": 0.0, "severity": 0.0}
    num_batches = 0

    for batch_idx, batch in enumerate(train_loader):
        # Move to device
        image = batch["image"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        structural = batch["structural"].to(device)
        binary_label = batch["binary_label"].to(device)
        type_labels = batch["type_labels"].to(device)
        severity_label = batch["severity_label"].to(device)

        # Forward
        outputs = model(image, input_ids, attention_mask, structural)

        # Loss
        loss, loss_dict = criterion(
            outputs["binary_logits"], outputs["type_logits"], outputs["severity_logits"],
            binary_label, type_labels, severity_label,
        )

        # Backward
        optimizer.zero_grad()
        loss.backward()

        # Gradient clipping
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
def validate(model, val_loader, criterion, device):
    """Run validation and compute metrics."""
    model.eval()

    total_loss = 0.0
    num_batches = 0

    all_preds = {"binary": [], "types": [], "severity": []}
    all_labels = {"binary": [], "types": [], "severity": []}

    for batch in val_loader:
        image = batch["image"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        structural = batch["structural"].to(device)
        binary_label = batch["binary_label"].to(device)
        type_labels = batch["type_labels"].to(device)
        severity_label = batch["severity_label"].to(device)

        outputs = model(image, input_ids, attention_mask, structural)

        loss, loss_dict = criterion(
            outputs["binary_logits"], outputs["type_logits"], outputs["severity_logits"],
            binary_label, type_labels, severity_label,
        )

        total_loss += loss_dict["total"]
        num_batches += 1

        # Collect predictions
        all_preds["binary"].append(outputs["binary_logits"])
        all_preds["types"].append(outputs["type_logits"])
        all_preds["severity"].append(outputs["severity_logits"])

        all_labels["binary"].append(binary_label)
        all_labels["types"].append(type_labels)
        all_labels["severity"].append(severity_label)

    # Concatenate all batches
    for key in all_preds:
        all_preds[key] = torch.cat(all_preds[key], dim=0)
        all_labels[key] = torch.cat(all_labels[key], dim=0)

    avg_loss = total_loss / max(num_batches, 1)
    metrics = compute_metrics(all_preds, all_labels)

    return avg_loss, metrics


# ============================================================================
# CHECKPOINT
# ============================================================================

def save_checkpoint(model, optimizer, scheduler, criterion, epoch, metrics, path):
    """Save training checkpoint."""
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
        "criterion_state_dict": criterion.state_dict(),
        "metrics": metrics,
        "timestamp": datetime.now().isoformat(),
    }
    torch.save(checkpoint, path)
    logger.info(f"  Checkpoint saved: {path}")


def load_checkpoint(path, model, optimizer=None, scheduler=None, criterion=None):
    """Load training checkpoint."""
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
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
    """Full training pipeline."""

    # --- Setup ---
    device = torch.device("cuda" if torch.cuda.is_available() else
                          "mps" if torch.backends.mps.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Tokenizer ---
    logger.info("Loading RoBERTa tokenizer...")
    tokenizer = RobertaTokenizer.from_pretrained("roberta-base")

    # --- Data ---
    logger.info("Creating dataloaders...")
    train_loader, val_loader, dataset_info = create_dataloaders(
        tokenizer=tokenizer,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        data_dir=args.data_dir,
        label_dir=args.label_dir,
        use_yada=not args.no_yada,
    )

    if dataset_info["num_train"] == 0:
        logger.error("No training data found. Check data_dir and label_dir paths.")
        sys.exit(1)

    # --- Model ---
    logger.info("Building model...")
    model = DarkPatternDetector(
        num_structural_features=NUM_STRUCTURAL_FEATURES,
        num_types=NUM_TYPES,
        num_severity=NUM_SEVERITY,
        freeze_backbone_layers=args.freeze_layers,
        dropout=args.dropout,
    )

    param_info = model.get_trainable_params()
    logger.info(f"Parameters: {param_info['total']:,} total, "
                f"{param_info['trainable']:,} trainable ({param_info['trainable_pct']}%)")

    model = model.to(device)

    # --- Loss ---
    criterion = MultiTaskLoss().to(device)

    # --- Optimizer (differential learning rates) ---
    param_groups = model.get_param_groups(
        lr_backbone=args.lr_backbone,
        lr_new=args.lr_new,
    )
    # Add criterion parameters (learnable task weights)
    param_groups.append({"params": criterion.parameters(), "lr": args.lr_new})

    optimizer = AdamW(param_groups, weight_decay=args.weight_decay)

    # --- Scheduler ---
    scheduler = CosineAnnealingWarmRestarts(
        optimizer,
        T_0=args.epochs // 3 + 1,    # restart period
        T_mult=2,                      # double period after each restart
        eta_min=1e-7,
    )

    # --- Resume from checkpoint ---
    start_epoch = 0
    if args.resume:
        start_epoch = load_checkpoint(
            args.resume, model, optimizer, scheduler, criterion
        ) + 1
        logger.info(f"Resuming from epoch {start_epoch}")

    # --- Training log ---
    training_log = {
        "args": vars(args),
        "dataset": dataset_info,
        "params": param_info,
        "device": str(device),
        "epochs": [],
    }

    best_val_f1 = 0.0

    # --- Training loop ---
    logger.info(f"\nStarting training for {args.epochs} epochs...")
    logger.info(f"Train: {dataset_info['num_train']} | Val: {dataset_info['num_val']}")
    logger.info(f"Batch size: {args.batch_size} | LR backbone: {args.lr_backbone} | LR new: {args.lr_new}")
    logger.info("")

    for epoch in range(start_epoch, args.epochs):
        epoch_start = time.time()

        # Train
        logger.info(f"Epoch {epoch + 1}/{args.epochs}")
        train_loss, train_components = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch + 1
        )

        # Validate
        val_loss, val_metrics = validate(model, val_loader, criterion, device)

        # Step scheduler
        scheduler.step()

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
        )
        logger.info(
            f"  Types:  macro_f1={val_metrics['type_macro_f1']:.3f} "
            f"sample_acc={val_metrics['type_sample_accuracy']:.3f}"
        )
        logger.info(
            f"  Severity: acc={val_metrics['severity_accuracy']:.3f}"
        )

        # Save to training log
        epoch_log = {
            "epoch": epoch + 1,
            "train_loss": train_loss,
            "train_components": train_components,
            "val_loss": val_loss,
            "val_metrics": val_metrics,
            "epoch_time": epoch_time,
            "lr": optimizer.param_groups[0]["lr"],
        }
        training_log["epochs"].append(epoch_log)

        # Save best model
        current_f1 = val_metrics["binary_f1"]
        if current_f1 > best_val_f1:
            best_val_f1 = current_f1
            save_checkpoint(
                model, optimizer, scheduler, criterion, epoch,
                val_metrics, output_dir / "best_model.pt"
            )
            logger.info(f"  New best model! Binary F1: {best_val_f1:.4f}")

        # Save periodic checkpoint
        if (epoch + 1) % args.save_every == 0:
            save_checkpoint(
                model, optimizer, scheduler, criterion, epoch,
                val_metrics, output_dir / f"checkpoint_epoch{epoch + 1}.pt"
            )

    # --- Final save ---
    save_checkpoint(
        model, optimizer, scheduler, criterion, args.epochs - 1,
        val_metrics, output_dir / "final_model.pt"
    )

    # Save training log
    log_path = output_dir / "training_log.json"
    with open(log_path, "w") as f:
        json.dump(training_log, f, indent=2, default=str)
    logger.info(f"\nTraining log saved to {log_path}")

    # --- Print final summary ---
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Best Binary F1: {best_val_f1:.4f}")
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
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Path to data/raw/ (default: auto-detect)")
    parser.add_argument("--label-dir", type=str, default=None,
                        help="Path to data/labeled/ (default: auto-detect)")
    parser.add_argument("--output-dir", type=str,
                        default=str(PROJECT_ROOT / "models"),
                        help="Where to save model checkpoints")

    # External datasets
    parser.add_argument("--no-yada", action="store_true",
                        help="Exclude Yada et al. text dataset")

    # Training
    parser.add_argument("--epochs", type=int, default=20, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr-backbone", type=float, default=1e-5,
                        help="Learning rate for pre-trained ViT/RoBERTa layers")
    parser.add_argument("--lr-new", type=float, default=1e-4,
                        help="Learning rate for new layers (fusion, heads, structural)")
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--dropout", type=float, default=0.2)
    parser.add_argument("--freeze-layers", type=int, default=8,
                        help="Freeze first N layers of ViT/RoBERTa (out of 12)")

    # System
    parser.add_argument("--num-workers", type=int, default=2,
                        help="Dataloader workers")
    parser.add_argument("--save-every", type=int, default=5,
                        help="Save checkpoint every N epochs")
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to checkpoint to resume from")

    args = parser.parse_args()

    setup_training_logging()

    logger.info("=" * 60)
    logger.info("DARK PATTERN DETECTION — MODEL TRAINING")
    logger.info("=" * 60)
    logger.info(f"Config: epochs={args.epochs}, batch={args.batch_size}, "
                f"lr_backbone={args.lr_backbone}, lr_new={args.lr_new}")
    logger.info(f"Frozen layers: {args.freeze_layers}/12")
    logger.info("")

    train(args)


if __name__ == "__main__":
    main()
