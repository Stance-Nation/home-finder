import hashlib
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
    ("Richmond Hill",      "Queens", "Richmond+Hill"),
    ("South Richmond Hill","Queens", "South+Richmond+Hill"),
]

# CSS selectors for IDX-based listing cards (in priority order)
_CARD_SELECTORS = [
    "[data-propertyid]",
    "li[data-id]",
    ".idx-property",
    ".idx-listing",
    ".idx-listing-container",
    ".property-card",
    ".listing-card",
    "[class*='property-card']",
    "[class*='listing-card']",
]

_PRICE_SELECTORS = [".price", "[class*='price']", "[data-price]"]
_BEDS_SELECTORS  = [".beds", "[class*='beds']", "[class*='bedroom']"]
_ADDR_SELECTORS  = [".address", "[class*='address']", "h2", "h3", "address"]


def _parse_int(text: str) -> int:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group().replace(",", "")) if m else 0


def _parse_html(html: str, neighborhood: str, borough: str) -> list[Listing]:
    """
    Parse LIRealtor search results HTML and return a list of Listing objects.

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
    results = []
    for script in soup.find_all("script"):
        text = script.string or ""
        for pattern in [
            r"(?:var\s+listings|window\.listings|listingData|propertiesData|window\.__IDX_LISTINGS__)\s*=\s*(\[.+?\]);",
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
            or item.get("listing_url", "")
        )
        raw_id = item.get("id", "") or item.get("listingId", "") or href
        lid = f"lirealtor-{hashlib.md5(str(raw_id).encode()).hexdigest()[:12]}"
        if not raw_id or lid in seen:
            continue
        seen.add(lid)
        price = _parse_int(str(item.get("price", 0) or item.get("listPrice", 0)))
        beds = 0
        try:
            beds = int(item.get("bedrooms", 0) or item.get("beds", 0) or 0)
        except (ValueError, TypeError):
            pass
        address = item.get("address", "") or item.get("streetAddress", "")
        full_url = href if href.startswith("http") else f"https://www.lirealtor.com{href}"
        listings.append(Listing(
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="LIRealtor",
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
        link = card.select_one("a")
        if not link:
            continue
        href = link.get("href", "")
        lid = f"lirealtor-{hashlib.md5(href.encode()).hexdigest()[:12]}"
        if lid in seen or not href:
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

        full_url = href if href.startswith("http") else f"https://www.lirealtor.com{href}"
        listings.append(Listing(
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="LIRealtor",
            listing_url=full_url,
        ))
    return listings


class LIRealtorSource(BaseSource):
    name = "lirealtor"

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
                            f"https://www.lirealtor.com/listing/search?"
                            f"location={search_term}&type=residential&"
                            f"max_price={config['max_price']}&"
                            f"min_beds={config['min_bedrooms']}&max_beds={config['max_bedrooms']}&"
                            f"garage=1"
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
                                "[lirealtor] page load error for %s: %s", neighborhood, e
                            )
                            continue
                        finally:
                            page.close()

                        found = _parse_html(html, neighborhood, borough)
                        logger.info(
                            "[lirealtor] %s: %d listings", neighborhood, len(found)
                        )
                        for listing in found:
                            if listing.listing_id not in seen:
                                seen.add(listing.listing_id)
                                listings.append(listing)
                finally:
                    browser.close()
        except Exception as e:
            logger.error("[lirealtor] browser error: %s", e)

        return listings
