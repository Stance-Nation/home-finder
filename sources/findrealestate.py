import re
import hashlib
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class FindRealEstateSource(BaseSource):
    name = "findrealestate"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-ny"),
        ("Kew Gardens", "Queens", "kew-gardens-ny"),
        ("Richmond Hill", "Queens", "richmond-hill-ny"),
        ("Pelham Bay", "Bronx", "pelham-bay-ny"),
        ("Morris Park", "Bronx", "morris-park-ny"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = f"https://www.findrealestate.com/homes-for-sale/{slug}/?garage=1&max_price={config['max_price']}&min_beds={config['min_bedrooms']}"
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".listing-item, .property-card"):
                link = card.select_one("a[href*='/homes-for-sale/']")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"fre-{hashlib.md5(href.encode()).hexdigest()[:12]}"
                if lid in seen:
                    continue
                seen.add(lid)
                price_el = card.select_one(".price, .listing-price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                addr_el = card.select_one(".address, .listing-address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                beds_el = card.select_one(".beds, [class*='bed']")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="findrealestate",
                    listing_url=href if href.startswith("http") else f"https://www.findrealestate.com{href}",
                ))
        return listings
