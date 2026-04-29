import json
import logging
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from core.models import Listing
from sources.base import BaseSource

try:
    from playwright_stealth import stealth_sync as _stealth_sync
    _STEALTH_AVAILABLE = True
except ImportError:
    _STEALTH_AVAILABLE = False

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_SEARCHES = [
    ("Forest Hills",       "Queens", "forest-hills-queens"),
    ("Kew Gardens",        "Queens", "kew-gardens-queens"),
    ("Kew Garden Hills",   "Queens", "kew-garden-hills-queens"),
    ("Richmond Hill",      "Queens", "richmond-hill-queens"),
    ("South Richmond Hill","Queens", "south-richmond-hill-queens"),
    ("Pelham Gardens",     "Bronx",  "pelham-gardens-bronx"),
    ("Pelham Bay",         "Bronx",  "pelham-bay-bronx"),
    ("Pelham Parkway",     "Bronx",  "pelham-parkway-bronx"),
    ("Morris Park",        "Bronx",  "morris-park-bronx"),
    ("Country Club",       "Bronx",  "country-club-bronx"),
]

# CSS selectors to try for listing cards (in priority order)
_CARD_SELECTORS = [
    "article.listingCard",
    "[data-testid='listing-card']",
    "[class*='listingCard']",
    ".SC-listing-card",
    "article.ListingCard",
    ".listing-item",
]


def _parse_int(text: str) -> int:
    m = re.search(r"\d[\d,]*", text or "")
    return int(m.group().replace(",", "")) if m else 0


def _parse_html(html: str, neighborhood: str, borough: str) -> list[Listing]:
    """
    Parse StreetEasy search results HTML and return a list of Listing objects.

    This function is pure (no browser/network calls) and is the primary target
    for unit tests. It tries three strategies in order:
      1. JSON-LD structured data (<script type="application/ld+json">)
      2. Embedded JS state (window.__INITIAL_STATE__ or similar)
      3. CSS-based card parsing with multiple selector patterns
    """
    soup = BeautifulSoup(html, "lxml")
    listings: list[Listing] = []

    # Strategy 1: JSON-LD
    listings = _listings_from_json_ld(_extract_json_ld(soup), neighborhood, borough)
    if listings:
        return listings

    # Strategy 2: embedded JS state
    state = _extract_embedded_json_state(soup)
    if state:
        listings = _listings_from_embedded_state(state, neighborhood, borough)
    if listings:
        return listings

    # Strategy 3: HTML card parsing
    return _listings_from_html_cards(soup, neighborhood, borough)


def _extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    """Return all JSON-LD objects found in the page."""
    results = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(tag.string or "")
            if isinstance(obj, list):
                results.extend(obj)
            else:
                results.append(obj)
        except Exception:
            pass
    return results


def _listings_from_json_ld(
    json_ld_objects: list[dict], neighborhood: str, borough: str
) -> list[Listing]:
    listings = []
    for obj in json_ld_objects:
        items = []
        if obj.get("@type") == "ItemList":
            items = obj.get("itemListElement", [])
        elif obj.get("@type") in (
            "SingleFamilyResidence", "House", "Residence", "RealEstateListing"
        ):
            items = [{"item": obj}]
        for element in items:
            item = element.get("item", element)
            if not isinstance(item, dict):
                continue
            offers = item.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price_raw = offers.get("price", 0) or item.get("price", 0)
            try:
                price = int(str(price_raw).replace(",", "").replace("$", "") or 0)
            except (ValueError, TypeError):
                price = 0
            url = item.get("url", "") or offers.get("url", "")
            address_obj = item.get("address", {})
            if isinstance(address_obj, str):
                address = address_obj
            else:
                parts = [
                    address_obj.get("streetAddress", ""),
                    address_obj.get("addressLocality", ""),
                    address_obj.get("addressRegion", ""),
                ]
                address = ", ".join(p for p in parts if p)
            beds_raw = item.get("numberOfRooms", 0) or item.get("numberOfBedrooms", 0)
            try:
                beds = int(beds_raw or 0)
            except (ValueError, TypeError):
                beds = 0
            if not url:
                continue
            lid = f"se-{url.rstrip('/').split('/')[-1]}"
            listing_url = url if url.startswith("http") else f"https://streeteasy.com{url}"
            listings.append(Listing(
                listing_id=lid,
                address=address,
                neighborhood=neighborhood,
                borough=borough,
                price=price,
                bedrooms=beds,
                garage=True,
                garage_confirmed=False,
                source="streeteasy",
                listing_url=listing_url,
            ))
    return listings


def _extract_embedded_json_state(soup: BeautifulSoup) -> dict:
    """Try to extract window.__INITIAL_STATE__ or similar embedded JSON."""
    patterns = [
        r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\});\s*</script>",
        r"window\.__data\s*=\s*(\{.+?\});\s*</script>",
        r"window\.SE_STATE\s*=\s*(\{.+?\});\s*</script>",
    ]
    for script_tag in soup.find_all("script"):
        text = script_tag.string or ""
        for pattern in patterns:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    pass
    return {}


