"""
URL sources for dark pattern detection research.

~1,000+ URLs across 20 categories with sub-page coverage.
Each major site includes homepage + checkout/pricing/signup sub-pages
to capture dark patterns at different stages of the user journey.

Balance: ~65% likely dark pattern sites, ~35% clean baseline sites.
"""

import logging
logger = logging.getLogger("darksite")


# ============================================================================
# ECOMMERCE — urgency, scarcity, hidden costs, social proof
# ============================================================================

ECOMMERCE_URLS = [
    # Amazon
    "https://www.amazon.com/gp/goldbox",
    "https://www.amazon.com/deals",
    "https://www.amazon.com/gp/bestsellers",
    "https://www.amazon.com/gp/new-releases",
    "https://www.amazon.com/amazonprime",
    "https://www.amazon.com/gp/subscribe-and-save",
    "https://www.amazon.com/gp/browse.html?node=16225007011",

    # eBay
    "https://www.ebay.com/deals",
    "https://www.ebay.com/globaldeals",
    "https://www.ebay.com/b/Electronics/bn_7000259124",
    "https://www.ebay.com/deals/fashion",

    # Wish / Temu / AliExpress (aggressive dark patterns)
    "https://www.wish.com",
    "https://www.wish.com/feed/tabbed_feed_latest",
    "https://www.temu.com",
    "https://www.temu.com/best-sellers.html",
    "https://www.temu.com/flash-sale.html",
    "https://www.aliexpress.com",
    "https://www.aliexpress.com/category/44/phones-telecommunications.html",
    "https://www.aliexpress.com/w/wholesale-flash-deals.html",
    "https://www.aliexpress.com/campaign/wow/gcp/superdeal-g/index",

    # Fashion (fast fashion = aggressive marketing)
    "https://www.shein.com",
    "https://www.shein.com/flash-sale.html",
    "https://www.shein.com/New-in-Trends-sc-00654187.html",
    "https://www.asos.com",
    "https://www.asos.com/women/sale/cat/?cid=7046",
    "https://www.asos.com/men/sale/cat/?cid=8274",
    "https://www.zara.com",
    "https://www.zara.com/us/en/woman-new-in-l1180.html",
    "https://www.hm.com",
    "https://www.hm.com/en_us/sale.html",
    "https://www.hm.com/en_us/sale/shopbyproductladies.html",
    "https://www.fashionnova.com",
    "https://www.fashionnova.com/collections/sale",
    "https://www.fashionnova.com/collections/new-arrivals",
    "https://www.romwe.com",
    "https://www.romwe.com/Women-Sale-c-1727.html",
    "https://www.boohoo.com",
    "https://www.boohoo.com/page/sale.html",
    "https://www.forever21.com",
    "https://www.forever21.com/us/shop/catalog/category/f21/sale",
    "https://www.prettylittlething.us",
    "https://www.prettylittlething.us/sale.html",
    "https://www.missguided.com",
    "https://www.urbanoutfitters.com/sale",
    "https://www.freepeople.com/sale/",
    "https://www.nike.com/w/sale-3yaep",
    "https://www.adidas.com/us/sale",
    "https://www.uniqlo.com/us/en/sale",

    # Electronics
    "https://www.bestbuy.com/site/deals",
    "https://www.bestbuy.com/site/electronics/top-deals/pcmcat1563299784494.c",
    "https://www.bestbuy.com/site/membership/totaltech/pcmcat1629744267498.c",
    "https://www.bestbuy.com/site/misc/open-box/pcmcat293600050014.c",
    "https://www.newegg.com/todays-deals",
    "https://www.newegg.com/promotions",
    "https://www.newegg.com/p/pl?N=4131",
    "https://www.bhphotovideo.com/c/browse/deal-zone/ci/17590",
    "https://www.microcenter.com/site/content/specialoffer.aspx",
    "https://www.adorama.com/l/deals",

    # General retail
    "https://www.walmart.com/deals",
    "https://www.walmart.com/plus",
    "https://www.walmart.com/browse/flash-deals",
    "https://www.walmart.com/cp/electronics/3944",
    "https://www.target.com/c/top-deals",
    "https://www.target.com/circle",
    "https://www.target.com/c/clearance/-/N-5q0ga",
    "https://www.costco.com/online-offers.html",
    "https://www.costco.com/warehouse-savings.html",
    "https://www.wayfair.com",
    "https://www.wayfair.com/daily-sales",
    "https://www.wayfair.com/daily-sales/clearance",
    "https://www.overstock.com",
    "https://www.overstock.com/deals",
    "https://www.groupon.com",
    "https://www.groupon.com/deals",
    "https://www.groupon.com/local/deals",
    "https://www.kohls.com/sale-event.jsp",
    "https://www.macys.com/shop/sale",
    "https://www.macys.com/shop/sale/flash-sale",
    "https://www.nordstromrack.com",
    "https://www.nordstromrack.com/clearance",
    "https://www.tjmaxx.com/shop/clearance",
    "https://www.samsclub.com/savings",
    "https://www.qvc.com/content/shop-clearance.html",
    "https://www.hsn.com/shop/clearance/0702",

    # Supplements / health products
    "https://www.goop.com",
    "https://www.goop.com/shop/sale",
    "https://www.iherb.com/specials",
    "https://www.bodybuilding.com/store/deals",
    "https://www.gnc.com/deals/",
    "https://www.vitacost.com/productResults.aspx?ss=1&ic=sale",
]


# ============================================================================
# TRAVEL — scarcity, urgency, hidden costs, social proof
# ============================================================================

