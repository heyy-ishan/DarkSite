#!/usr/bin/env python3
"""
run_ablations.py — Automates ablation study training runs.

Runs all 7 ablation variants across multiple seeds, then generates
a comparison table for the paper.

Usage:
    python run_ablations.py --seeds 42 123 456 --epochs 30
    python run_ablations.py --variants full text-only --seeds 42 --epochs 5
    python run_ablations.py --collect-only   # Just aggregate existing results
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 7 ablation variants: name -> disable_branches flag for train.py
ABLATION_VARIANTS = {
    "full":               None,
    "text-only":          "visual,structural",
    "visual-only":        "text,structural",
    "structural-only":    "visual,text",
    "visual-text":        "structural",
    "text-structural":    "visual",
    "visual-structural":  "text",
}


def run_single(variant, seed, args):
    """Run a single training job as a subprocess."""
    output_dir = Path(args.output_dir) / variant

    cmd = [
        sys.executable, str(Path(__file__).parent / "train.py"),
        "--epochs", str(args.epochs),
        "--batch-size", str(args.batch_size),
        "--seed", str(seed),
        "--output-dir", str(output_dir),
        "--patience", str(args.patience),
    ]

    disable = ABLATION_VARIANTS[variant]
    if disable:
        cmd.extend(["--disable-branches", disable])

    if args.amp:
        cmd.append("--amp")

    if args.no_yada:
        cmd.append("--no-yada")

    if args.data_dir:
        cmd.extend(["--data-dir", args.data_dir])
    if args.label_dir:
        cmd.extend(["--label-dir", args.label_dir])

    print(f"\n{'='*60}")
    print(f"Running: {variant} (seed={seed})")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd)
    return result.returncode == 0


def collect_results(output_dir, variants, seeds):
    """Collect test results from all completed runs."""
    results = {}
    for variant in variants:
        results[variant] = {"seeds": {}, "metrics": {}}
        for seed in seeds:
            test_file = Path(output_dir) / variant / f"seed_{seed}" / "test_results.json"
            if test_file.exists():
                with open(test_file) as f:
                    data = json.load(f)
                results[variant]["seeds"][str(seed)] = data.get("test_metrics", {})

        # Compute mean +/- std across seeds
        if results[variant]["seeds"]:
            all_metrics = list(results[variant]["seeds"].values())
            keys = [k for k in all_metrics[0] if isinstance(all_metrics[0][k], (int, float))]
            for key in keys:
                vals = [m[key] for m in all_metrics if key in m]
                if vals:
                    results[variant]["metrics"][key] = {
                        "mean": float(np.mean(vals)),
                        "std": float(np.std(vals)),
                        "values": vals,
                    }

    return results


def print_results_table(results):
    """Print a paper-ready results table."""
    print("\n" + "=" * 100)
    print("ABLATION RESULTS")
    print("=" * 100)

    header = f"{'Variant':<22} | {'Binary F1':<16} | {'Type Macro F1':<16} | {'Severity Acc':<16} | {'ROC-AUC':<16}"
    print(header)
    print("-" * len(header))

    for variant in ABLATION_VARIANTS:
        if variant not in results or not results[variant]["metrics"]:
            continue

        m = results[variant]["metrics"]

        def fmt(key):
            if key in m:
                return f"{m[key]['mean']:.3f} +/- {m[key]['std']:.3f}"
            return "N/A"

        print(f"{variant:<22} | {fmt('binary_f1'):<16} | {fmt('type_macro_f1'):<16} | "
              f"{fmt('severity_accuracy'):<16} | {fmt('binary_roc_auc'):<16}")

    print("=" * 100)

    # Attention weights for full model
    if "full" in results and results["full"]["metrics"]:
        m = results["full"]["metrics"]
        if "attention_visual" in m:
            print(f"\nAttention weights (full model):")
            print(f"  Visual:     {m['attention_visual']['mean']:.3f} +/- {m['attention_visual']['std']:.3f}")
            print(f"  Text:       {m['attention_text']['mean']:.3f} +/- {m['attention_text']['std']:.3f}")
            print(f"  Structural: {m['attention_structural']['mean']:.3f} +/- {m['attention_structural']['std']:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Run ablation studies")
    parser.add_argument("--variants", nargs="+",
                        default=list(ABLATION_VARIANTS.keys()),
                        choices=list(ABLATION_VARIANTS.keys()),
                        help="Which variants to run")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 456])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--patience", type=int, default=7)
    parser.add_argument("--output-dir", type=str,
                        default=str(PROJECT_ROOT / "models"))
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--no-yada", action="store_true")
    parser.add_argument("--data-dir", type=str, default=None)
    parser.add_argument("--label-dir", type=str, default=None)
    parser.add_argument("--collect-only", action="store_true",
                        help="Skip training, just collect results")

    args = parser.parse_args()

    total_runs = len(args.variants) * len(args.seeds)
    print(f"Ablation study: {len(args.variants)} variants x {len(args.seeds)} seeds = {total_runs} runs")
    print(f"Variants: {args.variants}")
    print(f"Seeds: {args.seeds}")

    if not args.collect_only:
        completed = 0
        failed = 0
        for variant in args.variants:
            for seed in args.seeds:
                success = run_single(variant, seed, args)
                if success:
                    completed += 1
                else:
                    failed += 1
                    print(f"WARNING: {variant} seed={seed} FAILED")

        print(f"\nCompleted: {completed}/{total_runs} (failed: {failed})")

    # Collect and display results
    results = collect_results(args.output_dir, args.variants, args.seeds)
    print_results_table(results)

    # Save results JSON
    results_path = Path(args.output_dir) / "ablation_results.json"
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
