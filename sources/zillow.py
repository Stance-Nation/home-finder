import os
import time
import logging
import requests
from core.models import Listing
from sources.base import BaseSource

logger = logging.getLogger(__name__)

class ZillowSource(BaseSource):
    name = "zillow"
    # RapidAPI zillow-com1 host
    _HOST = "zillow-com1.p.rapidapi.com"
    # Primary endpoint (propertyExtendedSearch accepts location string + filters)
    _PRIMARY_URL = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    # Fallback endpoint
    _FALLBACK_URL = "https://zillow-com1.p.rapidapi.com/search"

    # Each entry: (neighborhood_label, borough, location_string)
    _SEARCHES = [
        ("Forest Hills",       "Queens", "Forest Hills, Queens, NY"),
        ("Kew Gardens",        "Queens", "Kew Gardens, Queens, NY"),
        ("Kew Garden Hills",   "Queens", "Kew Garden Hills, Queens, NY"),
        ("Richmond Hill",      "Queens", "Richmond Hill, Queens, NY"),
        ("South Richmond Hill","Queens", "South Richmond Hill, Queens, NY"),
        ("Pelham Gardens",     "Bronx",  "Pelham Gardens, Bronx, NY"),
        ("Pelham Bay",         "Bronx",  "Pelham Bay, Bronx, NY"),
        ("Pelham Parkway",     "Bronx",  "Pelham Parkway, Bronx, NY"),
        ("Morris Park",        "Bronx",  "Morris Park, Bronx, NY"),
        ("Country Club",       "Bronx",  "Country Club, Bronx, NY"),
    ]

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        if not api_key:
            logger.warning("[zillow] RAPIDAPI_KEY not set — skipping")
            return []

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": self._HOST,
        }
        listings = []
        seen_zpids: set = set()

        for neighborhood, borough, location in self._SEARCHES:
            time.sleep(1)  # stay within RapidAPI free-tier rate limit
            props = self._fetch_location(headers, config, location)
            for prop in props:
                zpid = str(prop.get("zpid", ""))
                if not zpid or zpid in seen_zpids:
                    continue
                seen_zpids.add(zpid)
                # Extract property type
                raw_type = prop.get("homeType", "").lower()
                type_map = {
                    "single_family": "single_family",
                    "multi_family": "multi_family",
                    "townhouse": "townhouse",
                    "land": "land",
                    "condo": "condo",
                    "apartment": "apartment",
                    "co_op": "co_op",
                    "manufactured": "mobile",
                }
                prop_type = type_map.get(raw_type, raw_type)
                # Extract HOA fee
                hoa_fee = None
                raw_hoa = prop.get("monthlyHoaFee") or prop.get("hoaFee")
                if raw_hoa:
                    try:
                        hoa_fee = float(raw_hoa)
                    except (ValueError, TypeError):
                        pass
                # Land exemption — don't require garage for vacant lots
                is_land = prop_type == "land"
                garage_spaces = prop.get("garageSpaces", 0) or 0
                if is_land:
                    garage = False
                    garage_confirmed = False
                else:
                    garage = any(
                        "garage" in (prop.get(f) or "").lower()
                        for f in ["parkingType", "description", "garageSpaces"]
                    )
                    # garageSpaces > 0 also counts as confirmed garage
                    if garage_spaces:
                        garage = True
                    garage_confirmed = bool(garage_spaces)
                try:
                    price = int(prop.get("price", 0) or 0)
                    bedrooms = int(prop.get("bedrooms", 0) or 0)
                except (TypeError, ValueError):
                    price, bedrooms = 0, 0

                listings.append(Listing(
                    listing_id=f"zillow-{zpid}",
                    address=prop.get("address", ""),
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=bedrooms,
                    garage=garage,
                    garage_confirmed=garage_confirmed,
                    source="zillow",
                    listing_url=f"https://www.zillow.com/homedetails/{zpid}_zpid/",
                    photo_url=prop.get("imgSrc"),
                    days_on_market=prop.get("daysOnZillow"),
                    property_type=prop_type,
                    hoa_fee=hoa_fee,
                ))

        return listings

    def _fetch_location(self, headers: dict, config: dict, location: str) -> list:
        """Try primary endpoint, fall back to secondary. Returns list of property dicts."""
        # Primary: propertyExtendedSearch
        params = {
            "location": location,
            "status_type": "ForSale",
            "home_type": "Houses,Multi-family,Townhomes,Land",
            "maxPrice": config["max_price"],
            "bedsMin": config["min_bedrooms"],
            "bedsMax": config["max_bedrooms"],
        }
        try:
            resp = requests.get(
                self._PRIMARY_URL, headers=headers, params=params, timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                props = data.get("props", [])
                if props is not None:
                    return props
            elif resp.status_code == 429:
                logger.warning("[zillow] rate limited on %s — skipping fallback", location)
                return []
            elif resp.status_code not in (404, 422):
                logger.warning(
                    "[zillow] primaryEndpoint %s returned %s", location, resp.status_code
                )
        except Exception as e:
            logger.warning("[zillow] primary fetch error for %s: %s", location, e)

        # Fallback: /search endpoint
        fallback_params = {
            "location": location,
            "status_type": "ForSale",
            "home_type": "Houses,Multi-family,Townhomes,Land",
            "price_max": config["max_price"],
            "beds_min": config["min_bedrooms"],
            "beds_max": config["max_bedrooms"],
        }
        try:
            resp = requests.get(
                self._FALLBACK_URL, headers=headers, params=fallback_params, timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("props", []) or []
            logger.warning(
                "[zillow] fallbackEndpoint %s returned %s", location, resp.status_code
            )
        except Exception as e:
            logger.warning("[zillow] fallback fetch error for %s: %s", location, e)

        return []