TRAVEL_URLS = [
    # Hotels
    "https://www.booking.com",
    "https://www.booking.com/deals",
    "https://www.booking.com/lastminute/index.html",
    "https://www.booking.com/genius.html",
    "https://www.hotels.com",
    "https://www.hotels.com/deals",
    "https://www.hotels.com/page/rewards/",
    "https://www.expedia.com",
    "https://www.expedia.com/deals",
    "https://www.expedia.com/membership-rewards",
    "https://www.expedia.com/last-minute-deals",
    "https://www.trivago.com",
    "https://www.agoda.com",
    "https://www.agoda.com/deals",
    "https://www.agoda.com/vip-deals",
    "https://www.hostelworld.com",
    "https://www.priceline.com",
    "https://www.priceline.com/deals",
    "https://www.priceline.com/express-deals/",
    "https://www.hotwire.com",
    "https://www.hotwire.com/deals",
    "https://www.tripadvisor.com",
    "https://www.tripadvisor.com/Hotels",

    # Flights
    "https://www.kayak.com",
    "https://www.kayak.com/deals",
    "https://www.kayak.com/explore/",
    "https://www.skyscanner.com",
    "https://www.skyscanner.com/routes",
    "https://www.google.com/travel/flights",
    "https://www.cheapflights.com",
    "https://www.momondo.com",
    "https://www.orbitz.com",
    "https://www.kiwi.com",
    "https://www.scottscheapflights.com",
    "https://www.secretflying.com",
    "https://www.farecompare.com",
    "https://www.airfarewatchdog.com",

    # Budget airlines (aggressive seat/baggage upsells)
    "https://www.spirit.com",
    "https://www.spirit.com/deals",
    "https://www.frontier.com",
    "https://www.frontier.com/deals",
    "https://www.ryanair.com",
    "https://www.ryanair.com/gb/en/lp/cheap-flights",
    "https://www.easyjet.com",
    "https://www.wizzair.com",
    "https://www.allegiantair.com",
    "https://www.sunwing.ca",

    # Vacation rentals
    "https://www.airbnb.com",
    "https://www.airbnb.com/s/experiences",
    "https://www.airbnb.com/plus",
    "https://www.vrbo.com",

    # Car rental
    "https://www.enterprise.com",
    "https://www.hertz.com",
    "https://www.avis.com",
    "https://www.sixt.com",
    "https://www.rentalcars.com",
    "https://www.budget.com",
    "https://www.nationalcar.com",
    "https://turo.com",

    # Cruise / package
    "https://www.cruises.com",
    "https://www.royalcaribbean.com/cruise-deals",
    "https://www.carnival.com/cruise-deals",
    "https://www.travelzoo.com",
    "https://www.vacationexpress.com",
]


# ============================================================================
# STREAMING — subscription flows, cancellation friction
# ============================================================================

STREAMING_URLS = [
    # Video
    "https://www.netflix.com",
    "https://www.netflix.com/signup/planform",
    "https://www.hulu.com/welcome",
    "https://www.hulu.com/start/affiliate",
    "https://www.disneyplus.com",
    "https://www.disneyplus.com/sign-up",
    "https://www.hbomax.com",
    "https://www.peacocktv.com",
    "https://www.peacocktv.com/plans",
    "https://www.paramountplus.com",
    "https://www.paramountplus.com/account/signup/plan/",
    "https://www.crunchyroll.com",
    "https://www.crunchyroll.com/premium",
    "https://tv.apple.com",
    "https://www.discoveryplus.com",
    "https://www.discoveryplus.com/subscribe",
    "https://www.fubo.tv/signup",
    "https://www.sling.com",
    "https://www.sling.com/deals",
    "https://www.philo.com",
    "https://www.britbox.com/us/subscribe",
    "https://www.amc.com/amcplus",
    "https://www.starz.com/signup",
    "https://www.showtime.com/stream-showtime",
    "https://www.mgmplus.com/subscribe",

    # Music
    "https://www.spotify.com/premium",
    "https://www.spotify.com/us/premium/#plans",
    "https://music.apple.com",
    "https://www.youtube.com/premium",
    "https://music.youtube.com/music_premium",
    "https://www.tidal.com",
    "https://www.tidal.com/pricing",
    "https://www.deezer.com/us",
    "https://www.deezer.com/us/offers",
    "https://www.pandora.com/upgrade",
    "https://www.amazon.com/music/unlimited",
    "https://www.soundcloud.com/go",
    "https://www.qobuz.com/us-en/plans",

    # Audiobooks / podcasts / reading
    "https://www.audible.com/ep/membershipplans",
    "https://www.scribd.com/subscribe",
    "https://www.kindle-unlimited.amazon.com",
    "https://www.blinkist.com/en/plans",
]


# ============================================================================
# SOCIAL MEDIA — signup flows, notification nudges, data collection
# ============================================================================

SOCIAL_MEDIA_URLS = [
    "https://www.instagram.com/accounts/emailsignup/",
    "https://www.tiktok.com/signup",
    "https://www.tiktok.com/coin",
    "https://www.linkedin.com/signup",
    "https://www.linkedin.com/premium",
    "https://www.linkedin.com/sales/ssi",
    "https://twitter.com/i/flow/signup",
    "https://twitter.com/i/premium_sign_up",
    "https://www.facebook.com/r.php",
    "https://www.facebook.com/gaming",
    "https://www.facebook.com/marketplace",
    "https://www.snapchat.com/create",
    "https://www.snapchat.com/plus",
    "https://www.pinterest.com",
    "https://www.pinterest.com/business/create/",
    "https://www.reddit.com/register",
    "https://www.reddit.com/premium",
    "https://www.threads.net",
    "https://discord.com/register",
    "https://discord.com/nitro",
    "https://www.quora.com",
    "https://www.quora.com/about/quora_plus",
    "https://nextdoor.com/join",
    "https://www.tumblr.com/register",
    "https://bsky.app",
    "https://mastodon.social/auth/sign_up",
    "https://www.meetup.com/register/",
    "https://www.clubhouse.com",
    "https://www.twitch.tv/signup",
    "https://www.patreon.com/create",
    "https://www.substack.com",
]


