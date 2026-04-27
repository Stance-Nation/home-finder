#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import date

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
        transit_passed.append(listing)
    print(f"[agent] After transit filter: {len(transit_passed)}")

    from core.flags import apply_all_flags
    flagged = apply_all_flags(transit_passed, config)

    from core.scorer import score_all
    scored = score_all(flagged)

    from core.database import Database
    db = Database()
    favourite_ids = load_favourites()
    db.cleanup_expired(days=7, favourite_ids=favourite_ids)
    print(f"[agent] Expired listings cleaned up. Favourites preserved: {len(favourite_ids)}")
    new_listings = db.filter_new(scored)
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
        send_email(new_listings, len(all_db_listings), dashboard_url, config)

    print(f"[agent] Done. {len(new_listings)} new listings processed.")

if __name__ == "__main__":
    main()
