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

    # (label, borough, postal_code)
    _NEIGHBORHOOD_ZIPS = [
        ("Forest Hills",        "Queens", "11375"),
        ("Kew Gardens",         "Queens", "11415"),
        ("Kew Garden Hills",    "Queens", "11367"),
        ("Richmond Hill",       "Queens", "11418"),
        ("South Richmond Hill", "Queens", "11419"),
        ("Pelham Gardens",      "Bronx",  "10469"),
        ("Pelham Bay",          "Bronx",  "10461"),
        ("Pelham Parkway",      "Bronx",  "10462"),
        ("Morris Park",         "Bronx",  "10462"),
        ("Country Club",        "Bronx",  "10464"),
    ]

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        headers = {**self._HEADERS, "X-RapidAPI-Key": api_key}
        listings = []
        seen_ids = set()

        for neighborhood, borough, postal_code in self._NEIGHBORHOOD_ZIPS:
            payload = {
                "limit": 50,
                "offset": 0,
                "filters": {
                    "list_price": {"max": config["max_price"]},
                    "beds": {"min": config["min_bedrooms"], "max": config["max_bedrooms"]},
                    "prop_type": ["single_family", "multi_family", "townhomes", "land"],
                },
                "postal_code": postal_code,
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
                prop_str = str(prop).lower()
                garage_spaces = int(desc.get("garage") or 0)
                garage_confirmed = garage_spaces > 0 or "garage" in prop_str
                # Extract property type
                prop_type = (desc.get("type") or "").lower().replace(" ", "_")
                # Normalize "townhomes" -> "townhouse" to match our canonical names
                if prop_type == "townhomes":
                    prop_type = "townhouse"
                # Land exemption — don't require garage for vacant lots
                is_land = prop_type == "land"
                garage = True if not is_land else False
                garage_confirmed = garage_confirmed if not is_land else False
                # Extract HOA fee
                hoa_fee = None
                hoa = prop.get("hoa") or {}
                if hoa:
                    monthly = hoa.get("fee") or hoa.get("monthly_fee") or 0
                    if monthly:
                        hoa_fee = float(monthly)
                location = prop.get("location", {}).get("address", {})
                price = (prop.get("list_price") or 0)
                listings.append(Listing(
                    listing_id=f"realtor-{prop_id}",
                    address=f"{location.get('line','')}, {location.get('city','')}, NY",
                    neighborhood=neighborhood,
                    borough=borough,
                    price=int(price),
                    bedrooms=int(desc.get("beds") or 0),
                    garage=garage,
                    garage_confirmed=garage_confirmed,
                    source="realtor",
                    listing_url=f"https://www.realtor.com/realestateandhomes-detail/{prop_id}",
                    photo_url=(prop.get("primary_photo") or {}).get("href"),
                    days_on_market=prop.get("list_date_delta"),
                    property_type=prop_type,
                    hoa_fee=hoa_fee,
                ))
        return listings