# ============================================================================
# SAAS / SUBSCRIPTIONS — pricing tricks, forced upgrades
# ============================================================================

SAAS_URLS = [
    # Productivity
    "https://www.dropbox.com/plans",
    "https://www.dropbox.com/business/plans",
    "https://www.notion.so/pricing",
    "https://www.notion.so/product",
    "https://slack.com/pricing",
    "https://slack.com/features",
    "https://zoom.us/pricing",
    "https://zoom.us/en/workplace-plans",
    "https://www.grammarly.com/plans",
    "https://www.grammarly.com/business",
    "https://evernote.com/compare-plans",
    "https://monday.com/pricing",
    "https://monday.com/lp/crm",
    "https://asana.com/pricing",
    "https://clickup.com/pricing",
    "https://todoist.com/pricing",
    "https://www.trello.com/pricing",
    "https://airtable.com/pricing",
    "https://www.basecamp.com/pricing",
    "https://www.microsoft.com/en-us/microsoft-365/business/compare-all-plans",
    "https://workspace.google.com/pricing",
    "https://www.zoho.com/workplace/pricing.html",
    "https://www.freshworks.com/pricing/",
    "https://www.hubspot.com/pricing",
    "https://www.salesforce.com/editions-pricing/overview/",

    # Design
    "https://www.canva.com/pricing",
    "https://www.canva.com/pro/",
    "https://www.figma.com/pricing",
    "https://www.adobe.com/creativecloud/plans.html",
    "https://www.adobe.com/products/photoshop.html",
    "https://www.adobe.com/products/illustrator.html",
    "https://www.invisionapp.com/plans",
    "https://www.sketch.com/pricing/",
    "https://www.miro.com/pricing/",

    # Cloud storage
    "https://one.google.com",
    "https://www.icloud.com",
    "https://www.box.com/pricing",
    "https://www.pcloud.com/cloud-storage-pricing-plans.html",
    "https://www.sync.com/pricing/",
    "https://www.backblaze.com/cloud-backup/pricing",

    # VPNs (aggressive urgency + fake discounts)
    "https://nordvpn.com",
    "https://nordvpn.com/pricing",
    "https://nordvpn.com/offer/",
    "https://www.expressvpn.com",
    "https://www.expressvpn.com/order",
    "https://surfshark.com",
    "https://surfshark.com/pricing",
    "https://surfshark.com/deal",
    "https://www.cyberghostvpn.com",
    "https://www.cyberghostvpn.com/en_US/buy",
    "https://www.privateinternetaccess.com",
    "https://www.privateinternetaccess.com/pages/buy-vpn/",
    "https://www.purevpn.com/order",
    "https://atlasvpn.com",
    "https://www.ipvanish.com/pricing/",
    "https://protonvpn.com/pricing",
    "https://windscribe.com/upgrade",

    # Antivirus / security
    "https://www.mcafee.com",
    "https://www.mcafee.com/en-us/antivirus/mcafee-total-protection.html",
    "https://www.norton.com",
    "https://us.norton.com/products",
    "https://www.avast.com",
    "https://www.avast.com/en-us/premium-security",
    "https://www.bitdefender.com/solutions/",
    "https://www.bitdefender.com/solutions/total-security.html",
    "https://www.kaspersky.com/home-security",
    "https://www.malwarebytes.com/pricing",
    "https://www.webroot.com/us/en/home/products/compare",
    "https://www.totalav.com/semi-annual-offer",
    "https://www.avg.com/en-us/ultimate",

    # Website builders / hosting
    "https://www.wix.com/upgrade/website",
    "https://www.wix.com/premium-purchase-plan/dynamo",
    "https://www.squarespace.com/pricing",
    "https://www.godaddy.com/hosting/web-hosting",
    "https://www.godaddy.com/offers/domains",
    "https://www.bluehost.com/hosting",
    "https://www.bluehost.com/hosting/shared",
    "https://www.hostinger.com/hosting",
    "https://www.hostinger.com/web-hosting",
    "https://www.siteground.com/web-hosting.htm",
    "https://www.namecheap.com/hosting/shared/",
    "https://www.a2hosting.com/web-hosting",
    "https://www.dreamhost.com/hosting/shared/",
    "https://www.ionos.com/hosting/web-hosting",
    "https://www.shopify.com/pricing",
    "https://www.bigcommerce.com/essentials/pricing/",
    "https://www.weebly.com/pricing",

    # Email marketing
    "https://mailchimp.com/pricing/",
    "https://www.constantcontact.com/pricing",
    "https://www.getresponse.com/pricing",
    "https://www.sendinblue.com/pricing/",
    "https://www.aweber.com/pricing.htm",
    "https://convertkit.com/pricing",
]


# ============================================================================
# NEWS / MEDIA — paywalls, cookie banners, newsletter popups
# ============================================================================

