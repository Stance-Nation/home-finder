import re
import hashlib
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class LIRealtorSource(BaseSource):
    name = "lirealtor"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "Forest+Hills"),
        ("Kew Gardens", "Queens", "Kew+Gardens"),
        ("Richmond Hill", "Queens", "Richmond+Hill"),
        ("South Richmond Hill", "Queens", "South+Richmond+Hill"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, search_term in self._SEARCHES:
            url = (
                f"https://www.lirealtor.com/listing/search?"
                f"location={search_term}&type=residential&"
                f"max_price={config['max_price']}&"
                f"min_beds={config['min_bedrooms']}&max_beds={config['max_bedrooms']}&"
                f"garage=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".property-card, .listing-card"):
                link = card.select_one("a")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"lirealtor-{hashlib.md5(href.encode()).hexdigest()[:12]}"
                if lid in seen or not href:
                    continue
                seen.add(lid)
                price_el = card.select_one(".price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one(".beds")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds_match = re.search(r"\d+", beds_text)
                beds = int(beds_match.group()) if beds_match else 0
                addr_el = card.select_one(".address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                full_url = href if href.startswith("http") else f"https://www.lirealtor.com{href}"
                listings.append(Listing(
                    listing_id=lid, address=address, neighborhood=neighborhood, borough=borough,
                    price=price, bedrooms=beds, garage=True, source="LIRealtor", listing_url=full_url,
                ))
        return listings
