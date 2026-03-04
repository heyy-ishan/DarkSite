# DarkSite: Multi-Modal Dark Pattern Detection on the Web

A research project (targeting CHI/CSCW/WWW) that uses deep learning to catch deceptive UI designs on websites. It combines visual, textual, and structural signals to spot dark patterns like fake urgency timers, hidden fees, confirmshaming, and the rest.

## Overview

Dark patterns are those manipulative UI tricks that push users into doing things they didn't mean to. Think countdown timers that reset, guilt-trip opt-out buttons, fees that show up only at checkout. They're everywhere.

DarkSite tackles this with a three-stage pipeline:

1. **Automated data collection** - A Playwright-based scraper grabs screenshots, DOM structure, and behavioral signals (temporal verification, A/B testing, interaction triggers, session simulation) from 178 websites across 17 categories.

2. **Multi-modal auto-labeling** - Screenshots and metadata get fed through Gemini Vision API to produce structured annotations (dark pattern type, severity, confidence). Humans review a subset for quality control.

3. **Multi-modal detection model** - ViT + RoBERTa + MLP with cross-modal attention fusion. Jointly predicts whether a dark pattern exists (binary), what kind (11-class multi-label), and how bad it is (4-class severity).

## Architecture

```
Screenshot (224x224)     DOM Text (tokenized)     Structural Features (25-dim)
        |                       |                          |
   ViT-Base-16              RoBERTa-Base               3-layer MLP
        |                       |                          |
        +------ 768-dim -------+-------- 768-dim ---------+
                                |
                   Cross-Modal Attention Fusion
                        (8-head, learnable modality embeddings)
                                |
                +---------------+---------------+
          Binary Head      Type Head       Severity Head
           (yes/no)      (11 classes)     (none/low/med/high)
```

**Structural features** are hand-crafted from the scraper's metadata: scarcity/urgency text counts, button area asymmetry ratios, countdown timer presence, pre-checked checkbox counts, modal/popup counts, temporal verification flags, A/B personalization detection, interaction-triggered popup counts, hidden fee detection, and forced account creation signals.

**Loss function** uses uncertainty-based multi-task weighting (Kendall et al., 2018) so the three prediction tasks balance themselves during training. No manual tuning needed.

## Dark Pattern Taxonomy

| Type | Description | Example |
|------|-------------|---------|
| Scarcity | False limited availability | "Only 2 left in stock!" |
| Urgency | Fake time pressure | Countdown timer that resets |
| Social Proof | Manipulative social signals | "47 people viewing this" |
| Confirmshaming | Guilt-tripping opt-outs | "No thanks, I hate saving money" |
| Misdirection | Visual tricks for preferred option | Pre-selected premium plan |
| Hidden Costs | Late-revealed fees | Service fee at checkout |
| Forced Action | Unnecessary required steps | Mandatory account creation |
| Sneaking | Adding items without consent | Pre-checked add-ons |
| Obstruction | Difficulty canceling | Hidden unsubscribe button |
| Nagging | Persistent prompts | Repeated upgrade popups |
| Interface Interference | Asymmetric UI design | Tiny "Decline" vs large "Accept" |

## Dataset

178 URLs across 17 categories, with a deliberate mix:

**Dark pattern-prone sites (~67%):** e-commerce, travel booking, streaming, social media, SaaS, news/media, gaming, food delivery, fitness/health, dating, finance

**Clean baseline sites (~33%):** government, education, nonprofit/open-source, developer tools, ethical companies, utility/reference

Each sample includes a full-page screenshot, raw DOM HTML, and a metadata JSON with outputs from six automated detection methods: pattern extraction, temporal verification, A/B test detection, interaction-based detection, session simulation, and screenshot diff analysis.

## Project Structure

```
DarkSite/
├── scripts/
│   ├── scraper.py          # Phase 1: Playwright-based web scraper
│   ├── url_sources.py       # URL lists by category
│   ├── utils.py             # Shared utilities (logging, hashing, validation)
│   ├── labeler.py           # Phase 2: LLM-based auto-labeling pipeline
│   ├── dataset.py           # Phase 3: PyTorch dataset with all modalities
│   ├── model.py             # Phase 3: Multi-modal model architecture
│   └── train.py             # Phase 3: Training loop with evaluation
├── data/
│   ├── raw/                 # Scraper outputs (screenshots, DOM, metadata, diffs)
│   └── labeled/             # Auto-generated labels
├── models/                  # Saved checkpoints
└── requirements_train.txt
```

## Setup

```bash
# Clone
git clone https://github.com/heyy-ishan/DarkSite.git
cd DarkSite

# Install dependencies
pip install -r requirements_train.txt
pip install playwright google-generativeai imagehash
playwright install firefox

# Phase 1: Scrape
cd scripts && python scraper.py

# Phase 2: Label (requires GEMINI_API_KEY)
export GEMINI_API_KEY="your-key"
python labeler.py

# Phase 3: Train
python train.py --epochs 20 --batch-size 8
```

## Current Status

- [x] Phase 1 - Data collection pipeline (scraper with 6 detection methods)
- [x] Phase 2 - Auto-labeling pipeline (Gemini Vision + Ollama fallback)
- [x] Phase 3 - Model architecture and training pipeline
- [ ] Phase 3 - Training and evaluation (in progress)
- [ ] Phase 4 - Browser extension (Manifest V3, ONNX.js)
- [ ] Phase 5 - User study
- [ ] Phase 6 - Paper

## Key Design Decisions

- **Multi-modal fusion over single-modality** - Dark patterns work across visual, textual, and structural dimensions at the same time. Using just one modality means you miss the cross-modal tricks.
- **Temporal verification** - Tells apart real marketing from dark patterns by checking whether urgency/scarcity claims actually change over time. If that "Only 2 left!" never goes to 1, it's probably fake.
- **A/B test detection** - Catches personalized manipulation by visiting the same pages with different user profiles and comparing what shows up.
- **Uncertainty-weighted multi-task loss** - Lets the model figure out how to balance the binary, multi-label, and severity losses on its own instead of us hand-tuning weights.
- **Differential learning rates** - Pre-trained ViT/RoBERTa backbones fine-tune at 10x lower learning rate than the new layers. Standard practice, but worth noting.

## References

- Mathur et al., "Dark Patterns at Scale: Findings from a Crawl of 11K Shopping Websites," CSCW 2019
- Kendall et al., "Multi-Task Learning Using Uncertainty to Weigh Losses," CVPR 2018
- Dosovitskiy et al., "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale," ICLR 2021
- Liu et al., "RoBERTa: A Robustly Optimized BERT Pretraining Approach," 2019
