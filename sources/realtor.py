import os
import requests
from core.models import Listing
from sources.base import BaseSource

class RealtorSource(BaseSource):
    name = "realtor"
    _BASE_URL = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
    _HEADERS = {
        "X-RapidAPI-Key": "",
        "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com",
    }

    _NEIGHBORHOOD_CITIES = [
        ("Forest Hills", "Queens", "NY"),
        ("Kew Gardens", "Queens", "NY"),
        ("Richmond Hill", "Queens", "NY"),
        ("South Richmond Hill", "Queens", "NY"),
        ("Pelham Bay", "Bronx", "NY"),
        ("Morris Park", "Bronx", "NY"),
        ("Country Club", "Bronx", "NY"),
        ("Kew Garden Hills", "Queens", "NY"),
        ("Pelham Gardens", "Bronx", "NY"),
        ("Pelham Parkway", "Bronx", "NY"),
    ]

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        headers = {**self._HEADERS, "X-RapidAPI-Key": api_key}
        listings = []
        seen_ids = set()

        for neighborhood, borough, state in self._NEIGHBORHOOD_CITIES:
            payload = {
                "limit": 50,
                "offset": 0,
                "filters": {
                    "list_price": {"max": config["max_price"]},
                    "beds": {"min": config["min_bedrooms"], "max": config["max_bedrooms"]},
                    "prop_type": ["single_family"],
                },
                "city": neighborhood,
                "state_code": state,
                "sort": {"direction": "desc", "field": "list_date"},
            }
            resp = requests.post(self._BASE_URL, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for prop in (data.get("data", {}).get("home_search", {}).get("results") or []):
                prop_id = prop.get("property_id", "")
                if not prop_id or prop_id in seen_ids:
                    continue
                seen_ids.add(prop_id)
                desc = (prop.get("description") or {})
                garage = bool(desc.get("garage")) or "garage" in str(desc).lower()
                location = prop.get("location", {}).get("address", {})
                price = (prop.get("list_price") or 0)
                listings.append(Listing(
                    listing_id=f"realtor-{prop_id}",
                    address=f"{location.get('line','')}, {location.get('city','')}, {state}",
                    neighborhood=neighborhood,
                    borough=borough,
                    price=int(price),
                    bedrooms=int(desc.get("beds") or 0),
                    garage=garage,
                    source="realtor",
                    listing_url=f"https://www.realtor.com/realestateandhomes-detail/{prop_id}",
                    photo_url=(prop.get("primary_photo") or {}).get("href"),
                    days_on_market=prop.get("list_date_delta"),
                ))
        return listings
