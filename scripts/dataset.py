# dataset.py
# Phase 3: Multi-Source Dataset for Dark Pattern Detection
#
# Merges 2 data sources into a unified PyTorch Dataset:
#
#   1. OWN SCRAPED DATA (~1500 samples)
#      → All 3 modalities: screenshot, DOM text, structural features
#      → Labels from Phase 2 auto-labeler
#
#   2. YADA ET AL. (IEEE BigData 2022) (~2,300 samples)
#      → Text-only: balanced dark + non-dark pattern texts
#      → Includes Mathur/Princeton dark pattern strings + clean negatives
#      → Image & structural branches get zero tensors
#
# Features:
#   - Domain-level train/val/test split (no data leakage)
#   - WeightedRandomSampler (own data 2x weight over Yada)
#   - Confidence-weighted training support
#   - Train-time image augmentation

import copy
import csv
import json
import logging
import random
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from PIL import Image

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from scripts.utils import extract_html_text
except ImportError:
    from utils import extract_html_text


# ============================================================================
# CONSTANTS
# ============================================================================

DARK_PATTERN_TYPES = [
    "SCARCITY",
    "URGENCY",
    "SOCIAL_PROOF",
    "CONFIRMSHAMING",
    "MISDIRECTION",
    "HIDDEN_COSTS",
    "FORCED_ACTION",
    "SNEAKING",
    "OBSTRUCTION",
    "NAGGING",
    "INTERFACE_INTERFERENCE",
]
NUM_TYPES = len(DARK_PATTERN_TYPES)
TYPE_TO_IDX = {t: i for i, t in enumerate(DARK_PATTERN_TYPES)}

SEVERITY_LEVELS = ["none", "low", "medium", "high"]
NUM_SEVERITY = len(SEVERITY_LEVELS)
SEVERITY_TO_IDX = {s: i for i, s in enumerate(SEVERITY_LEVELS)}

NUM_STRUCTURAL_FEATURES = 24

# Training augmentation: conservative transforms for web screenshots
# No horizontal flip — flipped web screenshots reverse text direction and UI layout,
# creating unnatural images that don't resemble real websites
IMAGE_TRANSFORM_TRAIN = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Evaluation: deterministic transform
IMAGE_TRANSFORM_EVAL = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# Mapping from external dataset type names to our taxonomy
DARK_PATTERN_TYPE_MAP = {
    "Urgency": "URGENCY",
    "Scarcity": "SCARCITY",
    "Social Proof": "SOCIAL_PROOF",
    "Misdirection": "MISDIRECTION",
    "Forced Action": "FORCED_ACTION",
    "Sneaking": "SNEAKING",
    "Confirmshaming": "CONFIRMSHAMING",
    "Obstruction": "OBSTRUCTION",
    # Catch-all variations
    "urgency": "URGENCY",
    "scarcity": "SCARCITY",
    "social proof": "SOCIAL_PROOF",
    "social_proof": "SOCIAL_PROOF",
    "misdirection": "MISDIRECTION",
    "forced action": "FORCED_ACTION",
    "forced_action": "FORCED_ACTION",
    "sneaking": "SNEAKING",
    "confirmshaming": "CONFIRMSHAMING",
    "confirm shaming": "CONFIRMSHAMING",
    "obstruction": "OBSTRUCTION",
    "trick question": "MISDIRECTION",
    "hidden subscription": "SNEAKING",
    "hidden costs": "HIDDEN_COSTS",
    "bait and switch": "MISDIRECTION",
    "roach motel": "OBSTRUCTION",
    "privacy zuckering": "MISDIRECTION",
    "disguised ad": "MISDIRECTION",
    "friend spam": "FORCED_ACTION",
}

# Severity mapping for Yada text dataset (by dark pattern type)
TYPE_SEVERITY_MAP = {
    "HIDDEN_COSTS": "high",
    "SNEAKING": "high",
    "FORCED_ACTION": "high",
    "OBSTRUCTION": "high",
    "SCARCITY": "medium",
    "URGENCY": "medium",
    "MISDIRECTION": "medium",
    "INTERFACE_INTERFERENCE": "medium",
    "SOCIAL_PROOF": "low",
    "CONFIRMSHAMING": "low",
    "NAGGING": "low",
}


