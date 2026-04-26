import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class StreetEasySource(BaseSource):
    name = "streeteasy"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-queens"),
        ("Kew Gardens", "Queens", "kew-gardens-queens"),
        ("Kew Garden Hills", "Queens", "kew-garden-hills-queens"),
        ("Richmond Hill", "Queens", "richmond-hill-queens"),
        ("South Richmond Hill", "Queens", "south-richmond-hill-queens"),
        ("Pelham Gardens", "Bronx", "pelham-gardens-bronx"),
        ("Pelham Bay", "Bronx", "pelham-bay-bronx"),
        ("Pelham Parkway", "Bronx", "pelham-parkway-bronx"),
        ("Morris Park", "Bronx", "morris-park-bronx"),
        ("Country Club", "Bronx", "country-club-bronx"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = (
                f"https://streeteasy.com/for-sale/{slug}"
                f"?price=-{config['max_price']}"
                f"&beds={config['min_bedrooms']}-{config['max_bedrooms']}"
                f"&amenities=garage"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("article.ListingCard"):
                link_tag = card.select_one("a.listingCard-globalLink")
                if not link_tag:
                    continue
                href = link_tag.get("href", "")
                listing_id = f"se-{href.split('/')[-1].split('?')[0]}"
                if listing_id in seen:
                    continue
                seen.add(listing_id)
                price_tag = card.select_one("[data-price]")
                price = int(price_tag["data-price"]) if price_tag else 0
                beds_tag = card.select_one(".listingDetailDefinitions-item--beds")
                beds_text = beds_tag.get_text() if beds_tag else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                addr_tag = card.select_one(".listingCard-addressLabel")
                address = addr_tag.get_text(strip=True) if addr_tag else ""
                photo_tag = card.select_one("img.listingCard-image")
                photo = photo_tag.get("src") if photo_tag else None
                listings.append(Listing(
                    listing_id=listing_id,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="streeteasy",
                    listing_url=f"https://streeteasy.com{href}",
                    photo_url=photo,
                ))
        return listings
