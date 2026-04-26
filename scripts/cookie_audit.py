# cookie_audit.py
# Audits cookies on scraped websites to classify tracking vs functional cookies

import asyncio
import argparse
import ipaddress
import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from scripts.utils import setup_log, domain_name, valid_url
except ImportError:
    from utils import setup_log, domain_name, valid_url

logger = setup_log()

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

METADATA_DIR = PROJECT_ROOT / "data" / "raw" / "metadata"

# Known tracking domains
TRACKING_DOMAINS = {
    "google-analytics.com",
    "doubleclick.net",
    "facebook.com",
    "fbcdn.net",
    "hotjar.com",
    "mixpanel.com",
    "segment.com",
    "criteo.com",
    "adnxs.com",
    "adsrvr.org",
    "amazon-adsystem.com",
    "scorecardresearch.com",
    "quantserve.com",
    "taboola.com",
    "outbrain.com",
    "rubiconproject.com",
    "pubmatic.com",
    "openx.net",
    "casalemedia.com",
    "bluekai.com",
    "krxd.net",
    "demdex.net",
    "rlcdn.com",
    "moatads.com",
    "chartbeat.com",
    "newrelic.com",
    "nr-data.net",
    "snapchat.com",
    "tiktok.com",
    "linkedin.com",
    "twitter.com",
    "pinterest.com",
    "yahoo.com",
    "bing.com",
    "yandex.ru",
}

# Known tracking cookie name patterns
TRACKING_COOKIE_NAMES = {
    "_ga", "_gid", "_gat", "_gac_", "_gat_gtag",
    "_fbp", "_fbc", "fr",
    "NID", "IDE", "DSID", "1P_JAR", "ANID", "CONSENT",
    "_gcl_au", "_gcl_aw", "_gcl_dc",
    "_uetsid", "_uetvid",
    "hubspotutk", "__hstc", "__hssc", "__hssrc",
    "_hjSession", "_hjSessionUser", "_hjid", "_hjFirstSeen",
    "_mkto_trk",
    "mp_", "distinct_id",
    "ajs_anonymous_id", "ajs_user_id",
    "_pin_unauth",
    "_tt_enable_cookie", "_ttp",
    "li_sugr", "bcookie", "lidc",
    "cto_bundle", "cto_bidid",
    "_clck", "_clsk",
    "sc_at",
    "muc_ads",
    "_rdt_uuid",
}

# Cookie name prefixes that indicate tracking
TRACKING_COOKIE_PREFIXES = (
    "_ga", "_gac_", "_gat_", "_gcl_", "_fbp", "_fbc",
    "_hj", "_mk", "mp_", "ajs_", "_tt_", "_ue", "_cl",
    "_rdt_", "cto_", "__utm",
)

# Maximum cookie age (in seconds) threshold for long-expiry heuristic: 365 days
LONG_EXPIRY_SECONDS = 365 * 24 * 60 * 60

# Per-page audit hard timeout (seconds). Prevents one stalled page from hanging the loop.
AUDIT_PAGE_TIMEOUT_SEC = 60


def _is_safe_external_url(url):
    """
    SSRF guard: accept only http(s) URLs whose resolved host is a public IP.
    Blocks file://, javascript:, RFC-1918, loopback, link-local, and metadata IPs.
    """
    if not valid_url(url):
        return False
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        # Resolve and check every returned address
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            addr = info[4][0]
            ip = ipaddress.ip_address(addr)
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_multicast or ip.is_reserved or ip.is_unspecified):
                return False
        return True
    except (socket.gaierror, ValueError, OSError):
        return False

# Common cookie banner selectors and button text patterns
BANNER_SELECTORS = [
    "[id*='cookie' i]",
    "[class*='cookie' i]",
    "[id*='consent' i]",
    "[class*='consent' i]",
    "[id*='gdpr' i]",
    "[class*='gdpr' i]",
    "[id*='privacy' i]",
    "[class*='ccpa' i]",
    "[aria-label*='cookie' i]",
    "[data-testid*='cookie' i]",
]

ACCEPT_BUTTON_PATTERNS = [
    "accept all",
    "accept cookies",
    "accept",
    "agree",
    "allow all",
    "allow cookies",
    "got it",
    "i agree",
    "ok",
    "okay",
    "consent",
    "continue",
    "close",
    "dismiss",
]


