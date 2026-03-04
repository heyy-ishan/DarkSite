# labeler.py
# Phase 2: Auto-Labeling Pipeline for Dark Pattern Detection
#
# This script reads ALL scraped data from Phase 1 and uses multimodal LLMs
# to generate structured dark pattern labels.
#
# DATA SOURCES USED (from scraper.py output):
#   - data/raw/screenshots/{page_id}.png     → Full page screenshot (primary visual)
#   - data/raw/diffs/{page_id}_t1.png        → First snapshot (before wait)
#   - data/raw/diffs/{page_id}_t2.png        → Second snapshot (after 5s wait)
#   - data/raw/diffs/{page_id}_t3.png        → Third snapshot (after reload)
#   - data/raw/dom/{page_id}.html            → Raw HTML for text/structure extraction
#   - data/raw/metadata/{page_id}.json       → All analysis: extraction, verification,
#                                               A/B test, interaction, session, diff analysis
#
# PROVIDERS:
#   Primary:  Google Gemini 2.5 Flash (free API, 250 RPD)
#   Fallback: Ollama + Llama 3.2 Vision (local, unlimited)
#
# SETUP:
#   1. Get free Gemini API key from https://aistudio.google.com
#   2. pip install google-generativeai Pillow
#   3. export GEMINI_API_KEY="your-key-here"
#   4. (Optional) brew install ollama && ollama pull llama3.2-vision
#
# USAGE:
#   python labeler.py                     # Label all unlabeled samples
#   python labeler.py --provider ollama   # Use only local Ollama
#   python labeler.py --category travel   # Label only travel category
#   python labeler.py --dry-run           # Preview without calling API

import json
import os
import sys
import time
import re
import base64
import argparse
import logging
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser

# ============================================================================
# SETUP
# ============================================================================

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Paths — matches scraper output structure exactly
PATHS = {
    "screenshots": PROJECT_ROOT / "data" / "raw" / "screenshots",
    "diffs": PROJECT_ROOT / "data" / "raw" / "diffs",
    "dom": PROJECT_ROOT / "data" / "raw" / "dom",
    "metadata": PROJECT_ROOT / "data" / "raw" / "metadata",
    "sessions": PROJECT_ROOT / "data" / "raw" / "sessions",
    "temporal": PROJECT_ROOT / "data" / "raw" / "temporal",
    "labels": PROJECT_ROOT / "data" / "labeled",
    "labels_summary": PROJECT_ROOT / "data" / "labeled" / "summary.json",
}

PATHS["labels"].mkdir(parents=True, exist_ok=True)

# Rate limiting for Gemini free tier (post-Dec 2025 limits)
GEMINI_CONFIG = {
    "model": "gemini-2.5-flash",
    "rpm_limit": 10,
    "rpd_limit": 250,
    "delay_between_calls": 7,      # safe margin for 10 RPM
    "max_retries": 3,
    "retry_delay": 30,
}

OLLAMA_CONFIG = {
    "model": "llama3.2-vision",
    "base_url": "http://localhost:11434",
    "delay_between_calls": 1,
}


# ============================================================================
# DARK PATTERN TAXONOMY
# ============================================================================

DARK_PATTERN_TAXONOMY = """
1. SCARCITY: False claims of limited stock/availability ("Only 2 left!", "3 people viewing")
2. URGENCY: Fake time pressure ("Offer expires in 05:00", "Flash sale ends tonight")
3. SOCIAL_PROOF: Manipulative social proof ("1,247 bought today", fake reviews)
4. CONFIRMSHAMING: Guilt-tripping decline options ("No thanks, I hate saving money")
5. MISDIRECTION: Visual tricks to push preferred option ("Recommended", pre-selected premium plan)
6. HIDDEN_COSTS: Fees revealed late in checkout (service fees, handling charges)
7. FORCED_ACTION: Requiring unnecessary steps (forced account creation, mandatory newsletter signup)
8. SNEAKING: Adding items/charges without consent (pre-checked boxes for extras)
9. OBSTRUCTION: Making it hard to cancel/unsubscribe (hidden cancel button, multi-step cancellation)
10. NAGGING: Persistent repeated prompts (repeated upgrade popups, notification spam)
11. INTERFACE_INTERFERENCE: Asymmetric button design (big "Accept" vs tiny "Decline", low-contrast opt-out)
"""


# ============================================================================
# DOM TEXT EXTRACTOR
# Extracts visible text from raw HTML for additional context
# ============================================================================