# ============================================================================
# DOMAIN-LEVEL SPLITTING (prevents data leakage between train/val/test)
# ============================================================================

def _extract_domain(label_path):
    """Extract domain from a label JSON file."""
    try:
        with open(label_path) as f:
            data = json.load(f)
        url = data.get("url", "")
        if not url:
            return "unknown"
        netloc = urlparse(url).netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc.startswith("www2."):
            netloc = netloc[5:]
        return netloc or "unknown"
    except Exception:
        return "unknown"


def _is_dark_category(label_path):
    """Check if a sample is from a dark-pattern-prone category."""
    clean_categories = {"government", "education", "nonprofit", "developer",
                        "ethical", "utility", "public_tools"}
    try:
        with open(label_path) as f:
            data = json.load(f)
        return data.get("category", "") not in clean_categories
    except Exception:
        return True


def domain_level_split(samples, train_ratio=0.70, val_ratio=0.15, seed=42):
    """
    Split samples by domain so no domain appears in multiple splits.
    Stratified by dark/clean category to maintain class balance.

    Returns:
        (train_indices, val_indices, test_indices)
    """
    domain_to_indices = defaultdict(list)
    domain_is_dark = {}
    for idx, sample in enumerate(samples):
        domain = _extract_domain(sample["label"])
        domain_to_indices[domain].append(idx)
        if domain not in domain_is_dark:
            domain_is_dark[domain] = _is_dark_category(sample["label"])

    dark_domains = [d for d in domain_to_indices if domain_is_dark.get(d, True)]
    clean_domains = [d for d in domain_to_indices if not domain_is_dark.get(d, True)]

    rng = random.Random(seed)
    rng.shuffle(dark_domains)
    rng.shuffle(clean_domains)

    def split_domain_list(domains):
        n = len(domains)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        return domains[:n_train], domains[n_train:n_train + n_val], domains[n_train + n_val:]

    dark_train, dark_val, dark_test = split_domain_list(dark_domains)
    clean_train, clean_val, clean_test = split_domain_list(clean_domains)

    train_indices, val_indices, test_indices = [], [], []
    for d in dark_train + clean_train:
        train_indices.extend(domain_to_indices[d])
    for d in dark_val + clean_val:
        val_indices.extend(domain_to_indices[d])
    for d in dark_test + clean_test:
        test_indices.extend(domain_to_indices[d])

    logger.info(f"  Domain split: {len(dark_domains)} dark + {len(clean_domains)} clean domains")
    logger.info(f"  Train: {len(train_indices)} samples ({len(dark_train)+len(clean_train)} domains)")
    logger.info(f"  Val:   {len(val_indices)} samples ({len(dark_val)+len(clean_val)} domains)")
    logger.info(f"  Test:  {len(test_indices)} samples ({len(dark_test)+len(clean_test)} domains)")

    return train_indices, val_indices, test_indices


# ============================================================================
# STRUCTURAL FEATURE EXTRACTION (from own scraped metadata)
# ============================================================================

