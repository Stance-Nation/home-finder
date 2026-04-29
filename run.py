#!/usr/bin/env python3
import os
import sys
import json
import re as _re
import argparse
from datetime import date


def _normalize_addr(addr: str) -> str:
    """Normalise a street address to bare street portion for deduplication.

    Takes only the part before the first comma, lowercases it, strips all
    non-alphanumeric characters and collapses whitespace so that minor
    formatting differences between sources don't prevent matching.
    """
    part = addr.split(",")[0].lower()
    part = _re.sub(r"[^a-z0-9\s]", "", part)
    return " ".join(part.split())

def load_config():
    with open("config.json") as f:
        return json.load(f)

def load_favourites() -> set:
    import json as _json
    try:
        with open("favourites.json") as f:
            return set(_json.load(f).get("favourites", []))
    except Exception:
        return set()

def load_dismissed() -> set:
    try:
        with open("dismissed.json") as f:
            return set(json.load(f).get("dismissed", []))
    except Exception:
        return set()

def main():
    parser = argparse.ArgumentParser(description="NYC Home Finder Agent")
    parser.add_argument("--report", action="store_true", help="Print current listings without fetching")
    parser.add_argument("--no-email", action="store_true", help="Skip sending email")
    args = parser.parse_args()

    config = load_config()

    if args.report:
        from core.database import Database
        from outputs.cli import format_report
        db = Database()
        all_listings = db.get_all()
        if not all_listings:
            print("No listings in database yet. Run without --report to fetch.")
            return
        print(format_report(all_listings, new_count=0))
        return

    print("[agent] Starting Home Finder Agent...")

    from sources.zillow import ZillowSource
    from sources.realtor import RealtorSource
    from sources.streeteasy import StreetEasySource
    from sources.redfin import RedfinSource
    from sources.homes import HomesSource
    from sources.findrealestate import FindRealEstateSource
    from sources.mlsli import MLSLISource
    from sources.lirealtor import LIRealtorSource
    from sources.brokerages import get_all_brokerage_sources

    sources = [
        ZillowSource(), RealtorSource(), StreetEasySource(),
        RedfinSource(), HomesSource(), FindRealEstateSource(),
        MLSLISource(), LIRealtorSource(),
        *get_all_brokerage_sources(),
    ]

    raw_listings = []
    for source in sources:
        fetched = source.safe_fetch(config)
        print(f"[{source.name}] fetched {len(fetched)} listings")
        raw_listings.extend(fetched)
    print(f"[agent] Total raw listings: {len(raw_listings)}")

    from core.filters import apply_hard_filters
    filtered = apply_hard_filters(raw_listings, config)
    print(f"[agent] After hard filters: {len(filtered)}")

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    from core.transit import get_transit_minutes
    transit_passed = []
    for listing in filtered:
        minutes = get_transit_minutes(listing.address, api_key, config)
        if minutes is None:
            print(f"[transit] No subway route: {listing.address} — excluded")
            continue
        listing.transit_minutes = minutes
        hard_limit = config.get("commute_hard_limit_minutes", 85)
        if minutes > hard_limit:
            print(f"[transit] {minutes}min exceeds {hard_limit}min limit: {listing.address} — excluded")
            continue
        transit_passed.append(listing)
    print(f"[agent] After transit filter: {len(transit_passed)}")

    from core.flags import apply_all_flags
    flagged = apply_all_flags(transit_passed, config)

    from core.scorer import score_all
    scored = score_all(flagged)

    # Within-run deduplication: keep highest-scored listing per unique address
    addr_map: dict = {}
    for listing in scored:
        key = _normalize_addr(listing.address)
        if not key:
            continue
        existing = addr_map.get(key)
        if existing is None:
            addr_map[key] = listing
        else:
            def rank(l):
                return (l.garage_confirmed, l.photo_url is not None, l.value_score or 0)
            if rank(listing) > rank(existing):
                addr_map[key] = listing
    pre_dedup = len(scored)
    scored = list(addr_map.values())
    print(f"[agent] After address dedup: {len(scored)} (dropped {pre_dedup - len(scored)} duplicates)")

    from core.database import Database
    db = Database()
    favourite_ids = load_favourites()
    dismissed_ids = load_dismissed()
    db.cleanup_expired(days=7, favourite_ids=favourite_ids)
    db.remove_dismissed(dismissed_ids)
    print(f"[agent] Expired listings cleaned up. Favourites preserved: {len(favourite_ids)}")
    scored = [l for l in scored if l.listing_id not in dismissed_ids]
    new_listings = db.filter_new(scored)
    # Cross-run deduplication: skip listings whose address already exists in DB
    existing_addresses = db.get_normalized_addresses()
    new_listings = [
        l for l in new_listings
        if _normalize_addr(l.address) not in existing_addresses
    ]
    print(f"[agent] New listings (not seen before): {len(new_listings)}")

    for listing in new_listings:
        db.save(listing)

    all_db_listings = db.get_all()
    new_ids = {l.listing_id for l in new_listings}

    from outputs.cli import format_report, save_report
    report_text = format_report(new_listings, new_count=len(new_listings))
    print(report_text)
    today = date.today().isoformat()
    save_report(new_listings, len(new_listings), f"reports/{today}.txt")

    from outputs.dashboard import save_dashboard
    save_dashboard(all_db_listings, new_ids)

    if not args.no_email and new_listings:
        from outputs.email_sender import send_email
        dashboard_url = os.environ.get("DASHBOARD_URL", "")
        try:
            send_email(new_listings, len(all_db_listings), dashboard_url, config)
        except Exception as e:
            print(f"[email] Failed to send email: {e}")

    print(f"[agent] Done. {len(new_listings)} new listings processed.")

if __name__ == "__main__":
    main()
