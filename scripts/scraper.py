# scraper.py
# Complete Dark Pattern Detection Scraper with Advanced Robustness Features

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image
import imagehash

try:
    from scripts.utils import setup_log, get_page_id, domain_name, load_complete_urls, save_completed_website, valid_url
except ImportError:
    from utils import setup_log, get_page_id, domain_name, load_complete_urls, save_completed_website, valid_url

logger = setup_log()

# Alias for backward compatibility within scraper.py
generate_page_id = get_page_id
get_domain = domain_name

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG = {
    "output_dir": str(PROJECT_ROOT / "data"), #output directory
    "screenshots_dir": str(PROJECT_ROOT / "data/raw/screenshots"), #screenshot directory
    "dom_dir": str(PROJECT_ROOT / "data/raw/dom"),  #dom directory
    "temporal_dir": str(PROJECT_ROOT / "data/raw/temporal"), #temporal directory
    "session_dir": str(PROJECT_ROOT / "data/raw/sessions"), #session directory
    "diff_dir": str(PROJECT_ROOT / "data/raw/diffs"), #diff directory
    "metadata_dir": str(PROJECT_ROOT / "data/raw/metadata"), #metadata directory
    
    # Timeouts
    "page_timeout": 30000,
    "action_timeout": 5000,
    
    # Verification settings
    "temporal_visits": 3, #how many times to visit the same page
    "temporal_interval": 10,  # seconds between visits
    "ab_test_profiles": 3, #how many user profiles to use for AB Testing
    
    # Rate limiting
    #this is used as the webistes have security systems that detect non-human behavior
    #if 100 sites are scraped in 1 second, then the website may consider it as a bot attack
    "delay_between_pages": 2,  # seconds
    
    # Screenshot settings
    "full_page_screenshot": True, 
    "screenshot_quality": 80,
    
    # Screenshot diff thresholds
    "diff_no_change_threshold": 3,
    "diff_dynamic_content_min": 5,
    "diff_dynamic_content_max": 20,
    "diff_significant_change": 10
}

# Create directories if not already existing
for dir_path in [CONFIG["output_dir"], CONFIG["screenshots_dir"], 
                 CONFIG["dom_dir"], CONFIG["temporal_dir"], 
                 CONFIG["session_dir"], CONFIG["diff_dir"], CONFIG["metadata_dir"]]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)


# ============================================================================
# DARK PATTERN DEFINITIONS
# ============================================================================

#Scarcity: Creating a false sense of limited availability
DARK_PATTERNS = {
    "scarcity": [
        r"only \d+ left",
        r"\d+ (items? )?left",
        r"\d+ (people|users|customers) (are )?(viewing|watching|looking)",
        r"limited (stock|availability|time|quantity)",
        r"selling fast",
        r"high demand",
        r"almost (sold out|gone)",
        r"hurry",
        r"don't miss",
        r"last chance",
        r"ends (soon|today|tonight)",
        r"low stock",
        r"few left",
        r"running (low|out)",
        r"while (supplies|stocks?) last",
        r"exclusive (offer|deal|access)",
        r"rare find",
        r"\d+ (bought|sold|purchased) (in last|today|recently)",
        r"in \d+ carts?",
        r"\d+ rooms? left",
        r"\d+ seats? left",
        r"\d+ tickets? left",
        r"booked \d+ times",
        r"likely to sell out"
    ],

    #creating a false sense of urgency
    "urgency": [
        r"offer expires",
        r"deal ends",
        r"sale ends",
        r"expires in",
        r"only (today|tonight|now)",
        r"today only",
        r"flash sale",
        r"limited time",
        r"act (fast|now|quickly)",
        r"before it'?s gone",
        r"won'?t last( long)?",
        r"ending soon",
        r"\d+:\d+:\d+",  # Timer format HH:MM:SS
        r"\d+h \d+m",    # Timer format Xh Xm
        r"hours? left",
        r"minutes? left",
        r"seconds? left",
        r"time is running out",
        r"clock is ticking",
        r"order within"
    ],
    
    #creating false social proof
    "social_proof": [
        r"\d+\+? (people|customers|users) (bought|purchased|ordered)",
        r"\d+\+? (reviews?|ratings?)",
        r"best seller",
        r"most popular",
        r"trending( now)?",
        r"hot (item|deal|product)",
        r"as seen on",
        r"trusted by \d+",
        r"join \d+\+? (customers|users|members)",
        r"★|⭐",
        r"\d+(\.\d+)? out of \d+ stars?",
        r"verified (purchase|buyer|review)",
        r"someone (just )?(bought|purchased)",
        r"recently (bought|purchased|viewed)"
    ],
    
    #making the user feel guilty for not taking an action
    "confirmshaming": [
        r"no,? thanks,? i (don'?t|do not) (want|like|need)",
        r"i (don'?t|do not) (want|like) (saving|discounts?|money|deals?)",
        r"i'?ll pay full price",
        r"i (hate|don'?t like) (savings?|deals?|discounts?)",
        r"no,? i prefer to pay more",
        r"i'?m not interested in saving",
        r"continue without",
        r"miss out",
        r"i'?ll pass on",
        r"not for me",
        r"maybe later",
        r"remind me never"
    ],
    
    #drawing attention away from important information
    "misdirection": [
        r"recommended",
        r"best (value|choice|deal)",
        r"most popular( choice)?",
        r"selected for you",
        r"personalized",
        r"upgrade",
        r"premium",
        r"pro version"
    ],
    
    #adding hidden costs
    "hidden_costs": [
        r"service fee",
        r"handling fee",
        r"processing fee",
        r"convenience fee",
        r"booking fee",
        r"admin(istration)? fee",
        r"taxes? (and|&) fees?",
        r"additional charges?",
        r"extra charges?"
    ],
    
    #forcing the user to take an action
    "forced_action": [
        r"create (an )?account to continue",
        r"sign up to (view|see|access)",
        r"register to",
        r"login required",
        r"subscribe to continue",
        r"enter email to"
    ]
}

# Compile patterns for efficiency
COMPILED_PATTERNS = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in DARK_PATTERNS.items()
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================



#matching patterns in the text based on the category
def match_patterns(text, category):
    matches = []
    for pattern in COMPILED_PATTERNS.get(category, []):
        found = pattern.findall(text)
        if found:
            matches.extend(found)
    return matches


# ============================================================================
# USER PROFILES FOR A/B TESTING
# ============================================================================

#getting different user profiles for ab testing
#this helps in simulating different user behaviors on the website
#this is done to check how the website responds to different user behaviors