NEWS_MEDIA_URLS = [
    "https://www.nytimes.com",
    "https://www.nytimes.com/subscription",
    "https://www.nytimes.com/wirecutter/",
    "https://www.washingtonpost.com",
    "https://www.washingtonpost.com/subscribe",
    "https://www.wsj.com",
    "https://www.wsj.com/membership",
    "https://www.economist.com",
    "https://www.economist.com/subscribe",
    "https://www.forbes.com",
    "https://www.forbes.com/advisor/",
    "https://www.bloomberg.com",
    "https://www.bloomberg.com/subscriptions",
    "https://www.medium.com",
    "https://medium.com/plans",
    "https://medium.com/membership",
    "https://www.businessinsider.com",
    "https://www.wired.com",
    "https://www.wired.com/subscribe/",
    "https://www.theatlantic.com",
    "https://www.theatlantic.com/subscribe/",
    "https://www.newyorker.com",
    "https://www.newyorker.com/subscribe",
    "https://www.ft.com",
    "https://www.ft.com/products",
    "https://www.latimes.com",
    "https://www.usatoday.com",
    "https://www.theguardian.com",
    "https://support.theguardian.com/contribute",
    "https://www.bbc.com/news",
    "https://www.cnn.com",
    "https://www.foxnews.com",
    "https://www.foxnews.com/foxnation",
    "https://www.huffpost.com",
    "https://www.buzzfeed.com",
    "https://www.dailymail.co.uk",
    "https://www.vice.com",
    "https://www.vox.com",
    "https://www.axios.com",
    "https://www.politico.com",
    "https://www.reuters.com",
    "https://www.rollingstone.com",
    "https://www.vanity-fair.com",
    "https://www.gq.com",
    "https://www.cosmopolitan.com",
]


# ============================================================================
# GAMING — loot boxes, premium currency, subscription upsells
# ============================================================================

GAMING_URLS = [
    "https://store.steampowered.com",
    "https://store.steampowered.com/specials",
    "https://store.steampowered.com/points/shop",
    "https://store.steampowered.com/sale",
    "https://www.epicgames.com/store",
    "https://www.epicgames.com/store/en-US/free-games",
    "https://www.epicgames.com/fortnite/en-US/vbuckscard",
    "https://www.gog.com",
    "https://www.gog.com/en/games?priceRange=0,0",
    "https://www.ea.com",
    "https://www.ea.com/ea-play",
    "https://www.ea.com/games/fifa/ultimate-team",
    "https://www.xbox.com/games",
    "https://www.xbox.com/en-US/xbox-game-pass",
    "https://www.xbox.com/en-US/games/store/deals",
    "https://www.playstation.com/en-us/ps-plus",
    "https://www.playstation.com/en-us/deals",
    "https://store.playstation.com/en-us/category/deals",
    "https://www.nintendo.com/us/switch/online",
    "https://www.nintendo.com/us/store/sales-and-deals/",
    "https://www.roblox.com",
    "https://www.roblox.com/premium/membership",
    "https://www.roblox.com/upgrades/robux",
    "https://www.g2a.com",
    "https://www.g2a.com/deals",
    "https://www.cdkeys.com",
    "https://www.greenmangaming.com",
    "https://www.greenmangaming.com/vip/",
    "https://www.humblebundle.com",
    "https://www.humblebundle.com/membership",
    "https://www.twitch.tv/turbo",
    "https://www.fanatical.com",
    "https://www.kinguin.net",
    "https://www.eneba.com",
]


# ============================================================================
# FOOD DELIVERY — hidden fees, surge pricing, tipping pressure
# ============================================================================

FOOD_DELIVERY_URLS = [
    "https://www.doordash.com",
    "https://www.doordash.com/dashpass/",
    "https://www.doordash.com/consumer/checkout/",
    "https://www.ubereats.com",
    "https://www.ubereats.com/plans",
    "https://www.ubereats.com/category/deals",
    "https://www.grubhub.com",
    "https://www.grubhub.com/plus",
    "https://www.grubhub.com/deals",
    "https://www.instacart.com",
    "https://www.instacart.com/plus",
    "https://www.instacart.com/store/deals",
    "https://www.postmates.com",
    "https://www.gopuff.com",
    "https://www.gopuff.com/fam",
    "https://www.seamless.com",
    "https://www.yelp.com",
    "https://www.yelp.com/advertise",
    "https://www.opentable.com",
    "https://www.hellofresh.com",
    "https://www.hellofresh.com/plans",
    "https://www.hellofresh.com/pages/pricing",
    "https://www.blueapron.com",
    "https://www.blueapron.com/pricing",
    "https://www.freshly.com",
    "https://www.factor75.com/plans",
    "https://www.hungryroot.com/plans",
    "https://www.sunbasket.com/menu",
    "https://www.greenchef.com/plans",
    "https://www.homechef.com/pricing",
]


# ============================================================================
# FITNESS / HEALTH — subscription traps, cancellation friction, nagging
# ============================================================================

FITNESS_HEALTH_URLS = [
    "https://www.myfitnesspal.com/premium",
    "https://www.noom.com",
    "https://www.noom.com/programs/",
    "https://www.noom.com/noom-clinical/",
    "https://www.headspace.com",
    "https://www.headspace.com/subscriptions",
    "https://www.calm.com",
    "https://www.calm.com/subscribe",
    "https://www.peloton.com/app",
    "https://www.peloton.com/membership",
    "https://www.beachbodyondemand.com",
    "https://www.fitbit.com/global/us/products/services/premium",
    "https://www.strava.com/subscribe",
    "https://www.nike.com/ntc-app",
    "https://www.weightwatchers.com/us/plans",
    "https://www.weightwatchers.com/us/how-it-works",
    "https://www.betterhelp.com",
    "https://www.betterhelp.com/get-started",
    "https://www.talkspace.com",
    "https://www.talkspace.com/pricing",
    "https://www.cerebral.com",
    "https://www.hims.com",
    "https://www.hims.com/hair-loss",
    "https://www.hers.com",
    "https://www.hers.com/weight-loss",
    "https://www.nurx.com",
    "https://www.ro.co",
    "https://www.keeps.com",
    "https://www.ritual.com",
    "https://www.care-of.com",
    "https://www.whoop.com/membership/",
    "https://www.oura.com/membership",
    "https://www.classpass.com/pricing",
    "https://www.mindbodyonline.com",
    "https://www.fabletics.com/subscribe",
]


# ============================================================================
# DATING — premium upsells, social proof manipulation, urgency
# ============================================================================