def extract_structural_features(metadata):
    """Extract 24-dim feature vector from scraper metadata."""
    features = []
    ext = metadata.get("extraction", {}) or {}

    # Pattern counts (7)
    features.append(float(len(ext.get("scarcity", []))))
    features.append(float(len(ext.get("urgency", []))))
    features.append(float(len(ext.get("socialProof", []))))
    features.append(float(len(ext.get("confirmshaming", []))))
    features.append(float(len(ext.get("hiddenCosts", []))))
    features.append(float(len(ext.get("misdirection", []))))
    features.append(float(len(ext.get("forcedAction", []))))

    # UI element counts (5)
    features.append(float(len(ext.get("countdowns", []))))
    prechecked = ext.get("precheckedBoxes", [])
    suspicious = [b for b in prechecked if b.get("isSuspicious")]
    features.append(float(len(suspicious)))
    features.append(float(len(ext.get("modals", []))))
    features.append(float(len(ext.get("hiddenElements", []))))
    features.append(float(len(ext.get("cookieBanners", []))))

    # Button asymmetry (3)
    buttons = ext.get("buttons", [])
    pos_btns = [b for b in buttons if b.get("isPositive")]
    neg_btns = [b for b in buttons if b.get("isNegative")]
    features.append(float(len(pos_btns)))
    features.append(float(len(neg_btns)))
    if pos_btns and neg_btns:
        avg_pos = sum(b.get("area", 0) for b in pos_btns) / len(pos_btns)
        avg_neg = sum(b.get("area", 0) for b in neg_btns) / len(neg_btns)
        area_ratio = avg_pos / max(avg_neg, 1.0)
        # Only signal asymmetry when ratio is extreme enough to be manipulative
        # Below 2.0 is normal primary/secondary button hierarchy
        if area_ratio < 2.0:
            area_ratio = 0.0
        else:
            area_ratio = min(area_ratio, 5.0)
    else:
        area_ratio = 0.0
    features.append(area_ratio)

    # Page metadata (2)
    page_meta = ext.get("metadata", {}) or {}
    features.append(1.0 if page_meta.get("hasLoginWall") else 0.0)
    features.append(1.0 if page_meta.get("hasNewsletterPopup") else 0.0)

    # Price (1)
    prices = ext.get("prices", {}) or {}
    features.append(float(prices.get("discount", 0) or 0) / 100.0)

    # Temporal verification (1)
    v = metadata.get("verification", {}) or {}
    features.append(1.0 if (v.get("analysis") or {}).get("is_suspicious") else 0.0)

    # A/B test (1)
    ab = metadata.get("ab_test", {}) or {}
    features.append(1.0 if (ab.get("analysis") or {}).get("personalization_detected") else 0.0)

    # Interaction (2)
    intr = metadata.get("interaction", {}) or {}
    ia = intr.get("analysis", {}) or {}
    features.append(float(ia.get("total_triggered_popups", 0)))
    features.append(1.0 if ia.get("has_decline_guilt") else 0.0)

    # Session (2)
    sess = metadata.get("session", {}) or {}
    sa = sess.get("analysis", {}) or {}
    features.append(1.0 if sa.get("has_hidden_fees") else 0.0)
    features.append(1.0 if sa.get("has_checkout_dark_patterns") else 0.0)

    assert len(features) == NUM_STRUCTURAL_FEATURES
    return features


# ============================================================================
# LABEL EXTRACTION (from own auto-labeler output)
# ============================================================================

def extract_labels_from_labeler(label_data):
    """Convert Phase 2 labeler JSON into training targets."""
    label = label_data.get("label", {})

    binary = 1.0 if label.get("has_dark_patterns", False) else 0.0

    types = [0.0] * NUM_TYPES
    for dp in label.get("dark_patterns", []):
        dp_type = dp.get("type", "").upper()
        if dp_type in TYPE_TO_IDX:
            types[TYPE_TO_IDX[dp_type]] = 1.0

    severity_str = label.get("overall_severity", "none").lower()
    severity = SEVERITY_TO_IDX.get(severity_str, 0)

    return {"binary": binary, "types": types, "severity": severity}


# ============================================================================
# DATASET 1: OWN SCRAPED DATA (all 3 modalities)
# ============================================================================