class HTMLTextExtractor(HTMLParser):
    """Extract visible text from HTML, skipping script/style/hidden content."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "path", "meta", "link", "head"}

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip_depth += 1
        # Check for hidden elements
        attr_dict = dict(attrs)
        style = attr_dict.get("style", "")
        if "display:none" in style.replace(" ", "") or "visibility:hidden" in style.replace(" ", ""):
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


def extract_dom_text(dom_path, max_chars=3000):
    """
    Extract visible text from DOM HTML file.
    Returns a truncated version suitable for the LLM prompt.
    """
    try:
        with open(dom_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        extractor = HTMLTextExtractor()
        extractor.feed(html)
        text = extractor.get_text()

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"

        return text

    except Exception as e:
        logger.debug(f"DOM text extraction failed: {e}")
        return None


def extract_dom_structure(dom_path):
    """
    Extract structural signals from DOM that indicate dark patterns.
    Returns a dict of structural indicators.
    """
    try:
        with open(dom_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()

        structure = {
            "has_countdown_classes": bool(re.search(r'class="[^"]*(?:countdown|timer|clock)[^"]*"', html, re.I)),
            "has_modal_classes": bool(re.search(r'class="[^"]*(?:modal|popup|overlay|dialog)[^"]*"', html, re.I)),
            "has_cookie_classes": bool(re.search(r'class="[^"]*(?:cookie|consent|gdpr)[^"]*"', html, re.I)),
            "has_urgency_classes": bool(re.search(r'class="[^"]*(?:urgency|hurry|limited|expire)[^"]*"', html, re.I)),
            "prechecked_checkboxes": len(re.findall(r'<input[^>]*type="checkbox"[^>]*checked', html, re.I)),
            "hidden_inputs": len(re.findall(r'<input[^>]*type="hidden"', html, re.I)),
            "total_forms": len(re.findall(r'<form', html, re.I)),
            "external_scripts": len(re.findall(r'<script[^>]*src=', html, re.I)),
        }

        return structure

    except Exception as e:
        logger.debug(f"DOM structure extraction failed: {e}")
        return None


# ============================================================================
# DATA COLLECTOR
# Gathers ALL available data for a single sample
# ============================================================================

def collect_sample_data(page_id):
    """
    Collect all available data for a page_id from every scraper output directory.

    Returns:
        dict with keys: screenshot, diffs, dom_text, dom_structure, metadata
        Each key is None if that data source doesn't exist.
    """
    data = {
        "page_id": page_id,
        "screenshot_path": None,
        "diff_paths": [],           # list of (path, label) tuples
        "dom_text": None,
        "dom_structure": None,
        "metadata": None,
    }

    # 1. Main screenshot
    screenshot = PATHS["screenshots"] / f"{page_id}.png"
    if screenshot.exists():
        data["screenshot_path"] = screenshot

    # 2. Diff screenshots (temporal visual evidence)
    for suffix, label in [("_t1.png", "initial"), ("_t2.png", "after_5s"), ("_t3.png", "after_reload")]:
        diff_path = PATHS["diffs"] / f"{page_id}{suffix}"
        if diff_path.exists():
            data["diff_paths"].append((diff_path, label))

    # 3. DOM content
    dom_path = PATHS["dom"] / f"{page_id}.html"
    if dom_path.exists():
        data["dom_text"] = extract_dom_text(dom_path)
        data["dom_structure"] = extract_dom_structure(dom_path)

    # 4. Metadata JSON (contains extraction, verification, ab_test, interaction, session, diff analysis)
    meta_path = PATHS["metadata"] / f"{page_id}.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                data["metadata"] = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Bad metadata for {page_id}: {e}")

    return data


# ============================================================================
# PROMPT BUILDER
# Builds a comprehensive prompt using ALL available data
# ============================================================================

def build_prompt(sample_data):
    """
    Build the labeling prompt using every data source available.
    The screenshot images are sent separately — this builds the text portion.
    """
    metadata = sample_data.get("metadata") or {}
    url = metadata.get("url", "unknown")
    category = metadata.get("category", "unknown")

    sections = []

    # --- Section 1: Basic info ---
    sections.append(f"WEBSITE: {url}\nCATEGORY: {category}")

    # --- Section 2: Pre-extracted pattern indicators (from scraper's JS extraction) ---
    indicators = []
    ext = metadata.get("extraction", {}) or {}

    if ext.get("scarcity"):
        indicators.append(f"Scarcity text: {ext['scarcity'][:5]}")
    if ext.get("urgency"):
        indicators.append(f"Urgency text: {ext['urgency'][:5]}")
    if ext.get("socialProof"):
        indicators.append(f"Social proof: {ext['socialProof'][:5]}")
    if ext.get("confirmshaming"):
        indicators.append(f"Confirmshaming: {ext['confirmshaming'][:5]}")
    if ext.get("hiddenCosts"):
        indicators.append(f"Hidden costs: {ext['hiddenCosts'][:5]}")
    if ext.get("misdirection"):
        indicators.append(f"Misdirection: {ext['misdirection'][:5]}")
    if ext.get("forcedAction"):
        indicators.append(f"Forced action: {ext['forcedAction'][:5]}")
    if ext.get("countdowns"):
        indicators.append(f"Countdown timers: {len(ext['countdowns'])} found — {[c.get('text','') for c in ext['countdowns'][:3]]}")
    if ext.get("precheckedBoxes"):
        suspicious = [b for b in ext["precheckedBoxes"] if b.get("isSuspicious")]
        if suspicious:
            labels = [b.get("label", "")[:60] for b in suspicious[:3]]
            indicators.append(f"Suspicious pre-checked boxes ({len(suspicious)}): {labels}")
    if ext.get("modals"):
        indicators.append(f"Modals/popups: {len(ext['modals'])} found")
        for m in ext["modals"][:2]:
            indicators.append(f"  Modal text: {m.get('textPreview', '')[:100]}")
    if ext.get("hiddenElements"):
        for h in ext["hiddenElements"][:3]:
            indicators.append(f"Hidden element: '{h.get('text','')}' (reason: {h.get('reason','')})")
    if ext.get("cookieBanners"):
        for banner in ext["cookieBanners"][:2]:
            has_reject = banner.get("hasRejectAll", False)
            has_accept = banner.get("hasAcceptAll", False)
            btn_texts = [b.get("text", "") for b in banner.get("buttons", [])]
            indicators.append(f"Cookie banner: accept={has_accept}, reject={has_reject}, buttons={btn_texts}")

    # Buttons for asymmetry analysis
    buttons = ext.get("buttons", [])
    positive_btns = [b for b in buttons if b.get("isPositive")]
    negative_btns = [b for b in buttons if b.get("isNegative")]
    if positive_btns and negative_btns:
        pos_areas = [b.get("area", 0) for b in positive_btns[:3]]
        neg_areas = [b.get("area", 0) for b in negative_btns[:3]]
        indicators.append(f"Button asymmetry: {len(positive_btns)} positive buttons (areas: {pos_areas}), "
                          f"{len(negative_btns)} negative buttons (areas: {neg_areas})")

    # Prices
    prices = ext.get("prices", {}) or {}
    if prices.get("current"):
        price_str = f"Current price: ${prices['current']}"
        if prices.get("original"):
            price_str += f" (was ${prices['original']}, {prices.get('discount', '?')}% off)"
        if prices.get("claimedDiscount"):
            price_str += f" — page claims {prices['claimedDiscount']}% off"
        indicators.append(price_str)

    # Page metadata
    page_meta = ext.get("metadata", {}) or {}
    if page_meta.get("hasLoginWall"):
        indicators.append("LOGIN WALL detected — content blocked until sign-in")
    if page_meta.get("hasNewsletterPopup"):
        indicators.append("Newsletter popup detected on page load")

    if indicators:
        sections.append("SCRAPER EXTRACTION RESULTS:\n" + "\n".join(f"- {ind}" for ind in indicators))
    else:
        sections.append("SCRAPER EXTRACTION RESULTS:\n- No pattern indicators extracted")

    # --- Section 3: Temporal verification results ---
    verification = metadata.get("verification", {}) or {}
    v_analysis = verification.get("analysis", {}) or {}
    v_snapshots = verification.get("snapshots", [])

    temporal_info = []
    if v_analysis.get("is_suspicious"):
        temporal_info.append(f"SUSPICIOUS — reasons: {v_analysis.get('reasons', [])}")
    if v_analysis.get("stock_suspicious"):
        temporal_info.append("Stock numbers did NOT change across multiple page visits (likely fake)")
    if v_analysis.get("viewers_suspicious"):
        temporal_info.append("Viewer counts did NOT change across visits (likely fake)")
    if v_analysis.get("countdown_suspicious"):
        temporal_info.append("Countdown timer did NOT decrease between visits (likely fake)")
    if v_analysis.get("cart_suspicious"):
        temporal_info.append("Cart count static across visits (likely fake)")

    if v_snapshots:
        for i, snap in enumerate(v_snapshots[:3]):
            snap_info = []
            if snap.get("stockClaims"):
                snap_info.append(f"stock={snap['stockClaims']}")
            if snap.get("viewerCounts"):
                snap_info.append(f"viewers={snap['viewerCounts']}")
            if snap.get("countdownValues"):
                snap_info.append(f"countdown={snap['countdownValues'][:2]}")
            if snap.get("cartCounts"):
                snap_info.append(f"carts={snap['cartCounts']}")
            if snap_info:
                temporal_info.append(f"Visit {i + 1}: {', '.join(snap_info)}")

    if temporal_info:
        sections.append("TEMPORAL VERIFICATION (page visited 3 times, 10s apart):\n" +
                         "\n".join(f"- {t}" for t in temporal_info))

    # --- Section 4: A/B test detection results ---
    ab_test = metadata.get("ab_test", {}) or {}
    ab_analysis = ab_test.get("analysis", {}) or {}
    ab_results = ab_test.get("results", [])

    ab_info = []
    if ab_analysis.get("personalization_detected"):
        ab_info.append(f"PERSONALIZATION DETECTED (severity: {ab_analysis.get('severity', 'unknown')})")
        for diff in ab_analysis.get("differences", []):
            ab_info.append(f"  {diff.get('type', 'unknown')}: profile={diff.get('profile', '?')}, "
                           f"baseline={diff.get('baseline', '?')}, variant={diff.get('variant', '?')}")
    elif ab_results:
        ab_info.append("No significant personalization differences detected across user profiles")

    if ab_info:
        sections.append("A/B TEST DETECTION (tested with new user, returning user, mobile, EU profiles):\n" +
                         "\n".join(f"- {a}" for a in ab_info))

    # --- Section 5: Interaction detection results ---
    interaction = metadata.get("interaction", {}) or {}
    int_analysis = interaction.get("analysis", {}) or {}

    int_info = []
    if int_analysis.get("has_scroll_trap"):
        scroll_data = interaction.get("scroll_triggered", [])
        int_info.append(f"Scroll-triggered popup: {[s.get('text','')[:80] for s in scroll_data[:2]]}")
    if int_analysis.get("has_exit_intent"):
        exit_data = interaction.get("exit_intent_triggered", [])
        int_info.append(f"Exit-intent popup: {[e.get('text','')[:80] for e in exit_data[:2]]}")
    if int_analysis.get("has_idle_popup"):
        idle_data = interaction.get("idle_triggered", [])
        int_info.append(f"Idle popup (appeared after inactivity): {[i.get('text','')[:80] for i in idle_data[:2]]}")
    if int_analysis.get("has_decline_guilt"):
        decline = interaction.get("decline_response", {}) or {}
        int_info.append(f"Guilt-trip after declining: modal_text={decline.get('modalText', '')[:100]}")
    total_popups = int_analysis.get("total_triggered_popups", 0)
    if total_popups > 0:
        int_info.append(f"Total triggered popups: {total_popups}")

    if int_info:
        sections.append("INTERACTION DETECTION (scroll, exit intent, idle, decline tests):\n" +
                         "\n".join(f"- {i}" for i in int_info))

    # --- Section 6: Session simulation results ---
    session = metadata.get("session", {}) or {}
    s_analysis = session.get("analysis", {}) or {}
    s_stages = session.get("stages", [])

    session_info = []
    if s_analysis.get("has_checkout_dark_patterns"):
        session_info.append("Forced account creation at checkout (no guest option)")
    if s_analysis.get("has_hidden_fees"):
        session_info.append("Hidden fees appeared during cart/checkout flow")
    if s_analysis.get("has_exit_manipulation"):
        session_info.append("Exit popup with discount appeared when trying to leave checkout")
    if s_analysis.get("has_upsell_pressure"):
        session_info.append("Upsell/cross-sell pressure after adding to cart")

    for stage in s_stages:
        action = stage.get("action", "")
        success = stage.get("success", False)
        if not success and action not in ("browse", "abandon"):
            session_info.append(f"Session stage '{action}': FAILED (button not found)")
        if stage.get("upsells"):
            ups = stage["upsells"]
            if ups.get("hasUpsell"):
                session_info.append(f"Upsell detected after '{action}': warranty={ups.get('hasWarranty')}, "
                                    f"pre-checked extras={ups.get('hasPrechecked', 0)}")
        if stage.get("forced_signup"):
            fs = stage["forced_signup"]
            session_info.append(f"Checkout: requires_account={fs.get('requiresAccount')}, "
                                f"guest_option={fs.get('hasGuestOption')}")
        if stage.get("hidden_fees"):
            session_info.append(f"Hidden fees at '{action}': {stage['hidden_fees']}")
        if stage.get("exit_popups"):
            for popup in stage["exit_popups"][:2]:
                session_info.append(f"Exit popup: has_discount={popup.get('hasDiscount')}, "
                                    f"text={popup.get('text', '')[:80]}")

    if session_info:
        sections.append("SESSION SIMULATION (browse → cart → checkout → abandon):\n" +
                         "\n".join(f"- {s}" for s in session_info))

    # --- Section 7: Screenshot diff analysis ---
    diff_data = metadata.get("screenshot_diff", {}) or {}
    d_analysis = diff_data.get("analysis", {}) or {}
    d_elements = diff_data.get("dynamic_elements", {}) or {}

    diff_info = []
    if d_analysis.get("significant_change"):
        diff_info.append(f"SIGNIFICANT visual change detected between snapshots "
                          f"(diff_over_time={d_analysis.get('diff_over_time')}, "
                          f"diff_after_reload={d_analysis.get('diff_after_reload')})")
    if d_analysis.get("possible_dynamic_content"):
        diff_info.append("Possible dynamic content (elements changing between visits)")
    if d_analysis.get("likely_static_page"):
        diff_info.append("Page appears static (minimal visual changes)")
    if d_elements.get("countdownPresent"):
        diff_info.append("Countdown timer visible in diff screenshots")
    if d_elements.get("stockTextPresent"):
        diff_info.append("Stock availability text visible in diff screenshots")
    if d_elements.get("viewerCountPresent"):
        diff_info.append("Viewer count visible in diff screenshots")

    if diff_info:
        sections.append("SCREENSHOT DIFF ANALYSIS (visual changes over time):\n" +
                         "\n".join(f"- {d}" for d in diff_info))

    # --- Section 8: DOM structure signals ---
    dom_structure = sample_data.get("dom_structure")
    if dom_structure:
        struct_info = []
        if dom_structure.get("has_countdown_classes"):
            struct_info.append("HTML contains countdown/timer CSS classes")
        if dom_structure.get("has_urgency_classes"):
            struct_info.append("HTML contains urgency-related CSS classes")
        if dom_structure.get("prechecked_checkboxes", 0) > 0:
            struct_info.append(f"HTML has {dom_structure['prechecked_checkboxes']} pre-checked checkboxes")
        if dom_structure.get("has_modal_classes"):
            struct_info.append("HTML contains modal/popup CSS classes")
        if dom_structure.get("has_cookie_classes"):
            struct_info.append("HTML contains cookie/consent CSS classes")
        if struct_info:
            sections.append("DOM STRUCTURE ANALYSIS:\n" + "\n".join(f"- {s}" for s in struct_info))

    # --- Section 9: DOM visible text excerpt ---
    dom_text = sample_data.get("dom_text")
    if dom_text:
        sections.append(f"PAGE TEXT EXCERPT (first ~3000 chars of visible text):\n{dom_text}")

    # --- Section 10: Image context ---
    image_context = ["The MAIN SCREENSHOT shows the full page as captured by the scraper."]
    if sample_data.get("diff_paths"):
        labels = [label for _, label in sample_data["diff_paths"]]
        image_context.append(
            f"You are also provided {len(sample_data['diff_paths'])} DIFF SCREENSHOTS ({', '.join(labels)}) "
            f"taken at different times. Compare them to verify if countdowns, stock numbers, or "
            f"viewer counts actually changed — if they didn't, the urgency/scarcity is likely fake."
        )
    sections.append("IMAGE CONTEXT:\n" + "\n".join(f"- {c}" for c in image_context))

    # --- Build final prompt ---
    data_block = "\n\n".join(sections)

    prompt = f"""You are a dark pattern detection expert. Analyze the provided screenshot(s) and all the data below to identify dark patterns on this website.

