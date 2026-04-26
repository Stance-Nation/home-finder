import requests
from typing import Optional

DESTINATION = "200 5th Avenue, New York, NY 10010"
LIRR_AGENCY_NAMES = {"long island rail road", "lirr"}

def _call_api(origin: str, api_key: str, config: dict = None) -> dict:
    from datetime import datetime, timedelta
    config = config or {}
    destination = config.get("commute_destination", DESTINATION)
    departure_time_str = config.get("commute_departure_time", "08:30")
    hour, minute = map(int, departure_time_str.split(":"))
    now = datetime.now()
    days_until_monday = (7 - now.weekday()) % 7 or 7
    next_monday = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_until_monday)
    departure_ts = int(next_monday.timestamp())

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "transit",
        "transit_mode": "subway|bus",
        "departure_time": departure_ts,
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

def get_transit_minutes(address: str, api_key: str, config: dict = None) -> Optional[int]:
    try:
        data = _call_api(address, api_key, config or {})
    except Exception:
        return None
    if data.get("status") != "OK":
        return None
    for route in data.get("routes", []):
        if _uses_lirr(route):
            continue
        total_seconds = sum(
            leg.get("duration", {}).get("value", 0)
            for leg in route.get("legs", [])
        )
        if total_seconds > 0:
            return total_seconds // 60
    return None
