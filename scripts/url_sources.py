"""
Gets the list of URLs to scrape by the domain categories

Choose the websites that mostly have:
- Checkout flows
- Subscription pages
- Cookie consent banners
- Cancellation flows
- Free trial signups

IMPORTANT:
- Respect robots.txt
- Adding delays to not overload the servers
- Some websites can block scraping
"""

import logging
logger = logging.getLogger("darksite")


# ============================================================================
# ECOMMERCE
# ============================================================================

ECOMMERCE_URLS = [
    # Amazon
    "https://www.amazon.com/gp/goldbox",
    "https://www.amazon.com/deals",
    "https://www.amazon.com/gp/bestsellers",

    # eBay
    "https://www.ebay.com/deals",
    "https://www.ebay.com/globaldeals",

    # Wish
    "https://www.wish.com",

    # Fashion
    "https://www.shein.com",
    "https://www.asos.com",
    "https://www.zara.com",
    "https://www.hm.com",
    "https://www.fashionnova.com",
    "https://www.romwe.com",
    "https://www.boohoo.com",

    # Electronics
    "https://www.bestbuy.com/site/deals",
    "https://www.newegg.com/todays-deals",

    # General
    "https://www.walmart.com/deals",
    "https://www.target.com/c/top-deals",
    "https://www.aliexpress.com",
    "https://www.temu.com",
    "https://www.wayfair.com",
    "https://www.overstock.com",
]


# ============================================================================
# TRAVEL - known for urgency/scarcity patterns
# ============================================================================

TRAVEL_URLS = [
    # Hotels
    "https://www.booking.com",
    "https://www.hotels.com",
    "https://www.expedia.com",
    "https://www.trivago.com",
    "https://www.agoda.com",
    "https://www.hostelworld.com",

    # Flights
    "https://www.kayak.com",
    "https://www.skyscanner.com",
    "https://www.google.com/travel/flights",
    "https://www.cheapflights.com",
    "https://www.momondo.com",

    # Vacation rentals
    "https://www.airbnb.com",
    "https://www.vrbo.com",

    # Car rental
    "https://www.enterprise.com",
    "https://www.hertz.com",
]


# ============================================================================
# STREAMING - subscription flows
# ============================================================================

STREAMING_URLS = [
    # Video
    "https://www.netflix.com",
    "https://www.hulu.com/welcome",
    "https://www.disneyplus.com",
    "https://www.hbomax.com",
    "https://www.peacocktv.com",
    "https://www.paramountplus.com",
    "https://www.crunchyroll.com",

    # Music
    "https://www.spotify.com/premium",
    "https://music.apple.com",
    "https://www.youtube.com/premium",
    "https://www.tidal.com",
    "https://www.deezer.com/us",
]


# ============================================================================
# SOCIAL MEDIA - signup flows, settings, notifications
# ============================================================================

SOCIAL_MEDIA_URLS = [
    "https://www.instagram.com/accounts/emailsignup/",
    "https://www.tiktok.com/signup",
    "https://www.linkedin.com/signup",
    "https://twitter.com/i/flow/signup",
    "https://www.facebook.com/r.php",
    "https://www.snapchat.com/create",
    "https://www.pinterest.com",
    "https://www.reddit.com/register",
    "https://www.threads.net",
]


# ============================================================================
# SAAS AND SUBSCRIPTION SERVICES
# ============================================================================

SAAS_URLS = [
    # Productivity
    "https://www.dropbox.com/plans",
    "https://www.notion.so/pricing",
    "https://slack.com/pricing",
    "https://zoom.us/pricing",
    "https://www.grammarly.com/plans",
    "https://evernote.com/compare-plans",

    # Design
    "https://www.canva.com/pricing",
    "https://www.figma.com/pricing",
    "https://www.adobe.com/creativecloud/plans.html",

    # Cloud storage
    "https://one.google.com",
    "https://www.icloud.com",

    # VPNs (often have aggressive dark patterns)
    "https://nordvpn.com",
    "https://www.expressvpn.com",
    "https://surfshark.com",
    "https://www.cyberghostvpn.com",
    "https://www.privateinternetaccess.com",

    # Antivirus
    "https://www.mcafee.com",
    "https://www.norton.com",
    "https://www.avast.com",
]


