# dataset.py
# Phase 3: Multi-Source Dataset for Dark Pattern Detection
#
# Merges 2 data sources into a unified PyTorch Dataset:
#
#   1. OWN SCRAPED DATA (946 samples)
#      → All 3 modalities: screenshot, DOM text, structural features
#      → Labels from Phase 2 auto-labeler
#
#   2. YADA ET AL. (IEEE BigData 2022) (~3,600 samples)
#      → Text-only: balanced dark + non-dark pattern texts
#      → Includes Mathur/Princeton dark pattern strings + clean negatives
#      → Image & structural branches get zero tensors
#
# Combined: ~4,500 training samples

import csv
import json
import re
import logging
from pathlib import Path
from html.parser import HTMLParser

import torch
from torch.utils.data import Dataset, DataLoader, ConcatDataset
from torchvision import transforms
from PIL import Image

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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

NUM_STRUCTURAL_FEATURES = 25

IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
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


# ============================================================================
# HTML TEXT EXTRACTOR
# ============================================================================

class HTMLTextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "path", "meta", "link", "head"}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data):
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self):
        return " ".join(self.text_parts)


def extract_text_from_html(html_path, max_chars=5000):
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


# ============================================================================
# STRUCTURAL FEATURE EXTRACTION (from own scraped metadata)
# ============================================================================

def extract_structural_features(metadata):
    """Extract 25-dim feature vector from scraper metadata."""
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
    else:
        area_ratio = 1.0
    features.append(min(area_ratio, 10.0))

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

    def __init__(self, data_dir=None, label_dir=None, tokenizer=None, max_text_len=256):
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data" / "raw"
        self.label_dir = Path(label_dir) if label_dir else PROJECT_ROOT / "data" / "labeled"
        self.tokenizer = tokenizer
        self.max_text_len = max_text_len
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

        # Image
        try:
            image = IMAGE_TRANSFORM(Image.open(s["screenshot"]).convert("RGB"))
        except Exception:
            image = torch.zeros(3, 224, 224)

        # Text from DOM
        text = ""
        if s["dom"].exists():
            text = extract_text_from_html(s["dom"])
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
            except Exception:
                pass
        structural = torch.tensor(extract_structural_features(metadata), dtype=torch.float32)

        # Labels
        try:
            with open(s["label"]) as f:
                label_data = json.load(f)
        except Exception:
            label_data = {}
        labels = extract_labels_from_labeler(label_data)

        return {
            "image": image,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "structural": structural,
            "binary_label": torch.tensor([labels["binary"]], dtype=torch.float32),
            "type_labels": torch.tensor(labels["types"], dtype=torch.float32),
            "severity_label": torch.tensor([labels["severity"]], dtype=torch.long),
            "page_id": s["page_id"],
            "source": "own",
        }


# ============================================================================
# DATASET 2: YADA ET AL. (text-only, balanced dark + clean)
# Includes Mathur/Princeton dark pattern texts + clean negative samples
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
                    if len(row) < 2:
                        continue

                    text = row[0].strip()
                    if not text:
                        continue

                    # Label: 1 = dark pattern, 0 = clean
                    try:
                        is_dark = int(row[1]) == 1
                    except (ValueError, IndexError):
                        continue

                    # Type (if available, column 3+)
                    dp_type_raw = row[2].strip() if len(row) > 2 else ""
                    dp_type = DARK_PATTERN_TYPE_MAP.get(dp_type_raw,
                              DARK_PATTERN_TYPE_MAP.get(dp_type_raw.lower(), ""))

                    types = [0.0] * NUM_TYPES
                    if is_dark and dp_type and dp_type in TYPE_TO_IDX:
                        types[TYPE_TO_IDX[dp_type]] = 1.0

                    samples.append({
                        "text": text,
                        "binary": 1.0 if is_dark else 0.0,
                        "types": types,
                        "severity": SEVERITY_TO_IDX["medium"] if is_dark else SEVERITY_TO_IDX["none"],
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
            "page_id": f"yada_{idx}",
            "source": "yada",
        }


# ============================================================================
# COMBINED DATASET + DATALOADERS
# ============================================================================

class CombinedDarkPatternDataset(Dataset):
    """
    Wraps ConcatDataset to provide unified access to all 3 sources.
    Handles train/val splitting across the combined data.
    """

    def __init__(self, tokenizer=None, max_text_len=256, split="train",
                 split_ratio=0.8, seed=42, data_dir=None, label_dir=None,
                 use_yada=True):

        datasets = []

        # Source 1: Own scraped data (always included)
        own = OwnScrapedDataset(data_dir=data_dir, label_dir=label_dir,
                                tokenizer=tokenizer, max_text_len=max_text_len)
        if len(own) > 0:
            datasets.append(own)
            logger.info(f"  Own scraped data: {len(own)} samples")

        # Source 2: Yada (includes Mathur/Princeton texts + clean negatives)
        if use_yada:
            yada = YadaDataset(tokenizer=tokenizer, max_text_len=max_text_len)
            if len(yada) > 0:
                datasets.append(yada)

        if not datasets:
            logger.error("No datasets found! Check your data directories.")
            self.samples_list = []
            return

        # Combine all
        combined = ConcatDataset(datasets)
        total = len(combined)
        logger.info(f"  Combined total: {total} samples")

        # Split
        torch.manual_seed(seed)
        indices = torch.randperm(total).tolist()
        n_train = int(total * split_ratio)

        if split == "train":
            self.indices = indices[:n_train]
        else:
            self.indices = indices[n_train:]

        self.combined = combined
        logger.info(f"  Split [{split}]: {len(self.indices)} samples")

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        return self.combined[self.indices[idx]]


def create_dataloaders(tokenizer, batch_size=8, num_workers=2,
                       data_dir=None, label_dir=None,
                       use_yada=True):
    """
    Create train and validation dataloaders from all available sources.

    Args:
        tokenizer: HuggingFace RobertaTokenizer
        batch_size: Batch size
        num_workers: Dataloader workers
        data_dir: Override for data/raw/
        label_dir: Override for data/labeled/
        use_yada: Include Yada text dataset

    Returns:
        (train_loader, val_loader, dataset_info)
    """
    logger.info("Loading datasets...")

    train_dataset = CombinedDarkPatternDataset(
        tokenizer=tokenizer, split="train",
        data_dir=data_dir, label_dir=label_dir,
        use_yada=use_yada,
    )
    val_dataset = CombinedDarkPatternDataset(
        tokenizer=tokenizer, split="val",
        data_dir=data_dir, label_dir=label_dir,
        use_yada=use_yada,
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True,
    )

    dataset_info = {
        "num_train": len(train_dataset),
        "num_val": len(val_dataset),
        "num_types": NUM_TYPES,
        "num_severity": NUM_SEVERITY,
        "num_structural": NUM_STRUCTURAL_FEATURES,
        "type_names": DARK_PATTERN_TYPES,
        "severity_names": SEVERITY_LEVELS,
    }

    logger.info(f"Train: {dataset_info['num_train']} | Val: {dataset_info['num_val']}")
    return train_loader, val_loader, dataset_info
