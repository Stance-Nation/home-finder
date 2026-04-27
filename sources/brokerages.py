import logging
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

logger = logging.getLogger(__name__)

BROKERAGE_CONFIGS = [
    {"name": "brown_harris_stevens", "display": "Brown Harris Stevens",
     "search_url": "https://www.bhsusa.com/search#?Status=For+Sale&PropertyType=House&MinPrice=0&MaxPrice={max_price}&MinBeds={min_beds}&MaxBeds={max_beds}&Neighborhoods={neighborhood}",
     "card_selector": ".property-card, .listing-card", "address_selector": ".property-address, .address",
     "price_selector": ".property-price, .price", "beds_selector": ".property-beds, .beds",
     "link_selector": "a", "base_url": "https://www.bhsusa.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"]},
    {"name": "douglas_elliman", "display": "Douglas Elliman",
     "search_url": "https://www.elliman.com/new-york/search/for-sale-in-{neighborhood_slug}/priceto-{max_price}/beds-{min_beds}-{max_beds}",
     "card_selector": ".listing-card, .property-item", "address_selector": ".listing-address, h3",
     "price_selector": ".listing-price, .price", "beds_selector": ".listing-beds, .beds",
     "link_selector": "a.listing-link, a", "base_url": "https://www.elliman.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"]},
    {"name": "corcoran", "display": "Corcoran",
     "search_url": "https://www.corcoran.com/nyc/for-sale?neighborhoods={neighborhood}&maxPrice={max_price}&minBeds={min_beds}&propertyType=house",
     "card_selector": "[data-testid='listing-card'], .listing", "address_selector": "[data-testid='address'], .address",
     "price_selector": "[data-testid='price'], .price", "beds_selector": "[data-testid='beds'], .beds",
     "link_selector": "a", "base_url": "https://www.corcoran.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"]},
    {"name": "compass", "display": "Compass Real Estate",
     "search_url": "https://www.compass.com/homes-for-sale/{neighborhood_slug}-new-york/?price_max={max_price}&beds_min={min_beds}&beds_max={max_beds}&property_type=single_family",
     "card_selector": ".uc-listingCard, .listing-card", "address_selector": ".uc-listingCard-address, .address",
     "price_selector": ".uc-listingCard-price, .price", "beds_selector": ".uc-listingCard-beds, .beds",
     "link_selector": "a", "base_url": "https://www.compass.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"]},
    {"name": "nest_seekers", "display": "Nest Seekers International",
     "search_url": "https://www.nestseekers.com/sale/{neighborhood_slug}?MaxPrice={max_price}&MinBeds={min_beds}&Type=House",
     "card_selector": ".listing-item, .property-card", "address_selector": ".listing-address, .address",
     "price_selector": ".listing-price, .price", "beds_selector": ".listing-beds, .beds",
     "link_selector": "a", "base_url": "https://www.nestseekers.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"]},
    {"name": "sothebys", "display": "Sotheby's International Realty",
     "search_url": "https://www.sothebysrealty.com/eng/sales/li-usa/pr-0-{max_price}/be-{min_beds}-{max_beds}/hse/{neighborhood_slug}",
     "card_selector": ".property-item, .listing-card", "address_selector": ".property-address, .address",
     "price_selector": ".property-price, .price", "beds_selector": ".property-beds, .beds",
     "link_selector": "a", "base_url": "https://www.sothebysrealty.com",
     "neighborhoods": ["Forest Hills", "Pelham Bay", "Country Club"]},
    {"name": "coldwell_banker", "display": "Coldwell Banker",
     "search_url": "https://www.coldwellbanker.com/for-sale/homes/{neighborhood_slug}-ny?price=0_{max_price}&beds={min_beds}_{max_beds}&garage=true",
     "card_selector": ".listing-card, [data-testid='property-card']", "address_selector": ".listing-address, address",
     "price_selector": ".listing-price, .price", "beds_selector": ".listing-beds, .beds",
     "link_selector": "a", "base_url": "https://www.coldwellbanker.com",
     "neighborhoods": ["Forest Hills", "Richmond Hill", "Pelham Bay", "Morris Park"]},
    {"name": "century21", "display": "Century 21",
     "search_url": "https://www.century21.com/real-estate/homes-for-sale/filterQS=pg~1|sid~{neighborhood_slug}|prc~0_{max_price}|bd~{min_beds}_{max_beds}|gsr~t/",
     "card_selector": ".property-card, .listing", "address_selector": ".property-address, .address",
     "price_selector": ".property-price, .price", "beds_selector": ".beds, .bedrooms",
     "link_selector": "a", "base_url": "https://www.century21.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay"]},
    {"name": "remax", "display": "RE/MAX",
     "search_url": "https://www.remax.com/homes-for-sale/{neighborhood_slug}-ny-usa/type_sfr/pr_0-{max_price}/bd_{min_beds}-{max_beds}",
     "card_selector": ".listing-card, [class*='listing']", "address_selector": "[class*='address']",
     "price_selector": "[class*='price']", "beds_selector": "[class*='bed']",
     "link_selector": "a", "base_url": "https://www.remax.com",
     "neighborhoods": ["Forest Hills", "Richmond Hill", "Pelham Bay", "Morris Park"]},
    {"name": "bizzarro", "display": "The Bizzarro Agency",
     "search_url": "https://www.bizzarroagency.com/listings/?max_price={max_price}&min_beds={min_beds}&neighborhood={neighborhood}",
     "card_selector": ".listing-item, .property", "address_selector": ".listing-address, .address",
     "price_selector": ".listing-price, .price", "beds_selector": ".beds, .bedrooms",
     "link_selector": "a", "base_url": "https://www.bizzarroagency.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay"]},
    {"name": "bond_new_york", "display": "Bond New York",
     "search_url": "https://www.bondnewyork.com/listings/for-sale?neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing-card, .property-card", "address_selector": ".listing-address, .address",
     "price_selector": ".listing-price, .price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.bondnewyork.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"]},
    {"name": "livingny", "display": "LivingNY",
     "search_url": "https://www.livingny.com/search?type=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing, .property-card", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.livingny.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"]},
    # morrell_hirsch removed — www.morrellhirsch.com does not resolve DNS (domain defunct)
    {"name": "realny", "display": "RealNY / RealNYProperties",
     "search_url": "https://www.realny.com/sale?neighborhood={neighborhood}&max_price={max_price}&beds_min={min_beds}",
     "card_selector": ".listing-card, .property", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.realny.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"]},
    {"name": "alphanyc", "display": "AlphaNYC",
     "search_url": "https://www.alphanyc.com/listings?status=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing, .property-card", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.alphanyc.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"]},
    {"name": "howard_hanna_rand", "display": "Howard Hanna Rand",
     "search_url": "https://www.howardhannarand.com/listing-search/?status=active&type=house&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing-card, .property", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.howardhannarand.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"]},
    {"name": "bohemia", "display": "Bohemia Realty Group",
     "search_url": "https://www.bohemiarealty.com/listings?sale=true&neighborhood={neighborhood}&max_price={max_price}&beds={min_beds}",
     "card_selector": ".listing, .property-card", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.bohemiarealty.com",
     "neighborhoods": ["Pelham Bay", "Morris Park", "Pelham Gardens", "Country Club"]},
    {"name": "real_brokerage", "display": "Real Brokerage",
     "search_url": "https://www.joinreal.com/listings?type=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing-card, .property", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.joinreal.com",
     "neighborhoods": ["Forest Hills", "Pelham Bay", "Morris Park"]},
    {"name": "terrace_sothebys", "display": "Terrace Sotheby's",
     "search_url": "https://www.terracesothebysrealty.com/listings?type=sale&neighborhood={neighborhood}&max_price={max_price}&beds_min={min_beds}",
     "card_selector": ".listing-item, .property-card", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.terracesothebysrealty.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Kew Garden Hills"]},
    {"name": "daniel_gale", "display": "Daniel Gale Sotheby's",
     "search_url": "https://www.danielgale.com/search?status=active&type=SF&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
     "card_selector": ".listing-card, .property", "address_selector": ".address",
     "price_selector": ".price", "beds_selector": ".beds",
     "link_selector": "a", "base_url": "https://www.danielgale.com",
     "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"]},
]

_NEIGHBORHOOD_SLUGS = {
    "Forest Hills": "forest-hills", "Kew Gardens": "kew-gardens",
    "Kew Garden Hills": "kew-garden-hills", "Richmond Hill": "richmond-hill",
    "South Richmond Hill": "south-richmond-hill", "Pelham Gardens": "pelham-gardens",
    "Pelham Bay": "pelham-bay", "Pelham Parkway": "pelham-parkway",
    "Morris Park": "morris-park", "Country Club": "country-club",
}

_BOROUGHS = {
    "Forest Hills": "Queens", "Kew Gardens": "Queens", "Kew Garden Hills": "Queens",
    "Richmond Hill": "Queens", "South Richmond Hill": "Queens",
    "Pelham Gardens": "Bronx", "Pelham Bay": "Bronx", "Pelham Parkway": "Bronx",
    "Morris Park": "Bronx", "Country Club": "Bronx",
}

class BrokerageSource(BaseSource):
    name = "brokerages"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    def __init__(self, brokerage_config: dict):
        self.cfg = brokerage_config
        self.name = brokerage_config["name"]

    # Brokerage headers — more realistic to avoid bot-detection
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
    }

    def fetch(self, config: dict) -> list:
        listings = []
        seen: set = set()
        for neighborhood in self.cfg["neighborhoods"]:
            slug = _NEIGHBORHOOD_SLUGS.get(neighborhood, neighborhood.lower().replace(" ", "-"))
            url = self.cfg["search_url"].format(
                max_price=config["max_price"],
                min_beds=config["min_bedrooms"],
                max_beds=config["max_bedrooms"],
                neighborhood=neighborhood,
                neighborhood_slug=slug,
            )
            try:
                resp = requests.get(url, headers=self._HEADERS, timeout=20)
                if resp.status_code != 200:
                    logger.warning(
                        "[%s] %s returned HTTP %s", self.name, neighborhood, resp.status_code
                    )
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                for card in soup.select(self.cfg["card_selector"]):
                    link_el = card.select_one(self.cfg["link_selector"])
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    lid = f"{self.name}-{hashlib.md5(href.encode()).hexdigest()[:12]}"
                    if lid in seen or not href:
                        continue
                    seen.add(lid)
                    price_el = card.select_one(self.cfg["price_selector"])
                    price_text = price_el.get_text(strip=True) if price_el else "0"
                    price = int(re.sub(r"[^\d]", "", price_text) or 0)
                    beds_el = card.select_one(self.cfg["beds_selector"])
                    beds_text = beds_el.get_text() if beds_el else "0"
                    beds_match = re.search(r"\d+", beds_text)
                    beds = int(beds_match.group()) if beds_match else 0
                    addr_el = card.select_one(self.cfg["address_selector"])
                    address = addr_el.get_text(strip=True) if addr_el else ""
                    full_url = href if href.startswith("http") else f"{self.cfg['base_url']}{href}"
                    listings.append(Listing(
                        listing_id=lid,
                        address=address,
                        neighborhood=neighborhood,
                        borough=_BOROUGHS.get(neighborhood, "Queens"),
                        price=price,
                        bedrooms=beds,
                        garage=True,
                        source=self.cfg["display"],
                        listing_url=full_url,
                    ))
            except requests.exceptions.SSLError as e:
                logger.warning("[%s] SSL error for %s: %s", self.name, neighborhood, e)
            except requests.exceptions.ConnectionError as e:
                logger.warning(
                    "[%s] Connection error for %s (DNS/reset?): %s", self.name, neighborhood, e
                )
            except requests.exceptions.Timeout:
                logger.warning("[%s] Timeout for %s", self.name, neighborhood)
            except Exception as e:
                logger.warning("[%s] %s failed: %s", self.name, neighborhood, e)
        return listings


def get_all_brokerage_sources() -> list:
    return [BrokerageSource(cfg) for cfg in BROKERAGE_CONFIGS]