# ============================================================================
# NEWS AND MEDIA - paywalls, cookie banners
# ============================================================================

NEWS_MEDIA_URLS = [
    "https://www.nytimes.com",
    "https://www.washingtonpost.com",
    "https://www.wsj.com",
    "https://www.economist.com",
    "https://www.forbes.com",
    "https://www.bloomberg.com",
    "https://www.medium.com",
    "https://www.businessinsider.com",
    "https://www.wired.com",
    "https://www.theatlantic.com",
]


# ============================================================================
# GAMING
# ============================================================================

GAMING_URLS = [
    "https://store.steampowered.com",
    "https://www.epicgames.com/store",
    "https://www.gog.com",
    "https://www.ea.com",
    "https://www.xbox.com/games",
    "https://www.playstation.com/en-us/ps-plus",
    "https://www.nintendo.com/us/switch/online",
    "https://www.roblox.com",
    "https://www.g2a.com",
]


# ============================================================================
# FOOD DELIVERY - hidden fees and surge pricing
# ============================================================================

FOOD_DELIVERY_URLS = [
    "https://www.doordash.com",
    "https://www.ubereats.com",
    "https://www.grubhub.com",
    "https://www.instacart.com",
    "https://www.postmates.com",
    "https://www.gopuff.com",
]


# ============================================================================
# FITNESS / HEALTH - subscription traps, cancellation friction
# ============================================================================

FITNESS_HEALTH_URLS = [
    "https://www.myfitnesspal.com/premium",
    "https://www.noom.com",
    "https://www.headspace.com",
    "https://www.calm.com",
    "https://www.peloton.com/app",
    "https://www.beachbodyondemand.com",
]


# ============================================================================
# DATING - premium upsells, urgency, social proof manipulation
# ============================================================================

DATING_URLS = [
    "https://www.tinder.com",
    "https://www.match.com",
    "https://www.bumble.com",
    "https://www.okcupid.com",
    "https://www.eharmony.com",
    "https://hinge.co",
]


# ============================================================================
# FINANCE - hidden fees, forced account creation
# ============================================================================

FINANCE_URLS = [
    "https://www.creditkarma.com",
    "https://www.mint.com",
    "https://www.sofi.com",
    "https://www.nerdwallet.com",
    "https://www.bankrate.com",
    "https://www.lendingtree.com",
    "https://www.turbotax.com",
]


# ============================================================================
# GOVERNMENT - regulated, minimal manipulation (clean examples)
# ============================================================================

GOVERNMENT_URLS = [
    "https://www.usa.gov",
    "https://www.irs.gov",
    "https://www.ssa.gov",
    "https://www.cdc.gov",
    "https://www.nasa.gov",
    "https://www.weather.gov",
    "https://www.gov.uk",
    "https://www.canada.ca",
    "https://www.data.gov",
    "https://www.recreation.gov",
]


# ============================================================================
# EDUCATION - informational, not transactional (clean examples)
# ============================================================================

EDUCATION_URLS = [
    "https://www.wikipedia.org",
    "https://www.khanacademy.org",
    "https://www.coursera.org",
    "https://www.edx.org",
    "https://www.mit.edu",
    "https://www.stanford.edu",
    "https://www.harvard.edu",
    "https://arxiv.org",
    "https://scholar.google.com",
    "https://www.gutenberg.org",
]


# ============================================================================
# NONPROFIT / OPEN SOURCE - mission-driven, user-respecting (clean examples)
# ============================================================================

NONPROFIT_OPENSOURCE_URLS = [
    "https://www.mozilla.org",
    "https://www.eff.org",
    "https://www.archive.org",
    "https://www.w3.org",
    "https://www.apache.org",
    "https://www.redcross.org",
    "https://www.unicef.org",
    "https://www.doctorswithoutborders.org",
    "https://signal.org",
    "https://www.linux.org",
]


