import json
import logging
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from core.models import Listing
from sources.base import BaseSource

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_SEARCHES = [
    ("Forest Hills",       "Queens", "Forest+Hills"),
    ("Kew Gardens",        "Queens", "Kew+Gardens"),
    ("Kew Garden Hills",   "Queens", "Kew+Garden+Hills"),
    ("Richmond Hill",      "Queens", "Richmond+Hill"),
    ("South Richmond Hill","Queens", "South+Richmond+Hill"),
]

# CSS selectors for IDX-based listing cards (in priority order)
_CARD_SELECTORS = [
    "[data-listingid]",
    "li[data-listingid]",
    ".idx-listing",
    ".idx-listing-container",
    ".listing-item",
    "[class*='idx-listing']",
    "[class*='listing-item']",
    ".property-listing",
    "[class*='property-card']",
]

_PRICE_SELECTORS = [".listing-price", ".price", "[class*='price']", "[data-price]"]
_BEDS_SELECTORS  = [".listing-beds", ".beds", "[class*='beds']", "[class*='bedroom']"]
_ADDR_SELECTORS  = [".listing-address", ".address", "[class*='address']", "h2", "h3"]
_LINK_SELECTORS  = ["a[href*='/listing/']", "a[href*='/property/']", "a"]


def _parse_int(text: str) -> int:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group().replace(",", "")) if m else 0


def _parse_html(html: str, neighborhood: str, borough: str) -> list[Listing]:
    """
    Parse MLSLI search results HTML and return a list of Listing objects.

    This function is pure (no browser/network calls) and is the primary target
    for unit tests. It tries two strategies in order:
      1. Embedded JSON arrays in <script> tags (IDX window variables)
      2. CSS-based card parsing with IDX-specific selector patterns
    """
    soup = BeautifulSoup(html, "lxml")

    # Strategy 1: embedded JSON
    json_items = _try_embedded_json(soup)
    if json_items:
        return _listings_from_json(json_items, neighborhood, borough)

    # Strategy 2: HTML card parsing
    return _listings_from_html_cards(soup, neighborhood, borough)


def _try_embedded_json(soup: BeautifulSoup) -> list[dict]:
    """Try to find a JSON array of listings embedded in a <script> tag."""
    results = []
    for script in soup.find_all("script"):
        text = script.string or ""
        for pattern in [
            r"(?:var\s+listings|window\.listings|listingData|window\.__IDX_LISTINGS__)\s*=\s*(\[.+?\]);",
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


def _listings_from_json(
    json_items: list[dict], neighborhood: str, borough: str
) -> list[Listing]:
    listings = []
    seen: set = set()
    for item in json_items:
        if not isinstance(item, dict):
            continue
        href = (
            item.get("url", "")
            or item.get("link", "")
            or item.get("detailUrl", "")
        )
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
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="MLSLI",
            listing_url=full_url,
        ))
    return listings


def _listings_from_html_cards(
    soup: BeautifulSoup, neighborhood: str, borough: str
) -> list[Listing]:
    cards = []
    for selector in _CARD_SELECTORS:
        cards = soup.select(selector)
        if cards:
            break

    listings = []
    seen: set = set()
    for card in cards:
        # Also check for listingid in data attribute directly on the card
        listing_id_attr = card.get("data-listingid", "")

        link = None
        for sel in _LINK_SELECTORS:
            link = card.select_one(sel)
            if link:
                break
        if not link and not listing_id_attr:
            continue

        href = link.get("href", "") if link else ""
        raw_id = listing_id_attr or href.split("/")[-1]
        lid = f"mlsli-{raw_id}"
        if not raw_id or lid == "mlsli-" or lid in seen:
            continue
        seen.add(lid)

        price_el = next(
            (card.select_one(s) for s in _PRICE_SELECTORS if card.select_one(s)), None
        )
        price_text = (
            (price_el.get("data-price") or price_el.get_text(strip=True))
            if price_el
            else "0"
        )
        price = _parse_int(price_text)

        beds_el = next(
            (card.select_one(s) for s in _BEDS_SELECTORS if card.select_one(s)), None
        )
        beds = _parse_int(beds_el.get_text() if beds_el else "0")

        addr_el = next(
            (card.select_one(s) for s in _ADDR_SELECTORS if card.select_one(s)), None
        )
        address = addr_el.get_text(strip=True) if addr_el else ""

        full_url = href if href.startswith("http") else f"https://www.mlsli.com{href}"
        listings.append(Listing(
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="MLSLI",
            listing_url=full_url,
        ))
    return listings


class MLSLISource(BaseSource):
    name = "mlsli"

    def fetch(self, config: dict) -> list:
        listings = []
        seen: set = set()

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    context = browser.new_context(user_agent=_USER_AGENT)
                    for neighborhood, borough, search_term in _SEARCHES:
                        url = (
                            f"https://www.mlsli.com/listing/search/results?"
                            f"Address={search_term}&PropertyType=Single+Family&"
                            f"PriceMax={config['max_price']}&"
                            f"BedsMin={config['min_bedrooms']}&BedsMax={config['max_bedrooms']}&"
                            f"GarageSpacesMin=1"
                        )
                        page = context.new_page()
                        try:
                            page.goto(url, timeout=30_000)
                            try:
                                page.wait_for_load_state("networkidle", timeout=30_000)
                            except PlaywrightTimeoutError:
                                pass
                            for selector in _CARD_SELECTORS:
                                try:
                                    page.wait_for_selector(selector, timeout=5_000)
                                    break
                                except Exception:
                                    continue
                            html = page.content()
                        except Exception as e:
                            logger.warning(
                                "[mlsli] page load error for %s: %s", neighborhood, e
                            )
                            continue
                        finally:
                            page.close()

                        found = _parse_html(html, neighborhood, borough)
                        logger.info("[mlsli] %s: %d listings", neighborhood, len(found))
                        for listing in found:
                            if listing.listing_id not in seen:
                                seen.add(listing.listing_id)
                                listings.append(listing)
                finally:
                    browser.close()
        except Exception as e:
            logger.error("[mlsli] browser error: %s", e)

        return listings