DATING_URLS = [
    "https://www.tinder.com",
    "https://tinder.com/feature/subscription-tiers",
    "https://tinder.com/feature/tinder-plus",
    "https://www.match.com",
    "https://www.match.com/register",
    "https://www.match.com/dnws/cpx/en-us/landing/subscription",
    "https://www.bumble.com",
    "https://bumble.com/en-us/bumble-premium",
    "https://bumble.com/en-us/bumble-boost",
    "https://www.okcupid.com",
    "https://www.okcupid.com/premium",
    "https://www.eharmony.com",
    "https://www.eharmony.com/premium/",
    "https://hinge.co",
    "https://www.pof.com",
    "https://www.zoosk.com",
    "https://www.zoosk.com/subscribe",
    "https://www.elitesingles.com",
    "https://www.silversingles.com",
    "https://www.ourtime.com",
    "https://www.coffee-meets-bagel.com",
    "https://www.happn.com",
]


# ============================================================================
# FINANCE / FINTECH — hidden fees, forced account creation, urgency
# ============================================================================

FINANCE_URLS = [
    "https://www.creditkarma.com",
    "https://www.creditkarma.com/credit-cards",
    "https://www.creditkarma.com/personal-loans",
    "https://www.mint.com",
    "https://www.sofi.com",
    "https://www.sofi.com/credit-card/",
    "https://www.sofi.com/personal-loans/",
    "https://www.nerdwallet.com",
    "https://www.nerdwallet.com/the-best-credit-cards",
    "https://www.nerdwallet.com/mortgages",
    "https://www.bankrate.com",
    "https://www.bankrate.com/credit-cards/",
    "https://www.bankrate.com/mortgages/",
    "https://www.lendingtree.com",
    "https://www.lendingtree.com/credit-cards/",
    "https://www.turbotax.com",
    "https://turbotax.intuit.com/personal-taxes/pricing/",
    "https://www.hrblock.com",
    "https://www.hrblock.com/online-tax-filing/pricing/",
    "https://www.robinhood.com",
    "https://www.robinhood.com/gold",
    "https://www.coinbase.com",
    "https://www.coinbase.com/price",
    "https://www.coinbase.com/join",
    "https://www.paypal.com/us/digital-wallet/manage-money/crypto",
    "https://www.affirm.com",
    "https://www.klarna.com/us/",
    "https://www.klarna.com/us/klarna-app/",
    "https://www.afterpay.com/en-US",
    "https://www.chime.com",
    "https://www.chime.com/apply-debit-card/",
    "https://www.acorns.com",
    "https://www.acorns.com/pricing/",
    "https://www.personalcapital.com",
    "https://www.wealthfront.com",
    "https://www.betterment.com/pricing",
    "https://www.marcus.com/us/en",
    "https://www.discover.com/credit-cards/",
    "https://www.capitalone.com/credit-cards/",
    "https://www.citi.com/credit-cards/",
]


# ============================================================================
# TICKETING / EVENTS — hidden fees, urgency, scarcity
# ============================================================================

TICKETING_URLS = [
    "https://www.ticketmaster.com",
    "https://www.ticketmaster.com/deals",
    "https://www.ticketmaster.com/discover/concerts",
    "https://www.ticketmaster.com/discover/sports",
    "https://www.stubhub.com",
    "https://www.stubhub.com/concerts-tickets",
    "https://www.stubhub.com/nba-tickets",
    "https://www.vividseats.com",
    "https://www.vividseats.com/concerts",
    "https://www.vividseats.com/nfl",
    "https://www.seatgeek.com",
    "https://www.seatgeek.com/concerts",
    "https://www.seatgeek.com/nba",
    "https://www.eventbrite.com",
    "https://www.axs.com",
    "https://www.livenation.com",
    "https://www.gametime.co",
    "https://www.tickpick.com",
    "https://www.telecharge.com",
    "https://www.goldstar.com",
    "https://www.dice.fm",
]


# ============================================================================
# EDUCATION PLATFORMS (paid) — trial traps, upgrade pressure
# ============================================================================

EDUCATION_PAID_URLS = [
    "https://www.masterclass.com",
    "https://www.masterclass.com/subscribe",
    "https://www.skillshare.com",
    "https://www.skillshare.com/membership/checkout",
    "https://www.udemy.com",
    "https://www.udemy.com/courses/development/",
    "https://www.udemy.com/courses/business/",
    "https://www.udemy.com/courses/marketing/",
    "https://www.coursera.org/courseraplus",
    "https://www.coursera.org/professional-certificates",
    "https://www.linkedin.com/learning/subscription",
    "https://www.pluralsight.com/pricing",
    "https://www.datacamp.com/pricing",
    "https://www.codecademy.com/pricing",
    "https://www.duolingo.com/super",
    "https://www.duolingo.com/register",
    "https://www.chegg.com/study",
    "https://www.chegg.com/math-solver",
    "https://www.bartleby.com/subscribe",
    "https://brilliant.org/premium/",
    "https://www.babbel.com/en/prices",
    "https://www.rosettastone.com/lp/sbsr/sale/",
    "https://www.kumon.com",
    "https://www.varsitytutors.com/plans",
    "https://www.outschool.com",
    "https://www.teachable.com/pricing",
    "https://www.thinkific.com/pricing/",
]


# ============================================================================
# TELECOM / ISP — hidden fees, contract traps, forced bundles
# ============================================================================