{data_block}

DARK PATTERN TAXONOMY:
{DARK_PATTERN_TAXONOMY}

INSTRUCTIONS:
1. Examine the main screenshot for visual dark patterns (button asymmetry, hidden options, deceptive layouts)
2. If diff screenshots are provided, compare them to verify temporal claims (countdowns, stock, viewers)
3. Cross-reference ALL the pre-extracted data above — the scraper has already done automated checks
4. For each dark pattern found, provide type, severity, evidence, and explanation
5. Also note if the page appears CLEAN (no dark patterns) — this is equally important
6. Be precise — only flag genuine dark patterns, not standard marketing or legitimate UX

Respond with ONLY valid JSON (no markdown, no backticks, no preamble) in this exact format:

{{
    "has_dark_patterns": true/false,
    "overall_severity": "none" | "low" | "medium" | "high",
    "confidence": 0.0 to 1.0,
    "dark_patterns": [
        {{
            "type": "one of: SCARCITY, URGENCY, SOCIAL_PROOF, CONFIRMSHAMING, MISDIRECTION, HIDDEN_COSTS, FORCED_ACTION, SNEAKING, OBSTRUCTION, NAGGING, INTERFACE_INTERFERENCE",
            "severity": "low" | "medium" | "high",
            "evidence": "exact text or UI element from the page",
            "explanation": "why this is a dark pattern and how it manipulates the user",
            "confidence": 0.0 to 1.0
        }}
    ],
    "temporal_verification": "confirmed_fake" | "confirmed_real" | "inconclusive" | "not_applicable",
    "clean_indicators": ["list any user-respecting design choices observed"],
    "page_summary": "one sentence describing what the page is and its primary purpose"
}}

