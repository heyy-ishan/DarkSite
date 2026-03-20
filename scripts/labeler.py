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

# ============================================================================
# SETUP
# ============================================================================

logger = logging.getLogger("darksite")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from scripts.utils import extract_html_text
except ImportError:
    from utils import extract_html_text

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
# Flash-Lite: 15 RPM, 1000 RPD — enough for all ~945 URLs in 1 day
# Flash:      10 RPM, 250 RPD  — higher quality, 4 days to finish
GEMINI_CONFIG = {
    "model": "gemini-2.5-flash-lite",       # 1000 RPD on free tier
    "model_flash": "gemini-2.5-flash",       # 250 RPD, better quality
    "rpm_limit": 15,
    "rpd_limit": 1000,
    "delay_between_calls": 15,
    "max_retries": 3,
    "retry_delay": 30,
}
# Kimi K2.5 via NVIDIA NIM — free prototyping access
# OpenAI-compatible API, credit-based (not daily reset)
KIMI_CONFIG = {
    "model": "moonshotai/kimi-k2.5",
    "base_url": "https://integrate.api.nvidia.com/v1",
    "rpm_limit": 40,
    "delay_between_calls": 2,
    "max_retries": 3,
    "retry_delay": 10,
    "use_thinking": False,     # instant mode uses fewer tokens
}

# OpenAI — vision supported
# $5 free credits on signup (no credit card)
OPENAI_CONFIG = {
    "model": "gpt-5-mini",
    "base_url": "https://api.openai.com/v1",
    "rpm_limit": 500,
    "delay_between_calls": 1,
    "max_retries": 3,
    "retry_delay": 5,
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
1. SCARCITY: Claims of limited stock/availability ("Only 2 left!", "3 people viewing") — may be real or fabricated
2. URGENCY: Time pressure messaging ("Offer expires in 05:00", "Flash sale ends tonight") — may be real or fabricated
3. SOCIAL_PROOF: Social proof messaging ("1,247 bought today", review counts, popularity claims)
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

def extract_dom_text(dom_path, max_chars=3000):
    try:
        text = extract_html_text(dom_path, max_chars=max_chars)
        if len(text) >= max_chars:
            text = text + "... [truncated]"
        return text

    except Exception as e:
        logger.debug(f"DOM text extraction failed: {e}")
        return None


def extract_dom_structure(dom_path):
    
    #Extract structural signals from DOM that indicate dark patterns.
    #Returns a dict of structural indicators.
    
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
    
    #Collect all available data for a page_id from every scraper output directory.
    #Returns:
    #    dict with keys: screenshot, diffs, dom_text, dom_structure, metadata
    #    Each key is None if that data source doesn't exist.

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

    # 4. Metadata JSON (contains extraction, ab_test, interaction, diff analysis)
    meta_path = PATHS["metadata"] / f"{page_id}.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                data["metadata"] = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Bad metadata for {page_id}: {e}")

    # 5. Temporal verification (saved separately by scraper)
    temporal_path = PATHS["temporal"] / f"{page_id}.json"
    if temporal_path.exists():
        try:
            with open(temporal_path, "r") as f:
                data.setdefault("metadata", {})["verification"] = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Bad temporal data for {page_id}: {e}")

    # 6. Session simulation (saved separately by scraper)
    session_path = PATHS["sessions"] / f"{page_id}.json"
    if session_path.exists():
        try:
            with open(session_path, "r") as f:
                data.setdefault("metadata", {})["session"] = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Bad session data for {page_id}: {e}")

    return data


# ============================================================================
# PROMPT BUILDER
# Builds a comprehensive prompt using ALL available data
# ============================================================================