USER_PROFILES = [
    {
        "name": "new_desktop_user",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
        "cookies": []
    },
    {
        #this is the returning user profile as the location and timezone are same
        "name": "returning_user",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "geolocation": {"latitude": 40.7128, "longitude": -74.0060},
        "cookies": [
            {"name": "returning_visitor", "value": "true"},
            {"name": "visit_count", "value": "5"}
        ]
    },
    {
        #mobile user profile with different location and timezone
        "name": "mobile_user",
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 390, "height": 844},
        "locale": "en-US",
        "timezone_id": "America/Los_Angeles",
        "geolocation": {"latitude": 34.0522, "longitude": -118.2437},
        "cookies": [],
        "is_mobile": True
    },
    {
        #user profile in another country.
        "name": "eu_user",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-GB",
        "timezone_id": "Europe/London",
        "geolocation": {"latitude": 51.5074, "longitude": -0.1278},
        "cookies": []
    }
]


# ============================================================================
# MAIN SCRAPER CLASS
# ============================================================================

class DarkPatternScraper:
    """
    Comprehensive dark pattern detection scraper with:
    - Basic pattern detection
    - Temporal verification
    - A/B test detection
    - Interaction-based detection
    - Session simulation
    - Screenshot diff analysis
    """
    
    def __init__(self, config=None):
        self.config = config or CONFIG
        self.results = []
        
    # ========================================================================
    # CORE EXTRACTION - Runs on every page (fast)
    # ========================================================================
    
    async def extract_dark_patterns(self, page):
        """
        Extract all dark pattern indicators from page.
        This is the main extraction that runs on every page.
        """
        
        extraction_script = r'''() => {
            const result = {
                url: window.location.href,
                timestamp: new Date().toISOString(),
                
                // Pattern matches
                scarcity: [],
                urgency: [],
                socialProof: [],
                confirmshaming: [],
                misdirection: [],
                hiddenCosts: [],
                forcedAction: [],
                
                // UI elements
                countdowns: [],
                precheckedBoxes: [],
                buttons: [],
                modals: [],
                cookieBanners: [],
                hiddenElements: [],
                
                // Prices
                prices: {
                    current: null,
                    original: null,
                    discount: null
                },
                
                // Page metadata
                metadata: {
                    title: document.title,
                    hasLoginWall: false,
                    hasNewsletterPopup: false,
                    totalTextLength: document.body?.innerText?.length || 0
                }
            };
            
            // Helper: Get bounding box
            const getBbox = (el) => {
                const rect = el.getBoundingClientRect();
                return {
                    x: Math.round(rect.x),
                    y: Math.round(rect.y),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                };
            };
            
            // Helper: Check if element is visible
            const isVisible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       parseFloat(style.opacity) > 0 &&
                       rect.width > 0 && rect.height > 0;
            };
            
            // ============================================================
            // 1. COUNTDOWN TIMERS
            // ============================================================
            const timerSelectors = [
                '[class*="countdown"]', '[class*="timer"]', '[class*="clock"]',
                '[class*="expires"]', '[class*="ends-in"]', '[data-countdown]'
            ];
            
            timerSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (isVisible(el)) {
                        const text = el.innerText?.trim();
                        if (text && text.length < 100) {
                            result.countdowns.push({
                                text: text,
                                bbox: getBbox(el),
                                classes: el.className,
                                hasNumbers: /\d/.test(text)
                            });
                        }
                    }
                });
            });
            
            // Also find timers by content pattern
            document.querySelectorAll('*').forEach(el => {
                const text = el.innerText?.trim();
                if (text && /^\d{1,2}:\d{2}(:\d{2})?$/.test(text)) {
                    if (isVisible(el) && !result.countdowns.some(c => c.text === text)) {
                        result.countdowns.push({
                            text: text,
                            bbox: getBbox(el),
                            classes: el.className,
                            hasNumbers: true,
                            detectedByPattern: true
                        });
                    }
                }
            });
            
            // ============================================================
            // 2. PRE-CHECKED BOXES
            // ============================================================
            document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
                const label = cb.closest('label')?.innerText || 
                             document.querySelector(`label[for="${cb.id}"]`)?.innerText ||
                             cb.parentElement?.innerText || '';
                
                const isSuspicious = /(newsletter|marketing|email|subscribe|offers|promotions|partners|terms|agree|consent|opt|notify|updates|news|deals)/i.test(label);
                
                result.precheckedBoxes.push({
                    label: label.trim().slice(0, 300),
                    name: cb.name,
                    id: cb.id,
                    bbox: getBbox(cb),
                    isSuspicious: isSuspicious,
                    isRequired: cb.required
                });
            });
            
            // ============================================================
            // 3. BUTTONS (for asymmetry detection)
            // ============================================================
            const buttonSelectors = 'button, [role="button"], input[type="submit"], input[type="button"], a[class*="btn"], a[class*="button"]';
            
            document.querySelectorAll(buttonSelectors).forEach(btn => {
                if (!isVisible(btn)) return;
                
                const text = btn.innerText?.trim() || btn.value || '';
                if (!text || text.length > 100) return;
                
                const styles = window.getComputedStyle(btn);
                const rect = btn.getBoundingClientRect();
                
                const isPositive = /(accept|agree|yes|continue|ok|got it|allow|add|buy|subscribe|sign up|submit|confirm|checkout|proceed)/i.test(text);
                const isNegative = /(decline|reject|no|cancel|skip|later|close|dismiss|not now|no thanks|maybe later)/i.test(text);
                
                result.buttons.push({
                    text: text,
                    bbox: getBbox(btn),
                    area: Math.round(rect.width * rect.height),
                    styles: {
                        backgroundColor: styles.backgroundColor,
                        color: styles.color,
                        fontSize: styles.fontSize,
                        fontWeight: styles.fontWeight,
                        border: styles.border,
                        opacity: styles.opacity
                    },
                    isPositive: isPositive,
                    isNegative: isNegative,
                    tag: btn.tagName.toLowerCase()
                });
            });
            
            // ============================================================
            // 4. MODALS & POPUPS
            // ============================================================
            const modalSelectors = [
                '[class*="modal"]', '[class*="popup"]', '[class*="overlay"]',
                '[class*="dialog"]', '[role="dialog"]', '[class*="lightbox"]',
                '[class*="interstitial"]', '[class*="banner"]'
            ];
            
            modalSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (!isVisible(el)) return;
                    
                    const rect = el.getBoundingClientRect();
                    // Only count if it's a significant overlay
                    if (rect.width < 200 || rect.height < 100) return;
                    
                    const text = el.innerText?.trim().slice(0, 500) || '';
                    
                    result.modals.push({
                        bbox: getBbox(el),
                        classes: el.className,
                        textPreview: text.slice(0, 200),
                        coversFullScreen: rect.width > window.innerWidth * 0.8 && rect.height > window.innerHeight * 0.8,
                        hasCloseButton: el.querySelector('[class*="close"], [aria-label*="close"], button') !== null
                    });
                });
            });
            
            // ============================================================
            // 5. COOKIE BANNERS
            // ============================================================
            const cookieSelectors = [
                '[class*="cookie"]', '[class*="consent"]', '[class*="gdpr"]',
                '[class*="privacy"]', '[id*="cookie"]', '[id*="consent"]'
            ];
            
            cookieSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    if (!isVisible(el)) return;
                    
                    const rect = el.getBoundingClientRect();
                    if (rect.width < 200) return;
                    
                    const buttons = Array.from(el.querySelectorAll('button, a[class*="btn"]')).map(btn => ({
                        text: btn.innerText?.trim(),
                        area: btn.getBoundingClientRect().width * btn.getBoundingClientRect().height,
                        styles: {
                            backgroundColor: window.getComputedStyle(btn).backgroundColor,
                            fontSize: window.getComputedStyle(btn).fontSize
                        }
                    }));
                    
                    result.cookieBanners.push({
                        bbox: getBbox(el),
                        classes: el.className,
                        textPreview: el.innerText?.trim().slice(0, 300),
                        buttons: buttons,
                        hasRejectAll: buttons.some(b => /(reject|decline|deny|refuse)/i.test(b.text)),
                        hasAcceptAll: buttons.some(b => /(accept|agree|allow|ok|got it)/i.test(b.text))
                    });
                });
            });
            
            // ============================================================
            // 6. HIDDEN/DECEPTIVE ELEMENTS
            // ============================================================
            document.querySelectorAll('a, button, span, div').forEach(el => {
                const text = el.innerText?.trim();
                if (!text || text.length > 100) return;
                
                // Check for decline/close options that might be hidden
                if (/(no thanks|skip|decline|close|dismiss|cancel|not now)/i.test(text)) {
                    const styles = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    
                    const isHidden = 
                        parseFloat(styles.opacity) < 0.7 ||
                        parseFloat(styles.fontSize) < 11 ||
                        rect.width < 50 ||
                        styles.color === styles.backgroundColor ||
                        rect.x < 0 || rect.y < 0;
                    
                    if (isHidden) {
                        result.hiddenElements.push({
                            text: text,
                            bbox: getBbox(el),
                            reason: parseFloat(styles.opacity) < 0.7 ? 'low_opacity' :
                                   parseFloat(styles.fontSize) < 11 ? 'small_font' :
                                   rect.width < 50 ? 'small_width' :
                                   'color_blend',
                            styles: {
                                opacity: styles.opacity,
                                fontSize: styles.fontSize,
                                color: styles.color
                            }
                        });
                    }
                }
            });
            
            // ============================================================
            // 7. PRICES
            // ============================================================
            const pricePattern = /[\$\€\£]\s*(\d+[.,]?\d*)/;
            
            // Current price
            const currentPriceSelectors = [
                '[class*="price-current"]', '[class*="sale-price"]', '[class*="final-price"]',
                '[class*="priceAmount"]', '.a-price .a-offscreen', '[data-price]',
                '[class*="price"] [class*="now"]'
            ];
            
            for (const selector of currentPriceSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    const text = el.innerText || el.getAttribute('data-price') || '';
                    const match = text.match(pricePattern);
                    if (match) {
                        result.prices.current = parseFloat(match[1].replace(',', '.'));
                        break;
                    }
                }
            }
            
            // Original price
            const originalPriceSelectors = [
                '[class*="price-original"]', '[class*="was-price"]', '[class*="list-price"]',
                '[class*="rrp"]', '.a-text-price', '[class*="strike"]', 's', 'del',
                '[class*="price"] [class*="was"]'
            ];
            
            for (const selector of originalPriceSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    const text = el.innerText || '';
                    const match = text.match(pricePattern);
                    if (match) {
                        result.prices.original = parseFloat(match[1].replace(',', '.'));
                        break;
                    }
                }
            }
            
            // Calculate discount
            if (result.prices.current && result.prices.original && result.prices.original > result.prices.current) {
                result.prices.discount = Math.round((1 - result.prices.current / result.prices.original) * 100);
            }
            
            // Look for claimed discount
            const discountMatch = document.body.innerText.match(/(\d+)\s*%\s*off/i);
            if (discountMatch) {
                result.prices.claimedDiscount = parseInt(discountMatch[1]);
            }
            
            // ============================================================
            // 8. TEXT PATTERN MATCHING
            // ============================================================
            const bodyText = document.body?.innerText || '';
            
            // Scarcity patterns
            const scarcityPatterns = [
                /only (\d+) left/gi,
                /(\d+) (items? )?left/gi,
                /(\d+) (people|users|customers) (are )?(viewing|watching)/gi,
                /limited (stock|availability|time|quantity)/gi,
                /selling fast/gi,
                /high demand/gi,
                /almost (sold out|gone)/gi,
                /low stock/gi,
                /while supplies last/gi,
                /in (\d+) carts?/gi
            ];
            
            scarcityPatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    result.scarcity.push(...matches.map(m => m.trim()));
                }
            });
            
            // Social proof patterns
            const socialPatterns = [
                /(\d+[\d,]*)\+? (people|customers|users) (bought|purchased|ordered)/gi,
                /(\d+[\d,]*)\+? (reviews?|ratings?)/gi,
                /best seller/gi,
                /trending( now)?/gi,
                /most popular/gi,
                /someone (just )?(bought|purchased)/gi
            ];
            
            socialPatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    result.socialProof.push(...matches.map(m => m.trim()));
                }
            });
            
            // Confirmshaming patterns
            const confirmshamePatterns = [
                /no,? thanks,? i (don'?t|do not) (want|like|need)/gi,
                /i (don'?t|do not) (want|like) (saving|discounts?|money)/gi,
                /i'?ll pay full price/gi,
                /continue without/gi
            ];
            
            confirmshamePatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    result.confirmshaming.push(...matches.map(m => m.trim()));
                }
            });
            
            // Urgency patterns
            const urgencyPatterns = [
                /offer expires/gi,
                /deal ends/gi,
                /sale ends/gi,
                /limited time/gi,
                /act (fast|now|quickly)/gi,
                /order within/gi,
                /ends (soon|today|tonight)/gi
            ];
            
            urgencyPatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    result.urgency.push(...matches.map(m => m.trim()));
                }
            });
            
            // Hidden costs patterns
            const hiddenCostPatterns = [
                /service fee/gi,
                /handling fee/gi,
                /processing fee/gi,
                /convenience fee/gi,
                /booking fee/gi,
                /taxes? (and|&) fees?/gi
            ];
            
            hiddenCostPatterns.forEach(pattern => {
                const matches = bodyText.match(pattern);
                if (matches) {
                    result.hiddenCosts.push(...matches.map(m => m.trim()));
                }
            });
            
            // ============================================================
            // 9. METADATA CHECKS
            // ============================================================
            // Login wall detection
            result.metadata.hasLoginWall = !!(
                document.querySelector('[class*="login-wall"]') ||
                document.querySelector('[class*="signin-required"]') ||
                bodyText.match(/sign in to (view|continue|access)/i)
            );
            
            // Newsletter popup detection
            result.metadata.hasNewsletterPopup = !!(
                document.querySelector('[class*="newsletter"][class*="popup"]') ||
                document.querySelector('[class*="subscribe"][class*="modal"]') ||
                (result.modals.some(m => /(newsletter|subscribe|email|sign up)/i.test(m.textPreview)))
            );
            
            // Remove duplicates
            result.scarcity = [...new Set(result.scarcity)];
            result.socialProof = [...new Set(result.socialProof)];
            result.confirmshaming = [...new Set(result.confirmshaming)];
            result.urgency = [...new Set(result.urgency)];
            result.hiddenCosts = [...new Set(result.hiddenCosts)];
            
            return result;
        }''';
        
        try:
            return await page.evaluate(extraction_script)
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None