If no dark patterns are found, return has_dark_patterns: false with an empty dark_patterns array.
"""
    return prompt


def _repair_json(text):
    """
    Attempt to repair truncated JSON from LLM responses.
    Handles common issues: unclosed strings, arrays, objects.
    """
    try:
        # First, try as-is
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try closing unclosed strings and brackets
    repaired = text.rstrip()

    # Close any unclosed string
    quote_count = repaired.count('"') - repaired.count('\\"')
    if quote_count % 2 != 0:
        repaired += '"'

    # Close unclosed arrays and objects
    open_brackets = repaired.count('[') - repaired.count(']')
    open_braces = repaired.count('{') - repaired.count('}')

    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


# ============================================================================
# GEMINI PROVIDER
# ============================================================================

class GeminiLabeler:
    """Labels screenshots using Google Gemini 2.5 Flash API."""

    def __init__(self):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            )

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Get a free key from https://aistudio.google.com\n"
                "Then run: export GEMINI_API_KEY='your-key-here'"
            )

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_CONFIG["model"])
        self.genai = genai
        self.calls_today = 0
        self.day_start = datetime.now().date()
        logger.info(f"Gemini initialized (model: {GEMINI_CONFIG['model']})")

    def _check_daily_limit(self):
        today = datetime.now().date()
        if today != self.day_start:
            self.calls_today = 0
            self.day_start = today
        if self.calls_today >= GEMINI_CONFIG["rpd_limit"]:
            logger.warning(f"Gemini daily limit reached ({self.calls_today}/{GEMINI_CONFIG['rpd_limit']})")
            return False
        return True

    def label(self, sample_data):
        """
        Send all available images + comprehensive prompt to Gemini.

        Args:
            sample_data: Dict from collect_sample_data()

        Returns:
            dict: Parsed label JSON, or None on failure
        """
        if not self._check_daily_limit():
            return None

        from PIL import Image

        prompt = build_prompt(sample_data)

        # Build content list: [prompt, main_screenshot, diff1, diff2, diff3...]
        content = [prompt]

        # Main screenshot (required)
        if sample_data["screenshot_path"]:
            content.append(Image.open(sample_data["screenshot_path"]))

        # Diff screenshots (optional, for temporal verification)
        for diff_path, label in sample_data.get("diff_paths", []):
            content.append(f"\n[DIFF SCREENSHOT — {label}]:")
            content.append(Image.open(diff_path))

        for attempt in range(GEMINI_CONFIG["max_retries"]):
            try:
                response = self.model.generate_content(
                    content,
                    generation_config=self.genai.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                    ),
                )

                self.calls_today += 1
                text = response.text.strip()

                # Clean markdown fences
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

                return json.loads(text)

            except json.JSONDecodeError as e:
                logger.warning(f"  JSON parse error (attempt {attempt + 1}): {e}")
                logger.debug(f"  Raw response: {text[:300]}")
                # Try to repair truncated JSON
                repaired = _repair_json(text)
                if repaired:
                    logger.info(f"  JSON repaired successfully")
                    return repaired
                if attempt < GEMINI_CONFIG["max_retries"] - 1:
                    time.sleep(5)

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str or "rate" in error_str:
                    wait = GEMINI_CONFIG["retry_delay"] * (attempt + 1)
                    logger.warning(f"  Rate limited. Waiting {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                elif "500" in error_str or "503" in error_str:
                    logger.warning(f"  Server error. Retrying in 10s (attempt {attempt + 1})")
                    time.sleep(10)
                else:
                    logger.error(f"  Gemini error: {e}")
                    if attempt < GEMINI_CONFIG["max_retries"] - 1:
                        time.sleep(5)

        return None


# ============================================================================
# OLLAMA PROVIDER (LOCAL FALLBACK)
# ============================================================================

class OllamaLabeler:
    """Labels screenshots using local Ollama + Llama 3.2 Vision."""

    def __init__(self):
        import urllib.request
        try:
            req = urllib.request.Request(f"{OLLAMA_CONFIG['base_url']}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                model_names = [m["name"] for m in data.get("models", [])]
                model_base = OLLAMA_CONFIG["model"].split(":")[0]
                if not any(model_base in name for name in model_names):
                    raise RuntimeError(
                        f"Model '{OLLAMA_CONFIG['model']}' not found. "
                        f"Available: {model_names}\n"
                        f"Run: ollama pull {OLLAMA_CONFIG['model']}"
                    )
        except urllib.error.URLError:
            raise RuntimeError(
                "Ollama not running. Start with: ollama serve\n"
                "Then: ollama pull llama3.2-vision"
            )
        logger.info(f"Ollama initialized (model: {OLLAMA_CONFIG['model']})")

    def label(self, sample_data):
        """
        Send screenshot + prompt to local Ollama.
        Note: Ollama only supports a single image, so we send the main screenshot
        and include diff analysis from metadata in the text prompt.
        """
        import urllib.request

        prompt = build_prompt(sample_data)

        # Ollama supports one image — use main screenshot
        img_path = sample_data.get("screenshot_path")
        if not img_path:
            return None

        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = json.dumps({
            "model": OLLAMA_CONFIG["model"],
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        }).encode("utf-8")

        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"{OLLAMA_CONFIG['base_url']}/api/generate",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read())

                text = result.get("response", "").strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

                return json.loads(text)

            except json.JSONDecodeError as e:
                logger.warning(f"  Ollama JSON error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2)
            except Exception as e:
                logger.error(f"  Ollama error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(5)

        return None


# ============================================================================
# MAIN LABELING PIPELINE
# ============================================================================

class LabelingPipeline:
    """
    Orchestrates the full labeling process:
    1. Scans all scraper output directories for samples
    2. Collects ALL data per sample (screenshots, diffs, DOM, metadata)
    3. Labels using Gemini (primary) or Ollama (fallback)
    4. Saves labels to data/labeled/
    5. Tracks progress for resume
    """

    def __init__(self, provider="gemini", fallback=True):
        self.primary = None
        self.fallback_provider = None

        if provider == "gemini":
            try:
                self.primary = GeminiLabeler()
            except (ImportError, ValueError, RuntimeError) as e:
                logger.error(f"Gemini init failed: {e}")
                if fallback:
                    logger.info("Falling back to Ollama...")
                    provider = "ollama"
                else:
                    raise

        if provider == "ollama":
            self.primary = OllamaLabeler()

        if fallback and provider == "gemini":
            try:
                self.fallback_provider = OllamaLabeler()
                logger.info("Ollama fallback ready")
            except Exception:
                logger.info("Ollama fallback not available (OK)")

        self.stats = {
            "total": 0, "labeled": 0, "skipped": 0, "failed": 0,
            "dark_patterns_found": 0, "clean_pages": 0,
            "by_provider": {}, "by_type": {},
            "by_confidence": {"high": 0, "medium": 0, "low": 0},
            "data_sources_used": {"with_diffs": 0, "with_dom": 0, "screenshot_only": 0},
        }

    def get_sample_ids(self, category_filter=None):
        """Get all page_ids that have at least a metadata JSON and a screenshot."""
        ids = []
        for meta_file in sorted(PATHS["metadata"].glob("*.json")):
            page_id = meta_file.stem
            if page_id in ("scraped_urls", "summary"):
                continue
            if not (PATHS["screenshots"] / f"{page_id}.png").exists():
                continue
            if category_filter:
                try:
                    with open(meta_file, "r") as f:
                        meta = json.load(f)
                    if meta.get("category") != category_filter:
                        continue
                except Exception:
                    continue
            ids.append(page_id)
        return ids

    def get_labeled_ids(self):
        labeled = set()
        for f in PATHS["labels"].glob("*.json"):
            if f.stem not in ("summary",):
                labeled.add(f.stem)
        return labeled

    def label_sample(self, sample_data):
        """Try primary, fall back if needed."""
        label = self.primary.label(sample_data)
        if label:
            name = "gemini" if isinstance(self.primary, GeminiLabeler) else "ollama"
            return label, name

        if self.fallback_provider:
            logger.info(f"  Primary failed, trying fallback...")
            label = self.fallback_provider.label(sample_data)
            if label:
                return label, "ollama"

        return None, None

    def save_label(self, sample_data, label, provider_name):
        """Save label with full context."""
        metadata = sample_data.get("metadata") or {}
        page_id = sample_data["page_id"]

        output = {
            "page_id": page_id,
            "url": metadata.get("url", "unknown"),
            "domain": metadata.get("domain", "unknown"),
            "category": metadata.get("category", "unknown"),
            "scraped_at": metadata.get("scraped_at", "unknown"),
            "labeled_at": datetime.now().isoformat(),
            "provider": provider_name,
            "data_sources": {
                "screenshot": sample_data["screenshot_path"] is not None,
                "diff_screenshots": len(sample_data.get("diff_paths", [])),
                "dom_text": sample_data.get("dom_text") is not None,
                "dom_structure": sample_data.get("dom_structure") is not None,
                "has_verification": metadata.get("verification") is not None,
                "has_ab_test": metadata.get("ab_test") is not None,
                "has_interaction": metadata.get("interaction") is not None,
                "has_session": metadata.get("session") is not None,
                "has_diff_analysis": metadata.get("screenshot_diff") is not None,
            },
            "label": label,
        }

        out_path = PATHS["labels"] / f"{page_id}.json"
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2, default=str)
        return out_path

    def update_stats(self, sample_data, label, provider_name):
        self.stats["labeled"] += 1
        self.stats["by_provider"][provider_name] = self.stats["by_provider"].get(provider_name, 0) + 1

        if label.get("has_dark_patterns"):
            self.stats["dark_patterns_found"] += 1
        else:
            self.stats["clean_pages"] += 1

        for dp in label.get("dark_patterns", []):
            t = dp.get("type", "UNKNOWN")
            self.stats["by_type"][t] = self.stats["by_type"].get(t, 0) + 1

        conf = label.get("confidence", 0)
        if conf >= 0.85:
            self.stats["by_confidence"]["high"] += 1
        elif conf >= 0.6:
            self.stats["by_confidence"]["medium"] += 1
        else:
            self.stats["by_confidence"]["low"] += 1

        # Track data richness
        if sample_data.get("diff_paths"):
            self.stats["data_sources_used"]["with_diffs"] += 1
        if sample_data.get("dom_text"):
            self.stats["data_sources_used"]["with_dom"] += 1
        if not sample_data.get("diff_paths") and not sample_data.get("dom_text"):
            self.stats["data_sources_used"]["screenshot_only"] += 1

    def save_summary(self):
        self.stats["completed_at"] = datetime.now().isoformat()
        with open(PATHS["labels_summary"], "w") as f:
            json.dump(self.stats, f, indent=2)

    def run(self, category_filter=None, dry_run=False, limit=None):
        """Main labeling loop."""
        all_ids = self.get_sample_ids(category_filter)
        labeled_ids = self.get_labeled_ids()
        unlabeled_ids = [pid for pid in all_ids if pid not in labeled_ids]

        self.stats["total"] = len(all_ids)
        self.stats["skipped"] = len(labeled_ids)

        logger.info(f"Total samples: {len(all_ids)}")
        logger.info(f"Already labeled: {len(labeled_ids)}")
        logger.info(f"To label: {len(unlabeled_ids)}")

        if dry_run:
            logger.info("\n--- DRY RUN ---")
            for pid in unlabeled_ids[:10]:
                data = collect_sample_data(pid)
                meta = data.get("metadata") or {}
                n_diffs = len(data.get("diff_paths", []))
                has_dom = "yes" if data.get("dom_text") else "no"
                logger.info(f"  {meta.get('url', pid)} [{meta.get('category', '?')}] "
                            f"diffs={n_diffs} dom={has_dom}")
            if len(unlabeled_ids) > 10:
                logger.info(f"  ... and {len(unlabeled_ids) - 10} more")
            return

        if not unlabeled_ids:
            logger.info("All samples already labeled!")
            self.save_summary()
            return

        if limit:
            unlabeled_ids = unlabeled_ids[:limit]

        delay = (GEMINI_CONFIG["delay_between_calls"]
                 if isinstance(self.primary, GeminiLabeler)
                 else OLLAMA_CONFIG["delay_between_calls"])

        for i, page_id in enumerate(unlabeled_ids):
            # Collect ALL data for this sample
            sample_data = collect_sample_data(page_id)
            meta = sample_data.get("metadata") or {}
            url = meta.get("url", page_id)
            category = meta.get("category", "?")
            n_diffs = len(sample_data.get("diff_paths", []))

            logger.info(f"[{i + 1}/{len(unlabeled_ids)}] {url} [{category}] "
                         f"(diffs={n_diffs}, dom={'yes' if sample_data.get('dom_text') else 'no'})")

            label, provider_name = self.label_sample(sample_data)

            if label:
                self.save_label(sample_data, label, provider_name)
                self.update_stats(sample_data, label, provider_name)

                has_dp = label.get("has_dark_patterns", False)
                n_patterns = len(label.get("dark_patterns", []))
                conf = label.get("confidence", 0)
                severity = label.get("overall_severity", "none")

                if has_dp:
                    types = [dp.get("type") for dp in label.get("dark_patterns", [])]
                    logger.info(f"  → {n_patterns} dark patterns (severity={severity}, "
                                f"conf={conf:.2f}): {types}")
                else:
                    logger.info(f"  → Clean page (conf={conf:.2f})")
            else:
                self.stats["failed"] += 1
                logger.error(f"  → FAILED to label {page_id}")

            if i < len(unlabeled_ids) - 1:
                time.sleep(delay)

        self.save_summary()
        self._print_summary()

    def _print_summary(self):
        s = self.stats
        logger.info("\n" + "=" * 60)
        logger.info("LABELING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total samples:      {s['total']}")
        logger.info(f"Labeled this run:   {s['labeled']}")
        logger.info(f"Previously done:    {s['skipped']}")
        logger.info(f"Failed:             {s['failed']}")
        logger.info(f"")
        logger.info(f"Dark pattern pages: {s['dark_patterns_found']}")
        logger.info(f"Clean pages:        {s['clean_pages']}")
        logger.info(f"")
        logger.info(f"Providers:    {s['by_provider']}")
        logger.info(f"Confidence:   {s['by_confidence']}")
        logger.info(f"Data sources: {s['data_sources_used']}")
        logger.info(f"")
        if s["by_type"]:
            logger.info("Dark patterns by type:")
            for t, c in sorted(s["by_type"].items(), key=lambda x: -x[1]):
                logger.info(f"  {t:30s} {c}")
        logger.info("=" * 60)


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_labeler_logging():
    named_logger = logging.getLogger("darksite")
    named_logger.setLevel(logging.INFO)
    if not named_logger.handlers:
        log_dir = PROJECT_ROOT / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh = logging.FileHandler(str(log_dir / "labeling.log"))
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
    parser = argparse.ArgumentParser(description="Auto-label scraped data for dark pattern detection")
    parser.add_argument("--provider", choices=["gemini", "ollama"], default="gemini",
                        help="Primary LLM provider (default: gemini)")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Disable Ollama fallback")
    parser.add_argument("--category", type=str, default=None,
                        help="Only label this category (e.g., travel)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without calling APIs")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max samples to label")

    args = parser.parse_args()
    setup_labeler_logging()

    logger.info("=" * 60)
    logger.info("DARK PATTERN AUTO-LABELING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Provider: {args.provider} | Fallback: {'off' if args.no_fallback else 'ollama'}")
    logger.info(f"Data sources: screenshots + diffs + DOM + full metadata")
    if args.category:
        logger.info(f"Category filter: {args.category}")

    try:
        pipeline = LabelingPipeline(provider=args.provider, fallback=not args.no_fallback)
        pipeline.run(category_filter=args.category, dry_run=args.dry_run, limit=args.limit)
    except (ImportError, ValueError, RuntimeError) as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()