# ============================================================================
# COOKIE CLASSIFICATION
# ============================================================================

def _domain_matches_tracking(cookie_domain):
    """Check if a cookie domain belongs to a known tracking provider."""
    clean = cookie_domain.lstrip(".")
    for td in TRACKING_DOMAINS:
        if clean == td or clean.endswith("." + td):
            return True
    return False


def _name_matches_tracking(cookie_name):
    """Check if a cookie name matches known tracking cookie names or prefixes."""
    if cookie_name in TRACKING_COOKIE_NAMES:
        return True
    for prefix in TRACKING_COOKIE_PREFIXES:
        if cookie_name.startswith(prefix):
            return True
    return False


def _strip_www(host):
    """Remove a leading 'www.' PREFIX (not chars). Safe against 'www2.example.com'."""
    return host[4:] if host.startswith("www.") else host


def _is_third_party(cookie_domain, site_domain):
    """Check if the cookie domain is third-party relative to the visited site."""
    cookie_clean = cookie_domain.lstrip(".")
    site_clean = _strip_www(site_domain)
    # First-party if cookie domain matches or is a subdomain of the site
    if cookie_clean == site_clean or cookie_clean.endswith("." + site_clean):
        return False
    # Also check if site is a subdomain of the cookie domain
    if site_clean.endswith("." + cookie_clean):
        return False
    return True


def _has_long_expiry(cookie):
    """Check if a cookie has an expiration date more than 365 days from now."""
    expires = cookie.get("expires", -1)
    if expires <= 0:
        # Session cookie or no expiry set
        return False
    try:
        now_ts = datetime.now(timezone.utc).timestamp()
        remaining = expires - now_ts
        return remaining > LONG_EXPIRY_SECONDS
    except Exception:
        return False


def classify_cookie(cookie, site_domain):
    """
    Classify a single cookie as 'tracking' or 'functional'.

    Uses multiple signals:
      1. Known tracking domain
      2. Known tracking cookie name
      3. Third-party detection
      4. Long expiry heuristic (>365 days)

    Returns: dict with classification and reasons
    """
    cookie_domain = cookie.get("domain", "")
    cookie_name = cookie.get("name", "")
    reasons = []

    if _domain_matches_tracking(cookie_domain):
        reasons.append("known_tracking_domain")

    if _name_matches_tracking(cookie_name):
        reasons.append("known_tracking_name")

    third_party = _is_third_party(cookie_domain, site_domain)
    if third_party:
        reasons.append("third_party")

    long_expiry = _has_long_expiry(cookie)
    if long_expiry:
        reasons.append("long_expiry")

    # Classification logic: tracking if any strong signal or combination of weaker ones
    is_tracking = False
    if "known_tracking_domain" in reasons or "known_tracking_name" in reasons:
        is_tracking = True
    elif third_party and long_expiry:
        # Third-party cookie with long expiry is likely tracking
        is_tracking = True

    classification = "tracking" if is_tracking else "functional"

    return {
        "name": cookie_name,
        "domain": cookie_domain,
        "path": cookie.get("path", "/"),
        "secure": cookie.get("secure", False),
        "httpOnly": cookie.get("httpOnly", False),
        "sameSite": cookie.get("sameSite", "None"),
        "expires": cookie.get("expires", -1),
        "classification": classification,
        "reasons": reasons,
        "third_party": third_party,
    }


# ============================================================================
# BANNER INTERACTION
# ============================================================================

