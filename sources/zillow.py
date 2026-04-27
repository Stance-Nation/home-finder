import os
import requests
from core.models import Listing
from sources.base import BaseSource

class ZillowSource(BaseSource):
    name = "zillow"
    _BASE_URL = "https://zillow-com1.p.rapidapi.com/propertySearch"
    _HEADERS = {
        "X-RapidAPI-Key": "",
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
    }

    _NEIGHBORHOOD_ZIPCODES = {
        "Forest Hills": ["11375"],
        "Kew Gardens": ["11415"],
        "Kew Garden Hills": ["11367"],
        "Richmond Hill": ["11418"],
        "South Richmond Hill": ["11419"],
        "Pelham Gardens": ["10469"],
        "Pelham Bay": ["10461"],
        "Pelham Parkway": ["10461", "10462"],
        "Morris Park": ["10462"],
        "Country Club": ["10464"],
    }

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        headers = {**self._HEADERS, "X-RapidAPI-Key": api_key}
        listings = []
        seen_zpids = set()

        for neighborhood, zipcodes in self._NEIGHBORHOOD_ZIPCODES.items():
            for zipcode in zipcodes:
                params = {
                    "zipcode": zipcode,
                    "status": "forSale",
                    "sortSelection": "days",
                    "listing_type": "by_agent",
                    "doz": "any",
                }
                resp = requests.get(self._BASE_URL, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                for prop in data.get("props", []):
                    zpid = str(prop.get("zpid", ""))
                    if not zpid or zpid in seen_zpids:
                        continue
                    seen_zpids.add(zpid)
                    garage = any(
                        "garage" in (prop.get(f) or "").lower()
                        for f in ["parkingType", "description"]
                    )
                    listings.append(Listing(
                        listing_id=f"zillow-{zpid}",
                        address=prop.get("address", ""),
                        neighborhood=neighborhood,
                        borough="Queens" if zipcode[:3] in ["113", "114"] else "Bronx",
                        price=int(prop.get("price", 0)),
                        bedrooms=int(prop.get("bedrooms", 0)),
                        garage=garage,
                        source="zillow",
                        listing_url=f"https://www.zillow.com/homedetails/{zpid}_zpid/",
                        photo_url=prop.get("imgSrc"),
                        days_on_market=prop.get("daysOnZillow"),
                    ))
        return listings
