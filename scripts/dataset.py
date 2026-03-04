import json
import re
import logging
from pathlib import Path
from html.parser import HTMLParser

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ============================================================================
# CONSTANTS
# ============================================================================

# Dark pattern types — maps to multi-label vector indices
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

# Severity levels — maps to class indices for classification
SEVERITY_LEVELS = ["none", "low", "medium", "high"]
NUM_SEVERITY = len(SEVERITY_LEVELS)
SEVERITY_TO_IDX = {s: i for i, s in enumerate(SEVERITY_LEVELS)}

# Number of hand-crafted structural features
NUM_STRUCTURAL_FEATURES = 25

# Image transforms for ViT (224x224, ImageNet normalization)
IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


# ============================================================================
# HTML TEXT EXTRACTOR (same as labeler.py)
# ============================================================================

class HTMLTextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping script/style/hidden tags."""

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
    """Extract visible text from an HTML file."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] if len(text) > max_chars else text
    except Exception:
        return ""


# ============================================================================
# STRUCTURAL FEATURE EXTRACTION
# Extracts numeric features from the scraper's metadata JSON
# ============================================================================

def extract_structural_features(metadata):
    """
    Extract a fixed-length numeric feature vector from scraper metadata.

    These features capture the structural/behavioral signals the scraper detected,
    giving the model information beyond what's visible in the screenshot or text.

    Returns:
        list: 25 float values (NUM_STRUCTURAL_FEATURES)
    """
    features = []
    ext = metadata.get("extraction", {}) or {}

    # --- Pattern counts (7 features) ---
    features.append(float(len(ext.get("scarcity", []))))
    features.append(float(len(ext.get("urgency", []))))
    features.append(float(len(ext.get("socialProof", []))))
    features.append(float(len(ext.get("confirmshaming", []))))
    features.append(float(len(ext.get("hiddenCosts", []))))
    features.append(float(len(ext.get("misdirection", []))))
    features.append(float(len(ext.get("forcedAction", []))))

    # --- UI element counts (5 features) ---
    features.append(float(len(ext.get("countdowns", []))))
    prechecked = ext.get("precheckedBoxes", [])
    suspicious_prechecked = [b for b in prechecked if b.get("isSuspicious")]
    features.append(float(len(suspicious_prechecked)))
    features.append(float(len(ext.get("modals", []))))
    features.append(float(len(ext.get("hiddenElements", []))))
    features.append(float(len(ext.get("cookieBanners", []))))

    # --- Button asymmetry (3 features) ---
    buttons = ext.get("buttons", [])
    positive_btns = [b for b in buttons if b.get("isPositive")]
    negative_btns = [b for b in buttons if b.get("isNegative")]
    features.append(float(len(positive_btns)))
    features.append(float(len(negative_btns)))

    # Area ratio: avg positive button area / avg negative button area
    if positive_btns and negative_btns:
        avg_pos = sum(b.get("area", 0) for b in positive_btns) / len(positive_btns)
        avg_neg = sum(b.get("area", 0) for b in negative_btns) / len(negative_btns)
        area_ratio = avg_pos / max(avg_neg, 1.0)
    else:
        area_ratio = 1.0
    features.append(min(area_ratio, 10.0))  # cap at 10 to avoid outliers

    # --- Page metadata (2 features) ---
    page_meta = ext.get("metadata", {}) or {}
    features.append(1.0 if page_meta.get("hasLoginWall") else 0.0)
    features.append(1.0 if page_meta.get("hasNewsletterPopup") else 0.0)

    # --- Price info (1 feature) ---
    prices = ext.get("prices", {}) or {}
    discount = prices.get("discount", 0) or 0
    features.append(float(discount) / 100.0)  # normalize to 0-1

    # --- Temporal verification (1 feature) ---
    verification = metadata.get("verification", {}) or {}
    v_analysis = verification.get("analysis", {}) or {}
    features.append(1.0 if v_analysis.get("is_suspicious") else 0.0)

    # --- A/B test detection (1 feature) ---
    ab_test = metadata.get("ab_test", {}) or {}
    ab_analysis = ab_test.get("analysis", {}) or {}
    features.append(1.0 if ab_analysis.get("personalization_detected") else 0.0)

    # --- Interaction detection (2 features) ---
    interaction = metadata.get("interaction", {}) or {}
    int_analysis = interaction.get("analysis", {}) or {}
    features.append(float(int_analysis.get("total_triggered_popups", 0)))
    features.append(1.0 if int_analysis.get("has_decline_guilt") else 0.0)

    # --- Session simulation (2 features) ---
    session = metadata.get("session", {}) or {}
    s_analysis = session.get("analysis", {}) or {}
    features.append(1.0 if s_analysis.get("has_hidden_fees") else 0.0)
    features.append(1.0 if s_analysis.get("has_checkout_dark_patterns") else 0.0)

    # --- Screenshot diff (1 feature) ---
    diff_data = metadata.get("screenshot_diff", {}) or {}
    d_analysis = diff_data.get("analysis", {}) or {}
    features.append(1.0 if d_analysis.get("significant_change") else 0.0)

    assert len(features) == NUM_STRUCTURAL_FEATURES, (
        f"Expected {NUM_STRUCTURAL_FEATURES} features, got {len(features)}"
    )

    return features