TELECOM_URLS = [
    "https://www.att.com/deals/",
    "https://www.att.com/plans/wireless/",
    "https://www.att.com/internet/",
    "https://www.att.com/buy/phones/",
    "https://www.verizon.com/deals/",
    "https://www.verizon.com/plans/",
    "https://www.verizon.com/smartphones/",
    "https://www.verizon.com/home/fios-internet/",
    "https://www.t-mobile.com/deals",
    "https://www.t-mobile.com/cell-phone-plans",
    "https://www.t-mobile.com/home-internet",
    "https://www.xfinity.com/learn/offers",
    "https://www.xfinity.com/learn/internet-service",
    "https://www.xfinity.com/learn/internet-service/deals",
    "https://www.spectrum.com/internet",
    "https://www.spectrum.com/cable-tv",
    "https://www.spectrum.com/mobile",
    "https://www.cox.com/residential/internet.html",
    "https://www.cox.com/residential/bundles.html",
    "https://www.mintmobile.com",
    "https://www.mintmobile.com/plans/",
    "https://www.visible.com",
    "https://www.visible.com/plans",
    "https://www.cricketwireless.com/cell-phone-plans",
    "https://www.boost.com/plans",
    "https://www.uscellular.com/plans",
    "https://www.dish.com/programming/packages/",
    "https://www.directv.com/deals/",
    "https://www.hughesnet.com/internet",
    "https://www.starlink.com",
]


# ============================================================================
# INSURANCE / LEAD GEN — aggressive forms, urgency, misdirection
# ============================================================================

INSURANCE_URLS = [
    "https://www.progressive.com",
    "https://www.progressive.com/auto/",
    "https://www.progressive.com/bundles/",
    "https://www.geico.com",
    "https://www.geico.com/auto-insurance/",
    "https://www.statefarm.com",
    "https://www.statefarm.com/insurance/auto",
    "https://www.allstate.com",
    "https://www.allstate.com/auto-insurance",
    "https://www.libertymutual.com",
    "https://www.libertymutual.com/auto-insurance",
    "https://www.nationwide.com",
    "https://www.nationwide.com/personal/insurance/auto/",
    "https://www.usaa.com/inet/wc/insurance-auto-main",
    "https://www.thezebra.com",
    "https://www.thezebra.com/auto-insurance/",
    "https://www.policygenius.com",
    "https://www.policygenius.com/auto-insurance/",
    "https://www.insurify.com",
    "https://www.lemonade.com",
    "https://www.lemonade.com/renters",
    "https://www.lemonade.com/car",
    "https://www.cover.com",
    "https://www.ehealthinsurance.com",
    "https://www.ehealthinsurance.com/health-insurance-quotes",
    "https://www.oscar.com",
    "https://www.healthmarkets.com",
]


# ============================================================================
# HOME SERVICES / CLASSIFIEDS — urgency, fake reviews, upsells
# ============================================================================

HOME_SERVICES_URLS = [
    "https://www.thumbtack.com",
    "https://www.thumbtack.com/k/home-improvement/",
    "https://www.angi.com",
    "https://www.angi.com/nearme/",
    "https://www.homeadvisor.com",
    "https://www.taskrabbit.com",
    "https://www.taskrabbit.com/services",
    "https://www.fiverr.com",
    "https://www.fiverr.com/categories",
    "https://www.fiverr.com/business",
    "https://www.upwork.com",
    "https://www.upwork.com/hire",
    "https://www.upwork.com/freelance-jobs/",
    "https://www.rover.com",
    "https://www.rover.com/become-a-sitter/",
    "https://www.care.com",
    "https://www.care.com/enroll-p1126-freemium.html",
    "https://www.handy.com",
    "https://www.zillow.com",
    "https://www.zillow.com/homes/for_sale/",
    "https://www.zillow.com/rent/",
    "https://www.realtor.com",
    "https://www.realtor.com/soldhomeprices",
    "https://www.apartments.com",
    "https://www.trulia.com",
    "https://www.redfin.com",
    "https://www.opendoor.com",
    "https://www.offerup.com",
    "https://www.craigslist.org",
    "https://www.facebook.com/marketplace/",
]


# ============================================================================
# CLEAN: GOVERNMENT — regulated, minimal manipulation
# ============================================================================

GOVERNMENT_URLS = [
    "https://www.usa.gov",
    "https://www.usa.gov/find-a-federal-agency",
    "https://www.usa.gov/about-the-us",
    "https://www.irs.gov",
    "https://www.irs.gov/filing",
    "https://www.irs.gov/refunds",
    "https://www.ssa.gov",
    "https://www.ssa.gov/benefits/retirement",
    "https://www.ssa.gov/myaccount/",
    "https://www.cdc.gov",
    "https://www.cdc.gov/vaccines",
    "https://www.cdc.gov/chronicdisease/",
    "https://www.nasa.gov",
    "https://www.nasa.gov/missions",
    "https://www.nasa.gov/image-of-the-day/",
    "https://www.weather.gov",
    "https://www.weather.gov/safety",
    "https://www.gov.uk",
    "https://www.gov.uk/browse/benefits",
    "https://www.gov.uk/browse/tax",
    "https://www.canada.ca",
    "https://www.canada.ca/en/services/benefits.html",
    "https://www.data.gov",
    "https://www.data.gov/education/",
    "https://www.recreation.gov",
    "https://www.usps.com",
    "https://www.usps.com/manage/",
    "https://www.loc.gov",
    "https://www.loc.gov/collections/",
    "https://www.census.gov",
    "https://www.fda.gov",
    "https://www.fda.gov/drugs",
    "https://www.epa.gov",
    "https://www.energy.gov",
    "https://www.nist.gov",
    "https://www.nih.gov",
    "https://www.nsf.gov",
    "https://www.state.gov",
    "https://www.justice.gov",
    "https://www.ftc.gov",
    "https://www.sec.gov",
    "https://www.fcc.gov",
    "https://www.ed.gov",
]


# ============================================================================
# CLEAN: EDUCATION / RESEARCH — informational, not transactional
# ============================================================================

