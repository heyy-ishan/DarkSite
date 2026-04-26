#!/usr/bin/env python3
"""
review_disagreements.py — Review samples where relabeling changed the label.

Shows only the cookie-relabeled samples where old != new label.
For each disagreement, displays the evidence and lets you accept the new
label or revert to the original.

Usage:
    python review_disagreements.py           # Interactive review
    python review_disagreements.py --list    # Just list disagreements, no interaction
"""

import json
import argparse
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LABELS_DIR = PROJECT_ROOT / "data" / "labeled"
ORIGINALS_DIR = LABELS_DIR / "originals"


def find_disagreements():
    """Find relabeled samples where the binary label changed."""
    disagreements = []

    for label_file in sorted(LABELS_DIR.glob("*.json")):
        if label_file.stem == "summary":
            continue

        try:
            with open(label_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        if not data.get("relabeled"):
            continue

        old_label = data.get("original_label", {})
        new_label = data.get("label", {})

        old_dark = old_label.get("has_dark_patterns", False)
        new_dark = new_label.get("has_dark_patterns", False)

        if old_dark != new_dark:
            disagreements.append({
                "page_id": data.get("page_id", label_file.stem),
                "url": data.get("url", "unknown"),
                "category": data.get("category", "unknown"),
                "label_path": label_file,
                "old_dark": old_dark,
                "new_dark": new_dark,
                "old_label": old_label,
                "new_label": new_label,
                "cookie_summary": data.get("cookie_audit_summary", {}),
            })

    return disagreements


def display_disagreement(d, idx, total):
    """Display a single disagreement for review."""
    print(f"\n{'='*70}")
    print(f"[{idx+1}/{total}] {d['url']}")
    print(f"Category: {d['category']} | Page ID: {d['page_id']}")
    print(f"{'='*70}")

    # Label change
    old = "DARK" if d["old_dark"] else "CLEAN"
    new = "DARK" if d["new_dark"] else "CLEAN"
    print(f"\n  Label changed: {old} → {new}")

    # Cookie audit data
    ca = d["cookie_summary"]
    if ca:
        print(f"\n  Cookie audit:")
        print(f"    Tracking cookies: {ca.get('tracking_after', '?')}")
        print(f"    Functional cookies: {ca.get('functional_after', '?')}")
        print(f"    Third-party: {ca.get('third_party_after', '?')}")
        print(f"    Banner found: {ca.get('banner_found', '?')}")

    # Old label details
    print(f"\n  OLD label ({old}):")
    old_patterns = d["old_label"].get("dark_patterns", [])
    if old_patterns:
        for dp in old_patterns:
            print(f"    - {dp.get('type', '?')} ({dp.get('severity', '?')}): {dp.get('evidence', '')[:100]}")
    else:
        print(f"    No dark patterns")
    print(f"    Confidence: {d['old_label'].get('confidence', '?')}")

    # New label details
    print(f"\n  NEW label ({new}):")
    new_patterns = d["new_label"].get("dark_patterns", [])
    if new_patterns:
        for dp in new_patterns:
            print(f"    - {dp.get('type', '?')} ({dp.get('severity', '?')}): {dp.get('evidence', '')[:100]}")
    else:
        print(f"    No dark patterns")
    print(f"    Confidence: {d['new_label'].get('confidence', '?')}")


def revert_label(d):
    """
    Revert a relabeled sample to its original label.

    Always snapshots the CURRENT (relabeled) file to a .reverted.bak sibling
    BEFORE overwriting, so an accidental revert is itself recoverable.
    Writes the restored file atomically via tmp + os.replace.
    """
    label_path = d["label_path"]
    backup_path = label_path.with_suffix(label_path.suffix + ".reverted.bak")

    # Snapshot current (relabeled) state before overwrite
    try:
        shutil.copy2(label_path, backup_path)
    except OSError as e:
        print(f"  Error: cannot create backup of current label ({e}). Aborting revert.")
        return

    original_path = ORIGINALS_DIR / f"{d['page_id']}.json"
    if original_path.exists():
        # Restore from file backup. Re-read freshly (do not trust in-memory dict).
        try:
            with open(original_path, "r") as f:
                restored = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"  Error reading original backup ({e}). Aborting revert.")
            return
        tmp = label_path.with_suffix(label_path.suffix + ".tmp")
        with open(tmp, "w") as f:
            json.dump(restored, f, indent=2, default=str)
        os.replace(tmp, label_path)
        print(f"  Reverted to original label (backup: {backup_path.name}).")
        return

    # Restore from embedded original_label field — re-read the file to avoid trusting
    # the in-memory d["old_label"] snapshot built during find_disagreements.
    try:
        with open(label_path, "r") as f:
            data = json.load(f)
        embedded = data.get("original_label")
        if not embedded:
            print(f"  Error: no backup file AND no embedded original_label. Aborting.")
            return
        data["label"] = embedded
        data["relabeled"] = False
        data["reverted"] = True
        tmp = label_path.with_suffix(label_path.suffix + ".tmp")
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, label_path)
        print(f"  Reverted via embedded backup (backup: {backup_path.name}).")
    except (OSError, json.JSONDecodeError) as e:
        print(f"  Error reverting: {e}")


def main():
    parser = argparse.ArgumentParser(description="Review relabeling disagreements")
    parser.add_argument("--list", action="store_true",
                        help="Just list disagreements without interactive review")
    args = parser.parse_args()

    disagreements = find_disagreements()

    if not disagreements:
        print("No disagreements found. All relabeled samples kept the same binary label.")
        # Also show count of confirmed samples
        confirmed = 0
        for label_file in LABELS_DIR.glob("*.json"):
            if label_file.stem == "summary":
                continue
            try:
                with open(label_file) as f:
                    data = json.load(f)
                if data.get("relabeled"):
                    confirmed += 1
            except Exception:
                pass
        if confirmed:
            print(f"({confirmed} samples were relabeled but kept the same binary classification)")
        return

    print(f"\nFound {len(disagreements)} disagreements (label flipped after cookie relabeling)\n")

    if args.list:
        for i, d in enumerate(disagreements):
            old = "DARK" if d["old_dark"] else "CLEAN"
            new = "DARK" if d["new_dark"] else "CLEAN"
            tracking = d["cookie_summary"].get("tracking_after", "?")
            print(f"  {i+1}. {d['url']}")
            print(f"     {old} → {new} | tracking_cookies={tracking}")
        return

    # Interactive review
    print("For each disagreement, choose:")
    print("  [a] Accept new label (keep the relabeled version)")
    print("  [r] Revert to original label")
    print("  [s] Skip (decide later)")
    print("  [q] Quit review\n")

    accepted = 0
    reverted = 0
    skipped = 0

    for i, d in enumerate(disagreements):
        display_disagreement(d, i, len(disagreements))

        while True:
            choice = input(f"\n  Accept / Revert / Skip / Quit? [a/r/s/q]: ").strip().lower()
            if choice in ("a", "r", "s", "q"):
                break
            print("  Invalid choice. Enter a, r, s, or q.")

        if choice == "a":
            accepted += 1
            print(f"  Accepted new label.")
        elif choice == "r":
            revert_label(d)
            reverted += 1
        elif choice == "s":
            skipped += 1
            print(f"  Skipped.")
        elif choice == "q":
            skipped += len(disagreements) - i
            break

    print(f"\n{'='*70}")
    print(f"Review complete: {accepted} accepted, {reverted} reverted, {skipped} skipped")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