# ============================================================================
# LABEL EXTRACTION
# Converts labeler JSON output into training targets
# ============================================================================

def extract_labels(label_data):
    """
    Convert a label JSON into training targets.

    Returns:
        dict with:
            binary: float (0.0 or 1.0)
            types: list of floats, length 11 (multi-label)
            severity: int (0-3, class index)
    """
    label = label_data.get("label", {})

    # Binary: has dark patterns?
    binary = 1.0 if label.get("has_dark_patterns", False) else 0.0

    # Multi-label: which types are present?
    types = [0.0] * NUM_TYPES
    for dp in label.get("dark_patterns", []):
        dp_type = dp.get("type", "").upper()
        if dp_type in TYPE_TO_IDX:
            types[TYPE_TO_IDX[dp_type]] = 1.0

    # Severity: overall severity class
    severity_str = label.get("overall_severity", "none").lower()
    severity = SEVERITY_TO_IDX.get(severity_str, 0)

    return {
        "binary": binary,
        "types": types,
        "severity": severity,
    }


# ============================================================================
# MAIN DATASET CLASS
# ============================================================================

class DarkPatternDataset(Dataset):
    """
    Multi-modal dataset for dark pattern detection.

    Each sample contains:
        - image: Tensor [3, 224, 224] — screenshot for ViT
        - input_ids: Tensor [max_len] — tokenized DOM text for RoBERTa
        - attention_mask: Tensor [max_len] — attention mask for RoBERTa
        - structural: Tensor [25] — hand-crafted features from metadata
        - binary_label: Tensor [1] — has dark patterns (0/1)
        - type_labels: Tensor [11] — multi-label dark pattern types
        - severity_label: Tensor [1] — severity class (0-3)
    """

    def __init__(self, data_dir=None, label_dir=None, tokenizer=None, max_text_len=256,
                 split="train", split_ratio=0.8, seed=42):
        """
        Args:
            data_dir: Path to data/raw/ (screenshots, dom, metadata)
            label_dir: Path to data/labeled/
            tokenizer: HuggingFace tokenizer (RobertaTokenizer)
            max_text_len: Max token length for text input
            split: "train" or "val"
            split_ratio: Fraction of data for training
            seed: Random seed for reproducible splits
        """
        self.data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data" / "raw"
        self.label_dir = Path(label_dir) if label_dir else PROJECT_ROOT / "data" / "labeled"
        self.tokenizer = tokenizer
        self.max_text_len = max_text_len

        # Collect all valid samples (must have screenshot + metadata + label)
        self.samples = self._collect_samples()

        # Split into train/val
        torch.manual_seed(seed)
        n_total = len(self.samples)
        indices = torch.randperm(n_total).tolist()
        n_train = int(n_total * split_ratio)

        if split == "train":
            self.samples = [self.samples[i] for i in indices[:n_train]]
        elif split == "val":
            self.samples = [self.samples[i] for i in indices[n_train:]]

        logger.info(f"Dataset [{split}]: {len(self.samples)} samples")

    def _collect_samples(self):
        """Find all samples that have screenshot + metadata + label."""
        samples = []

        for label_file in sorted(self.label_dir.glob("*.json")):
            page_id = label_file.stem
            if page_id == "summary":
                continue

            screenshot_path = self.data_dir / "screenshots" / f"{page_id}.png"
            metadata_path = self.data_dir / "metadata" / f"{page_id}.json"
            dom_path = self.data_dir / "dom" / f"{page_id}.html"

            # Screenshot and label are required
            if not screenshot_path.exists() or not label_file.exists():
                continue

            samples.append({
                "page_id": page_id,
                "screenshot_path": screenshot_path,
                "metadata_path": metadata_path if metadata_path.exists() else None,
                "dom_path": dom_path if dom_path.exists() else None,
                "label_path": label_file,
            })

        return samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        # --- 1. Load and transform screenshot ---
        try:
            img = Image.open(sample["screenshot_path"]).convert("RGB")
            image = IMAGE_TRANSFORM(img)
        except Exception:
            # Fallback: blank image
            image = torch.zeros(3, 224, 224)

        # --- 2. Extract text from DOM ---
        text = ""
        if sample["dom_path"]:
            text = extract_text_from_html(sample["dom_path"])
        if not text:
            text = "No page text available."

        # Tokenize
        if self.tokenizer:
            encoding = self.tokenizer(
                text,
                max_length=self.max_text_len,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            input_ids = encoding["input_ids"].squeeze(0)
            attention_mask = encoding["attention_mask"].squeeze(0)
        else:
            # Placeholder if no tokenizer (for testing)
            input_ids = torch.zeros(self.max_text_len, dtype=torch.long)
            attention_mask = torch.zeros(self.max_text_len, dtype=torch.long)

        # --- 3. Extract structural features from metadata ---
        metadata = {}
        if sample["metadata_path"]:
            try:
                with open(sample["metadata_path"], "r") as f:
                    metadata = json.load(f)
            except Exception:
                pass
        structural = torch.tensor(extract_structural_features(metadata), dtype=torch.float32)

        # --- 4. Load labels ---
        try:
            with open(sample["label_path"], "r") as f:
                label_data = json.load(f)
        except Exception:
            label_data = {}

        labels = extract_labels(label_data)
        binary_label = torch.tensor([labels["binary"]], dtype=torch.float32)
        type_labels = torch.tensor(labels["types"], dtype=torch.float32)
        severity_label = torch.tensor([labels["severity"]], dtype=torch.long)

        return {
            "image": image,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "structural": structural,
            "binary_label": binary_label,
            "type_labels": type_labels,
            "severity_label": severity_label,
            "page_id": sample["page_id"],
        }


# ============================================================================
# DATALOADER HELPER
# ============================================================================

def create_dataloaders(tokenizer, batch_size=8, num_workers=2, data_dir=None, label_dir=None):
    """
    Create train and validation dataloaders.

    Args:
        tokenizer: HuggingFace RobertaTokenizer
        batch_size: Batch size for training
        num_workers: Number of data loading workers
        data_dir: Override for data/raw/ path
        label_dir: Override for data/labeled/ path

    Returns:
        (train_loader, val_loader, dataset_info)
    """
    train_dataset = DarkPatternDataset(
        data_dir=data_dir,
        label_dir=label_dir,
        tokenizer=tokenizer,
        split="train",
    )
    val_dataset = DarkPatternDataset(
        data_dir=data_dir,
        label_dir=label_dir,
        tokenizer=tokenizer,
        split="val",
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
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