EDUCATION_URLS = [
    "https://www.wikipedia.org",
    "https://en.wikipedia.org/wiki/Dark_pattern",
    "https://en.wikipedia.org/wiki/Main_Page",
    "https://www.khanacademy.org",
    "https://www.khanacademy.org/computing",
    "https://www.khanacademy.org/math",
    "https://www.edx.org",
    "https://www.edx.org/learn/computer-science",
    "https://www.edx.org/learn/data-science",
    "https://ocw.mit.edu",
    "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/",
    "https://online.stanford.edu/free-courses",
    "https://cs.stanford.edu",
    "https://www.harvard.edu",
    "https://pll.harvard.edu/catalog/free",
    "https://arxiv.org",
    "https://arxiv.org/list/cs.AI/recent",
    "https://arxiv.org/list/cs.HC/recent",
    "https://scholar.google.com",
    "https://www.gutenberg.org",
    "https://www.gutenberg.org/browse/scores/top",
    "https://www.openculture.com",
    "https://www.openculture.com/freeonlinecourses",
    "https://www.ted.com/talks",
    "https://www.ted.com/topics",
    "https://www.pbs.org",
    "https://www.pbs.org/wgbh/nova/",
    "https://www.smithsonianmag.com",
    "https://www.nationalgeographic.com/science",
    "https://www.nature.com",
    "https://www.science.org",
    "https://pubmed.ncbi.nlm.nih.gov",
    "https://www.jstor.org",
    "https://www.researchgate.net",
    "https://www.semanticscholar.org",
]


# ============================================================================
# CLEAN: NONPROFIT / OPEN SOURCE
# ============================================================================

NONPROFIT_OPENSOURCE_URLS = [
    "https://www.mozilla.org",
    "https://www.mozilla.org/en-US/firefox/new/",
    "https://www.mozilla.org/en-US/about/",
    "https://www.eff.org",
    "https://www.eff.org/issues/privacy",
    "https://www.eff.org/deeplinks",
    "https://www.archive.org",
    "https://web.archive.org",
    "https://archive.org/details/texts",
    "https://www.w3.org",
    "https://www.w3.org/standards/",
    "https://www.apache.org",
    "https://www.apache.org/index.html#projects-list",
    "https://www.redcross.org",
    "https://www.redcross.org/get-help.html",
    "https://www.unicef.org",
    "https://www.unicef.org/what-we-do",
    "https://www.doctorswithoutborders.org",
    "https://signal.org",
    "https://signal.org/download/",
    "https://www.linux.org",
    "https://www.linuxfoundation.org",
    "https://www.fsf.org",
    "https://www.fsf.org/about/",
    "https://creativecommons.org",
    "https://creativecommons.org/about/",
    "https://www.wikimedia.org",
    "https://www.opensourceinitiative.org",
    "https://www.accessnow.org",
    "https://www.charitynavigator.org",
    "https://www.givedirectly.org",
    "https://www.kiva.org",
    "https://www.habitat.org",
    "https://www.worldwildlife.org",
    "https://www.greenpeace.org/international/",
    "https://www.amnesty.org",
]


# ============================================================================
# CLEAN: DEVELOPER / DOCUMENTATION
# ============================================================================

DEVELOPER_URLS = [
    "https://github.com",
    "https://github.com/explore",
    "https://github.com/topics",
    "https://docs.python.org",
    "https://docs.python.org/3/tutorial/",
    "https://docs.python.org/3/library/",
    "https://developer.mozilla.org",
    "https://developer.mozilla.org/en-US/docs/Web",
    "https://developer.mozilla.org/en-US/docs/Learn",
    "https://stackoverflow.com",
    "https://stackoverflow.com/questions",
    "https://stackoverflow.com/tags",
    "https://www.rust-lang.org",
    "https://doc.rust-lang.org/book/",
    "https://go.dev",
    "https://go.dev/doc/",
    "https://go.dev/tour/",
    "https://docs.djangoproject.com",
    "https://docs.djangoproject.com/en/stable/intro/tutorial01/",
    "https://react.dev",
    "https://react.dev/learn",
    "https://vuejs.org",
    "https://vuejs.org/guide/introduction.html",
    "https://tailwindcss.com",
    "https://tailwindcss.com/docs",
    "https://nodejs.org",
    "https://nodejs.org/en/docs/",
    "https://www.typescriptlang.org",
    "https://www.typescriptlang.org/docs/",
    "https://www.postgresql.org/docs/",
    "https://redis.io/docs/",
    "https://kubernetes.io/docs/home/",
    "https://docs.docker.com",
    "https://docs.docker.com/get-started/",
    "https://git-scm.com/doc",
    "https://www.latex-project.org",
    "https://jupyter.org",
    "https://jupyter.org/try-jupyter",
    "https://huggingface.co/docs",
    "https://pytorch.org/docs/stable/",
    "https://www.tensorflow.org/learn",
    "https://scikit-learn.org/stable/",
    "https://pandas.pydata.org/docs/",
    "https://numpy.org/doc/stable/",
    "https://matplotlib.org/stable/",
    "https://flask.palletsprojects.com",
    "https://fastapi.tiangolo.com",
    "https://nextjs.org/docs",
    "https://svelte.dev/docs",
    "https://angular.io/docs",
]


# ============================================================================
# CLEAN: ETHICAL / PRIVACY-FOCUSED
# ============================================================================

