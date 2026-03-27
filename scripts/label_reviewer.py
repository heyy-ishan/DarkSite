#!/usr/bin/env python3
"""
review_labels.py — Manual review tool for low/medium confidence labels.

Launches a local web server with a visual review interface.
Shows screenshot + label side by side. You approve, reject, or edit.

Usage:
    python review_labels.py                     # Review low confidence only
    python review_labels.py --include-medium    # Review low + medium
    python review_labels.py --all               # Review everything

Opens in your browser at http://localhost:8899
"""

import json
import os
import sys
import html as html_module
import base64
import argparse
import logging
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PATHS = {
    "screenshots": PROJECT_ROOT / "data" / "raw" / "screenshots",
    "metadata": PROJECT_ROOT / "data" / "raw" / "metadata",
    "labels": PROJECT_ROOT / "data" / "labeled",
}

PORT = 8899


# ============================================================================
# LOAD SAMPLES FOR REVIEW
# ============================================================================

def load_review_queue(include_medium=False, review_all=False):
    """Load label JSONs filtered by confidence level."""
    queue = []

    for label_file in sorted(PATHS["labels"].glob("*.json")):
        if label_file.stem == "summary":
            continue
        try:
            with open(label_file, "r") as f:
                data = json.load(f)
        except Exception:
            continue

        label = data.get("label", {})
        conf = label.get("confidence", 0)

        # Already reviewed — skip
        if data.get("human_review"):
            continue

        if review_all:
            queue.append(data)
        elif include_medium and conf < 0.85:
            queue.append(data)
        elif not include_medium and conf < 0.6:
            queue.append(data)

    # Sort by confidence ascending (worst first)
    queue.sort(key=lambda x: x.get("label", {}).get("confidence", 0))
    return queue


def get_screenshot_b64(page_id):
    """Load screenshot as base64 for embedding in HTML."""
    img_path = PATHS["screenshots"] / f"{page_id}.png"
    if img_path.exists():
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None


# ============================================================================
# HTML TEMPLATES
# ============================================================================