# ============================================================================
# DEVELOPER / DOCS - utility-focused, minimal dark patterns (clean examples)
# ============================================================================

DEVELOPER_URLS = [
    "https://github.com",
    "https://docs.python.org",
    "https://developer.mozilla.org",
    "https://stackoverflow.com",
    "https://www.rust-lang.org",
    "https://go.dev",
    "https://docs.djangoproject.com",
    "https://react.dev",
    "https://vuejs.org",
    "https://tailwindcss.com",
]


# ============================================================================
# ETHICAL / PRIVACY-FOCUSED - intentionally clean UX (clean examples)
# ============================================================================

ETHICAL_URLS = [
    "https://basecamp.com",
    "https://www.fastmail.com",
    "https://proton.me",
    "https://duckduckgo.com",
    "https://www.patagonia.com",
    "https://www.everlane.com",
    "https://www.fairphone.com",
    "https://tutanota.com",
    "https://standardnotes.com",
]


# ============================================================================
# UTILITY / REFERENCE - informational, no sales pressure (clean examples)
# ============================================================================

UTILITY_URLS = [
    "https://www.timeanddate.com",
    "https://www.wolframalpha.com",
    "https://www.xe.com",
    "https://www.speedtest.net",
    "https://www.openstreetmap.org",
    "https://www.webmd.com",
    "https://www.mayoclinic.org",
    "https://www.snopes.com",
    "https://www.merriam-webster.com",
]


# ============================================================================
# AGGREGATION FUNCTIONS
# ============================================================================

def get_entire_urls():
    """
    Combining all URL lists into a single list with domain labels.

    Returns:
        list: Tuples of (url, domain_category)
    """
    all_urls = []

    url_sources = [
        (ECOMMERCE_URLS, "ecommerce"),
        (TRAVEL_URLS, "travel"),
        (STREAMING_URLS, "streaming"),
        (SOCIAL_MEDIA_URLS, "social_media"),
        (SAAS_URLS, "saas"),
        (NEWS_MEDIA_URLS, "news_media"),
        (GAMING_URLS, "gaming"),
        (FOOD_DELIVERY_URLS, "food_delivery"),
        (FITNESS_HEALTH_URLS, "fitness_health"),
        (DATING_URLS, "dating"),
        (FINANCE_URLS, "finance"),
        (GOVERNMENT_URLS, "government"),
        (EDUCATION_URLS, "education"),
        (NONPROFIT_OPENSOURCE_URLS, "nonprofit"),
        (DEVELOPER_URLS, "developer"),
        (ETHICAL_URLS, "ethical"),
        (UTILITY_URLS, "utility"),
    ]

    for urls, category in url_sources:
        for url in urls:
            all_urls.append((url, category))

    logger.info(f"Total URLs to scrape: {len(all_urls)}")
    return all_urls


def get_urls_by_category(category):
    """
    Get all URLs for a specific category.

    Args:
        category: Specifying the category of the website

    Returns:
        list: URLs for that category
    """
    categories = {
        "ecommerce": ECOMMERCE_URLS,
        "travel": TRAVEL_URLS,
        "streaming": STREAMING_URLS,
        "social_media": SOCIAL_MEDIA_URLS,
        "saas": SAAS_URLS,
        "news_media": NEWS_MEDIA_URLS,
        "gaming": GAMING_URLS,
        "food_delivery": FOOD_DELIVERY_URLS,
        "fitness_health": FITNESS_HEALTH_URLS,
        "dating": DATING_URLS,
        "finance": FINANCE_URLS,
        "government": GOVERNMENT_URLS,
        "education": EDUCATION_URLS,
        "nonprofit": NONPROFIT_OPENSOURCE_URLS,
        "developer": DEVELOPER_URLS,
        "ethical": ETHICAL_URLS,
        "utility": UTILITY_URLS,
    }

    return categories.get(category, [])