class OwnScrapedDataset(Dataset):
    """
    Loads our own scraped + labeled data.
    Has all 3 modalities: screenshot, DOM text, structural features.
    """

    def __init__(self, data_dir=None, label_dir=None, tokenizer=None,
                 max_text_len=256, image_transform=None):
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data" / "raw"
        self.label_dir = Path(label_dir) if label_dir else PROJECT_ROOT / "data" / "labeled"
        self.tokenizer = tokenizer
        self.max_text_len = max_text_len
        self.image_transform = image_transform or IMAGE_TRANSFORM_EVAL
        self.samples = self._collect()

    def _collect(self):
        samples = []
        if not self.label_dir.exists():
            return samples

        for label_file in sorted(self.label_dir.glob("*.json")):
            page_id = label_file.stem
            if page_id == "summary":
                continue

            screenshot = self.data_dir / "screenshots" / f"{page_id}.png"
            if not screenshot.exists():
                continue

            samples.append({
                "page_id": page_id,
                "screenshot": screenshot,
                "metadata": self.data_dir / "metadata" / f"{page_id}.json",
                "dom": self.data_dir / "dom" / f"{page_id}.html",
                "label": label_file,
            })
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        # Image (with augmentation for training)
        try:
            image = self.image_transform(Image.open(s["screenshot"]).convert("RGB"))
        except Exception:
            image = torch.zeros(3, 224, 224)

        # Text from DOM
        text = ""
        if s["dom"].exists():
            text = extract_html_text(s["dom"])
        if not text:
            text = "No page text available."

        if self.tokenizer:
            enc = self.tokenizer(text, max_length=self.max_text_len, padding="max_length",
                                 truncation=True, return_tensors="pt")
            input_ids = enc["input_ids"].squeeze(0)
            attention_mask = enc["attention_mask"].squeeze(0)
        else:
            input_ids = torch.zeros(self.max_text_len, dtype=torch.long)
            attention_mask = torch.zeros(self.max_text_len, dtype=torch.long)

        # Structural features
        metadata = {}
        if s["metadata"].exists():
            try:
                with open(s["metadata"]) as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata for {s['page_id']}: {e}")
        structural = torch.tensor(extract_structural_features(metadata), dtype=torch.float32)

        # Labels
        try:
            with open(s["label"]) as f:
                label_data = json.load(f)
        except Exception:
            label_data = {}
        labels = extract_labels_from_labeler(label_data)

        # Confidence from ensemble labeler
        confidence = label_data.get("label", {}).get("confidence", 0.7)

        return {
            "image": image,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "structural": structural,
            "binary_label": torch.tensor([labels["binary"]], dtype=torch.float32),
            "type_labels": torch.tensor(labels["types"], dtype=torch.float32),
            "severity_label": torch.tensor([labels["severity"]], dtype=torch.long),
            "confidence": torch.tensor([confidence], dtype=torch.float32),
            "page_id": s["page_id"],
            "source": "own",
        }


# ============================================================================
# DATASET 2: YADA ET AL. (text-only, balanced dark + clean)
# ============================================================================