def build_review_page(sample, index, total):
    """Build the HTML review page for a single sample."""
    label = sample.get("label", {})
    page_id = sample.get("page_id", "unknown")
    url = sample.get("url", "unknown")
    category = sample.get("category", "unknown")
    provider = sample.get("provider", "unknown")
    conf = label.get("confidence", 0)
    severity = label.get("overall_severity", "none")
    has_dp = label.get("has_dark_patterns", False)
    patterns = label.get("dark_patterns", [])
    clean_indicators = label.get("clean_indicators", [])
    page_summary = label.get("page_summary", "")
    temporal = label.get("temporal_verification", "not_applicable")

    img_b64 = get_screenshot_b64(page_id)
    img_html = f'<img src="data:image/png;base64,{img_b64}" class="screenshot">' if img_b64 else '<p class="no-img">No screenshot available</p>'

    # Build pattern rows
    pattern_rows = ""
    esc = html_module.escape
    for i, dp in enumerate(patterns):
        vs = dp.get("verification_status", "unverifiable")
        vs_class = "verified-fake" if vs == "verified_fake" else "verified-real" if vs == "verified_real" else ""
        pattern_rows += f"""
        <div class="pattern-card" id="pattern-{i}">
            <div class="pattern-header">
                <span class="pattern-type">{esc(dp.get('type', 'UNKNOWN'))}</span>
                <span class="pattern-severity sev-{dp.get('severity', 'low')}">{esc(dp.get('severity', 'low'))}</span>
                <span class="pattern-vs {vs_class}">{esc(vs)}</span>
                <span class="pattern-conf">conf: {dp.get('confidence', 0):.2f}</span>
            </div>
            <div class="pattern-evidence"><strong>Evidence:</strong> {esc(dp.get('evidence', 'N/A'))}</div>
            <div class="pattern-explanation"><strong>Why:</strong> {esc(dp.get('explanation', 'N/A'))}</div>
            <div class="pattern-actions">
                <label><input type="checkbox" class="pattern-reject" data-idx="{i}"> Reject this pattern</label>
            </div>
        </div>
        """

    if not patterns:
        pattern_rows = '<p class="no-patterns">No dark patterns detected — labeled as clean page</p>'

    clean_html = ""
    if clean_indicators:
        clean_items = "".join(f"<li>{c}</li>" for c in clean_indicators)
        clean_html = f'<div class="clean-box"><strong>Clean indicators:</strong><ul>{clean_items}</ul></div>'

    # Ensemble info
    ensemble_html = ""
    if sample.get("ensemble"):
        ens = sample["ensemble"]
        agreement = ens.get("agreement")
        if agreement:
            ensemble_html = f"""
            <div class="ensemble-box">
                <strong>Ensemble:</strong> {ens.get('mode', 'N/A')} |
                Binary: {'AGREE' if agreement.get('binary_agree') else 'DISAGREE'} |
                Type IoU: {agreement.get('type_iou', 0):.2f} |
                Overall: {agreement.get('overall', 0):.2f}
            </div>
            """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Review {index+1}/{total} — {url}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; }}
    .container {{ display: grid; grid-template-columns: 1fr 1fr; height: 100vh; }}

    .left {{ overflow-y: auto; padding: 16px; border-right: 1px solid #30363d; }}
    .right {{ overflow-y: auto; padding: 16px; }}

    .screenshot {{ max-width: 100%; border: 1px solid #30363d; border-radius: 6px; }}
    .no-img {{ color: #f85149; padding: 40px; text-align: center; }}

    .header {{ background: #161b22; padding: 12px 16px; border-radius: 6px; margin-bottom: 12px; }}
    .header h2 {{ color: #58a6ff; font-size: 14px; margin-bottom: 4px; }}
    .header .meta {{ font-size: 12px; color: #8b949e; }}
    .progress {{ font-size: 13px; color: #8b949e; margin-bottom: 8px; }}

    .verdict {{ padding: 12px; border-radius: 6px; margin-bottom: 12px; font-weight: 600; font-size: 16px; }}
    .verdict.dark {{ background: #3d1f1f; color: #f85149; border: 1px solid #f85149; }}
    .verdict.clean {{ background: #1f3d2a; color: #3fb950; border: 1px solid #3fb950; }}

    .stats {{ display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }}
    .stat {{ background: #161b22; padding: 6px 10px; border-radius: 4px; font-size: 12px; }}
    .stat.conf-high {{ border-left: 3px solid #3fb950; }}
    .stat.conf-med {{ border-left: 3px solid #d29922; }}
    .stat.conf-low {{ border-left: 3px solid #f85149; }}

    .pattern-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 8px; }}
    .pattern-header {{ display: flex; gap: 8px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }}
    .pattern-type {{ background: #1f6feb; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
    .pattern-severity {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .sev-low {{ background: #1f3d2a; color: #3fb950; }}
    .sev-medium {{ background: #3d2f00; color: #d29922; }}
    .sev-high {{ background: #3d1f1f; color: #f85149; }}
    .pattern-vs {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #21262d; }}
    .pattern-vs.verified-fake {{ background: #3d1f1f; color: #f85149; }}
    .pattern-vs.verified-real {{ background: #1f3d2a; color: #3fb950; }}
    .pattern-conf {{ font-size: 11px; color: #8b949e; }}
    .pattern-evidence, .pattern-explanation {{ font-size: 13px; margin-bottom: 4px; color: #b1bac4; }}
    .pattern-actions {{ margin-top: 8px; font-size: 13px; }}
    .pattern-actions label {{ cursor: pointer; color: #f85149; }}
    .no-patterns {{ color: #3fb950; padding: 20px; text-align: center; font-style: italic; }}

    .clean-box {{ background: #1f3d2a; border: 1px solid #3fb950; border-radius: 6px; padding: 10px; margin-bottom: 12px; font-size: 13px; }}
    .clean-box ul {{ margin-left: 20px; margin-top: 4px; }}

    .ensemble-box {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; font-size: 12px; color: #8b949e; }}

    .summary {{ font-size: 13px; color: #8b949e; font-style: italic; margin-bottom: 12px; }}

    .actions {{ position: sticky; bottom: 0; background: #0d1117; border-top: 1px solid #30363d; padding: 12px; display: flex; gap: 8px; }}
    .btn {{ padding: 10px 20px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }}
    .btn-approve {{ background: #238636; color: white; }}
    .btn-approve:hover {{ background: #2ea043; }}
    .btn-reject {{ background: #da3633; color: white; }}
    .btn-reject:hover {{ background: #f85149; }}
    .btn-flip {{ background: #1f6feb; color: white; }}
    .btn-flip:hover {{ background: #388bfd; }}
    .btn-skip {{ background: #30363d; color: #c9d1d9; }}
    .btn-skip:hover {{ background: #484f58; }}

    .note-box {{ margin-bottom: 8px; }}
    .note-box textarea {{ width: 100%; height: 50px; background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #c9d1d9; padding: 8px; font-size: 13px; resize: vertical; }}
</style>
</head>
<body>
<div class="container">
    <div class="left">
        {img_html}
    </div>
    <div class="right">
        <div class="progress">Review {index+1} of {total}</div>
        <div class="header">
            <h2>{url}</h2>
            <div class="meta">{category} | {provider} | page_id: {page_id}</div>
        </div>

        <div class="verdict {'dark' if has_dp else 'clean'}">
            {'DARK PATTERNS DETECTED' if has_dp else 'CLEAN PAGE'}
        </div>

        <div class="stats">
            <span class="stat conf-{'high' if conf >= 0.85 else 'med' if conf >= 0.6 else 'low'}">Confidence: {conf:.2f}</span>
            <span class="stat">Severity: {severity}</span>
            <span class="stat">Temporal: {temporal}</span>
            <span class="stat">Patterns: {len(patterns)}</span>
        </div>

        {ensemble_html}

        <div class="summary">{page_summary}</div>

        {pattern_rows}

        {clean_html}

        <div class="note-box">
            <textarea id="reviewer-note" placeholder="Optional note (e.g., why you disagree)..."></textarea>
        </div>

        <div class="actions">
            <button class="btn btn-approve" onclick="submit('approve')">Approve</button>
            <button class="btn btn-flip" onclick="submit('flip')">{'Flip to CLEAN' if has_dp else 'Flip to DARK'}</button>
            <button class="btn btn-reject" onclick="submit('reject')">Reject All</button>
            <button class="btn btn-skip" onclick="submit('skip')">Skip</button>
        </div>
    </div>
</div>

<script>
function submit(action) {{
    const rejected = [];
    document.querySelectorAll('.pattern-reject:checked').forEach(el => {{
        rejected.push(parseInt(el.dataset.idx));
    }});
    const note = document.getElementById('reviewer-note').value;

    fetch('/review', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
            page_id: '{page_id}',
            action: action,
            rejected_patterns: rejected,
            note: note,
        }})
    }}).then(() => {{
        window.location.reload();
    }});
}}
</script>
</body>
</html>"""


def build_done_page(stats):
    """Build the completion page."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Review Complete</title>
<style>
    body {{ font-family: -apple-system, sans-serif; background: #0d1117; color: #c9d1d9;
           display: flex; justify-content: center; align-items: center; height: 100vh; }}
    .done {{ text-align: center; }}
    h1 {{ color: #3fb950; margin-bottom: 16px; }}
    .stat {{ font-size: 18px; margin: 8px 0; }}
</style>
</head>
<body>
<div class="done">
    <h1>Review Complete</h1>
    <div class="stat">Approved: {stats['approved']}</div>
    <div class="stat">Flipped: {stats['flipped']}</div>
    <div class="stat">Rejected: {stats['rejected']}</div>
    <div class="stat">Skipped: {stats['skipped']}</div>
    <div class="stat">Patterns removed: {stats['patterns_removed']}</div>
    <p style="margin-top: 24px; color: #8b949e;">You can close this tab. Labels have been saved.</p>
</div>
</body>
</html>"""


# ============================================================================
# HTTP SERVER
# ============================================================================

class ReviewHandler(BaseHTTPRequestHandler):
    queue = []
    current_index = 0
    stats = {"approved": 0, "flipped": 0, "rejected": 0, "skipped": 0, "patterns_removed": 0}

    def log_message(self, format, *args):
        """Suppress default HTTP logging — we use our own logger."""
        pass

    def do_GET(self):
        if ReviewHandler.current_index >= len(ReviewHandler.queue):
            html = build_done_page(ReviewHandler.stats)
        else:
            sample = ReviewHandler.queue[ReviewHandler.current_index]
            html = build_review_page(sample, ReviewHandler.current_index, len(ReviewHandler.queue))

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self):
        if self.path != "/review":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        page_id = body["page_id"]
        action = body["action"]
        rejected_patterns = body.get("rejected_patterns", [])
        note = body.get("note", "")

        # Apply the review
        self._apply_review(page_id, action, rejected_patterns, note)

        ReviewHandler.current_index += 1

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def _apply_review(self, page_id, action, rejected_patterns, note):
        """Apply human review decision to the label file."""
        label_path = PATHS["labels"] / f"{page_id}.json"
        if not label_path.exists():
            return

        with open(label_path, "r") as f:
            data = json.load(f)

        label = data.get("label", {})
        original_confidence = label.get("confidence", 0)

        if action == "skip":
            ReviewHandler.stats["skipped"] += 1
            logger.info(f"  [{page_id}] SKIPPED")
            return

        if action == "approve":
            # Approve as-is, but remove any individually rejected patterns
            if rejected_patterns:
                patterns = label.get("dark_patterns", [])
                kept = [p for i, p in enumerate(patterns) if i not in rejected_patterns]
                removed = len(patterns) - len(kept)
                label["dark_patterns"] = kept
                ReviewHandler.stats["patterns_removed"] += removed
                # If all patterns removed, flip to clean
                if not kept:
                    label["has_dark_patterns"] = False
                    label["overall_severity"] = "none"
                logger.info(f"  [{page_id}] APPROVED (removed {removed} patterns)")
            else:
                logger.info(f"  [{page_id}] APPROVED")
            ReviewHandler.stats["approved"] += 1

        elif action == "flip":
            # Flip the binary classification
            was_dark = label.get("has_dark_patterns", False)
            label["has_dark_patterns"] = not was_dark
            if not was_dark:
                # Flipped to dark — but no patterns, just mark it
                label["overall_severity"] = "low"
            else:
                # Flipped to clean — remove all patterns
                removed = len(label.get("dark_patterns", []))
                label["dark_patterns"] = []
                label["overall_severity"] = "none"
                ReviewHandler.stats["patterns_removed"] += removed
            logger.info(f"  [{page_id}] FLIPPED to {'dark' if not was_dark else 'clean'}")
            ReviewHandler.stats["flipped"] += 1

        elif action == "reject":
            # Reject entire label — mark as clean with zero patterns
            removed = len(label.get("dark_patterns", []))
            label["has_dark_patterns"] = False
            label["dark_patterns"] = []
            label["overall_severity"] = "none"
            label["confidence"] = 0.0
            ReviewHandler.stats["rejected"] += 1
            ReviewHandler.stats["patterns_removed"] += removed
            logger.info(f"  [{page_id}] REJECTED (removed {removed} patterns)")

        # Save human review metadata
        data["human_review"] = {
            "action": action,
            "rejected_patterns": rejected_patterns,
            "note": note,
            "reviewed_at": datetime.now().isoformat(),
            "original_confidence": original_confidence,
        }

        # Boost confidence after human review
        if action in ("approve", "flip"):
            label["confidence"] = max(label.get("confidence", 0), 0.95)

        data["label"] = label

        with open(label_path, "w") as f:
            json.dump(data, f, indent=2, default=str)


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    named_logger = logging.getLogger("darksite")
    named_logger.setLevel(logging.INFO)
    if not named_logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        named_logger.addHandler(sh)
    return named_logger


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Manual review tool for dark pattern labels")
    parser.add_argument("--include-medium", action="store_true",
                        help="Also review medium confidence (0.6–0.85) labels")
    parser.add_argument("--all", action="store_true",
                        help="Review all labels regardless of confidence")
    parser.add_argument("--port", type=int, default=PORT,
                        help=f"Port for review server (default: {PORT})")

    args = parser.parse_args()
    setup_logging()

    queue = load_review_queue(include_medium=args.include_medium, review_all=args.all)

    if not queue:
        logger.info("Nothing to review! All labels are high confidence or already reviewed.")
        return

    conf_range = "all" if args.all else "low + medium (<0.85)" if args.include_medium else "low (<0.6)"
    logger.info(f"Loaded {len(queue)} samples for review (confidence: {conf_range})")
    logger.info(f"Starting review server at http://localhost:{args.port}")
    logger.info("Press Ctrl+C to stop\n")

    ReviewHandler.queue = queue
    ReviewHandler.current_index = 0

    server = HTTPServer(("localhost", args.port), ReviewHandler)

    # Open browser
    webbrowser.open(f"http://localhost:{args.port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nReview session ended.")
        s = ReviewHandler.stats
        logger.info(f"Approved: {s['approved']} | Flipped: {s['flipped']} | "
                    f"Rejected: {s['rejected']} | Skipped: {s['skipped']} | "
                    f"Patterns removed: {s['patterns_removed']}")
        server.server_close()


if __name__ == "__main__":
    main()