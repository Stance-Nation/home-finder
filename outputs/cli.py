from datetime import date
from urllib.parse import quote
from core.models import Listing

def _maps_url(address: str) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote(address)}"
        "&destination=200+5th+Ave%2C+New+York%2C+NY+10010"
        "&travelmode=transit"
    )

def _stars(score: float) -> str:
    if score is None:
        return "☆☆☆☆☆"
    filled = round(score * 5)
    return "★" * filled + "☆" * (5 - filled)

def format_listing(listing: Listing) -> str:
    flags = []
    if listing.flip_flag:
        flags.append("⚠ Likely Flip")
    if listing.commute_flag:
        flags.append("⚠ Long Commute")
    if listing.property_type == "land":
        pass  # No garage warning for vacant lots
    elif not listing.garage_confirmed:
        flags.append("⚠ Garage unconfirmed — verify before viewing")
    flag_str = "  " + " | ".join(flags) if flags else ""
    transit = f"{listing.transit_minutes}min" if listing.transit_minutes else "N/A"
    score = f"{_stars(listing.value_score)} ({listing.value_score:.2f})" if listing.value_score is not None else "Unscored"
    type_labels = {
        "single_family": "Detached",
        "multi_family": "Multi-Family",
        "townhouse": "Townhouse",
        "land": "Vacant Lot",
    }
    type_str = ""
    if listing.property_type:
        label = type_labels.get(listing.property_type, listing.property_type.replace("_", " ").title())
        type_str = f"  Type: {label}\n"
    return (
        f"\n[{score}] {listing.address}\n"
        f"{type_str}"
        f"  {listing.bedrooms} bed · ${listing.price:,} · Garage ✓ · Transit: {transit}\n"
        f"  Source: {listing.source}{flag_str}\n"
        f"  {listing.listing_url}\n"
        f"  🚇 Transit map: {_maps_url(listing.address)}"
    )

def format_report(listings: list, new_count: int) -> str:
    today = date.today().strftime("%B %d, %Y")
    header = (
        f"\nHOME FINDER — Queens & Bronx\n"
        f"{'=' * 50}\n"
        f"Report date: {today} | Total matches: {len(listings)} | New today: {new_count}\n"
        f"{'=' * 50}"
    )
    if not listings:
        return header + "\n\nNo new listings today.\n"
    body = "\n".join(format_listing(l) for l in listings)
    footer = f"\n{'─' * 50}\n"
    return header + "\n" + body + footer

def save_report(listings: list, new_count: int, path: str):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(format_report(listings, new_count))