async def _find_and_click_accept(page):
    """
    Attempt to find a cookie consent banner and click the accept/allow button.

    Returns True if a button was clicked, False otherwise.
    """
    try:
        # First, look for the banner container
        for selector in BANNER_SELECTORS:
            banner = page.locator(selector).first
            if await banner.count() > 0 and await banner.is_visible():
                # Look for accept-like buttons inside the banner
                buttons = banner.locator("button, a[role='button'], [role='button'], input[type='button'], input[type='submit']")
                count = await buttons.count()
                for i in range(count):
                    btn = buttons.nth(i)
                    try:
                        text = (await btn.inner_text()).strip().lower()
                    except Exception:
                        text = ""
                    for pattern in ACCEPT_BUTTON_PATTERNS:
                        if pattern in text:
                            await btn.click(timeout=3000)
                            logger.info(f"Clicked cookie banner button: '{text}'")
                            return True

        # Fallback: look for any visible button matching accept patterns on the whole page
        all_buttons = page.locator("button, a[role='button'], [role='button']")
        count = await all_buttons.count()
        for i in range(min(count, 50)):  # limit to avoid scanning too many elements
            btn = all_buttons.nth(i)
            try:
                if not await btn.is_visible():
                    continue
                text = (await btn.inner_text()).strip().lower()
            except Exception:
                continue
            for pattern in ACCEPT_BUTTON_PATTERNS:
                if pattern in text:
                    await btn.click(timeout=3000)
                    logger.info(f"Clicked fallback button: '{text}'")
                    return True

    except Exception as e:
        logger.debug(f"Banner interaction error: {e}")

    return False


# ============================================================================
# COOKIE COLLECTION
# ============================================================================

async def _collect_cookies(context):
    """Get all cookies from the browser context."""
    cookies = await context.cookies()
    return cookies


async def audit_single_page(browser, url, page_id):
    """
    Visit a URL, record cookies before and after banner interaction,
    classify each cookie, and return the audit result.
    """
    site_domain = domain_name(url)
    logger.info(f"Auditing cookies for {url} (page_id={page_id})")

    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        viewport={"width": 1280, "height": 720},
    )
    page = await context.new_page()

    audit_result = {
        "page_id": page_id,
        "url": url,
        "domain": site_domain,
        "audited_at": datetime.now().isoformat(),
        "cookies_before_interaction": [],
        "cookies_after_interaction": [],
        "banner_found": False,
        "summary": {},
    }

    try:
        # Navigate to the page
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)  # let cookies settle

        # Record cookies BEFORE interacting with the banner
        cookies_before = await _collect_cookies(context)
        classified_before = [classify_cookie(c, site_domain) for c in cookies_before]
        audit_result["cookies_before_interaction"] = classified_before

        # Try to interact with the cookie banner
        banner_clicked = await _find_and_click_accept(page)
        audit_result["banner_found"] = banner_clicked

        if banner_clicked:
            await page.wait_for_timeout(2000)  # let new cookies arrive

        # Record cookies AFTER interaction
        cookies_after = await _collect_cookies(context)
        classified_after = [classify_cookie(c, site_domain) for c in cookies_after]
        audit_result["cookies_after_interaction"] = classified_after

        # Build summary
        tracking_before = [c for c in classified_before if c["classification"] == "tracking"]
        functional_before = [c for c in classified_before if c["classification"] == "functional"]
        tracking_after = [c for c in classified_after if c["classification"] == "tracking"]
        functional_after = [c for c in classified_after if c["classification"] == "functional"]
        third_party_after = [c for c in classified_after if c["third_party"]]

        # Cookies added after banner click
        before_names = {(c["name"], c["domain"]) for c in classified_before}
        after_names = {(c["name"], c["domain"]) for c in classified_after}
        new_cookies = after_names - before_names

        audit_result["summary"] = {
            "total_before": len(classified_before),
            "total_after": len(classified_after),
            "tracking_before": len(tracking_before),
            "tracking_after": len(tracking_after),
            "functional_before": len(functional_before),
            "functional_after": len(functional_after),
            "third_party_after": len(third_party_after),
            "new_after_interaction": len(new_cookies),
            "banner_found": banner_clicked,
        }

        logger.info(
            f"  {site_domain}: {len(classified_before)} cookies before, "
            f"{len(classified_after)} after, "
            f"{len(tracking_after)} tracking, "
            f"{len(third_party_after)} third-party"
        )

    except Exception as e:
        logger.error(f"Error auditing {url}: {e}")
        audit_result["error"] = str(e)

    finally:
        await context.close()

    return audit_result


# ============================================================================
# METADATA I/O
# ============================================================================

