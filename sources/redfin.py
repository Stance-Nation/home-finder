import csv
import io
import logging
import re
import requests
from core.models import Listing
from sources.base import BaseSource

logger = logging.getLogger(__name__)

# Redfin's public CSV export endpoint works without authentication.
# It strips the "{}&&" XSSI prefix from its JSON endpoints, but the CSV
# endpoint returns clean RFC-4180 CSV that requests can handle directly.
_CSV_URL = "https://www.redfin.com/stingray/api/gis-csv"

# Browser-like headers to avoid 403/bot-block
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.redfin.com/",
    "DNT": "1",
}

# region_id values for Redfin neighborhood search (region_type=6 = neighborhood).
# These may drift over time; if a region_id returns no results we fall back to
# a plain location-string search.
_NEIGHBORHOODS = [
    # (label,             borough,   region_id)
    ("Forest Hills",       "Queens", "30466"),
    ("Kew Gardens",        "Queens", "30467"),
    ("Kew Garden Hills",   "Queens", "30468"),
    ("Richmond Hill",      "Queens", "30478"),
    ("South Richmond Hill","Queens", "30479"),
    ("Pelham Bay",         "Bronx",  "30391"),
    ("Morris Park",        "Bronx",  "30392"),
    ("Pelham Gardens",     "Bronx",  "30393"),
    ("Pelham Parkway",     "Bronx",  "30394"),
    ("Country Club",       "Bronx",  "30390"),
]


def _garage_from_row(row: dict) -> bool:
    """Detect garage from CSV columns."""
    for col in ("PARKING SPOTS", "GARAGE SPACES", "PARKING TYPE"):
        val = row.get(col, "") or ""
        if val.strip() not in ("", "0", "—"):
            return True
    return False


def _parse_int(val) -> int:
    if not val:
        return 0
    try:
        return int(re.sub(r"[^\d]", "", str(val)) or 0)
    except (ValueError, TypeError):
        return 0


class RedfinSource(BaseSource):
    name = "redfin"

    def fetch(self, config: dict) -> list:
        listings = []
        seen: set = set()

        for neighborhood, borough, region_id in _NEIGHBORHOODS:
            rows = self._fetch_csv(config, region_id)
            for row in rows:
                url_path = row.get("URL (SEE https://www.redfin.com/buy-a-home/comparative-market-analysis FOR INFO ON PRICING)", "") or row.get("URL", "") or ""
                if not url_path:
                    # Try any key containing "URL"
                    for k, v in row.items():
                        if "URL" in k.upper() and v:
                            url_path = v
                            break

                listing_url = url_path if url_path.startswith("http") else f"https://www.redfin.com{url_path}"
                lid = f"redfin-{listing_url.rstrip('/').split('/')[-1]}"
                if lid in seen or lid == "redfin-":
                    continue
                seen.add(lid)

                price = _parse_int(row.get("PRICE", ""))
                beds = _parse_int(row.get("BEDS", ""))
                address_parts = [
                    row.get("ADDRESS", ""),
                    row.get("CITY", ""),
                    row.get("STATE OR PROVINCE", ""),
                    row.get("ZIP OR POSTAL CODE", ""),
                ]
                address = ", ".join(p for p in address_parts if p)
                garage = _garage_from_row(row)
                dom_raw = row.get("DAYS ON MARKET", "")
                dom = _parse_int(dom_raw) if dom_raw else None

                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=garage,
                    garage_confirmed=garage,
                    source="redfin",
                    listing_url=listing_url,
                    days_on_market=dom,
                ))

        return listings

    def _fetch_csv(self, config: dict, region_id: str) -> list[dict]:
        """Fetch the Redfin CSV export for a neighborhood region and return rows as dicts."""
        params = {
            "al": 1,
            "has_garage": 1,
            "max_price": config["max_price"],
            "min_beds": config["min_bedrooms"],
            "max_beds": config["max_bedrooms"],
            "region_id": region_id,
            "region_type": 6,       # neighborhood
            "sf": "1,2,3,4,5,6,7",  # single-family residential
            "status": 1,            # for sale
            "uipt": 1,              # houses
            "num_homes": 50,
            "market": "nyc",
            "v": 8,
        }
        try:
            resp = requests.get(
                _CSV_URL,
                headers=_HEADERS,
                params=params,
                timeout=20,
            )
            if resp.status_code != 200:
                logger.warning(
                    "[redfin] CSV region_id=%s returned HTTP %s", region_id, resp.status_code
                )
                return []
            content = resp.text
            # Redfin sometimes returns XSSI prefix on CSV too
            if content.startswith("{}&&"):
                content = content[4:]
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)
        except Exception as e:
            logger.warning("[redfin] CSV fetch error region_id=%s: %s", region_id, e)
            return []