def _listings_from_embedded_state(
    state: dict, neighborhood: str, borough: str
) -> list[Listing]:
    listings = []
    candidates = []
    for key in ("listings", "searchResults", "results", "properties"):
        val = state.get(key)
        if isinstance(val, list):
            candidates = val
            break
        if isinstance(val, dict):
            for subkey in ("listings", "results", "properties", "items"):
                sub = val.get(subkey)
                if isinstance(sub, list):
                    candidates = sub
                    break
            if candidates:
                break

    for prop in candidates:
        if not isinstance(prop, dict):
            continue
        url = (
            prop.get("url", "")
            or prop.get("listingUrl", "")
            or prop.get("listing_url", "")
        )
        if not url:
            continue
        lid = f"se-{url.rstrip('/').split('/')[-1]}"
        listing_url = url if url.startswith("http") else f"https://streeteasy.com{url}"
        price = 0
        for price_key in ("price", "listingPrice", "asking_price"):
            raw = prop.get(price_key)
            if raw:
                try:
                    price = int(str(raw).replace(",", "").replace("$", ""))
                    break
                except (ValueError, TypeError):
                    pass
        beds = 0
        for bed_key in ("bedrooms", "beds", "bedroomCount"):
            raw = prop.get(bed_key)
            if raw:
                try:
                    beds = int(raw)
                    break
                except (ValueError, TypeError):
                    pass
        address = prop.get("address", "") or prop.get("fullAddress", "")
        listings.append(Listing(
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="streeteasy",
            listing_url=listing_url,
        ))
    return listings


def _listings_from_html_cards(
    soup: BeautifulSoup, neighborhood: str, borough: str
) -> list[Listing]:
    """CSS-selector fallback. Tries multiple selector patterns."""
    cards = []
    for selector in _CARD_SELECTORS:
        cards = soup.select(selector)
        if cards:
            break
    if not cards:
        return []

    listings = []
    seen: set = set()
    for card in cards:
        link_tag = (
            card.select_one("a[href*='/building/'], a[href*='/sale/']")
            or card.select_one("a.listingCard-globalLink")
            or card.select_one("a[class*='globalLink']")
            or card.select_one("a")
        )
        if not link_tag:
            continue
        href = link_tag.get("href", "")
        lid = f"se-{href.rstrip('/').split('/')[-1].split('?')[0]}"
        if not lid or lid == "se-" or lid in seen:
            continue
        seen.add(lid)

        price = 0
        price_tag = (
            card.select_one("[data-price]")
            or card.select_one("[class*='price']")
            or card.select_one(".price")
        )
        if price_tag:
            raw = price_tag.get("data-price") or price_tag.get_text()
            price = _parse_int(raw)

        beds = 0
        beds_tag = (
            card.select_one("[class*='beds']")
            or card.select_one("[class*='bedroom']")
            or card.select_one(".beds")
        )
        if beds_tag:
            beds = _parse_int(beds_tag.get_text())

        addr_tag = (
            card.select_one("[class*='address']")
            or card.select_one("[class*='Address']")
            or card.select_one("address")
        )
        address = addr_tag.get_text(strip=True) if addr_tag else ""

        photo = None
        img = card.select_one("img")
        if img:
            photo = img.get("src") or img.get("data-src")

        listing_url = href if href.startswith("http") else f"https://streeteasy.com{href}"
        listings.append(Listing(
            listing_id=lid,
            address=address,
            neighborhood=neighborhood,
            borough=borough,
            price=price,
            bedrooms=beds,
            garage=True,
            garage_confirmed=False,
            source="streeteasy",
            listing_url=listing_url,
            photo_url=photo,
        ))
    return listings


class StreetEasySource(BaseSource):
    name = "streeteasy"

    def fetch(self, config: dict) -> list:
        listings = []
        seen: set = set()

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                try:
                    context = browser.new_context(
                        user_agent=_USER_AGENT,
                        locale="en-US",
                        timezone_id="America/New_York",
                        viewport={"width": 1280, "height": 800},
                    )
                    for neighborhood, borough, slug in _SEARCHES:
                        url = (
                            f"https://streeteasy.com/for-sale/{slug}"
                            f"?price=-{config['max_price']}"
                            f"&beds={config['min_bedrooms']}-{config['max_bedrooms']}"
                            f"&amenities=garage"
                        )
                        page = context.new_page()
                        if _STEALTH_AVAILABLE:
                            _stealth_sync(page)
                        try:
                            page.goto(url, timeout=45_000)
                            # Wait for network idle or the first known card selector
                            try:
                                page.wait_for_load_state("networkidle", timeout=30_000)
                            except PlaywrightTimeoutError:
                                pass  # still try to parse whatever loaded
                            # Also try waiting for a listing card to appear
                            for selector in _CARD_SELECTORS:
                                try:
                                    page.wait_for_selector(selector, timeout=5_000)
                                    break
                                except Exception:
                                    continue
                            html = page.content()
                        except Exception as e:
                            logger.warning(
                                "[streeteasy] page load error for %s: %s", neighborhood, e
                            )
                            continue
                        finally:
                            page.close()

                        found = _parse_html(html, neighborhood, borough)
                        logger.info(
                            "[streeteasy] %s: %d listings", neighborhood, len(found)
                        )
                        for listing in found:
                            if listing.listing_id not in seen:
                                seen.add(listing.listing_id)
                                listings.append(listing)
                finally:
                    browser.close()
        except Exception as e:
            logger.error("[streeteasy] browser error: %s", e)

        return listings
