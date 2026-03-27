"""
URL sources for dark pattern detection research.

~1,520+ URLs across 20 categories with sub-page coverage.
Each major site includes homepage + checkout/pricing/signup sub-pages
to capture dark patterns at different stages of the user journey.

Balance: ~65% likely dark pattern sites, ~35% clean baseline sites.

CHANGELOG (fixed):
- Removed defunct/shutdown sites (Mint, Freshly, Postmates, HBO Max, etc.)
- Replaced with current successors (Max, Empower, Going, Brevo, etc.)
- Swapped login/signup/register pages for homepages or pricing pages
- Replaced stale deep links (pcmcat IDs, campaign URLs) with stable category pages
- Fixed wrong domains (soundcloud.com, vanityfair.com)
- Removed session-required pages (checkout pages needing active cart)
- Replaced FIFA references with EA FC
- Expansion round 2: Added ~587 new URLs across all categories (new domains only)
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
    "https://www.amazon.com/outlet",

    # eBay
    "https://www.ebay.com/deals",
    "https://www.ebay.com/globaldeals",
    "https://www.ebay.com/deals/tech",
    "https://www.ebay.com/deals/fashion",

    # Wish / Temu / AliExpress (aggressive dark patterns)
    "https://www.wish.com",
    "https://www.wish.com/feed/tabbed-feed-latest",
    "https://www.temu.com",
    "https://www.temu.com/best-sellers.html",
    "https://www.temu.com/flash-sale.html",
    "https://www.aliexpress.com",
    "https://www.aliexpress.com/category/44/phones-telecommunications.html",
    "https://www.aliexpress.com/wholesale",
    "https://www.aliexpress.com/premium",

    # Fashion (fast fashion = aggressive marketing)
    "https://www.shein.com",
    "https://www.shein.com/flash-sale.html",
    "https://www.shein.com/Women-New-in-c-1.html",
    "https://www.asos.com",
    "https://www.asos.com/women/sale",
    "https://www.asos.com/men/sale",
    "https://www.zara.com",
    "https://www.zara.com/us/en/woman-new-in-l1180.html",
    "https://www.hm.com",
    "https://www2.hm.com/en_us/sale.html",
    "https://www2.hm.com/en_us/women/shop-by-product.html",
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
    "https://www.urbanoutfitters.com/sale",
    "https://www.freepeople.com/sale/",
    "https://www.nike.com/w/sale-3yaep",
    "https://www.adidas.com/us/sale",
    "https://www.uniqlo.com/us/en/sale",
    "https://www.revolve.com/sale",
    "https://www.lulus.com/categories/sale/702.html",

    # Electronics
    "https://www.bestbuy.com/site/deals",
    "https://www.bestbuy.com/site/electronics/top-deals",
    "https://www.bestbuy.com/site/my-best-buy-memberships",
    "https://www.bestbuy.com/site/misc/open-box",
    "https://www.newegg.com/todays-deals",
    "https://www.newegg.com/promotions",
    "https://www.newegg.com/GPUs/SubCategory/ID-48",
    "https://www.bhphotovideo.com/c/browse/deal-zone/ci/17590",
    "https://www.microcenter.com/site/content/specialoffer.aspx",
    "https://www.adorama.com/l/deals",

    # General retail
    "https://www.walmart.com/deals",
    "https://www.walmart.com/plus",
    "https://www.walmart.com/shop/deals",
    "https://www.walmart.com/cp/electronics/3944",
    "https://www.target.com/c/top-deals",
    "https://www.target.com/circle",
    "https://www.target.com/c/clearance",
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
    "https://www.vitacost.com/sale",

    # --- Added: Expansion round 2 ---
    # Jewelry / accessories
    "https://www.bluenile.com",
    "https://www.bluenile.com/diamond-jewelry",
    "https://www.jared.com",
    "https://www.kay.com",
    "https://www.zales.com",
    "https://www.pandora.net/en-us",
    "https://www.mejuri.com",
    "https://www.brilliantearth.com",

    # Home goods / furniture
    "https://www.potterybarn.com",
    "https://www.westelm.com",
    "https://www.cb2.com",
    "https://www.crateandbarrel.com",
    "https://www.pier1.com",
    "https://www.article.com",
    "https://www.castlery.com",
    "https://www.burrow.com",

    # Luxury / department
    "https://www.saksfifthavenue.com",
    "https://www.neimanmarcus.com",
    "https://www.bloomingdales.com",
    "https://www.bergdorfgoodman.com",
    "https://www.net-a-porter.com",
    "https://www.farfetch.com",
    "https://www.ssense.com",

    # Marketplace / other retail
    "https://www.etsy.com",
    "https://www.mercari.com",
    "https://www.poshmark.com",
    "https://www.thredup.com",
    "https://www.6pm.com",
    "https://www.zappos.com",
    "https://www.chewy.com",

    # Beauty / cosmetics
    "https://www.sephora.com",
    "https://www.sephora.com/sale",
    "https://www.ulta.com",
    "https://www.ulta.com/promotion/sale",
    "https://www.glossier.com",
    "https://www.fentybeauty.com",
    "https://www.bathandbodyworks.com",
    "https://www.colourpop.com",

    # Sporting goods
    "https://www.dickssportinggoods.com",
    "https://www.rei.com",
    "https://www.rei.com/deals",
    "https://www.backcountry.com",
    "https://www.cabelas.com",
    "https://www.academy.com",

    # Office / craft supplies
    "https://www.staples.com/deals",
    "https://www.officedepot.com/deals",
    "https://www.hobbylobby.com",
    "https://www.joann.com",
    "https://www.michaels.com",

    # Discount / warehouse
    "https://www.dollargeneral.com",
    "https://www.dollartree.com",
    "https://www.fivebelow.com",
    "https://www.burlington.com",
    "https://www.rossstores.com",
    "https://www.bigbigdeals.com",
    "https://www.shopjustice.com",
    "https://www.gap.com/browse/sale",
    "https://www.oldnavy.com/shop/sale",
    "https://www.bananarepublic.com/shop/sale",
    "https://www.anthropologie.com/sale",
    "https://www.levi.com/US/en_US/sale",
    "https://www.coach.com/sale",
    "https://www.katespade.com/sale",
    "https://www.ralphlauren.com/sale",
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
    "https://www.expedia.com/rewards",
    "https://www.expedia.com/last-minute-deals",
    "https://www.trivago.com",
    "https://www.agoda.com",
    "https://www.agoda.com/deals",
    "https://www.agoda.com/vip-deals",
    "https://www.hostelworld.com",
    "https://www.priceline.com",
    "https://www.priceline.com/deals",
    "https://www.priceline.com/vacations/",
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
    "https://www.going.com",
    "https://www.secretflying.com",
    "https://www.farecompare.com",
    "https://www.airfarewatchdog.com",

    # Budget airlines (aggressive seat/baggage upsells)
    "https://www.spirit.com",
    "https://www.spirit.com/deals",
    "https://www.frontier.com",
    "https://www.frontier.com/deals",
    "https://www.ryanair.com",
    "https://www.ryanair.com/cheap-flights",
    "https://www.easyjet.com",
    "https://www.wizzair.com",
    "https://www.allegiantair.com",
    "https://www.sunwing.ca",

    # Vacation rentals
    "https://www.airbnb.com",
    "https://www.airbnb.com/s/experiences",
    "https://www.airbnb.com/s/homes",
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

    # --- Added: Expansion round 2 ---
    # More airlines
    "https://www.norwegian.com",
    "https://www.vueling.com",
    "https://www.volaris.com",
    "https://www.jetblue.com",
    "https://www.jetblue.com/trueblue",
    "https://www.southwest.com",

    # Tour operators / travel insurance
    "https://www.viator.com",
    "https://www.getyourguide.com",
    "https://www.klook.com",
    "https://www.contiki.com",
    "https://www.gadventures.com",
    "https://www.intrepidtravel.com",
    "https://www.worldnomads.com",
    "https://www.squaremouth.com",
    "https://www.allianzassistance.com",
    "https://www.travelguard.com",

    # Additional travel aggregators
    "https://www.lonelyplanet.com",
    "https://www.rome2rio.com",
    "https://www.omio.com",
    "https://www.trainline.com",

    # More hotels / vacation
    "https://www.ihg.com",
    "https://www.marriott.com",
    "https://www.hilton.com",
    "https://www.hyatt.com",
    "https://www.wyndhamhotels.com",
    "https://www.choicehotels.com",
    "https://www.accor.com",
    "https://www.radissonhotels.com",
    "https://www.homeaway.com",
    "https://www.getaroom.com",

    # Activities / experiences
    "https://www.musement.com",
    "https://www.tiqets.com",
    "https://www.civitatis.com/en/",
    "https://www.withlocals.com",
    "https://www.headout.com/travel-guides/",
]


# ============================================================================
# STREAMING — subscription flows, cancellation friction
# ============================================================================

STREAMING_URLS = [
    # Video
    "https://www.netflix.com",
    "https://www.netflix.com/tudum",
    "https://www.hulu.com/welcome",
    "https://www.hulu.com/live-tv",
    "https://www.disneyplus.com",
    "https://www.disneyplus.com/welcome",
    "https://www.max.com",
    "https://www.max.com/plans",
    "https://www.peacocktv.com",
    "https://www.peacocktv.com/plans-pricing",
    "https://www.paramountplus.com",
    "https://www.paramountplus.com/showtime/",
    "https://www.crunchyroll.com",
    "https://www.crunchyroll.com/premium",
    "https://tv.apple.com",
    "https://www.fubo.tv",
    "https://www.fubo.tv/welcome",
    "https://www.sling.com",
    "https://www.sling.com/deals",
    "https://www.philo.com",
    "https://www.amc.com/amcplus",
    "https://www.starz.com",
    "https://www.mgmplus.com",

    # Music
    "https://www.spotify.com/premium",
    "https://www.spotify.com/us/premium/",
    "https://music.apple.com",
    "https://www.youtube.com/premium",
    "https://music.youtube.com",
    "https://www.tidal.com",
    "https://www.tidal.com/pricing",
    "https://www.deezer.com/us",
    "https://www.deezer.com/us/offers",
    "https://www.pandora.com/upgrade",
    "https://www.amazon.com/music/unlimited",
    "https://soundcloud.com/go",
    "https://www.qobuz.com/us-en/plans",

    # Audiobooks / podcasts / reading
    "https://www.audible.com/ep/membershipplans",
    "https://www.scribd.com",
    "https://www.amazon.com/kindle-unlimited",
    "https://www.blinkist.com/en/plans",

    # --- Added: Expansion round 2 ---
    # Niche streaming / sports
    "https://www.britbox.com",
    "https://www.acorn.tv",
    "https://www.shudder.com",
    "https://www.curiositystream.com",
    "https://www.mubi.com",
    "https://www.kanopy.com",
    "https://www.espnplus.com",
    "https://www.dazn.com",

    # Audiobook / podcast premium
    "https://www.libro.fm",
    "https://www.kobo.com/us/en/audiobooks",
    "https://www.storytel.com",
    "https://www.podimo.com",
    "https://www.luminary.link",
    "https://www.stitcher.com",
    "https://pocketcasts.com",

    # Live TV / sports streaming
    "https://www.directvstream.com",
    "https://www.vidgo.com",
    "https://www.frndlytv.com",
]


# ============================================================================
# SOCIAL MEDIA — signup flows, notification nudges, data collection
# ============================================================================

SOCIAL_MEDIA_URLS = [
    # Kept intentionally: login walls are forced_action dark pattern examples
    "https://www.instagram.com",           # login wall example
    "https://www.linkedin.com",            # login wall example
    "https://www.facebook.com",            # login wall example

    # Accessible without login
    "https://www.tiktok.com",
    "https://www.pinterest.com",
    "https://www.pinterest.com/ideas/",
    "https://www.reddit.com",
    "https://www.reddit.com/r/popular/",
    "https://discord.com",
    "https://discord.com/nitro",
    "https://www.quora.com",
    "https://www.quora.com/topic/Technology",
    "https://www.tumblr.com",
    "https://bsky.app",
    "https://mastodon.social",
    "https://www.meetup.com",
    "https://www.twitch.tv",
    "https://www.patreon.com",
    "https://www.substack.com",
    "https://www.snapchat.com",

    # --- Added: Expansion round 2 ---
    "https://www.threads.net",
    "https://www.lemon8-app.com",
    "https://www.bereal.com",
    "https://www.clubhouse.com",
    "https://cohost.org",
    "https://www.deviantart.com",
    "https://www.goodreads.com/community",
    "https://www.flickr.com",
    "https://vero.co",
    "https://www.polywork.com",
    "https://www.producthunt.com",
    "https://www.minds.com",
    "https://hive.social",
    "https://www.spoutible.com",
    "https://www.truthsocial.com",
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
    "https://monday.com/crm",
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
    "https://www.sketch.com/pricing/",
    "https://www.miro.com/pricing/",
    "https://www.penpot.app",
    "https://icons8.com/lunacy",

    # Cloud storage
    "https://one.google.com",
    "https://www.box.com/pricing",
    "https://www.pcloud.com/cloud-storage-pricing-plans.html",
    "https://www.sync.com/pricing/",
    "https://www.backblaze.com/cloud-backup/pricing",
    "https://www.idrive.com/pricing",

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
    "https://www.brevo.com/pricing/",
    "https://www.aweber.com/pricing.htm",
    "https://convertkit.com/pricing",

    # --- Added: Expansion round 2 ---
    # CRM / project management
    "https://www.pipedrive.com/en/pricing",
    "https://www.insightly.com/pricing/",
    "https://www.copper.com/pricing",
    "https://www.teamwork.com/pricing",
    "https://www.wrike.com/pricing/",
    "https://www.smartsheet.com/pricing",

    # AI tools (subscription-heavy)
    "https://www.jasper.ai/pricing",
    "https://www.copy.ai/pricing",
    "https://www.writesonic.com/pricing",
    "https://www.synthesia.io/pricing",
    "https://www.midjourney.com",
    "https://openai.com/chatgpt/pricing",
    "https://www.runway.ml/pricing",

    # Marketing / analytics
    "https://www.semrush.com/prices/",
    "https://ahrefs.com/pricing",
    "https://moz.com/products/pro/pricing",
    "https://www.hotjar.com/pricing/",
    "https://www.crazyegg.com/pricing",
    "https://www.optimizely.com",
    "https://www.hootsuite.com/plans",
    "https://buffer.com/pricing",
    "https://sproutsocial.com/pricing/",

    # Accounting / HR
    "https://www.quickbooks.intuit.com/pricing/",
    "https://www.xero.com/us/pricing/",
    "https://www.gusto.com/pricing",
    "https://www.rippling.com/pricing",
    "https://www.bamboohr.com/pricing",
    "https://www.deel.com/pricing",

    # Communication / video
    "https://www.loom.com/pricing",
    "https://www.calendly.com/pricing",
    "https://www.ringcentral.com/office/plansandpricing.html",
    "https://www.vonage.com/unified-communications/pricing/",
    "https://www.dialpad.com/pricing/",

    # Document / signature
    "https://www.docusign.com/products-and-pricing",
    "https://www.hellosign.com/pricing",
    "https://www.pandadoc.com/pricing/",
    "https://www.signnow.com/pricing",

    # Survey / forms
    "https://www.surveymonkey.com/pricing/individual/",
    "https://www.typeform.com/pricing/",
    "https://www.jotform.com/pricing/",
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
    "https://medium.com",
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
    "https://www.vanityfair.com",
    "https://www.gq.com",
    "https://www.cosmopolitan.com",

    # --- Added: Expansion round 2 ---
    "https://www.thetimes.com",
    "https://www.telegraph.co.uk",
    "https://www.spiegel.de/international/",
    "https://www.lemonde.fr/en/",
    "https://www.japantimes.co.jp",
    "https://www.scmp.com",
    "https://www.aljazeera.com",
    "https://www.theverge.com",
    "https://www.techcrunch.com",
    "https://arstechnica.com",
    "https://www.salon.com",
    "https://www.slate.com",
    "https://www.thedailybeast.com",
    "https://www.esquire.com",
    "https://www.harpersbazaar.com",

    # Tech / science publications
    "https://www.cnet.com",
    "https://www.zdnet.com",
    "https://www.engadget.com",
    "https://www.tomshardware.com",
    "https://www.pcmag.com",
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
    "https://www.gog.com/en/games",
    "https://www.ea.com",
    "https://www.ea.com/ea-play",
    "https://www.ea.com/games/ea-sports-fc",
    "https://www.xbox.com/games",
    "https://www.xbox.com/en-US/xbox-game-pass",
    "https://www.xbox.com/en-US/games/store/deals",
    "https://www.playstation.com/en-us/ps-plus",
    "https://www.playstation.com/en-us/deals",
    "https://www.playstation.com/en-us/ps-store/",
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

    # --- Added: Expansion round 2 ---
    "https://www.instant-gaming.com",
    "https://www.allkeyshop.com",
    "https://gg.deals",
    "https://www.indiegala.com",
    "https://www.gamefly.com",
    "https://www.greenmangaming.com/hot-deals/",
    "https://www.ubisoft.com/en-us/store",
    "https://www.blizzard.com/en-us/games",
    "https://www.nexon.com",
    "https://www.square-enix-games.com/en_US/home",
    "https://www.bungie.net/7/en/Destiny/Buy",
    "https://www.wargaming.net",
    "https://www.mmoga.com",
    "https://www.gamersgate.com",
    "https://www.voidu.com",

    # Esports / gaming communities
    "https://www.faceit.com",
    "https://www.esea.net",
    "https://www.battlenet.com.cn/en-us/",
]


# ============================================================================
# FOOD DELIVERY — hidden fees, surge pricing, tipping pressure
# ============================================================================

FOOD_DELIVERY_URLS = [
    "https://www.doordash.com",
    "https://www.doordash.com/dashpass/",
    "https://www.doordash.com/food-delivery/",
    "https://www.ubereats.com",
    "https://www.ubereats.com/plans",
    "https://www.ubereats.com/category/deals",
    "https://www.grubhub.com",
    "https://www.grubhub.com/plus",
    "https://www.grubhub.com/deals",
    "https://www.instacart.com",
    "https://www.instacart.com/plus",
    "https://www.instacart.com/store/deals",
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
    "https://www.factor75.com/plans",
    "https://www.hungryroot.com/plans",
    "https://www.sunbasket.com/menu",
    "https://www.greenchef.com/plans",
    "https://www.homechef.com/pricing",
    "https://www.cookunity.com",
    "https://www.dailyharvest.com",

    # --- Added: Expansion round 2 ---
    # Grocery delivery
    "https://www.freshdirect.com",
    "https://www.peapod.com",
    "https://www.shipt.com",
    "https://www.thrive.market",
    "https://www.misfitsmarket.com",
    "https://www.imperfectfoods.com",

    # Specialty food / drink
    "https://www.drizly.com",
    "https://www.vivino.com",
    "https://www.wine.com",
    "https://www.goldbelly.com",
    "https://www.butcherbox.com",
    "https://www.sakara.com",
    "https://www.trifectanutrition.com",
    "https://www.territoryfoods.com",
    "https://www.splendidtable.org",

    # Coffee / snack subscriptions
    "https://www.tradecoffee.com",
    "https://www.bluebottlecoffee.com",
    "https://www.atlascoffeeclub.com",
    "https://www.naturebox.com",
    "https://www.urthbox.com",
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
    "https://www.fiton.app",
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

    # --- Added: Expansion round 2 ---
    # Wellness / supplements
    "https://www.athleticgreens.com",
    "https://www.onnit.com",
    "https://www.gardenoflife.com",
    "https://www.thorne.com",
    "https://www.momentous.com",
    "https://www.seedhealth.com",

    # Telehealth / digital health
    "https://www.teladoc.com",
    "https://www.mdlive.com",
    "https://www.amwell.com",
    "https://www.getsana.com",
    "https://www.sesamecare.com",
    "https://www.zocdoc.com",

    # Fitness wearables / apps
    "https://www.withings.com",
    "https://www.garmin.com/en-US/c/sports-fitness/",
    "https://www.centr.com",

    # Mental health / sleep
    "https://www.sleepio.com",
    "https://www.happify.com",
    "https://www.ginger.com",
    "https://www.lyrahealth.com",
    "https://www.springhealth.com",
]


# ============================================================================
# DATING — premium upsells, social proof manipulation, urgency
# ============================================================================

DATING_URLS = [
    "https://www.tinder.com",
    "https://tinder.com/feature/subscription-tiers",
    "https://tinder.com/feature/tinder-plus",
    "https://www.match.com",
    "https://www.match.com/cpx/en-us/landing",
    "https://www.match.com/dating-advice",
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

    # --- Added: Expansion round 2 ---
    "https://www.theleague.com",
    "https://www.heybaby.com",
    "https://www.feeld.co",
    "https://www.her.app",
    "https://www.grindr.com",
    "https://www.scruff.com",
    "https://www.christianmingle.com",
    "https://www.jdate.com",
    "https://www.muzmatch.com",
    "https://www.raya.app",

    # Niche dating
    "https://www.seeking.com",
    "https://www.taimi.com",
    "https://www.badoo.com",
]


# ============================================================================
# FINANCE / FINTECH — hidden fees, forced account creation, urgency
# ============================================================================

FINANCE_URLS = [
    "https://www.creditkarma.com",
    "https://www.creditkarma.com/credit-cards",
    "https://www.creditkarma.com/personal-loans",
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
    "https://www.coinbase.com/explore",
    "https://www.paypal.com/us/digital-wallet/manage-money/crypto",
    "https://www.affirm.com",
    "https://www.klarna.com/us/",
    "https://www.klarna.com/us/klarna-app/",
    "https://www.afterpay.com/en-US",
    "https://www.chime.com",
    "https://www.chime.com/apply-debit-card/",
    "https://www.acorns.com",
    "https://www.acorns.com/pricing/",
    "https://www.empower.com",
    "https://www.empower.com/personal-investors",
    "https://www.wealthfront.com",
    "https://www.betterment.com/pricing",
    "https://www.marcus.com/us/en",
    "https://www.discover.com/credit-cards/",
    "https://www.capitalone.com/credit-cards/",
    "https://www.citi.com/credit-cards/",

    # --- Added: Expansion round 2 ---
    # Crypto / investment
    "https://www.kraken.com",
    "https://www.binance.us",
    "https://www.gemini.com",
    "https://www.etoro.com",
    "https://www.webull.com",
    "https://www.moomoo.com",
    "https://www.publicinvesting.com",
    "https://www.stash.com",
    "https://www.fundrise.com",

    # Tax / financial planning
    "https://www.freetaxusa.com",
    "https://www.taxact.com",
    "https://www.taxslayer.com",
    "https://www.creditcards.com",
    "https://www.wallethub.com",

    # Banking / BNPL
    "https://www.ally.com",
    "https://www.varo.com",
    "https://www.current.com",
    "https://www.sezzle.com",
    "https://www.zip.co",

    # Insurance comparison / mortgage
    "https://www.credible.com",
    "https://www.rocketmortgage.com",
    "https://www.better.com",
    "https://www.loanDepot.com",
    "https://www.prosper.com",
    "https://www.upstart.com",
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

    # --- Added: Expansion round 2 ---
    "https://www.bandsintown.com",
    "https://www.songkick.com",
    "https://www.universe.com",
    "https://www.tixr.com",
    "https://www.showclix.com",
    "https://www.etix.com",
    "https://www.ticketnetwork.com",
    "https://www.cheaptickets.com",
    "https://www.ticketliquidator.com",
    "https://www.megaseats.com",
    "https://www.ticketsmarter.com",
    "https://www.razorgator.com",
    "https://www.todaytix.com",
    "https://www.broadwaybox.com",
    "https://www.headout.com",

    # Sports-specific ticketing
    "https://www.nflshop.com",
    "https://www.nbatopshot.com",
    "https://www.mlb.com/tickets",
]


# ============================================================================
# EDUCATION PLATFORMS (paid) — trial traps, upgrade pressure
# ============================================================================

EDUCATION_PAID_URLS = [
    "https://www.masterclass.com",
    "https://www.masterclass.com/subscribe",
    "https://www.skillshare.com",
    "https://www.skillshare.com/membership",
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
    "https://www.duolingo.com",
    "https://www.duolingo.com/super",
    "https://www.chegg.com/study",
    "https://www.chegg.com/math-solver",
    "https://www.bartleby.com/subscribe",
    "https://brilliant.org/premium/",
    "https://www.babbel.com/en/prices",
    "https://www.rosettastone.com",
    "https://www.kumon.com",
    "https://www.varsitytutors.com/plans",
    "https://www.outschool.com",
    "https://www.teachable.com/pricing",
    "https://www.thinkific.com/pricing/",

    # --- Added: Expansion round 2 ---
    "https://www.edclub.com",
    "https://www.simplilearn.com",
    "https://www.springboard.com",
    "https://www.generalassemb.ly",
    "https://www.brainly.com",
    "https://www.studypool.com",
    "https://www.wyzant.com",
    "https://www.preply.com",
    "https://www.italki.com",
    "https://www.busuu.com",
    "https://www.memrise.com",
    "https://www.futurelearn.com",
    "https://www.domestika.org",
    "https://www.creativelive.com",
    "https://www.podia.com/pricing",

    # Professional certification
    "https://www.pmi.org",
    "https://www.comptia.org",
    "https://www.coursera.org/google-certificates",
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

    # --- Added: Expansion round 2 ---
    "https://www.googlefi.com",
    "https://www.usmobile.com",
    "https://www.redditmobile.com",
    "https://www.tello.com",
    "https://www.lycamobile.us",
    "https://www.straighttalk.com",
    "https://www.tracfone.com",
    "https://www.metrobyt-mobile.com",
    "https://www.freedommobile.ca",
    "https://www.fido.ca",
    "https://www.koodo.com",
    "https://www.bell.ca/Mobility",
    "https://www.rogers.com/plans",
    "https://www.three.co.uk",
    "https://www.o2.co.uk",

    # More international carriers
    "https://www.vodafone.co.uk",
    "https://www.ee.co.uk",
    "https://www.telus.com",
    "https://www.sky.com",
    "https://www.bt.com/broadband",
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
    "https://www.thezebra.com",
    "https://www.thezebra.com/auto-insurance/",
    "https://www.policygenius.com",
    "https://www.policygenius.com/auto-insurance/",
    "https://www.insurify.com",
    "https://www.lemonade.com",
    "https://www.lemonade.com/renters",
    "https://www.lemonade.com/car",
    "https://www.ehealthinsurance.com",
    "https://www.ehealthinsurance.com/health-insurance-quotes",
    "https://www.oscar.com",
    "https://www.healthmarkets.com",
    "https://www.coverhound.com",
    "https://www.root.com",

    # --- Added: Expansion round 2 ---
    # Pet insurance
    "https://www.petsbest.com",
    "https://www.embracepetinsurance.com",
    "https://www.trupanion.com",
    "https://www.healthy-paws.com",
    "https://www.fetchpet.com",

    # Home / renters / life
    "https://www.hippo.com",
    "https://www.haven.com",
    "https://www.branch.com",
    "https://www.fabric.com",
    "https://www.bestow.com",
    "https://www.ethos.com",
    "https://www.ladderlife.com",
    "https://www.selectquote.com",
    "https://www.goosehead.com",
    "https://www.comparenow.com",

    # Travel / specialized insurance
    "https://www.metlife.com",
    "https://www.travelers.com",
    "https://www.usaa.com/insurance",
    "https://www.ameritas.com",
    "https://www.amica.com",
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
    "https://www.care.com/membership",
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
    "https://www.nextdoor.com/for_sale/",

    # --- Added: Expansion round 2 ---
    # Moving / storage
    "https://www.pods.com",
    "https://www.uhaul.com",
    "https://www.extraspace.com",
    "https://www.publicstoragedeals.com",
    "https://www.movinghelp.com",

    # Cleaning / home
    "https://www.mollymaids.com",
    "https://www.merrymaids.com",
    "https://www.servpro.com",
    "https://www.homeaglow.com",
    "https://www.lawnlove.com",

    # Rental marketplace
    "https://www.hotpads.com",
    "https://www.zumper.com",
    "https://www.rentcafe.com",
    "https://www.padmapper.com",
    "https://www.movoto.com",

    # Furniture / home improvement
    "https://www.homedepot.com",
    "https://www.lowes.com",
    "https://www.menards.com",
    "https://www.acehardware.com",
    "https://www.build.com",
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
    "https://www.ssa.gov/benefits/medicare",
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

    # --- Added: Expansion round 2 ---
    # EU institutions
    "https://europa.eu",
    "https://www.europarl.europa.eu",
    "https://www.ecb.europa.eu",
    # International government
    "https://www.service-public.fr",
    "https://www.bundesregierung.de/breg-en",
    "https://www.governo.it",
    "https://www.australia.gov.au",
    "https://www.govt.nz",
    "https://www.gov.za",
    "https://www.india.gov.in",

    # US state / local
    "https://www.ny.gov",
    "https://www.ca.gov",
    "https://www.texas.gov",
    "https://www.illinois.gov",

    # More US federal
    "https://www.dhs.gov",
    "https://www.sba.gov",
    "https://www.gsa.gov",
    "https://www.opm.gov",
    "https://www.va.gov",
    "https://www.fema.gov",
    "https://www.consumerfinance.gov",
    "https://www.healthcare.gov",
    "https://www.benefits.gov",

    # More international
    "https://www.gov.sg",
    "https://www.riksdagen.se/en/",
    "https://www.government.nl",

    # More state government
    "https://www.ohio.gov",
    "https://www.michigan.gov",
    "https://www.georgia.gov",
    "https://www.colorado.gov",
    "https://www.mass.gov",
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

    # --- Added: Expansion round 2 ---
    # Universities
    "https://www.ox.ac.uk",
    "https://www.cam.ac.uk",
    "https://www.caltech.edu",
    "https://www.berkeley.edu",
    "https://www.yale.edu",
    "https://www.princeton.edu",
    "https://www.columbia.edu",
    "https://www.uchicago.edu",

    # Research / libraries
    "https://www.doaj.org",
    "https://www.biorxiv.org",
    "https://www.medrxiv.org",
    "https://www.ssrn.com",
    "https://dl.acm.org",
    "https://ieeexplore.ieee.org",
    "https://www.worldcat.org",
    # Libraries / educational
    "https://www.dpla.io",
    "https://www.europeana.eu",
    "https://www.biodiversitylibrary.org",
    "https://www.hathitrust.org",
    "https://www.jstor.org/open/",
    "https://ocw.mit.edu/collections/",
    "https://www.coursehero.com/free-courses/",

    # More universities
    "https://www.ethz.ch/en.html",
    "https://www.epfl.ch/en/",
    "https://www.tum.de/en/",
    "https://www.anu.edu.au",
    "https://www.utoronto.ca",
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

    # --- Added: Expansion round 2 ---
    # More foundations / charities
    "https://www.gatesfoundation.org",
    "https://www.fordfoundation.org",
    "https://www.rockefellerfoundation.org",
    "https://www.macfound.org",
    "https://www.hewlett.org",
    "https://www.oxfam.org",
    "https://www.savethechildren.org",
    "https://www.care.org",
    "https://www.directrelief.org",
    "https://www.feedingamerica.org",

    # Open source projects
    "https://www.eclipse.org",
    "https://www.cncf.io",
    "https://www.openbsd.org",
    "https://www.freebsd.org",
    "https://www.gnome.org",
    "https://kde.org",
    "https://www.blender.org",
    "https://www.gimp.org",
    "https://www.vlcplayer.org",
    "https://www.audacityteam.org",
    "https://www.inkscape.org",
    "https://www.scribus.net",
    "https://calibre-ebook.com",
    "https://www.openstreetmap.org/about",
    "https://www.letsencrypt.org",

    # More charities
    "https://www.wfp.org",
    "https://www.unhcr.org",
    "https://www.msf.org",
    "https://www.nature.org",
    "https://www.aclu.org",
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

    # --- Added: Expansion round 2 ---
    # More programming languages / docs
    "https://www.haskell.org",
    "https://elixir-lang.org",
    "https://www.scala-lang.org",
    "https://kotlinlang.org",
    "https://www.swift.org",
    "https://ziglang.org",
    "https://julialang.org",
    "https://clojure.org",

    # More developer tools / docs
    "https://www.terraform.io/docs",
    "https://www.ansible.com/resources",
    "https://prometheus.io/docs/",
    "https://grafana.com/docs/",
    "https://www.rabbitmq.com/docs",
    "https://kafka.apache.org/documentation/",
    "https://www.elastic.co/guide/",
    "https://www.mongodb.com/docs/",
    "https://vitejs.dev",
    "https://astro.build/docs",
    "https://remix.run/docs",
    "https://www.prisma.io/docs",
    "https://supabase.com/docs",
    "https://pnpm.io",
    "https://deno.land/manual",
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
    "https://tuta.com",
    "https://tuta.com/pricing",
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

    # --- Added: Expansion round 2 ---
    # More privacy-focused / sustainable
    "https://www.startpage.com",
    "https://www.qwant.com",
    "https://www.ecosia.org",
    "https://www.braveSearch.com",
    "https://www.posteo.de/en",
    "https://www.disroot.org",
    "https://www.cryptpad.org",
    "https://www.nextcloud.com",
    "https://www.wireguard.com",
    "https://www.keepassxc.org",

    # Sustainable / ethical companies
    "https://www.allbirds.com",
    "https://www.tentree.com",
    "https://www.eileen-fisher.com",
    "https://www.tomshoes.com",
    "https://www.drbronnerssuds.com",
    "https://www.seventhgeneration.com",
    "https://www.grove.co",
    "https://www.thinkpenguin.com",
    "https://www.ifixit.com",
    "https://www.buymeacoffee.com",

    # More ethical tech
    "https://www.lineageos.org",
    "https://www.f-droid.org",
    "https://www.calyx.institute.org",
    "https://www.torproject.org",
    "https://tailscale.com",

    # More sustainable brands
    "https://www.who-gives-a-crap.com",
    "https://www.pela.earth",
    "https://www.naadam.co",
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

    # --- Added: Expansion round 2 ---
    # Reference / dictionaries
    "https://www.dictionary.com",
    "https://www.thesaurus.com",
    "https://www.vocabulary.com",
    "https://www.britannica.com",
    "https://www.infoplease.com",

    # Health / medical reference
    "https://www.clevelandclinic.org",
    "https://www.hopkinsmedicine.org",
    "https://www.mountsinai.org/health-library",
    "https://www.nhs.uk",
    "https://www.uptodate.com",

    # Calculators / tools
    "https://www.desmos.com",
    "https://www.symbolab.com",
    "https://www.mathway.com",
    "https://www.unitconverters.net",
    "https://www.rapidtables.com",

    # Data / statistics
    "https://ourworldindata.org",
    "https://www.gapminder.org",
    "https://datausa.io",
    "https://data.worldbank.org",
    "https://www.statista.com",
    "https://fred.stlouisfed.org",
    "https://trends.google.com",
    "https://www.similarweb.com",
    "https://www.archive.org/details/tv",

    # More reference
    "https://www.acronymfinder.com",
    "https://www.abbreviations.com",
    "https://www.almanac.com",
    "https://www.usgs.gov",
    "https://earthquake.usgs.gov",

    # Food / cooking reference
    "https://www.seriouseats.com",
    "https://www.foodnetwork.com",
    "https://www.epicurious.com",
    "https://www.simplyrecipes.com",
    "https://www.budgetbytes.com",
]


# ============================================================================
# CLEAN: PUBLIC TOOLS / STANDARDS
# ============================================================================

PUBLIC_TOOLS_URLS = [
    "https://openlibrary.org",
    "https://www.iana.org",
    "https://www.ietf.org",
    "https://www.iso.org",
    "https://www.ietf.org/standards/",
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

    # --- Added: Expansion round 2 ---
    # Standards bodies / registries
    "https://www.rfc-editor.org",
    "https://www.icann.org",
    "https://www.w3.org/WAI/",
    "https://www.ecma-international.org",
    "https://tc39.es",

    # Free online tools
    "https://www.photopea.com",
    "https://www.canva.com/free/",
    "https://app.diagrams.net",
    "https://www.overleaf.com/learn",
    "https://www.deepl.com/translator",
    "https://alternativeto.net",
    "https://www.virustotal.com",
    "https://haveibeenpwned.com",
    "https://www.ssllabs.com/ssltest/",
    "https://observatory.mozilla.org",

    # Code playgrounds / learning
    "https://www.typingclub.com",
    "https://exercism.org",
    "https://leetcode.com",
    "https://www.hackerrank.com",
    "https://www.freecodecamp.org",
    "https://glitch.com",
    "https://observablehq.com",
    "https://www.shadertoy.com",
    "https://play.rust-lang.org",
    "https://goplay.tools",

    # More free tools
    "https://jsonformatter.org",
    "https://www.base64decode.org",
    "https://crontab.guru",
    "https://explainshell.com",
    "https://www.diffchecker.com",
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