################# TEMPORAL VERIFICATION - Detects fake dynamic content #################
    
    async def temporal_verification(self, page, url, visits=3, interval=10):

        # Visit page multiple times to detect fake urgency/scarcity.
        # Returns analysis of what changed vs what stayed static.

        snapshots = []
        
        for i in range(visits):
            if i > 0:
                await asyncio.sleep(interval)
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(1)
            
            snapshot = await page.evaluate(r'''() => {
                const snapshot = {
                    timestamp: new Date().toISOString(),
                    stockClaims: [],
                    viewerCounts: [],
                    countdownValues: [],
                    cartCounts: []
                };
                
                const bodyText = document.body?.innerText || '';
                
                // Stock claims - to detect fake scarcity
                const stockMatches = bodyText.match(/only (\d+) left|(\d+) (items? )?left|(\d+) in stock/gi);
                if (stockMatches) {
                    stockMatches.forEach(m => {
                        const num = m.match(/\d+/);
                        if (num) snapshot.stockClaims.push(parseInt(num[0]));
                    });
                }
                
                // Viewer counts - to detect fake urgency
                const viewerMatches = bodyText.match(/(\d+) (people|users|customers|viewers?) (are )?(viewing|watching|looking)/gi);
                if (viewerMatches) {
                    viewerMatches.forEach(m => {
                        const num = m.match(/\d+/);
                        if (num) snapshot.viewerCounts.push(parseInt(num[0]));
                    });
                }
                
                // Cart counts - also used to detect fake urgency.
                const cartMatches = bodyText.match(/in (\d+) carts?|(\d+) (have|has) this in/gi);
                if (cartMatches) {
                    cartMatches.forEach(m => {
                        const num = m.match(/\d+/);
                        if (num) snapshot.cartCounts.push(parseInt(num[0]));
                    });
                }
                
                // Countdown values - also used to detect fake urgency
                document.querySelectorAll('[class*="countdown"], [class*="timer"]').forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && /\d/.test(text)) {
                        snapshot.countdownValues.push(text);
                    }
                });
                
                return snapshot;
            }''')
            
            snapshots.append(snapshot)
        
        # Analyze temporal consistency
        analysis = self._analyze_temporal_data(snapshots)
        
        return {
            "snapshots": snapshots,
            "analysis": analysis
        }
    
    def _analyze_temporal_data(self, snapshots):
        
        # Analyze snapshots for suspicious patterns.
        
        analysis = {
            "stock_suspicious": False,
            "viewers_suspicious": False,
            "countdown_suspicious": False,
            "cart_suspicious": False,
            "reasons": []
        }
        
        if len(snapshots) < 2:
            return analysis
        
        # Check stock claims
        all_stock = [s["stockClaims"] for s in snapshots if s["stockClaims"]]
        if all_stock and len(all_stock) >= 2:
            flat_stock = [item for sublist in all_stock for item in sublist]
            if len(set(flat_stock)) == 1 and len(flat_stock) > 1:
                analysis["stock_suspicious"] = True
                analysis["reasons"].append(f"Stock count static ({flat_stock[0]}) across {len(snapshots)} visits")
        
        # Check viewer counts
        all_viewers = [s["viewerCounts"] for s in snapshots if s["viewerCounts"]]
        if all_viewers and len(all_viewers) >= 2:
            flat_viewers = [item for sublist in all_viewers for item in sublist]
            if len(set(flat_viewers)) == 1 and len(flat_viewers) > 1:
                analysis["viewers_suspicious"] = True
                analysis["reasons"].append(f"Viewer count static ({flat_viewers[0]}) across visits")
            # Also check for suspiciously round numbers
            elif all(v % 5 == 0 for v in flat_viewers):
                analysis["viewers_suspicious"] = True
                analysis["reasons"].append("All viewer counts are round numbers")
        
        # Check cart counts
        all_carts = [s["cartCounts"] for s in snapshots if s["cartCounts"]]
        if all_carts and len(all_carts) >= 2:
            flat_carts = [item for sublist in all_carts for item in sublist]
            if len(set(flat_carts)) == 1 and len(flat_carts) > 1:
                analysis["cart_suspicious"] = True
                analysis["reasons"].append(f"Cart count static ({flat_carts[0]}) across visits")
        
        # Check countdowns - should be decreasing
        all_countdowns = [s["countdownValues"] for s in snapshots if s["countdownValues"]]
        if all_countdowns and len(all_countdowns) >= 2:
            # If countdown values are identical, it's suspicious
            if all_countdowns[0] == all_countdowns[-1]:
                analysis["countdown_suspicious"] = True
                analysis["reasons"].append("Countdown timer did not change between visits")
        
        analysis["is_suspicious"] = any([
            analysis["stock_suspicious"],
            analysis["viewers_suspicious"],
            analysis["countdown_suspicious"],
            analysis["cart_suspicious"]
        ])
        
        return analysis

