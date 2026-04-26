import json
import requests
from core.models import Listing
from sources.base import BaseSource

class RedfinSource(BaseSource):
    name = "redfin"
    _REGION_IDS = {
        "Forest Hills": ("Queens", "30466"),
        "Kew Gardens": ("Queens", "30467"),
        "Kew Garden Hills": ("Queens", "30468"),
        "Richmond Hill": ("Queens", "30478"),
        "South Richmond Hill": ("Queens", "30479"),
        "Pelham Bay": ("Bronx", "30391"),
        "Morris Park": ("Bronx", "30392"),
    }
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, (borough, region_id) in self._REGION_IDS.items():
            url = (
                f"https://www.redfin.com/stingray/api/gis?al=1&has_garage=1"
                f"&max_price={config['max_price']}"
                f"&min_beds={config['min_bedrooms']}&max_beds={config['max_bedrooms']}"
                f"&region_id={region_id}&region_type=neighborhood&num_homes=50"
                f"&sf=1,2,3,4,5,6,7&status=1&uipt=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            text = resp.text
            if text.startswith("{}&&"):
                text = text[4:]
            try:
                data = json.loads(text)
            except Exception:
                continue
            for home in (data.get("payload", {}).get("homes") or []):
                home_id = str(home.get("id", ""))
                if not home_id or home_id in seen:
                    continue
                seen.add(home_id)
                listings.append(Listing(
                    listing_id=f"redfin-{home_id}",
                    address=home.get("streetLine", {}).get("value", ""),
                    neighborhood=neighborhood,
                    borough=borough,
                    price=int(home.get("price", {}).get("value", 0)),
                    bedrooms=int(home.get("beds", 0)),
                    garage=True,
                    source="redfin",
                    listing_url=f"https://www.redfin.com{home.get('url','')}",
                    photo_url=home.get("smallPhotoUrl"),
                    days_on_market=home.get("dom", {}).get("value"),
                ))
        return listings
