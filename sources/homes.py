import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class HomesSource(BaseSource):
    name = "homes"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-queens-ny"),
        ("Kew Gardens", "Queens", "kew-gardens-queens-ny"),
        ("Richmond Hill", "Queens", "richmond-hill-queens-ny"),
        ("Pelham Bay", "Bronx", "pelham-bay-bronx-ny"),
        ("Morris Park", "Bronx", "morris-park-bronx-ny"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = f"https://www.homes.com/for-sale/{slug}/p1/?garage=true&price=0-{config['max_price']}&beds={config['min_bedrooms']}-{config['max_bedrooms']}"
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("[data-testid='listing-card']"):
                link = card.select_one("a")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"homes-{href.split('/')[-2] if href else ''}"
                if lid in seen or lid == "homes-":
                    continue
                seen.add(lid)
                price_el = card.select_one("[data-testid='price']")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one("[data-testid='beds']")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                addr_el = card.select_one("[data-testid='address']")
                address = addr_el.get_text(strip=True) if addr_el else ""
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="homes",
                    listing_url=f"https://www.homes.com{href}",
                ))
        return listings
