import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class MLSLISource(BaseSource):
    name = "mlsli"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "Forest+Hills"),
        ("Kew Gardens", "Queens", "Kew+Gardens"),
        ("Kew Garden Hills", "Queens", "Kew+Garden+Hills"),
        ("Richmond Hill", "Queens", "Richmond+Hill"),
        ("South Richmond Hill", "Queens", "South+Richmond+Hill"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, search_term in self._SEARCHES:
            url = (
                f"https://www.mlsli.com/listing/search/results?"
                f"Address={search_term}&PropertyType=Single+Family&"
                f"PriceMax={config['max_price']}&"
                f"BedsMin={config['min_bedrooms']}&BedsMax={config['max_bedrooms']}&"
                f"GarageSpacesMin=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".listing-item, .property-listing"):
                link = card.select_one("a[href*='/listing/']")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"mlsli-{href.split('/')[-1]}"
                if lid in seen:
                    continue
                seen.add(lid)
                price_el = card.select_one(".listing-price, .price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one(".listing-beds, .beds")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds_match = re.search(r"\d+", beds_text)
                beds = int(beds_match.group()) if beds_match else 0
                addr_el = card.select_one(".listing-address, .address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                full_url = href if href.startswith("http") else f"https://www.mlsli.com{href}"
                listings.append(Listing(
                    listing_id=lid, address=address, neighborhood=neighborhood, borough=borough,
                    price=price, bedrooms=beds, garage=True, source="MLSLI", listing_url=full_url,
                ))
        return listings