def load_metadata_files(limit=None, page_id=None):
    """
    Load metadata JSON files from the metadata directory.

    Returns a list of (file_path, metadata_dict) tuples.
    """
    metadata_files = []

    if page_id:
        # Load a specific page
        target = METADATA_DIR / f"{page_id}.json"
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata_files.append((target, data))
        else:
            logger.warning(f"Metadata file not found for page_id={page_id}")
        return metadata_files

    # Load all JSON files from metadata directory
    json_paths = sorted(METADATA_DIR.glob("*.json"))
    for jp in json_paths:
        if jp.name == "scraped_urls.txt":
            continue
        try:
            with open(jp, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Must have a URL to audit
            if "url" in data:
                metadata_files.append((jp, data))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping {jp.name}: {e}")

    if limit and limit > 0:
        metadata_files = metadata_files[:limit]

    logger.info(f"Loaded {len(metadata_files)} metadata files for auditing")
    return metadata_files


def save_metadata_with_audit(file_path, metadata, audit_result):
    """
    Append cookie_audit field to metadata JSON using an atomic write
    (tmp + os.replace) so a crash mid-write cannot truncate the original.
    """
    metadata["cookie_audit"] = {
        "audited_at": audit_result["audited_at"],
        "banner_found": audit_result["banner_found"],
        "cookies_before_interaction": audit_result["cookies_before_interaction"],
        "cookies_after_interaction": audit_result["cookies_after_interaction"],
        "summary": audit_result["summary"],
    }
    if "error" in audit_result:
        metadata["cookie_audit"]["error"] = audit_result["error"]

    tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, file_path)

    logger.info(f"Saved cookie audit to {file_path.name}")


# ============================================================================
# MAIN
# ============================================================================

async def run_audit(limit=None, page_id=None):
    """Run the cookie audit pipeline."""
    from playwright.async_api import async_playwright

    metadata_files = load_metadata_files(limit=limit, page_id=page_id)
    if not metadata_files:
        logger.warning("No metadata files to audit. Exiting.")
        return

    total_tracking = 0
    total_functional = 0
    total_third_party = 0
    total_banners = 0
    total_audited = 0
    total_errors = 0

    async with async_playwright() as pw:
        browser = await pw.firefox.launch(headless=True)

        for file_path, metadata in metadata_files:
            url = metadata.get("url", "")
            pid = metadata.get("page_id", file_path.stem)

            # SSRF + schema guard: skip file://, javascript:, private IPs, localhost, etc.
            if not _is_safe_external_url(url):
                logger.warning(f"Skipping unsafe URL in {file_path.name}: {url!r}")
                total_errors += 1
                continue

            # Per-page hard timeout so a hung page cannot block the whole loop
            try:
                audit_result = await asyncio.wait_for(
                    audit_single_page(browser, url, pid),
                    timeout=AUDIT_PAGE_TIMEOUT_SEC,
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Audit timeout after {AUDIT_PAGE_TIMEOUT_SEC}s for {url}"
                )
                audit_result = {
                    "page_id": pid, "url": url,
                    "domain": domain_name(url),
                    "audited_at": datetime.now().isoformat(),
                    "cookies_before_interaction": [],
                    "cookies_after_interaction": [],
                    "banner_found": False,
                    "summary": {}, "error": "audit_timeout",
                }

            # Save audit result back into the metadata file
            save_metadata_with_audit(file_path, metadata, audit_result)
            total_audited += 1

            # Accumulate summary stats
            summary = audit_result.get("summary", {})
            total_tracking += summary.get("tracking_after", 0)
            total_functional += summary.get("functional_after", 0)
            total_third_party += summary.get("third_party_after", 0)
            if summary.get("banner_found", False):
                total_banners += 1
            if "error" in audit_result:
                total_errors += 1

        await browser.close()

    # Print final summary
    logger.info("=" * 60)
    logger.info("COOKIE AUDIT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  Pages audited:       {total_audited}")
    logger.info(f"  Errors:              {total_errors}")
    logger.info(f"  Cookie banners found:{total_banners}")
    logger.info(f"  Total tracking:      {total_tracking}")
    logger.info(f"  Total functional:    {total_functional}")
    logger.info(f"  Total third-party:   {total_third_party}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="DarkSite Cookie Audit - classify tracking vs functional cookies"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum number of pages to audit"
    )
    parser.add_argument(
        "--page-id", type=str, default=None,
        help="Audit a specific page by its page ID"
    )
    args = parser.parse_args()

    asyncio.run(run_audit(limit=args.limit, page_id=args.page_id))


if __name__ == "__main__":
    main()