################# A/B TEST DETECTION - Detects personalized manipulation #################
    
    async def ab_test_detection(self, url, num_profiles=3, playwright_instance=None):
        
        # Visit page with different user profiles to detect personalization.
        
        results = []
        profiles_to_use = USER_PROFILES[:num_profiles]
        
        async def _run_ab_tests(p):
            for profile in profiles_to_use:
                browser = await p.chromium.launch(headless=True)
                
                context_options = {
                    "user_agent": profile["user_agent"],
                    "viewport": profile["viewport"],
                    "locale": profile["locale"],
                    "timezone_id": profile["timezone_id"],
                    "geolocation": profile.get("geolocation"),
                    "permissions": ["geolocation"] if profile.get("geolocation") else []
                }
                
                context = await browser.new_context(**context_options)
                
                # Add cookies with proper URL domain
                if profile.get("cookies"):
                    cookies_with_domain = []
                    for cookie in profile["cookies"]:
                        cookie_copy = cookie.copy()
                        cookie_copy["url"] = url
                        cookies_with_domain.append(cookie_copy)
                    await context.add_cookies(cookies_with_domain)
                
                page = await context.new_page()
                
                try:
                    await page.goto(url, timeout=self.config["page_timeout"])
                    await asyncio.sleep(2)
                    
                    # Extract key indicators
                    indicators = await page.evaluate(r'''() => {
                        const bodyText = document.body?.innerText || '';
                        
                        return {
                            // Prices
                            prices: Array.from(document.querySelectorAll('[class*="price"]'))
                                .map(el => el.innerText?.trim())
                                .filter(t => t && /[\$\€\£]\d/.test(t))
                                .slice(0, 5),
                            
                            // Discounts
                            discounts: (bodyText.match(/\d+%\s*off/gi) || []).slice(0, 5),
                            
                            // Urgency message count
                            urgencyCount: (bodyText.match(/(only \d+ left|limited|hurry|ends soon)/gi) || []).length,
                            
                            // Has popup on load
                            hasPopup: document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"])').length > 0,
                            
                            // Scarcity messages
                            scarcityMessages: (bodyText.match(/only \d+ left|\d+ left in stock/gi) || []).slice(0, 5),
                            
                            // Social proof numbers
                            socialProofNumbers: (bodyText.match(/\d+\+? (bought|sold|viewing|watching)/gi) || []).slice(0, 5)
                        };
                    }''')
                    
                    results.append({
                        "profile": profile["name"],
                        "indicators": indicators
                    })
                    
                except Exception as e:
                    logger.error(f"A/B test error for {profile['name']}: {e}")
                    results.append({
                        "profile": profile["name"],
                        "error": str(e)
                    })
                
                await browser.close()
        
        # Run with provided instance or create a new one
        if playwright_instance:
            await _run_ab_tests(playwright_instance)
        else:
            async with async_playwright() as p:
                await _run_ab_tests(p)
        
        # Analyze differences
        analysis = self._analyze_ab_results(results)
        
        return {
            "results": results,
            "analysis": analysis
        }
    
    #analysze the differences obtained from AB Testing and one which was original.
    def _analyze_ab_results(self, results):
        
        # Analyze A/B test results for personalization.

        analysis = {
            "personalization_detected": False,
            "differences": [],
            "severity": "none"
        }
        
        valid_results = [r for r in results if "indicators" in r]
        if len(valid_results) < 2:
            return analysis
        
        baseline = valid_results[0]["indicators"]
        
        for result in valid_results[1:]:
            profile = result["profile"]
            indicators = result["indicators"]
            
            # Price differences
            if set(baseline.get("prices", [])) != set(indicators.get("prices", [])):
                analysis["differences"].append({
                    "type": "price_discrimination",
                    "profile": profile,
                    "baseline": baseline.get("prices"),
                    "variant": indicators.get("prices")
                })
            
            # Urgency targeting
            baseline_urgency = baseline.get("urgencyCount", 0)
            variant_urgency = indicators.get("urgencyCount", 0)
            if abs(baseline_urgency - variant_urgency) > 2:
                analysis["differences"].append({
                    "type": "urgency_targeting",
                    "profile": profile,
                    "baseline_count": baseline_urgency,
                    "variant_count": variant_urgency
                })
            
            # Popup targeting
            if baseline.get("hasPopup") != indicators.get("hasPopup"):
                analysis["differences"].append({
                    "type": "popup_targeting",
                    "profile": profile,
                    "baseline": baseline.get("hasPopup"),
                    "variant": indicators.get("hasPopup")
                })
            
            # Discount differences
            if set(baseline.get("discounts", [])) != set(indicators.get("discounts", [])):
                analysis["differences"].append({
                    "type": "discount_discrimination",
                    "profile": profile,
                    "baseline": baseline.get("discounts"),
                    "variant": indicators.get("discounts")
                })
        
        if analysis["differences"]:
            analysis["personalization_detected"] = True
            analysis["severity"] = "high" if len(analysis["differences"]) > 2 else "medium"
        
        return analysis


