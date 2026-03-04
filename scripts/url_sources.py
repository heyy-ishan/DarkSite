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

ECOMMERCE_URLS = [
    # Amazon
    "https://www.amazon.com/gp/goldbox",
    "https://www.amazon.com/deals",
    
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
    
    # Electronics
    "https://www.bestbuy.com/site/deals",
    "https://www.newegg.com/todays-deals",
    
    # General
    "https://www.walmart.com/deals",
    "https://www.target.com/c/top-deals",
    
    # Add more URLs here..
]


# Travel booking sites - known for urgency/scarcity patterns
TRAVEL_URLS = [
    # Hotels
    "https://www.booking.com",
    "https://www.hotels.com",
    "https://www.expedia.com",
    "https://www.trivago.com",
    
    # Flights
    "https://www.kayak.com",
    "https://www.skyscanner.com",
    "https://www.google.com/travel/flights",
    
    # Vacation rentals
    "https://www.airbnb.com",
    "https://www.vrbo.com",
    
    # Add more URLs here...
]


# Streaming services - subscription flows
STREAMING_URLS = [
    # Video
    "https://www.netflix.com",
    "https://www.hulu.com/welcome",
    "https://www.disneyplus.com",
    "https://www.hbomax.com",
    "https://www.peacocktv.com",
    "https://www.paramountplus.com",
    
    # Music
    "https://www.spotify.com/premium",
    "https://music.apple.com",
    "https://www.youtube.com/premium",
    
    # Add more URLs here...
]


# Social media - signup flows, settings, notifications
SOCIAL_MEDIA_URLS = [
    "https://www.instagram.com/accounts/emailsignup/",
    "https://www.tiktok.com/signup",
    "https://www.linkedin.com/signup",
    "https://twitter.com/i/flow/signup",
    "https://www.facebook.com/r.php",
    "https://www.snapchat.com/create",
    "https://www.pinterest.com",
    
    # Add more URLs here...
]


# SaaS and subscription services
SAAS_URLS = [
    # Productivity
    "https://www.dropbox.com/plans",
    "https://www.notion.so/pricing",
    "https://slack.com/pricing",
    "https://zoom.us/pricing",
    
    # Design
    "https://www.canva.com/pricing",
    "https://www.figma.com/pricing",
    
    # Cloud storage
    "https://one.google.com",
    "https://www.icloud.com",
    
    # VPNs (often have aggressive dark patterns)
    "https://nordvpn.com",
    "https://www.expressvpn.com",
    "https://surfshark.com",
    
    # Add more URLs here...
]


# News and media - paywalls, cookie banners
NEWS_MEDIA_URLS = [
    "https://www.nytimes.com",
    "https://www.washingtonpost.com",
    "https://www.wsj.com",
    "https://www.economist.com",
    "https://www.forbes.com",
    "https://www.bloomberg.com",
    "https://www.medium.com",
    
    # Add more URLs here...
]


# Gaming platforms
GAMING_URLS = [
    "https://store.steampowered.com",
    "https://www.epicgames.com/store",
    "https://www.gog.com",
    "https://www.ea.com",
    "https://www.xbox.com/games",
    
    # Add more URLs here...
]


def get_entire_urls():
    """
    Combining all URL lists into a single list with domain labels.
    
    Returns:
        list: Tuples of (url, domain_category)
    """
    #initialising the list
    all_urls = []
    
    #making tuple that stores the category of the websites
    url_sources = [
        (ECOMMERCE_URLS, "ecommerce"),
        (TRAVEL_URLS, "travel"),
        (STREAMING_URLS, "streaming"),
        (SOCIAL_MEDIA_URLS, "social_media"),
        (SAAS_URLS, "saas"),
        (NEWS_MEDIA_URLS, "news_media"),
        (GAMING_URLS, "gaming"),
    ]
    
    for urls, category in url_sources:
        for url in urls:
            all_urls.append((url, category))
    
    print(f"✓ Total URLs to scrape: {len(all_urls)}")
    return all_urls


def get_urls_by_category(category):
    """
    code to get all the urls of a specific category
    
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
    }
    
    return categories.get(category, [])