class YadaDataset(Dataset):
    """
    Yada et al. IEEE BigData 2022 — balanced dark + non-dark texts.
    Text-only — image and structural branches get zeros.
    TSV format: text \\t label (1=dark, 0=clean) \\t type
    """

    def __init__(self, data_dir=None, tokenizer=None, max_text_len=256):
        self.tokenizer = tokenizer
        self.max_text_len = max_text_len
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data" / "external" / "yada"
        self.samples = self._load()

    def _load(self):
        samples = []
        tsv_file = self.data_dir / "dataset.tsv"

        if not tsv_file.exists():
            return samples

        try:
            with open(tsv_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                header = next(reader, None)  # skip header

                for row in reader:
                    if len(row) < 3:  # Need at least page_id, text, label
                        continue

                    text = row[1].strip()  # Text is in column 2 (index 1)
                    if not text:
                        continue

                    # Label: 1 = dark pattern, 0 = clean (column 3, index 2)
                    try:
                        is_dark = int(row[2]) == 1
                    except (ValueError, IndexError):
                        continue

                    # Type (if available, column 4, index 3)
                    dp_type_raw = row[3].strip() if len(row) > 3 else ""
                    dp_type = DARK_PATTERN_TYPE_MAP.get(dp_type_raw,
                              DARK_PATTERN_TYPE_MAP.get(dp_type_raw.lower(), ""))

                    types = [0.0] * NUM_TYPES
                    if is_dark and dp_type and dp_type in TYPE_TO_IDX:
                        types[TYPE_TO_IDX[dp_type]] = 1.0

                    # Severity by type (not hardcoded "medium")
                    if is_dark and dp_type:
                        sev_str = TYPE_SEVERITY_MAP.get(dp_type, "medium")
                    elif is_dark:
                        sev_str = "medium"
                    else:
                        sev_str = "none"

                    samples.append({
                        "text": text,
                        "binary": 1.0 if is_dark else 0.0,
                        "types": types,
                        "severity": SEVERITY_TO_IDX[sev_str],
                    })
        except Exception as e:
            logger.warning(f"Error reading Yada TSV: {e}")

        if samples:
            n_dark = sum(1 for s in samples if s["binary"] == 1.0)
            n_clean = len(samples) - n_dark
            logger.info(f"Yada dataset: {len(samples)} texts ({n_dark} dark, {n_clean} clean)")
        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]

        image = torch.zeros(3, 224, 224)

        if self.tokenizer:
            enc = self.tokenizer(s["text"], max_length=self.max_text_len, padding="max_length",
                                 truncation=True, return_tensors="pt")
            input_ids = enc["input_ids"].squeeze(0)
            attention_mask = enc["attention_mask"].squeeze(0)
        else:
            input_ids = torch.zeros(self.max_text_len, dtype=torch.long)
            attention_mask = torch.zeros(self.max_text_len, dtype=torch.long)

        structural = torch.zeros(NUM_STRUCTURAL_FEATURES, dtype=torch.float32)

        return {
            "image": image,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "structural": structural,
            "binary_label": torch.tensor([s["binary"]], dtype=torch.float32),
            "type_labels": torch.tensor(s["types"], dtype=torch.float32),
            "severity_label": torch.tensor([s["severity"]], dtype=torch.long),
            "confidence": torch.tensor([1.0], dtype=torch.float32),
            "page_id": f"yada_{idx}",
            "source": "yada",
        }


# ============================================================================
# COMBINED DATASET + DATALOADERS
# ============================================================================

class CombinedDarkPatternDataset(Dataset):
    """
    Combines own scraped data with Yada text data.
    Supports domain-level splitting and weighted sampling.
    """

    def __init__(self, tokenizer=None, max_text_len=256, split="train",
                 seed=42, data_dir=None, label_dir=None,
                 use_yada=True, image_transform=None,
                 _own_indices=None, _own_dataset=None, _yada_dataset=None):

        if _own_dataset is not None:
            own = _own_dataset
            own_indices = _own_indices or list(range(len(own)))
        else:
            own = OwnScrapedDataset(
                data_dir=data_dir, label_dir=label_dir,
                tokenizer=tokenizer, max_text_len=max_text_len,
                image_transform=image_transform,
            )
            own_indices = list(range(len(own)))

        self.own_dataset = own
        self.own_indices = own_indices

        # Yada: only add to train split
        self.yada_dataset = None
        self.yada_indices = []
        if use_yada and split == "train":
            if _yada_dataset is not None:
                yada = _yada_dataset
            else:
                yada = YadaDataset(tokenizer=tokenizer, max_text_len=max_text_len)
            if len(yada) > 0:
                self.yada_dataset = yada
                self.yada_indices = list(range(len(yada)))
                logger.info(f"  Yada dataset: {len(yada)} samples (train only)")

        # Build index map: (source, idx_in_source)
        self._index_map = []
        for idx in self.own_indices:
            self._index_map.append(("own", idx))
        for idx in self.yada_indices:
            self._index_map.append(("yada", idx))

        logger.info(f"  Split [{split}]: {len(self._index_map)} samples "
                    f"({len(self.own_indices)} own + {len(self.yada_indices)} yada)")

    def __len__(self):
        return len(self._index_map)

    def __getitem__(self, idx):
        source, source_idx = self._index_map[idx]
        if source == "own":
            return self.own_dataset[source_idx]
        else:
            return self.yada_dataset[source_idx]

    def get_source_weights(self):
        """Return per-sample weights for WeightedRandomSampler."""
        weights = []
        for source, _ in self._index_map:
            weights.append(2.0 if source == "own" else 1.0)
        return weights


