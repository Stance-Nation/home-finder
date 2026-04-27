import json
import logging
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

logger = logging.getLogger(__name__)

# MLSLI (Multiple Listing Service of Long Island) provides server-rendered
# search results for Queens neighborhoods. The site may embed listing data as
# JSON inside <script> tags or render HTML cards.

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.mlsli.com/",
    "DNT": "1",
}

_SEARCHES = [
    ("Forest Hills",       "Queens", "Forest+Hills"),
    ("Kew Gardens",        "Queens", "Kew+Gardens"),
    ("Kew Garden Hills",   "Queens", "Kew+Garden+Hills"),
    ("Richmond Hill",      "Queens", "Richmond+Hill"),
    ("South Richmond Hill","Queens", "South+Richmond+Hill"),
]

# CSS selectors to try for listing cards (site may redesign)
_CARD_SELECTORS = [
    ".listing-item",
    ".property-listing",
    "[class*='listing-item']",
    "[class*='property-card']",
    ".idx-listing",
    "li[data-listingid]",
    "[data-listingid]",
]

_PRICE_SELECTORS  = [".listing-price", ".price", "[class*='price']", "[data-price]"]
_BEDS_SELECTORS   = [".listing-beds", ".beds", "[class*='beds']", "[class*='bedroom']"]
_ADDR_SELECTORS   = [".listing-address", ".address", "[class*='address']", "h2", "h3"]
_LINK_SELECTORS   = ["a[href*='/listing/']", "a[href*='/property/']", "a"]


def _parse_int(text: str) -> int:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group().replace(",", "")) if m else 0


def _try_embedded_json(soup: BeautifulSoup) -> list[dict]:
    """Try to find a JSON array of listings embedded in a <script> tag."""
    results = []
    for script in soup.find_all("script"):
        text = script.string or ""
        # Look for patterns like var listings = [...] or window.listingData = [...]
        for pattern in [
            r"(?:var\s+listings|window\.listings|listingData)\s*=\s*(\[.+?\]);",
            r'"listings"\s*:\s*(\[.+?\])',
            r'"properties"\s*:\s*(\[.+?\])',
            r'"results"\s*:\s*(\[.+?\])',
        ]:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    if isinstance(data, list) and data:
                        results.extend(data)
                except Exception:
                    pass
    return results


class MLSLISource(BaseSource):
    name = "mlsli"

    def fetch(self, config: dict) -> list:
        listings = []
        seen: set = set()

        for neighborhood, borough, search_term in _SEARCHES:
            url = (
                f"https://www.mlsli.com/listing/search/results?"
                f"Address={search_term}&PropertyType=Single+Family&"
                f"PriceMax={config['max_price']}&"
                f"BedsMin={config['min_bedrooms']}&BedsMax={config['max_bedrooms']}&"
                f"GarageSpacesMin=1"
            )
            try:
                resp = requests.get(url, headers=_HEADERS, timeout=20)
            except Exception as e:
                logger.warning("[mlsli] request error for %s: %s", neighborhood, e)
                continue

            if resp.status_code != 200:
                logger.warning("[mlsli] %s returned HTTP %s", neighborhood, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Strategy 1: embedded JSON
            json_items = _try_embedded_json(soup)
            for item in json_items:
                if not isinstance(item, dict):
                    continue
                href = item.get("url", "") or item.get("link", "") or item.get("detailUrl", "")
                lid = f"mlsli-{item.get('id', '') or item.get('listingId', '') or href.split('/')[-1]}"
                if not lid or lid == "mlsli-" or lid in seen:
                    continue
                seen.add(lid)
                price = _parse_int(str(item.get("price", 0) or item.get("listPrice", 0)))
                beds = 0
                try:
                    beds = int(item.get("bedrooms", 0) or item.get("beds", 0) or 0)
                except (ValueError, TypeError):
                    pass
                address = item.get("address", "") or item.get("streetAddress", "")
                full_url = href if href.startswith("http") else f"https://www.mlsli.com{href}"
                listings.append(Listing(
                    listing_id=lid, address=address, neighborhood=neighborhood, borough=borough,
                    price=price, bedrooms=beds, garage=True, source="MLSLI", listing_url=full_url,
                ))

            if json_items:
                continue  # skip HTML parsing when we got JSON data

            # Strategy 2: HTML card parsing with multiple selector attempts
            cards = []
            for selector in _CARD_SELECTORS:
                cards = soup.select(selector)
                if cards:
                    break

            for card in cards:
                link = None
                for sel in _LINK_SELECTORS:
                    link = card.select_one(sel)
                    if link:
                        break
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"mlsli-{href.split('/')[-1]}"
                if not lid or lid == "mlsli-" or lid in seen:
                    continue
                seen.add(lid)

                price_el = next((card.select_one(s) for s in _PRICE_SELECTORS if card.select_one(s)), None)
                price_text = price_el.get("data-price") or price_el.get_text(strip=True) if price_el else "0"
                price = _parse_int(price_text)

                beds_el = next((card.select_one(s) for s in _BEDS_SELECTORS if card.select_one(s)), None)
                beds_text = beds_el.get_text() if beds_el else "0"
                beds = _parse_int(beds_text)

                addr_el = next((card.select_one(s) for s in _ADDR_SELECTORS if card.select_one(s)), None)
                address = addr_el.get_text(strip=True) if addr_el else ""

                full_url = href if href.startswith("http") else f"https://www.mlsli.com{href}"
                listings.append(Listing(
                    listing_id=lid, address=address, neighborhood=neighborhood, borough=borough,
                    price=price, bedrooms=beds, garage=True, source="MLSLI", listing_url=full_url,
                ))

        return listings