def build_prompt(sample_data):
    
    #Build the labeling prompt using every data source available.
    #The screenshot images are sent separately — this builds the text portion.
    
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
        int_info.append(f"Guilt-trip after declining: modal_text={(decline.get('modalText') or '')[:100]}")
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
        labels = [dl for _, dl in sample_data["diff_paths"]]
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
4. For each dark pattern found, provide type, severity, evidence, explanation, and verification_status
5. Also note if the page appears CLEAN (no dark patterns) — this is equally important
6. Be precise — only flag genuine dark patterns, not standard marketing or legitimate UX
7. For verification_status: use "verified_fake" ONLY if temporal data proves the claim is fabricated (countdown didn't tick, stock frozen across visits). Use "verified_real" ONLY if temporal data shows the value actually changed. Otherwise use "unverifiable" — this is the honest default for most cases.

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
            "confidence": 0.0 to 1.0,
            "verification_status": "verified_fake" | "verified_real" | "unverifiable"
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

    #Attempt to repair truncated JSON from LLM responses.
    #Handles common issues: unclosed strings, arrays, objects.

    try:
        # First, try as-is
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    repaired = text.rstrip()

    # Close any unclosed string
    quote_count = repaired.count('"') - repaired.count('\\"')
    if quote_count % 2 != 0:
        repaired += '"'

    # Track actual nesting order of { and [ so we close in correct reverse order
    stack = []
    in_string = False
    escape = False
    for ch in repaired:
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            stack.append('}')
        elif ch == '[':
            stack.append(']')
        elif ch in ('}', ']'):
            if stack:
                stack.pop()

    # Close in reverse nesting order
    repaired += ''.join(reversed(stack))

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


# ============================================================================
# GEMINI PROVIDER
# ============================================================================

class GeminiLabeler:
    
    #Labels screenshots using Google Gemini 2.5 Flash-Lite (or Flash) API.
    
    def __init__(self, use_flash=False):
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
        model_name = GEMINI_CONFIG["model_flash"] if use_flash else GEMINI_CONFIG["model"]
        rpd = 250 if use_flash else GEMINI_CONFIG["rpd_limit"]
        self.model = genai.GenerativeModel(model_name)
        self.genai = genai
        self.calls_today = 0
        self.rpd_limit = rpd
        self.day_start = datetime.now().date()
        self.model_name = model_name
        logger.info(f"Gemini initialized (model: {model_name}, RPD limit: {rpd})")

    def _check_daily_limit(self):
        today = datetime.now().date()
        if today != self.day_start:
            self.calls_today = 0
            self.day_start = today
        if self.calls_today >= self.rpd_limit:
            logger.warning(f"Gemini daily limit reached ({self.calls_today}/{self.rpd_limit})")
            return False
        return True

    def label(self, sample_data):
        
        #Send all available images + comprehensive prompt to Gemini.
        
        #Args:
        #    sample_data: Dict from collect_sample_data()

        #Returns:
        #    dict: Parsed label JSON, or None on failure
        
        if not self._check_daily_limit():
            return None

        from PIL import Image

        prompt = build_prompt(sample_data)

        # Build content list: [prompt, main_screenshot, diff1, diff2, diff3...]
        content = [prompt]

        # Main screenshot (required)
        if sample_data["screenshot_path"]:
            try:
                content.append(Image.open(sample_data["screenshot_path"]))
            except Exception as e:
                logger.warning(f"  Failed to load screenshot: {e}")
                return None

        # Diff screenshots (optional, for temporal verification)
        for diff_path, diff_label in sample_data.get("diff_paths", []):
            try:
                content.append(f"\n[DIFF SCREENSHOT — {diff_label}]:")
                content.append(Image.open(diff_path))
            except Exception as e:
                logger.warning(f"  Failed to load diff screenshot {diff_path}: {e}")

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
    
    #Labels screenshots using local Ollama + Llama 3.2 Vision.
    
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
        
        #Send screenshot + prompt to local Ollama.
        #Note: Ollama only supports a single image, so we send the main screenshot
        #and include diff analysis from metadata in the text prompt.
        
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
                repaired = _repair_json(text)
                if repaired:
                    logger.info(f"  Ollama JSON repaired successfully")
                    return repaired
                if attempt < 2:
                    time.sleep(2)
            except Exception as e:
                logger.error(f"  Ollama error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(5)

        return None


# ============================================================================
# NVIDIA KIMI K2.5 PROVIDER (FREE VIA NVIDIA NIM)
# ============================================================================

class NvidiaKimiLabeler:
    
    #Labels screenshots using Kimi K2.5 via NVIDIA NIM API.
    #OpenAI-compatible endpoint — free prototyping access via NVIDIA Developer Program.
    #
    #Setup:
    #  1. Go to build.nvidia.com and sign up for NVIDIA Developer Program
    #  2. Find Kimi K2.5 model card → click "Build with this NIM"
    #  3. Copy the API key
    #  4. export NVIDIA_API_KEY="nvapi-..."
    
    def __init__(self):
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY not set.\n"
                "1. Sign up at https://build.nvidia.com (free)\n"
                "2. Search for 'Kimi K2.5' → Build with this NIM\n"
                "3. Copy your API key\n"
                "4. Run: export NVIDIA_API_KEY='nvapi-your-key-here'"
            )

        self.api_key = api_key
        self.base_url = KIMI_CONFIG["base_url"]
        self.model = KIMI_CONFIG["model"]
        self.calls_made = 0
        logger.info(f"NVIDIA Kimi K2.5 initialized (model: {self.model})")

    def label(self, sample_data):
        
        #Send screenshot + prompt to Kimi K2.5 via NVIDIA NIM.
        #Uses OpenAI-compatible chat completions API.
        #Only sends main screenshot (single image per request).
        
        import urllib.request

        prompt = build_prompt(sample_data)

        # Encode main screenshot as base64
        img_path = sample_data.get("screenshot_path")
        if not img_path:
            return None

        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Build OpenAI-compatible message with image
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}",
                        },
                    },
                ],
            }
        ]

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.1 if not KIMI_CONFIG["use_thinking"] else 1.0,
            "max_tokens": 4096,
            "stream": False,
            "chat_template_kwargs": {
                "thinking": KIMI_CONFIG["use_thinking"],
            },
        }).encode("utf-8")

        for attempt in range(KIMI_CONFIG["max_retries"]):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                )

                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read())

                self.calls_made += 1

                # Extract text from OpenAI-compatible response
                text = result["choices"][0]["message"]["content"].strip()

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
                logger.warning(f"  Kimi JSON error (attempt {attempt + 1}): {e}")
                repaired = _repair_json(text)
                if repaired:
                    logger.info(f"  Kimi JSON repaired successfully")
                    return repaired
                if attempt < KIMI_CONFIG["max_retries"] - 1:
                    time.sleep(3)

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    wait = KIMI_CONFIG["retry_delay"] * (attempt + 1)
                    logger.warning(f"  Kimi rate limited. Waiting {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                elif e.code in (402, 403):
                    logger.error(f"  Kimi credits exhausted or access denied: {error_body[:200]}")
                    return None
                elif e.code >= 500:
                    logger.warning(f"  Kimi server error {e.code}. Retrying in 10s (attempt {attempt + 1})")
                    time.sleep(10)
                else:
                    logger.error(f"  Kimi HTTP {e.code}: {error_body[:200]}")
                    if attempt < KIMI_CONFIG["max_retries"] - 1:
                        time.sleep(5)

            except Exception as e:
                logger.error(f"  Kimi error (attempt {attempt + 1}): {e}")
                if attempt < KIMI_CONFIG["max_retries"] - 1:
                    time.sleep(5)

        return None


# ============================================================================
# OPENAI PROVIDER
# ============================================================================

class OpenAILabeler:

    #Labels screenshots using OpenAI API.
    #
    #Setup:
    #  1. Go to platform.openai.com and create an account
    #  2. Create an API key
    #  3. export OPENAI_API_KEY="sk-..."

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not set.\n"
                "1. Sign up at https://platform.openai.com (free $5 credits, no card needed)\n"
                "2. Go to API Keys → Create new secret key\n"
                "3. Run: export OPENAI_API_KEY='sk-your-key-here'"
            )

        self.api_key = api_key
        self.base_url = OPENAI_CONFIG["base_url"]
        self.model = OPENAI_CONFIG["model"]
        self.calls_made = 0
        logger.info(f"OpenAI initialized (model: {self.model})")

    def label(self, sample_data):

        #Send screenshot(s) + prompt to OpenAI.
        #Supports multiple images (main + diffs) unlike Kimi/Ollama.

        import urllib.request

        prompt = build_prompt(sample_data)

        # Build message content: text + all images
        content = [{"type": "text", "text": prompt}]

        # Main screenshot (required)
        img_path = sample_data.get("screenshot_path")
        if not img_path:
            return None

        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

        # Diff screenshots (OpenAI supports multiple images)
        for diff_path, diff_label in sample_data.get("diff_paths", []):
            try:
                with open(diff_path, "rb") as f:
                    diff_b64 = base64.b64encode(f.read()).decode("utf-8")
                content.append({"type": "text", "text": f"[DIFF SCREENSHOT — {diff_label}]:"})
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{diff_b64}", "detail": "low"},
                })
            except Exception as e:
                logger.warning(f"  Failed to load diff {diff_path}: {e}")

        messages = [{"role": "user", "content": content}]

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": 4096,
        }).encode("utf-8")

        for attempt in range(OPENAI_CONFIG["max_retries"]):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                )

                with urllib.request.urlopen(req, timeout=120) as resp:
                    result = json.loads(resp.read())

                self.calls_made += 1

                text = result["choices"][0]["message"]["content"].strip()

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
                logger.warning(f"  OpenAI JSON error (attempt {attempt + 1}): {e}")
                repaired = _repair_json(text)
                if repaired:
                    logger.info(f"  OpenAI JSON repaired successfully")
                    return repaired
                if attempt < OPENAI_CONFIG["max_retries"] - 1:
                    time.sleep(3)

            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429:
                    wait = OPENAI_CONFIG["retry_delay"] * (attempt + 1)
                    logger.warning(f"  OpenAI rate limited. Waiting {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                elif e.code == 400:
                    logger.error(f"  OpenAI bad request (not retrying): {error_body[:300]}")
                    return None
                elif e.code == 401:
                    logger.error(f"  OpenAI auth failed — check your OPENAI_API_KEY")
                    return None
                elif e.code == 402:
                    logger.error(f"  OpenAI credits exhausted: {error_body[:200]}")
                    return None
                elif e.code >= 500:
                    logger.warning(f"  OpenAI server error {e.code}. Retrying in 5s (attempt {attempt + 1})")
                    time.sleep(5)
                else:
                    logger.error(f"  OpenAI HTTP {e.code}: {error_body[:200]}")
                    if attempt < OPENAI_CONFIG["max_retries"] - 1:
                        time.sleep(3)

            except Exception as e:
                logger.error(f"  OpenAI error (attempt {attempt + 1}): {e}")
                if attempt < OPENAI_CONFIG["max_retries"] - 1:
                    time.sleep(3)

        return None


# ============================================================================
# ENSEMBLE AGREEMENT — compare two model outputs
# ============================================================================

DARK_PATTERN_TYPE_LIST = [
    "SCARCITY", "URGENCY", "SOCIAL_PROOF", "CONFIRMSHAMING", "MISDIRECTION",
    "HIDDEN_COSTS", "FORCED_ACTION", "SNEAKING", "OBSTRUCTION", "NAGGING",
    "INTERFACE_INTERFERENCE",
]

SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _extract_type_set(label):
    """Extract the set of dark pattern type strings from a label."""
    return {dp.get("type", "").upper() for dp in label.get("dark_patterns", [])
            if dp.get("type", "").upper() in DARK_PATTERN_TYPE_LIST}


def compute_agreement(label_a, label_b):
    """
    Compare two model labels and return detailed agreement metrics.

    Returns:
        dict with binary_agree, type_iou, severity_agree, per_type agreement,
        and an overall agreement score (0.0–1.0).
    """
    # --- Binary agreement ---
    bin_a = bool(label_a.get("has_dark_patterns", False))
    bin_b = bool(label_b.get("has_dark_patterns", False))
    binary_agree = bin_a == bin_b

    # --- Type agreement (Jaccard / IoU) ---
    types_a = _extract_type_set(label_a)
    types_b = _extract_type_set(label_b)

    if types_a or types_b:
        intersection = types_a & types_b
        union = types_a | types_b
        type_iou = len(intersection) / len(union)
    else:
        # Both found zero types — perfect agreement
        type_iou = 1.0

    # Per-type agreement vector (for kappa computation)
    per_type = {}
    for t in DARK_PATTERN_TYPE_LIST:
        per_type[t] = {
            "a": t in types_a,
            "b": t in types_b,
            "agree": (t in types_a) == (t in types_b),
        }

    # --- Severity agreement ---
    sev_a = label_a.get("overall_severity", "none").lower()
    sev_b = label_b.get("overall_severity", "none").lower()
    severity_exact = sev_a == sev_b
    severity_distance = abs(SEVERITY_ORDER.get(sev_a, 0) - SEVERITY_ORDER.get(sev_b, 0))

    # --- Overall agreement score ---
    # Weighted: binary (40%) + type IoU (40%) + severity (20%)
    severity_score = 1.0 if severity_exact else (1.0 - severity_distance / 3.0)
    overall = 0.4 * float(binary_agree) + 0.4 * type_iou + 0.2 * severity_score

    return {
        "binary_agree": binary_agree,
        "binary_a": bin_a,
        "binary_b": bin_b,
        "type_iou": round(type_iou, 3),
        "types_a": sorted(types_a),
        "types_b": sorted(types_b),
        "types_both": sorted(types_a & types_b),
        "types_only_a": sorted(types_a - types_b),
        "types_only_b": sorted(types_b - types_a),
        "per_type": per_type,
        "severity_a": sev_a,
        "severity_b": sev_b,
        "severity_exact": severity_exact,
        "severity_distance": severity_distance,
        "overall": round(overall, 3),
    }


def merge_labels(label_a, label_b, agreement):
    """
    Merge two model labels into a single consensus label.

    Strategy:
    - Binary: agree → use agreed value; disagree → conservative (flag as dark)
    - Types: union of both models' detected types
    - Severity: agree → use that; disagree → take the higher severity
    - Confidence: derived from agreement score, not self-reported
    - Per-pattern evidence: kept from whichever model detected it
    """
    merged = {}

    # --- Binary ---
    if agreement["binary_agree"]:
        merged["has_dark_patterns"] = agreement["binary_a"]
    else:
        # Conservative: if either model says dark patterns exist, flag it
        merged["has_dark_patterns"] = True

    # --- Dark patterns: union of both models' detections ---
    patterns_by_type = {}

    for source_label, source_name in [(label_a, "model_a"), (label_b, "model_b")]:
        for dp in source_label.get("dark_patterns", []):
            dp_type = dp.get("type", "").upper()
            if dp_type not in DARK_PATTERN_TYPE_LIST:
                continue
            if dp_type not in patterns_by_type:
                patterns_by_type[dp_type] = {
                    "type": dp_type,
                    "severity": dp.get("severity", "low"),
                    "evidence": dp.get("evidence", ""),
                    "explanation": dp.get("explanation", ""),
                    "verification_status": dp.get("verification_status", "unverifiable"),
                    "detected_by": [source_name],
                    "agreed": dp_type in agreement["types_both"],
                }
            else:
                patterns_by_type[dp_type]["detected_by"].append(source_name)
                patterns_by_type[dp_type]["agreed"] = True
                # Take higher severity if disagreement
                existing_sev = SEVERITY_ORDER.get(patterns_by_type[dp_type]["severity"], 0)
                new_sev = SEVERITY_ORDER.get(dp.get("severity", "low"), 0)
                if new_sev > existing_sev:
                    patterns_by_type[dp_type]["severity"] = dp.get("severity", "low")
                # Take the more definitive verification_status
                vs_priority = {"verified_fake": 3, "verified_real": 2, "unverifiable": 1}
                existing_vs = patterns_by_type[dp_type].get("verification_status", "unverifiable")
                new_vs = dp.get("verification_status", "unverifiable")
                if vs_priority.get(new_vs, 0) > vs_priority.get(existing_vs, 0):
                    patterns_by_type[dp_type]["verification_status"] = new_vs

    merged["dark_patterns"] = list(patterns_by_type.values())

    # --- Severity: take the higher if disagreement ---
    if agreement["severity_exact"]:
        merged["overall_severity"] = agreement["severity_a"]
    else:
        sev_a_ord = SEVERITY_ORDER.get(agreement["severity_a"], 0)
        sev_b_ord = SEVERITY_ORDER.get(agreement["severity_b"], 0)
        higher = agreement["severity_a"] if sev_a_ord >= sev_b_ord else agreement["severity_b"]
        merged["overall_severity"] = higher

    # --- Confidence: derived from inter-annotator agreement, not self-reported ---
    merged["confidence"] = agreement["overall"]

    # --- Temporal verification: prefer non-"not_applicable" answer ---
    tv_a = label_a.get("temporal_verification", "not_applicable")
    tv_b = label_b.get("temporal_verification", "not_applicable")
    if tv_a == tv_b:
        merged["temporal_verification"] = tv_a
    elif tv_a != "not_applicable" and tv_b == "not_applicable":
        merged["temporal_verification"] = tv_a
    elif tv_b != "not_applicable" and tv_a == "not_applicable":
        merged["temporal_verification"] = tv_b
    else:
        # Both gave different non-N/A answers — take the more suspicious one
        priority = {"confirmed_fake": 3, "inconclusive": 2, "confirmed_real": 1}
        merged["temporal_verification"] = tv_a if priority.get(tv_a, 0) >= priority.get(tv_b, 0) else tv_b

    # --- Clean indicators: union ---
    clean_a = set(label_a.get("clean_indicators", []))
    clean_b = set(label_b.get("clean_indicators", []))
    merged["clean_indicators"] = sorted(clean_a | clean_b)

    # --- Page summary: prefer model_a (Gemini, typically higher quality) ---
    merged["page_summary"] = label_a.get("page_summary", label_b.get("page_summary", ""))

    return merged


# ============================================================================
# COHEN'S KAPPA — inter-annotator agreement statistic
# ============================================================================

def compute_cohens_kappa(binary_pairs):
    """
    Compute Cohen's kappa for binary agreement between two annotators.

    Args:
        binary_pairs: list of (annotator_a_bool, annotator_b_bool) tuples

    Returns:
        float: kappa score (-1 to 1). 1 = perfect agreement,
               0 = agreement by chance, <0 = worse than chance.
    """
    if not binary_pairs:
        return 0.0

    n = len(binary_pairs)

    # Observed agreement
    agree = sum(1 for a, b in binary_pairs if a == b)
    p_o = agree / n

    # Expected agreement by chance
    a_pos = sum(1 for a, _ in binary_pairs if a) / n
    b_pos = sum(1 for _, b in binary_pairs if b) / n
    a_neg = 1 - a_pos
    b_neg = 1 - b_pos
    p_e = (a_pos * b_pos) + (a_neg * b_neg)

    if p_e == 1.0:
        return 1.0  # Both annotators gave identical labels for everything

    kappa = (p_o - p_e) / (1 - p_e)
    return round(kappa, 4)


def compute_per_type_kappa(per_type_pairs):
    """
    Compute Cohen's kappa per dark pattern type.

    Args:
        per_type_pairs: dict of {type_name: [(a_bool, b_bool), ...]}

    Returns:
        dict of {type_name: kappa_score}
    """
    result = {}
    for type_name, pairs in per_type_pairs.items():
        result[type_name] = compute_cohens_kappa(pairs)
    return result


# ============================================================================
# MAIN LABELING PIPELINE
# ============================================================================

class LabelingPipeline:

    #Full labeling pipeline with ensemble support.
    #
    #Modes:
    #  Single-provider: Labels using one model with optional fallback.
    #  Ensemble:        Runs BOTH Gemini and Kimi on every sample,
    #                   compares outputs, merges with agreement-based
    #                   confidence, and stores full traceability.

    def __init__(self, provider="openai", fallback=True, use_flash=False,
                 ensemble=False):
        self.ensemble = ensemble
        self.primary = None
        self.secondary = None
        self.fallback_provider = None
        self.provider_name = provider

        if ensemble:
            # Ensemble mode: initialize BOTH a primary (OpenAI or Gemini) and Kimi
            errors = []

            # Primary: prefer OpenAI (no rate limit pain), fall back to Gemini
            if provider in ("openai", "gemini"):
                try:
                    if provider == "openai":
                        self.primary = OpenAILabeler()
                    else:
                        self.primary = GeminiLabeler(use_flash=use_flash)
                except (ImportError, ValueError, RuntimeError) as e:
                    errors.append(f"Primary ({provider}): {e}")
                    # If OpenAI fails, try Gemini as backup primary
                    if provider == "openai":
                        try:
                            self.primary = GeminiLabeler(use_flash=use_flash)
                            logger.info("OpenAI unavailable, using Gemini as ensemble primary")
                        except (ImportError, ValueError, RuntimeError) as e2:
                            errors.append(f"Gemini fallback: {e2}")

            try:
                self.secondary = NvidiaKimiLabeler()
            except (ValueError, RuntimeError) as e:
                errors.append(f"Kimi: {e}")

            if not self.primary and not self.secondary:
                raise RuntimeError(
                    f"Ensemble mode requires at least one provider. Errors: {errors}"
                )
            if not self.primary or not self.secondary:
                missing = "Primary" if not self.primary else "Kimi"
                logger.warning(f"Ensemble: {missing} unavailable — falling back to single-provider mode")
                self.ensemble = False
                if not self.primary:
                    self.primary = self.secondary
                    self.secondary = None
                    self.provider_name = "kimi"

            # Ollama as emergency fallback if both cloud APIs fail on a sample
            if self.ensemble:
                try:
                    self.fallback_provider = OllamaLabeler()
                    logger.info("Ollama emergency fallback ready")
                except Exception:
                    logger.info("Ollama not available (OK — both cloud providers active)")

            if self.ensemble:
                primary_name = self._get_provider_name(self.primary) if self.primary else "?"
                logger.info(f"Ensemble mode: {primary_name} + Kimi K2.5 on every sample")
        else:
            # Single-provider mode
            if provider == "openai":
                try:
                    self.primary = OpenAILabeler()
                except (ValueError, RuntimeError) as e:
                    logger.error(f"OpenAI init failed: {e}")
                    if fallback:
                        logger.info("Falling back to Gemini...")
                        provider = "gemini"
                    else:
                        raise

            if provider == "gemini":
                try:
                    self.primary = GeminiLabeler(use_flash=use_flash)
                except (ImportError, ValueError, RuntimeError) as e:
                    logger.error(f"Gemini init failed: {e}")
                    if fallback:
                        logger.info("Falling back to Kimi K2.5...")
                        provider = "kimi"
                    else:
                        raise

            if provider == "kimi":
                try:
                    self.primary = NvidiaKimiLabeler()
                    self.provider_name = "kimi"
                except (ValueError, RuntimeError) as e:
                    logger.error(f"Kimi init failed: {e}")
                    if fallback:
                        logger.info("Falling back to Ollama...")
                        provider = "ollama"
                    else:
                        raise

            if provider == "ollama":
                self.primary = OllamaLabeler()
                self.provider_name = "ollama"

            # Setup fallback chain: openai → gemini → kimi → ollama
            if fallback and self.primary:
                if self.provider_name == "openai":
                    for FallbackClass, fb_name in [(NvidiaKimiLabeler, "kimi"), (OllamaLabeler, "ollama")]:
                        try:
                            self.fallback_provider = FallbackClass()
                            logger.info(f"{fb_name.capitalize()} fallback ready")
                            break
                        except Exception:
                            continue
                elif self.provider_name == "gemini":
                    for FallbackClass, fb_name in [(NvidiaKimiLabeler, "kimi"), (OllamaLabeler, "ollama")]:
                        try:
                            self.fallback_provider = FallbackClass()
                            logger.info(f"{fb_name.capitalize()} fallback ready")
                            break
                        except Exception:
                            continue
                elif self.provider_name == "kimi":
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
            "by_verification": {"verified_fake": 0, "verified_real": 0, "unverifiable": 0},
            "data_sources_used": {"with_diffs": 0, "with_dom": 0, "screenshot_only": 0},
        }

        # Ensemble-specific stats
        if self.ensemble:
            self.stats["ensemble"] = {
                "total_compared": 0,
                "binary_agreements": 0,
                "binary_disagreements": 0,
                "severity_exact_matches": 0,
                "avg_type_iou": 0.0,
                "avg_overall_agreement": 0.0,
                "primary_only_succeeded": 0,
                "kimi_only_succeeded": 0,
                "both_failed": 0,
            }
            # For kappa computation at the end
            self._binary_pairs = []         # [(gemini_bool, kimi_bool), ...]
            self._per_type_pairs = {t: [] for t in DARK_PATTERN_TYPE_LIST}
            self._agreement_scores = []     # raw overall scores for averaging
            self._type_iou_scores = []      # raw type IoU scores for averaging

    def get_sample_ids(self, category_filter=None):
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
            if f.stem != "summary":
                labeled.add(f.stem)
        return labeled

    def _get_provider_name(self, provider):
        if isinstance(provider, GeminiLabeler):
            return f"gemini:{provider.model_name}"
        elif isinstance(provider, OpenAILabeler):
            return f"openai:{provider.model}"
        elif isinstance(provider, NvidiaKimiLabeler):
            return "kimi-k2.5"
        else:
            return "ollama"

    def label_sample(self, sample_data):
        """
        Label a single sample.

        In ensemble mode: runs both models, compares, and merges.
        In single mode: tries primary, falls back if needed.

        Returns:
            (merged_label, provider_name, ensemble_data_or_None)
        """
        if self.ensemble:
            return self._label_sample_ensemble(sample_data)
        else:
            return self._label_sample_single(sample_data)

    def _label_sample_single(self, sample_data):
        """Original single-provider labeling with fallback."""
        label = self.primary.label(sample_data)
        if label:
            return label, self._get_provider_name(self.primary), None

        if self.fallback_provider:
            logger.info(f"  Primary failed, trying fallback...")
            label = self.fallback_provider.label(sample_data)
            if label:
                return label, self._get_provider_name(self.fallback_provider), None

        return None, None, None

    def _label_sample_ensemble(self, sample_data):
        """Run both primary and Kimi, compare, and merge."""
        label_primary = None
        label_kimi = None

        primary_name = self._get_provider_name(self.primary) if self.primary else "?"

        # Run primary (OpenAI or Gemini)
        if self.primary:
            label_primary = self.primary.label(sample_data)
            if label_primary:
                logger.info(f"  {primary_name}: {'dark' if label_primary.get('has_dark_patterns') else 'clean'} "
                            f"({len(label_primary.get('dark_patterns', []))} patterns)")

        # Run Kimi
        if self.secondary:
            label_kimi = self.secondary.label(sample_data)
            if label_kimi:
                logger.info(f"  Kimi:   {'dark' if label_kimi.get('has_dark_patterns') else 'clean'} "
                            f"({len(label_kimi.get('dark_patterns', []))} patterns)")

        ens = self.stats["ensemble"]

        # Case 1: Both succeeded — compare and merge
        if label_primary and label_kimi:
            agreement = compute_agreement(label_primary, label_kimi)
            merged = merge_labels(label_primary, label_kimi, agreement)

            # Update ensemble tracking
            ens["total_compared"] += 1
            if agreement["binary_agree"]:
                ens["binary_agreements"] += 1
            else:
                ens["binary_disagreements"] += 1
            if agreement["severity_exact"]:
                ens["severity_exact_matches"] += 1
            self._agreement_scores.append(agreement["overall"])
            self._type_iou_scores.append(agreement["type_iou"])

            # Track for kappa
            self._binary_pairs.append((agreement["binary_a"], agreement["binary_b"]))
            for t in DARK_PATTERN_TYPE_LIST:
                self._per_type_pairs[t].append(
                    (agreement["per_type"][t]["a"], agreement["per_type"][t]["b"])
                )

            ensemble_data = {
                "mode": "ensemble",
                "primary_label": label_primary,
                "primary_provider": primary_name,
                "kimi_label": label_kimi,
                "agreement": agreement,
            }

            status = "AGREE" if agreement["binary_agree"] else "DISAGREE"
            logger.info(f"  Ensemble: {status} (overall={agreement['overall']:.2f}, "
                        f"type_iou={agreement['type_iou']:.2f})")

            return merged, f"ensemble:{primary_name}+kimi", ensemble_data

        # Case 2: Only primary succeeded
        if label_primary:
            ens["primary_only_succeeded"] = ens.get("primary_only_succeeded", 0) + 1
            label_primary["confidence"] = min(label_primary.get("confidence", 0.5), 0.6)
            logger.info(f"  Ensemble: Kimi failed, using {primary_name} only (confidence capped at 0.6)")
            ensemble_data = {
                "mode": "single_fallback",
                "primary_label": label_primary,
                "primary_provider": primary_name,
                "kimi_label": None,
                "agreement": None,
            }
            return label_primary, f"{primary_name}-only", ensemble_data

        # Case 3: Only Kimi succeeded
        if label_kimi:
            ens["kimi_only_succeeded"] = ens.get("kimi_only_succeeded", 0) + 1
            label_kimi["confidence"] = min(label_kimi.get("confidence", 0.5), 0.6)
            logger.info(f"  Ensemble: {primary_name} failed, using Kimi only (confidence capped at 0.6)")
            ensemble_data = {
                "mode": "single_fallback",
                "primary_label": None,
                "primary_provider": primary_name,
                "kimi_label": label_kimi,
                "agreement": None,
            }
            return label_kimi, "kimi-only", ensemble_data

        # Case 4: Both failed — try Ollama emergency fallback
        if self.fallback_provider:
            logger.info(f"  Ensemble: Both failed, trying Ollama fallback...")
            label_ollama = self.fallback_provider.label(sample_data)
            if label_ollama:
                label_ollama["confidence"] = min(label_ollama.get("confidence", 0.3), 0.4)
                ensemble_data = {
                    "mode": "emergency_fallback",
                    "primary_label": None,
                    "primary_provider": primary_name,
                    "kimi_label": None,
                    "agreement": None,
                }
                return label_ollama, "ollama-emergency", ensemble_data

        ens["both_failed"] = ens.get("both_failed", 0) + 1
        return None, None, None

    def save_label(self, sample_data, label, provider_name, ensemble_data=None):
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
                "has_verification": (PATHS["temporal"] / f"{page_id}.json").exists(),
                "has_ab_test": metadata.get("ab_test") is not None,
                "has_interaction": metadata.get("interaction") is not None,
                "has_session": (PATHS["sessions"] / f"{page_id}.json").exists(),
                "has_diff_analysis": metadata.get("screenshot_diff") is not None,
            },
            "label": label,
        }

        # Full traceability: store both raw model outputs + agreement
        if ensemble_data:
            output["ensemble"] = {
                "mode": ensemble_data["mode"],
                "primary_provider": ensemble_data.get("primary_provider"),
                "agreement": ensemble_data.get("agreement"),
                "raw_labels": {
                    "primary": ensemble_data.get("primary_label"),
                    "kimi": ensemble_data.get("kimi_label"),
                },
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
            vs = dp.get("verification_status", "unverifiable")
            if vs in self.stats["by_verification"]:
                self.stats["by_verification"][vs] += 1

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

    def _finalize_ensemble_stats(self):
        """Compute final ensemble metrics including Cohen's kappa."""
        if not self.ensemble:
            return

        ens = self.stats["ensemble"]

        # Average agreement scores
        if self._agreement_scores:
            ens["avg_overall_agreement"] = round(
                sum(self._agreement_scores) / len(self._agreement_scores), 3
            )
        if self._type_iou_scores:
            ens["avg_type_iou"] = round(
                sum(self._type_iou_scores) / len(self._type_iou_scores), 3
            )

        # Cohen's kappa on binary classification
        if self._binary_pairs:
            ens["cohens_kappa_binary"] = compute_cohens_kappa(self._binary_pairs)

        # Per-type kappa
        if any(self._per_type_pairs.values()):
            per_type_kappa = compute_per_type_kappa(self._per_type_pairs)
            ens["cohens_kappa_per_type"] = per_type_kappa
            # Macro-average kappa across types that had any positive labels
            active_kappas = [k for t, k in per_type_kappa.items()
                            if any(a or b for a, b in self._per_type_pairs[t])]
            if active_kappas:
                ens["cohens_kappa_type_macro"] = round(
                    sum(active_kappas) / len(active_kappas), 4
                )

    def save_summary(self):
        self._finalize_ensemble_stats()
        self.stats["completed_at"] = datetime.now().isoformat()
        with open(PATHS["labels_summary"], "w") as f:
            json.dump(self.stats, f, indent=2)

    def run(self, category_filter=None, dry_run=False, limit=None):
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

        # In ensemble mode, use the slower of the two rate limits
        if self.ensemble:
            primary_delay = OPENAI_CONFIG["delay_between_calls"] if isinstance(self.primary, OpenAILabeler) \
                else GEMINI_CONFIG["delay_between_calls"]
            delay = max(primary_delay, KIMI_CONFIG["delay_between_calls"])
        else:
            delay = (OPENAI_CONFIG["delay_between_calls"]
                     if isinstance(self.primary, OpenAILabeler)
                     else GEMINI_CONFIG["delay_between_calls"]
                     if isinstance(self.primary, GeminiLabeler)
                     else KIMI_CONFIG["delay_between_calls"]
                     if isinstance(self.primary, NvidiaKimiLabeler)
                     else OLLAMA_CONFIG["delay_between_calls"])

        for i, page_id in enumerate(unlabeled_ids):
            sample_data = collect_sample_data(page_id)
            meta = sample_data.get("metadata") or {}
            url = meta.get("url", page_id)
            category = meta.get("category", "?")
            n_diffs = len(sample_data.get("diff_paths", []))

            logger.info(f"[{i + 1}/{len(unlabeled_ids)}] {url} [{category}] "
                         f"(diffs={n_diffs}, dom={'yes' if sample_data.get('dom_text') else 'no'})")

            label, provider_name, ensemble_data = self.label_sample(sample_data)

            if label:
                self.save_label(sample_data, label, provider_name, ensemble_data)
                self.update_stats(sample_data, label, provider_name)

                has_dp = label.get("has_dark_patterns", False)
                n_patterns = len(label.get("dark_patterns", []))
                conf = label.get("confidence", 0)
                severity = label.get("overall_severity", "none")

                if has_dp:
                    types = [dp.get("type") for dp in label.get("dark_patterns", [])]
                    logger.info(f"  Result: {n_patterns} dark patterns (severity={severity}, "
                                f"conf={conf:.2f}): {types}")
                else:
                    logger.info(f"  Result: Clean page (conf={conf:.2f})")
            else:
                self.stats["failed"] += 1
                logger.error(f"  FAILED to label {page_id}")

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
        logger.info(f"Verification: {s['by_verification']}")
        logger.info(f"Data sources: {s['data_sources_used']}")
        logger.info(f"")
        if s["by_type"]:
            logger.info("Dark patterns by type:")
            for t, c in sorted(s["by_type"].items(), key=lambda x: -x[1]):
                logger.info(f"  {t:30s} {c}")

        # Ensemble-specific summary
        if self.ensemble and "ensemble" in s:
            ens = s["ensemble"]
            logger.info("")
            logger.info("-" * 60)
            logger.info("ENSEMBLE AGREEMENT REPORT")
            logger.info("-" * 60)
            total_comp = ens.get("total_compared", 0)
            logger.info(f"Samples compared by both models: {total_comp}")
            if total_comp > 0:
                pct_agree = ens["binary_agreements"] / total_comp * 100
                logger.info(f"Binary agreement:  {ens['binary_agreements']}/{total_comp} "
                            f"({pct_agree:.1f}%)")
                pct_sev = ens["severity_exact_matches"] / total_comp * 100
                logger.info(f"Severity exact:    {ens['severity_exact_matches']}/{total_comp} "
                            f"({pct_sev:.1f}%)")
                logger.info(f"Avg agreement:     {ens.get('avg_overall_agreement', 0):.3f}")
                logger.info(f"")
                logger.info(f"Cohen's kappa (binary): {ens.get('cohens_kappa_binary', 'N/A')}")
                if "cohens_kappa_type_macro" in ens:
                    logger.info(f"Cohen's kappa (type macro): {ens['cohens_kappa_type_macro']}")
                if "cohens_kappa_per_type" in ens:
                    logger.info("Cohen's kappa per type:")
                    for t, k in sorted(ens["cohens_kappa_per_type"].items(), key=lambda x: -x[1]):
                        logger.info(f"  {t:30s} {k:.4f}")

            if ens.get("primary_only_succeeded", 0):
                logger.info(f"Primary-only (Kimi failed): {ens['primary_only_succeeded']}")
            if ens.get("kimi_only_succeeded", 0):
                logger.info(f"Kimi-only (Primary failed): {ens['kimi_only_succeeded']}")
            if ens.get("both_failed", 0):
                logger.info(f"Both failed:               {ens['both_failed']}")

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
    parser.add_argument("--provider", choices=["openai", "gemini", "kimi", "ollama"], default="openai",
                        help="Primary LLM provider (default: openai = GPT-4o Mini)")
    parser.add_argument("--ensemble", action="store_true",
                        help="Run BOTH primary + Kimi on every sample, compare and merge labels")
    parser.add_argument("--flash", action="store_true",
                        help="Use Gemini 2.5 Flash instead of Flash-Lite (only when --provider gemini)")
    parser.add_argument("--no-fallback", action="store_true",
                        help="Disable fallback providers (ignored in ensemble mode)")
    parser.add_argument("--category", type=str, default=None,
                        help="Only label this category (e.g., travel)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without calling APIs")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max samples to label")

    args = parser.parse_args()
    setup_labeler_logging()

    if args.ensemble:
        primary_str = OPENAI_CONFIG["model"] if args.provider == "openai" else args.provider.capitalize()
        if args.provider == "gemini" and args.flash:
            primary_str = "Gemini Flash"
        mode_str = f"ENSEMBLE ({primary_str} + Kimi K2.5)"
    else:
        fallback_str = "off" if args.no_fallback else "kimi → ollama"
        mode_str = f"{args.provider}"
        if args.provider == "openai":
            mode_str += f" ({OPENAI_CONFIG['model']})"
        elif args.provider == "gemini":
            mode_str += f" ({'Flash' if args.flash else 'Flash-Lite'})"
        mode_str += f" | Fallback: {fallback_str}"

    logger.info("=" * 60)
    logger.info("DARK PATTERN AUTO-LABELING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Mode: {mode_str}")
    logger.info(f"Data sources: screenshots + diffs + DOM + full metadata")
    if args.category:
        logger.info(f"Category filter: {args.category}")

    try:
        pipeline = LabelingPipeline(
            provider=args.provider,
            fallback=not args.no_fallback,
            use_flash=args.flash,
            ensemble=args.ensemble,
        )
        pipeline.run(category_filter=args.category, dry_run=args.dry_run, limit=args.limit)
    except (ImportError, ValueError, RuntimeError) as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()