def create_dataloaders(tokenizer, batch_size=8, num_workers=2,
                       data_dir=None, label_dir=None,
                       use_yada=True, seed=42):
    """
    Create train, val, and test dataloaders with domain-level splitting.

    Returns:
        (train_loader, val_loader, test_loader, dataset_info)
    """
    logger.info("Loading datasets...")

    # Build own dataset once with eval transform (for splitting)
    own_full = OwnScrapedDataset(
        data_dir=data_dir, label_dir=label_dir,
        tokenizer=tokenizer, image_transform=IMAGE_TRANSFORM_EVAL,
    )
    logger.info(f"  Own scraped data: {len(own_full)} samples")

    if len(own_full) == 0:
        logger.error("No own data found!")
        empty_info = {"num_train": 0, "num_val": 0, "num_test": 0,
                      "num_types": NUM_TYPES, "num_severity": NUM_SEVERITY,
                      "num_structural": NUM_STRUCTURAL_FEATURES,
                      "type_names": DARK_PATTERN_TYPES, "severity_names": SEVERITY_LEVELS}
        return None, None, None, empty_info

    # Domain-level split (indices valid against own_full.samples)
    train_idx, val_idx, test_idx = domain_level_split(own_full.samples, seed=seed)

    # Train: shallow-copy own_full to share the SAME samples list (indices aligned),
    # then swap image_transform for augmentation. Avoids re-scanning the filesystem
    # which could yield a different sample order and silently leak val/test into train.
    own_train = copy.copy(own_full)
    own_train.image_transform = IMAGE_TRANSFORM_TRAIN
    assert own_train.samples is own_full.samples, "train/full must share samples list"

    train_dataset = CombinedDarkPatternDataset(
        tokenizer=tokenizer, split="train", seed=seed,
        use_yada=use_yada,
        _own_indices=train_idx, _own_dataset=own_train,
    )

    # Val: own data only, no augmentation
    val_dataset = CombinedDarkPatternDataset(
        tokenizer=tokenizer, split="val", seed=seed,
        use_yada=False,
        _own_indices=val_idx, _own_dataset=own_full,
    )

    # Test: own data only, no augmentation
    test_dataset = CombinedDarkPatternDataset(
        tokenizer=tokenizer, split="test", seed=seed,
        use_yada=False,
        _own_indices=test_idx, _own_dataset=own_full,
    )

    # Weighted sampler for training (own data 2x, Yada 1x).
    # num_samples = len(train_dataset) fixes per-epoch step count. If gradient
    # accumulation or schedulers that depend on total optimizer steps are added,
    # scale this accordingly (effective_steps = num_samples / batch_size / accum).
    train_weights = train_dataset.get_source_weights()
    train_sampler = WeightedRandomSampler(
        weights=train_weights,
        num_samples=len(train_dataset),
        replacement=True,
    )

    # persistent_workers keeps worker pool alive across epochs, avoiding repeated
    # tokenizer import overhead. Only valid when num_workers > 0.
    persistent = num_workers > 0

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, sampler=train_sampler,
        num_workers=num_workers, pin_memory=True, drop_last=True,
        persistent_workers=persistent,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
        persistent_workers=persistent,
    )
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
        persistent_workers=persistent,
    )

    dataset_info = {
        "num_train": len(train_dataset),
        "num_val": len(val_dataset),
        "num_test": len(test_dataset),
        "num_own_train": len(train_idx),
        "num_yada_train": len(train_dataset) - len(train_idx),
        "num_types": NUM_TYPES,
        "num_severity": NUM_SEVERITY,
        "num_structural": NUM_STRUCTURAL_FEATURES,
        "type_names": DARK_PATTERN_TYPES,
        "severity_names": SEVERITY_LEVELS,
    }

    logger.info(f"Train: {dataset_info['num_train']} ({dataset_info['num_own_train']} own + "
                f"{dataset_info['num_yada_train']} yada) | Val: {dataset_info['num_val']} | "
                f"Test: {dataset_info['num_test']}")
    return train_loader, val_loader, test_loader, dataset_info
