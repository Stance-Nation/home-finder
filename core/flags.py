from datetime import date, timedelta
from core.models import Listing

def apply_flip_flag(listing: Listing, config: dict) -> Listing:
    if not listing.last_sale_price or not listing.last_sale_date:
        return listing
    threshold = config["flip_price_increase_threshold"]
    lookback_days = config["flip_lookback_months"] * 30
    try:
        sale_date = date.fromisoformat(listing.last_sale_date)
    except ValueError:
        return listing
    cutoff = date.today() - timedelta(days=lookback_days)
    if sale_date < cutoff:
        return listing
    increase = (listing.price - listing.last_sale_price) / listing.last_sale_price
    if increase >= threshold:
        listing.flip_flag = True
    return listing

def apply_commute_flag(listing: Listing, config: dict) -> Listing:
    if listing.transit_minutes is None:
        return listing
    if listing.transit_minutes > config["commute_flag_minutes"]:
        listing.commute_flag = True
    return listing

def apply_all_flags(listings: list, config: dict) -> list:
    result = []
    for listing in listings:
        listing = apply_flip_flag(listing, config)
        listing = apply_commute_flag(listing, config)
        result.append(listing)
    return result
