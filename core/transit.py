import requests
from typing import Optional

DESTINATION = "200 5th Avenue, New York, NY 10010"
LIRR_AGENCY_NAMES = {"long island rail road", "lirr"}

def _call_api(origin: str, api_key: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": DESTINATION,
        "mode": "transit",
        "transit_mode": "subway|bus",
        "departure_time": "next_monday_0830",
        "alternatives": "true",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def _uses_lirr(route: dict) -> bool:
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            if step.get("travel_mode") != "TRANSIT":
                continue
            agencies = step.get("transit_details", {}).get("line", {}).get("agencies", [])
            for agency in agencies:
                if agency.get("name", "").lower() in LIRR_AGENCY_NAMES:
                    return True
    return False

def get_transit_minutes(address: str, api_key: str) -> Optional[int]:
    try:
        data = _call_api(address, api_key)
    except Exception:
        return None
    if data.get("status") != "OK":
        return None
    for route in data.get("routes", []):
        if _uses_lirr(route):
            continue
        for leg in route.get("legs", []):
            seconds = leg.get("duration", {}).get("value")
            if seconds:
                return seconds // 60
    return None