ETHICAL_URLS = [
    "https://basecamp.com",
    "https://basecamp.com/pricing",
    "https://www.fastmail.com",
    "https://www.fastmail.com/pricing/",
    "https://proton.me",
    "https://proton.me/mail/pricing",
    "https://proton.me/drive",
    "https://duckduckgo.com",
    "https://duckduckgo.com/about",
    "https://spreadprivacy.com",
    "https://www.patagonia.com",
    "https://www.patagonia.com/activism/",
    "https://www.patagonia.com/our-footprint/",
    "https://www.everlane.com",
    "https://www.everlane.com/about",
    "https://www.fairphone.com",
    "https://www.fairphone.com/en/story/",
    "https://tutanota.com",
    "https://tutanota.com/pricing",
    "https://standardnotes.com",
    "https://standardnotes.com/plans",
    "https://bitwarden.com",
    "https://bitwarden.com/pricing/",
    "https://mullvad.net",
    "https://mullvad.net/en/pricing",
    "https://www.thunderbird.net",
    "https://www.libreoffice.org",
    "https://www.libreoffice.org/download/",
    "https://element.io",
    "https://element.io/pricing",
    "https://matrix.org",
    "https://www.pine64.org",
    "https://frame.work",
    "https://frame.work/products",
    "https://www.system76.com",
    "https://puri.sm",
    "https://www.kobo.com",
    "https://www.remarkable.com",
    "https://obsidian.md",
    "https://obsidian.md/pricing",
    "https://logseq.com",
    "https://joplinapp.org",
]


# ============================================================================
# CLEAN: UTILITY / REFERENCE
# ============================================================================

UTILITY_URLS = [
    "https://www.timeanddate.com",
    "https://www.timeanddate.com/worldclock/",
    "https://www.timeanddate.com/calendar/",
    "https://www.wolframalpha.com",
    "https://www.xe.com",
    "https://www.xe.com/currencyconverter/",
    "https://www.speedtest.net",
    "https://www.openstreetmap.org",
    "https://www.webmd.com",
    "https://www.webmd.com/drugs/2/index",
    "https://www.mayoclinic.org",
    "https://www.mayoclinic.org/patient-care-and-health-information",
    "https://www.mayoclinic.org/diseases-conditions",
    "https://www.snopes.com",
    "https://www.merriam-webster.com",
    "https://www.merriam-webster.com/word-of-the-day",
    "https://www.wikibooks.org",
    "https://www.imdb.com",
    "https://www.imdb.com/chart/top/",
    "https://www.rottentomatoes.com",
    "https://www.goodreads.com",
    "https://www.goodreads.com/list/popular_lists",
    "https://www.allrecipes.com",
    "https://www.allrecipes.com/recipes/",
    "https://www.weather.com",
    "https://www.calculator.net",
    "https://www.convertunits.com",
    "https://www.worldometers.info",
    "https://www.etymonline.com",
    "https://www.howstuffworks.com",
    "https://www.investopedia.com",
    "https://www.healthline.com",
    "https://www.drugs.com",
    "https://www.medlineplus.gov",
    "https://www.wiktionary.org",
    "https://commons.wikimedia.org",
    "https://www.who.int",
    "https://www.un.org",
    "https://www.worldbank.org",
    "https://www.numbeo.com",
    "https://www.numbeo.com/cost-of-living/",
    "https://www.glassdoor.com",
    "https://www.indeed.com",
    "https://www.bls.gov",
]


# ============================================================================
# CLEAN: PUBLIC TOOLS / STANDARDS
# ============================================================================

PUBLIC_TOOLS_URLS = [
    "https://openlibrary.org",
    "https://www.iana.org",
    "https://www.ietf.org",
    "https://www.iso.org",
    "https://tools.ietf.org",
    "https://www.unicode.org",
    "https://caniuse.com",
    "https://httpstatuses.com",
    "https://regex101.com",
    "https://jsonlint.com",
    "https://www.debuggex.com",
    "https://www.draw.io",
    "https://excalidraw.com",
    "https://mermaid.live",
    "https://www.remove.bg",
    "https://tinypng.com",
    "https://squoosh.app",
    "https://fonts.google.com",
    "https://colorhunt.co",
    "https://coolors.co",
    "https://www.colorzilla.com",
    "https://validator.w3.org",
    "https://wave.webaim.org",
    "https://pagespeed.web.dev",
    "https://web.dev",
    "https://web.dev/learn/",
    "https://roadmap.sh",
    "https://devdocs.io",
    "https://cheatography.com",
    "https://www.overleaf.com",
    "https://codepen.io",
    "https://jsfiddle.net",
    "https://replit.com",
    "https://codesandbox.io",
    "https://stackblitz.com",
]


# ============================================================================
# AGGREGATION
# ============================================================================

def get_entire_urls():
    """
    Combine all URL lists into a single list with domain labels.

    Returns:
        list: Tuples of (url, domain_category)
    """
    all_urls = []

    url_sources = [
        # Dark pattern sites
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
        (TICKETING_URLS, "ticketing"),
        (EDUCATION_PAID_URLS, "education_paid"),
        (TELECOM_URLS, "telecom"),
        (INSURANCE_URLS, "insurance"),
        (HOME_SERVICES_URLS, "home_services"),

        # Clean baseline sites
        (GOVERNMENT_URLS, "government"),
        (EDUCATION_URLS, "education"),
        (NONPROFIT_OPENSOURCE_URLS, "nonprofit"),
        (DEVELOPER_URLS, "developer"),
        (ETHICAL_URLS, "ethical"),
        (UTILITY_URLS, "utility"),
        (PUBLIC_TOOLS_URLS, "public_tools"),
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
        "ticketing": TICKETING_URLS,
        "education_paid": EDUCATION_PAID_URLS,
        "telecom": TELECOM_URLS,
        "insurance": INSURANCE_URLS,
        "home_services": HOME_SERVICES_URLS,
        "government": GOVERNMENT_URLS,
        "education": EDUCATION_URLS,
        "nonprofit": NONPROFIT_OPENSOURCE_URLS,
        "developer": DEVELOPER_URLS,
        "ethical": ETHICAL_URLS,
        "utility": UTILITY_URLS,
        "public_tools": PUBLIC_TOOLS_URLS,
    }

    return categories.get(category, [])