################# INTERACTION-BASED DETECTION - Triggers hidden dark patterns #################

    
    async def interaction_detection(self, page):

        # Perform interactions to trigger hidden dark patterns.

        interactions = {
            #different types of hidden dark patterns that might get trigerred from:
            "scroll_triggered": [],
            "exit_intent_triggered": [],
            "idle_triggered": [],
            "click_triggered": [],
            "decline_response": None
        }
        
        # Count initial modals
        initial_modals = await page.evaluate(r'''() => {
            return document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"])').length;
        }''')
        
        # 1. SCROLL TRIGGER
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await asyncio.sleep(1)
        
        scroll_modals = await page.evaluate(r'''() => {
            const modals = document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"])');
            return Array.from(modals).map(m => ({
                classes: m.className,
                text: m.innerText?.slice(0, 200)
            }));
        }''')
        
        if len(scroll_modals) > initial_modals:
            interactions["scroll_triggered"] = scroll_modals[initial_modals:]
        
        # 2. EXIT INTENT TRIGGER (move mouse to top of page)
        try:
            await page.mouse.move(500, 0)
            await asyncio.sleep(0.5)
            await page.mouse.move(500, -10)  # Move above viewport
            await asyncio.sleep(1)
            
            exit_modals = await page.evaluate(r'''() => {
                const modals = document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"]), [class*="exit"]:not([style*="display: none"])');
                return Array.from(modals).map(m => ({
                    classes: m.className,
                    text: m.innerText?.slice(0, 200)
                }));
            }''')
            
            current_count = len(scroll_modals) if scroll_modals else initial_modals
            if len(exit_modals) > current_count:
                interactions["exit_intent_triggered"] = exit_modals[current_count:]
        except Exception:
            pass
        
        # 3. IDLE TRIGGER (wait without interaction)
        await asyncio.sleep(3)
        
        idle_modals = await page.evaluate(r'''() => {
            const modals = document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"])');
            return Array.from(modals).map(m => ({
                classes: m.className,
                text: m.innerText?.slice(0, 200)
            }));
        }''')
        
        prev_count = len(exit_modals) if interactions["exit_intent_triggered"] else (len(scroll_modals) if interactions["scroll_triggered"] else initial_modals)
        if len(idle_modals) > prev_count:
            interactions["idle_triggered"] = idle_modals[prev_count:]
        
        # 4. DECLINE BUTTON RESPONSE
        decline_response = await page.evaluate(r'''() => {
            const declineButtons = Array.from(document.querySelectorAll('button, a')).filter(el => {
                const text = el.innerText?.toLowerCase() || '';
                return /(no thanks|skip|decline|close|dismiss|not now|maybe later|cancel)/i.test(text);
            });
            
            if (declineButtons.length > 0) {
                return {
                    found: true,
                    buttons: declineButtons.slice(0, 3).map(b => ({
                        text: b.innerText?.trim(),
                        classes: b.className
                    }))
                };
            }
            return { found: false };
        }''')
        
        # Try clicking a decline button and see what happens
        if decline_response and isinstance(decline_response, dict) and decline_response.get("found"):
            try:
                decline_selector = await page.evaluate(r'''() => {
                    const btn = Array.from(document.querySelectorAll('button, a')).find(el => {
                        const text = el.innerText?.toLowerCase() || '';
                        return /(no thanks|skip|decline|maybe later)/i.test(text);
                    });
                    if (btn) {
                        btn.setAttribute('data-decline-test', 'true');
                        return '[data-decline-test="true"]';
                    }
                    return null;
                }''')
                
                if decline_selector:
                    await page.click(decline_selector, timeout=2000)
                    await asyncio.sleep(1)
                    
                    # Check for guilt-trip or new popup
                    post_decline = await page.evaluate(r'''() => {
                        const bodyText = document.body?.innerText || '';
                        const newModals = document.querySelectorAll('[class*="modal"]:not([style*="display: none"])');
                        
                        return {
                            hasNewModal: newModals.length > 0,
                            guiltTrip: /(are you sure|missing out|last chance|wait|don't go)/i.test(bodyText),
                            modalText: newModals.length > 0 ? newModals[0].innerText?.slice(0, 200) : null
                        };
                    }''')
                    
                    interactions["decline_response"] = post_decline
            except Exception:
                pass
        
        # Analyze interaction results
        interactions["analysis"] = {
            "has_scroll_trap": len(interactions["scroll_triggered"]) > 0,
            "has_exit_intent": len(interactions["exit_intent_triggered"]) > 0,
            "has_idle_popup": len(interactions["idle_triggered"]) > 0,
            "has_decline_guilt": interactions.get("decline_response", {}).get("guiltTrip", False) if isinstance(interactions.get("decline_response"), dict) else False,
            "total_triggered_popups": (
                len(interactions["scroll_triggered"]) +
                len(interactions["exit_intent_triggered"]) +
                len(interactions["idle_triggered"])
            )
        }
        
        return interactions


