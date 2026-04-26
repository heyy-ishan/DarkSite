# DarkSite: Multi-Modal Dark Pattern Detection on the Web

A multi-modal deep learning system that detects deceptive UI designs (dark patterns) on websites in real time. Fuses visual, textual, and structural signals through a three-branch neural architecture with cross-modal attention, deployed as a Chrome extension for live browsing protection.

---

## Why This Matters

Dark patterns are manipulative UI tricks that push users into unintended actions — countdown timers that reset, guilt-trip opt-out buttons, fees hidden until checkout, tiny "Decline" buttons next to giant "Accept" ones. They're everywhere: e-commerce, travel, streaming, SaaS, dating, food delivery, finance.

Existing detection tools are either text-only (miss visual manipulation), single-modality (capture only one dimension), or offline-only (can't protect users in real time). DarkSite addresses all three gaps.

## How It Works

```
                        DarkSite Pipeline

   Phase 1                Phase 2               Phase 3
  ┌─────────┐          ┌───────────┐         ┌──────────────┐
  │ Scraper  │    →     │ Labeler   │    →    │  Multi-Modal  │
  │ 6 methods│          │ Ensemble  │         │    Model      │
  │ per URL  │          │ LLM + QC  │         │  ViT+RoBERTa  │
  └─────────┘          └───────────┘         │  +MLP+Fusion  │
   1,521 URLs           Auto-labels           └──────┬───────┘
   23 categories        + confidence                 │
   1,163 domains        scoring               Phase 4│
                                              ┌──────▼───────┐
                                              │  DarkGuard    │
                                              │  Chrome Ext.  │
                                              │  Real-time    │
                                              └──────────────┘
```

1. **Automated data collection** — Playwright-based scraper captures screenshots, DOM, and behavioral signals via 6 detection methods (temporal verification, A/B testing, interaction triggers, session simulation, screenshot diffs, core extraction) from 1,521 URLs across 23 categories.

2. **Ensemble auto-labeling** — Screenshots and all scraper metadata are analyzed by an ensemble of LLMs (GPT-5-mini + Kimi K2.5) with agreement scoring, confidence-based filtering, and human review for quality control.

3. **Multi-modal detection model** — ViT-Base-16 (vision) + RoBERTa-Base (text) + 3-layer MLP (structural features) with cross-modal attention fusion. Three prediction heads: binary detection, 11-class type classification, 4-class severity rating. Uncertainty-weighted multi-task loss.

4. **Browser extension** — DarkGuard Chrome extension with Shield Score (0-100), three visualization modes (highlight, heatmap, X-ray), Dark Pattern DNA fingerprinting, and research data export.

## Model Architecture

```
Screenshot (224x224)     DOM Text (tokenized)     Structural Features (24-dim)
        |                       |                          |
   ViT-Base-16              RoBERTa-Base               3-layer MLP
   (frozen: 8/12)          (frozen: 8/12)           (256-dim hidden)
        |                       |                          |
        +------ 768-dim -------+-------- 768-dim ---------+
                                |
                   Cross-Modal Attention Fusion
                   (8-head self-attention, learnable
                    modality embeddings, FFN block)
                                |
                         768-dim fused
                                |
                    Shared Bottleneck (512-dim)
                                |
                +---------------+---------------+
          Binary Head      Type Head       Severity Head
           (1 output)    (11 outputs)      (4 classes)
          BCE + sigmoid   BCE + sigmoid    CE + softmax
```

**Training features:**
- Uncertainty-weighted multi-task loss (Kendall et al., 2018)
- Class-weighted loss for imbalanced types and severity
- Confidence-weighted training (ensemble agreement as sample weight)
- Domain-level train/val/test split (no data leakage)
- Weighted sampling (2x own multi-modal data vs. text-only augmentation)
- Differential learning rates (1e-5 backbone, 1e-4 new layers)
- LR warmup (2 epochs) + cosine annealing with warm restarts
- Early stopping (patience=7)
- Full ablation study support (7 variants, multi-seed)

## Dark Pattern Taxonomy

| Type | Description | Example | Severity |
|------|-------------|---------|----------|
| Scarcity | False limited availability | "Only 2 left in stock!" | Medium-High |
| Urgency | Fake time pressure | Countdown timer that resets | High |
| Social Proof | Manipulative social signals | "47 people viewing this" | Medium |
| Confirmshaming | Guilt-tripping opt-outs | "No thanks, I hate saving money" | Medium |
| Misdirection | Visual tricks for preferred option | Pre-selected premium plan | High |
| Hidden Costs | Late-revealed fees | Service fee at checkout | High |
| Forced Action | Unnecessary required steps | Mandatory account creation | High |
| Sneaking | Adding items without consent | Pre-checked add-ons | High |
| Obstruction | Difficulty canceling | Hidden unsubscribe button | High |
| Nagging | Persistent prompts | Repeated upgrade popups | Low-Medium |
| Interface Interference | Asymmetric UI design | Tiny "Decline" vs large "Accept" | Medium-High |

## Dataset

**1,521 URLs** across **23 categories** from **1,163 unique domains**, split 68% dark-pattern-prone / 32% clean baseline:

| Category Type | Categories | URLs |
|---------------|-----------|------|
| Dark-prone | E-commerce, SaaS, Travel, News/Media, Streaming, Finance, Gaming, Fitness/Health, Food Delivery, Telecom, Home Services, Education (paid), Insurance, Ticketing, Dating, Social Media | 1,033 |
| Clean baseline | Government, Developer Docs, Utility/Reference, Ethical Companies, Nonprofit/Open Source, Education, Public Tools | 488 |

Each multi-modal sample includes:
- Full-page screenshot (224x224 for ViT)
- Raw DOM HTML (text extracted via HTMLTextExtractor)
- Metadata JSON with outputs from all 6 detection methods
- Up to 3 temporal diff screenshots

Supplemented by **Yada et al. (IEEE BigData 2022)** text-only dataset (~2,300 samples) for text branch augmentation during training.

## Project Structure

```
DarkSite/
├── scripts/
│   ├── scraper.py            # Phase 1: Playwright scraper (6 detection methods)
│   ├── url_sources.py        # 1,521 URLs across 23 categories
│   ├── utils.py              # Shared utilities (logging, hashing, HTML extraction)
│   ├── labeler.py            # Phase 2: Ensemble LLM labeling pipeline
│   ├── label_reviewer.py     # Phase 2.5: Human review web interface
│   ├── dataset.py            # Phase 3: PyTorch dataset (domain split, weighted sampling)
│   ├── model.py              # Phase 3: Multi-modal model + multi-task loss
│   ├── train.py              # Phase 3: Training (early stop, warmup, AMP, ablation)
│   └── run_ablations.py      # Phase 3: Ablation study launcher
├── data/
│   ├── raw/                  # Scraper outputs (screenshots, DOM, metadata, diffs)
│   ├── labeled/              # Auto-generated + reviewed labels
│   └── external/yada/        # Yada et al. text dataset
├── models/                   # Saved checkpoints + ablation results
├── darkguard-extension/      # Phase 4: Chrome extension
├── docs/                     # Spec and implementation docs
└── requirements.txt
```

## Setup

```bash
# Clone
git clone https://github.com/heyy-ishan/DarkSite.git
cd DarkSite

# Install dependencies
pip install -r requirements.txt
pip install playwright google-generativeai imagehash
playwright install firefox

# Phase 1: Scrape websites
cd scripts && python scraper.py

# Phase 2: Auto-label with ensemble LLMs (requires API keys)
export GEMINI_API_KEY="your-key"
export OPENAI_API_KEY="your-key"       # optional
export NVIDIA_API_KEY="nvapi-your-key"  # optional
python labeler.py

# Phase 2.5: Review low-confidence labels
python label_reviewer.py --include-medium

# Phase 3: Train (single run)
python train.py --epochs 30 --batch-size 8 --seed 42

# Phase 3: Full ablation study (7 variants x 3 seeds)
python run_ablations.py --seeds 42 123 456 --epochs 30

# Collect results from completed runs
python run_ablations.py --collect-only
```

### Training Options

```bash
# Ablation: text-only baseline
python train.py --disable-branches visual,structural --seed 42

# Mixed precision on CUDA
python train.py --amp --batch-size 16

# Without external text data
python train.py --no-yada

# Resume from checkpoint
python train.py --resume models/seed_42/best_model.pt
```

## Evaluation

The training pipeline produces:

- **Domain-level test set** metrics (no leakage between train/val/test)
- **Per-type precision, recall, F1** for all 11 dark pattern types
- **Severity confusion matrix** (none/low/medium/high)
- **ROC-AUC** for binary classification
- **Cross-modal attention weights** showing which modality the model relies on
- **Ablation table** with mean +/- std across 3 seeds:

## Results

Ablation study across 7 modality variants × 3 seeds (42, 123, 456) on the held-out domain-level test split.

```
Variant              | Binary F1        | Type Macro F1    | Severity Acc     | ROC-AUC
-----------------------------------------------------------------------------------------
full                 | 0.877 +/- 0.008  | 0.497 +/- 0.019  | 0.535 +/- 0.064  | 0.909 +/- 0.011
text-only            | 0.848 +/- 0.018  | 0.477 +/- 0.025  | 0.545 +/- 0.114  | 0.879 +/- 0.021
visual-only          | 0.787 +/- 0.001  | 0.408 +/- 0.004  | 0.494 +/- 0.059  | 0.751 +/- 0.021
structural-only      | 0.826 +/- 0.011  | 0.446 +/- 0.010  | 0.494 +/- 0.135  | 0.790 +/- 0.016
visual-text          | 0.841 +/- 0.019  | 0.477 +/- 0.029  | 0.575 +/- 0.107  | 0.871 +/- 0.016
text-structural      | 0.884 +/- 0.018  | 0.504 +/- 0.019  | 0.667 +/- 0.030  | 0.903 +/- 0.027
visual-structural    | 0.848 +/- 0.013  | 0.479 +/- 0.021  | 0.671 +/- 0.028  | 0.881 +/- 0.005
```

**Cross-modal attention weights (full model, mean ± std across seeds):**

```
Visual:     0.365 +/- 0.106
Text:       0.389 +/- 0.081
Structural: 0.246 +/- 0.043
```

### Key Findings

- **Best Binary F1:** `text-structural` (0.884) and `full` (0.877) — statistically tied within std.
- **Best ROC-AUC:** `full` (0.909).
- **Worst single modality:** `visual-only` (F1 0.787) — confirms text dominates dark pattern signal.
- **Attention agrees with ablations:** text > visual > structural.
- **Multi-modal fusion improves over best single modality** (`full` 0.877 vs `text-only` 0.848 = +2.9 F1 points).

## Current Status

- [x] Phase 1 — Data collection (Playwright scraper, 6 detection methods, 1,521 URLs)
- [x] Phase 2 — Ensemble auto-labeling (GPT-5-mini + Kimi K2.5, confidence scoring)
- [x] Phase 2.5 — Human review tool (local web UI for annotation QC)
- [x] Phase 3 — Model architecture + training pipeline
- [x] Phase 4 — DarkGuard Chrome extension (heuristic detection, 3 viz modes)
- [x] Phase 5 — Training + evaluation + ablation studies (7 variants × 3 seeds on NYU HPC)
- [ ] Phase 5.5 — DarkGuard: tracking cookie detection + ONNX model integration
- [ ] Phase 6 — Cross-domain holdout evaluation + per-class error analysis
- [ ] Phase 7 — User study (between-subjects design)

### Planned Before Publication

- [ ] **Cookie consent verification** — Automated cookie audit (`cookie_audit.py`) classifies every site's cookies as functional vs tracking. Identifies cookie consent dark patterns: dismiss-only banners with tracking cookies, pre-consent tracking, and asymmetric reject buttons. Results feed into the structural features and labeling pipeline.
- [ ] **Browser extension updates** — Integrate trained ONNX model for hybrid heuristic+ML inference. Add tracking cookie detection as a feature within the extension to warn users when sites drop tracking cookies without proper consent.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Multi-modal fusion over single-modality | Dark patterns exploit cross-modal cues (tiny "Decline" button + aggressive text + hidden DOM elements). Single modality misses these interactions. |
| Temporal verification | Distinguishes real marketing from dark patterns by checking if urgency/scarcity claims actually change over time. |
| A/B test detection | Catches personalized manipulation by visiting pages with 4 different user profiles. |
| Domain-level data split | Prevents data leakage — model must generalize to unseen websites, not memorize domain styles. |
| Uncertainty-weighted loss | Automatically balances binary, type, and severity losses without manual tuning (Kendall et al., 2018). |
| Class-weighted loss | Handles severe type imbalance (16 confirmshaming vs 465 interface interference samples). |
| Confidence-weighted training | Ensemble agreement score weights each sample's loss contribution. |
| Weighted sampling (3x own data) | Ensures ViT branch trains on real screenshots, not dominated by text-only Yada augmentation. |

## Novel Contributions

1. **First multi-modal dark pattern detector** fusing visual (ViT), textual (RoBERTa), and structural (hand-crafted DOM features) signals with cross-modal attention
2. **Temporal verification framework** that proves urgency/scarcity claims are fabricated by revisiting pages over time
3. **A/B test detection** for personalized manipulation across user profiles
4. **Real-time browser extension** (DarkGuard) with ONNX model integration
5. **End-to-end pipeline** from data collection through user study — rare in dark pattern research

## References

- Mathur et al., "Dark Patterns at Scale: Findings from a Crawl of 11K Shopping Websites," CSCW 2019
- Kendall et al., "Multi-Task Learning Using Uncertainty to Weigh Losses," CVPR 2018
- Dosovitskiy et al., "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale," ICLR 2021
- Liu et al., "RoBERTa: A Robustly Optimized BERT Pretraining Approach," 2019
- Gray et al., "The Dark (Patterns) Side of UX Design," CHI 2018
- Brignull, "Dark Patterns: Deception vs. Honesty in UI Design," 2010
- Yada et al., "Dark Pattern Detection Using Large Language Models," IEEE BigData 2022

## License

This project is for academic research purposes.