############ SESSION SIMULATION - Full user journey analysis #################
    
    async def session_simulation(self, page, url, actions=None):
        """
        Simulate a user session to detect funnel-stage dark patterns.
        """
        if actions is None:
            actions = ["browse", "add_to_cart", "view_cart", "start_checkout", "abandon"]
        
        session_data = {
            "stages": [],
            "dark_patterns_by_stage": {},
            "friction_analysis": {
                "positive_action_clicks": 0,
                "negative_action_clicks": 0
            }
        }
        
        for action in actions:
            stage_data = {
                "action": action,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "dark_patterns_found": [],
                "new_popups": [],
                "hidden_fees": []
            }
            
            try:
                if action == "browse":
                    # Just extract current state
                    patterns = await self.extract_dark_patterns(page)
                    stage_data["dark_patterns_found"] = self._summarize_patterns(patterns)
                    stage_data["success"] = True
                
                elif action == "add_to_cart":
                    # Try to find and click add to cart
                    added = await page.evaluate(r'''() => {
                        const addBtn = Array.from(document.querySelectorAll('button, [role="button"], a')).find(el => {
                            const text = el.innerText?.toLowerCase() || '';
                            return /(add to (cart|bag|basket)|buy now)/i.test(text);
                        });
                        if (addBtn) {
                            addBtn.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    stage_data["success"] = added
                    if added:
                        session_data["friction_analysis"]["positive_action_clicks"] += 1
                        await asyncio.sleep(2)
                        
                        # Check for upsells/cross-sells
                        upsells = await page.evaluate(r'''() => {
                            const text = document.body?.innerText || '';
                            return {
                                hasUpsell: /(frequently bought|customers also|you might also|add this|complete the look)/i.test(text),
                                hasWarranty: /(protection plan|warranty|insurance|coverage)/i.test(text),
                                hasPrechecked: document.querySelectorAll('input[type="checkbox"]:checked').length
                            };
                        }''')
                        stage_data["upsells"] = upsells
                
                elif action == "view_cart":
                    # Navigate to cart
                    cart_clicked = await page.evaluate(r'''() => {
                        const cartLink = document.querySelector('[class*="cart"], [href*="cart"], [aria-label*="cart"]');
                        if (cartLink) {
                            cartLink.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    stage_data["success"] = cart_clicked
                    if cart_clicked:
                        await asyncio.sleep(2)
                        
                        # Check for hidden fees
                        fees = await page.evaluate(r'''() => {
                            const text = document.body?.innerText || '';
                            const feePatterns = /(service fee|handling|shipping|tax|processing)/gi;
                            return text.match(feePatterns) || [];
                        }''')
                        stage_data["hidden_fees"] = fees
                
                elif action == "start_checkout":
                    # Try to start checkout
                    checkout_clicked = await page.evaluate(r'''() => {
                        const checkoutBtn = Array.from(document.querySelectorAll('button, a')).find(el => {
                            const text = el.innerText?.toLowerCase() || '';
                            return /(checkout|proceed|continue to payment)/i.test(text);
                        });
                        if (checkoutBtn) {
                            checkoutBtn.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    stage_data["success"] = checkout_clicked
                    if checkout_clicked:
                        session_data["friction_analysis"]["positive_action_clicks"] += 1
                        await asyncio.sleep(2)
                        
                        # Check for forced account creation
                        forced_signup = await page.evaluate(r'''() => {
                            const text = document.body?.innerText || '';
                            return {
                                requiresAccount: /(create account|sign up|register to continue|login required)/i.test(text),
                                hasGuestOption: /(guest checkout|continue as guest|checkout without account)/i.test(text)
                            };
                        }''')
                        stage_data["forced_signup"] = forced_signup
                
                elif action == "abandon":
                    # Try to leave/close and see what happens
                    await page.evaluate('window.scrollTo(0, 0)')
                    await page.mouse.move(500, 0)
                    stage_data["success"] = True
                    await asyncio.sleep(2)
                    
                    # Check for exit popups
                    exit_popup = await page.evaluate(r'''() => {
                        const modals = document.querySelectorAll('[class*="modal"]:not([style*="display: none"]), [class*="popup"]:not([style*="display: none"])');
                        return Array.from(modals).map(m => ({
                            text: m.innerText?.slice(0, 300),
                            hasDiscount: /(discount|off|save|deal|offer)/i.test(m.innerText || '')
                        }));
                    }''')
                    stage_data["exit_popups"] = exit_popup
                
            except Exception as e:
                stage_data["error"] = str(e)
            
            session_data["stages"].append(stage_data)
            session_data["dark_patterns_by_stage"][action] = stage_data.get("dark_patterns_found", [])
        
        # Analyze session
        session_data["analysis"] = {
            "has_checkout_dark_patterns": any(
                stage.get("forced_signup", {}).get("requiresAccount", False) and 
                not stage.get("forced_signup", {}).get("hasGuestOption", True)
                for stage in session_data["stages"]
            ),
            "has_hidden_fees": any(len(stage.get("hidden_fees", [])) > 0 for stage in session_data["stages"]),
            "has_exit_manipulation": any(len(stage.get("exit_popups", [])) > 0 for stage in session_data["stages"]),
            "has_upsell_pressure": any(stage.get("upsells", {}).get("hasUpsell", False) for stage in session_data["stages"])
        }
        
        return session_data
    
    def _summarize_patterns(self, patterns):
        
        # Summarize extracted patterns.
        
        if not patterns:
            return []
        
        summary = []
        if patterns.get("scarcity"):
            summary.append(f"Scarcity: {len(patterns['scarcity'])} instances")
        if patterns.get("urgency"):
            summary.append(f"Urgency: {len(patterns['urgency'])} instances")
        if patterns.get("socialProof"):
            summary.append(f"Social proof: {len(patterns['socialProof'])} instances")
        if patterns.get("precheckedBoxes"):
            summary.append(f"Pre-checked boxes: {len(patterns['precheckedBoxes'])}")
        if patterns.get("modals"):
            summary.append(f"Modals/popups: {len(patterns['modals'])}")
        
        return summary

    # ========================================================================
    # SCREENSHOT DIFF ANALYSIS - Visual change detection
    # ========================================================================
    
    async def screenshot_diff_analysis(self, page, url, page_id):

        # Take screenshots at different times and compare for suspicious changes.

        diff_data = {
            "screenshots": [],
            "hashes": [],
            "changes_detected": []
        }
        
        # Take first screenshot
        screenshot1_path = Path(self.config["diff_dir"]) / f"{page_id}_t1.png"
        await page.screenshot(path=str(screenshot1_path), full_page=False)
        
        # Get perceptual hash
        img1 = Image.open(screenshot1_path)
        hash1 = imagehash.phash(img1)
        diff_data["hashes"].append(str(hash1))
        diff_data["screenshots"].append(str(screenshot1_path))
        
        # Wait and take second screenshot
        await asyncio.sleep(5)
        
        screenshot2_path = Path(self.config["diff_dir"]) / f"{page_id}_t2.png"
        await page.screenshot(path=str(screenshot2_path), full_page=False)
        
        img2 = Image.open(screenshot2_path)
        hash2 = imagehash.phash(img2)
        diff_data["hashes"].append(str(hash2))
        diff_data["screenshots"].append(str(screenshot2_path))
        
        # Calculate difference
        hash_diff = hash1 - hash2
        diff_data["hash_difference"] = int(hash_diff)
        
        # Reload and take third screenshot
        await page.reload(wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        screenshot3_path = Path(self.config["diff_dir"]) / f"{page_id}_t3.png"
        await page.screenshot(path=str(screenshot3_path), full_page=False)
        
        img3 = Image.open(screenshot3_path)
        hash3 = imagehash.phash(img3)
        diff_data["hashes"].append(str(hash3))
        diff_data["screenshots"].append(str(screenshot3_path))
        
        # Analyze changes
        diff_1_2 = int(hash1 - hash2)
        diff_1_3 = int(hash1 - hash3)
        diff_2_3 = int(hash2 - hash3)
        
        sig = self.config["diff_significant_change"]
        dyn_min = self.config["diff_dynamic_content_min"]
        dyn_max = self.config["diff_dynamic_content_max"]
        static = self.config["diff_no_change_threshold"]
        
        diff_data["analysis"] = {
            "diff_over_time": diff_1_2,
            "diff_after_reload": diff_1_3,
            "diff_reload_vs_time": diff_2_3,
            "significant_change": diff_1_2 > sig or diff_1_3 > sig,
            "possible_dynamic_content": diff_1_2 > dyn_min and diff_1_2 < dyn_max,
            "likely_static_page": diff_1_2 < static and diff_1_3 < static
        }
        
        # Check for specific element changes
        element_changes = await page.evaluate(r'''() => {
            // This would need to compare with stored values
            // For now, just capture current dynamic elements
            return {
                countdownPresent: document.querySelectorAll('[class*="countdown"], [class*="timer"]').length > 0,
                stockTextPresent: /only \d+ left/i.test(document.body?.innerText || ''),
                viewerCountPresent: /\d+ (people|users) (viewing|watching)/i.test(document.body?.innerText || '')
            };
        }''')
        
        diff_data["dynamic_elements"] = element_changes
        
        return diff_data

############## Button Asymmetry Analysis    ##################

    def analyze_button_asymmetry(self, buttons):
        """
        Analyze buttons for visual manipulation (asymmetric design).
        """
        analysis = {
            "asymmetric_pairs": [],
            "hidden_negative_options": [],
            "is_manipulative": False
        }
        
        if not buttons:
            return analysis
        
        positive_buttons = [b for b in buttons if b.get("isPositive")]
        negative_buttons = [b for b in buttons if b.get("isNegative")]
        
        for pos in positive_buttons:
            for neg in negative_buttons:
                pos_area = pos.get("area", 0)
                neg_area = neg.get("area", 1)
                
                if neg_area > 0:
                    area_ratio = pos_area / neg_area
                else:
                    area_ratio = float('inf')
                
                pos_font = float(pos.get("styles", {}).get("fontSize", "14px").replace("px", ""))
                neg_font = float(neg.get("styles", {}).get("fontSize", "14px").replace("px", ""))
                
                if neg_font > 0:
                    font_ratio = pos_font / neg_font
                else:
                    font_ratio = float('inf')
                
                neg_opacity = float(neg.get("styles", {}).get("opacity", "1"))
                
                # Check for asymmetry
                is_asymmetric = (
                    area_ratio > 1.5 or
                    font_ratio > 1.2 or
                    neg_opacity < 0.8 or
                    neg_area < 2000  # Very small button
                )
                
                if is_asymmetric:
                    analysis["asymmetric_pairs"].append({
                        "positive": pos.get("text"),
                        "negative": neg.get("text"),
                        "area_ratio": round(area_ratio, 2),
                        "font_ratio": round(font_ratio, 2),
                        "negative_opacity": neg_opacity,
                        "severity": "high" if area_ratio > 3 or neg_opacity < 0.5 else "medium"
                    })
        
        # Check for hidden negative options
        for neg in negative_buttons:
            neg_opacity = float(neg.get("styles", {}).get("opacity", "1"))
            neg_font = float(neg.get("styles", {}).get("fontSize", "14px").replace("px", ""))
            neg_area = neg.get("area", 0)
            
            if neg_opacity < 0.6 or neg_font < 11 or neg_area < 1500:
                analysis["hidden_negative_options"].append({
                    "text": neg.get("text"),
                    "reason": "low_opacity" if neg_opacity < 0.6 else "small_font" if neg_font < 11 else "small_size"
                })
        
        analysis["is_manipulative"] = len(analysis["asymmetric_pairs"]) > 0 or len(analysis["hidden_negative_options"]) > 0
        
        return analysis

    # ========================================================================
    # MAIN SCRAPING FUNCTION
    # ========================================================================
    
    async def scrape_url(self, url, category="general", enable_verification=True, 
                         enable_ab_test=True, enable_interaction=True,
                         enable_session=True, enable_diff=True):
        """
        Main scraping function with configurable robustness features.
        
        Args:
            url: URL to scrape
            category: Category of the site (ecommerce, travel, etc.)
            enable_verification: Enable temporal verification (recommended)
            enable_ab_test: Enable A/B test detection (slower, run separately)
            enable_interaction: Enable interaction-based detection
            enable_session: Enable session simulation (slower)
            enable_diff: Enable screenshot diff analysis
        """
        
        page_id = generate_page_id(url)
        domain = get_domain(url)
        
        result = {
            "page_id": page_id,
            "url": url,
            "domain": domain,
            "category": category,
            "scraped_at": datetime.now().isoformat(),
            "extraction": None,
            "verification": None,
            "ab_test": None,
            "interaction": None,
            "session": None,
            "screenshot_diff": None,
            "button_analysis": None,
            "suspicion_score": None
        }
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Navigate to page
                await page.goto(url, timeout=self.config["page_timeout"], wait_until="domcontentloaded")
                await asyncio.sleep(2)
                
                # 1. CORE EXTRACTION (always runs)
                logger.info(f"  [1/6] Extracting dark patterns...")
                result["extraction"] = await self.extract_dark_patterns(page)
                
                # 2. TEMPORAL VERIFICATION
                if enable_verification:
                    logger.info(f"  [2/6] Running temporal verification...")
                    try:
                        result["verification"] = await self.temporal_verification(page, url)
                    except Exception as e:
                        logger.warning(f"    [WARN] Temporal verification failed: {e}")

                # 3. A/B TEST DETECTION
                if enable_ab_test:
                    logger.info(f"  [3/6] Running A/B test detection...")
                    try:
                        result["ab_test"] = await self.ab_test_detection(url, playwright_instance=p)
                    except Exception as e:
                        logger.warning(f"    [WARN] A/B test detection failed: {e}")

                # 4. INTERACTION ANALYSIS
                if enable_interaction:
                    logger.info(f"  [4/6] Analyze interactions...")
                    try:
                        result["interaction"] = await self.interaction_detection(page)
                    except Exception as e:
                        logger.warning(f"    [WARN] Interaction analysis failed: {e}")
                        
                # 5. SESSION SIMULATION
                if enable_session:
                    logger.info(f"  [5/6] Simulating session...")
                    try:
                        result["session"] = await self.session_simulation(page, url)
                    except Exception as e:
                        logger.warning(f"    [WARN] Session simulation failed: {e}")

                # 6. SCREENSHOT DIFF ANALYSIS
                if enable_diff:
                    logger.info(f"  [6/6] Analyzing visual changes...")
                    try:
                        result["screenshot_diff"] = await self.screenshot_diff_analysis(page, url, page_id)
                    except Exception as e:
                        logger.warning(f"    [WARN] Diff analysis failed: {e}")
            
                # 7. SAVE EXTRACTED DATA
                try:
                    # Save Screenshot
                    screenshot_path = Path(self.config["screenshots_dir"]) / f"{page_id}.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    
                    # Save DOM
                    dom_path = Path(self.config["dom_dir"]) / f"{page_id}.html"
                    dom_content = await page.content()
                    with open(dom_path, "w", encoding="utf-8") as f:
                        f.write(dom_content)
                    
                    # Save Metadata
                    meta_path = Path(self.config["metadata_dir"]) / f"{page_id}.json"
                    
                    # Convert unserializable objects (like numpy types or hash objects) to string if present
                    def json_serial(obj):
                        return str(obj)

                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, default=json_serial, indent=2)

                    logger.info(f"  [7/7] Saved scraping artifacts to data/raw/")
                    
                except Exception as e:
                    logger.warning(f"    [WARN] Failed to save scraping artifacts: {e}")

            except Exception as e:
                logger.error(f"  [ERROR] Scraping failed: {e}")
                import traceback
                traceback.print_exc()
            
            return result

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    logger.info("Starting scraper...")
    scraper = DarkPatternScraper()
    
    # Load previously scraped URLs to skip them
    completed_urls = load_complete_urls()
    
    # Use URLs from url_sources if available, otherwise default
    try:
        try:
            from scripts.url_sources import get_entire_urls
        except ImportError:
            from url_sources import get_entire_urls
            
        urls = [u[0] for u in get_entire_urls()] # Scrape all URLs
    except ImportError:
        urls = ["https://www.example.com"]
        logger.warning("Could not import url_sources, using default URL.")
    
    # Filter out already scraped URLs
    urls_to_scrape = [url for url in urls if url not in completed_urls]
    skipped = len(urls) - len(urls_to_scrape)
    if skipped > 0:
        logger.info(f"Skipping {skipped} already scraped URLs")
    logger.info(f"URLs remaining to scrape: {len(urls_to_scrape)}/{len(urls)}")
    
    for url in urls_to_scrape:
        if not valid_url(url):
            logger.warning(f"Skipping invalid URL: {url}")
            continue
        logger.info(f"Scraping {url}...")
        try:
            result = await scraper.scrape_url(url)
            logger.info(f"Completed {url}. Page ID: {result.get('page_id')}")
            save_completed_website(url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
