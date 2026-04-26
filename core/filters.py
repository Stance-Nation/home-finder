from core.models import Listing

def apply_hard_filters(listings: list, config: dict) -> list:
    return [l for l in listings if _passes(l, config)]

def _passes(listing: Listing, config: dict) -> bool:
    if listing.price > config["max_price"]:
        return False
    if listing.bedrooms < config["min_bedrooms"]:
        return False
    if listing.bedrooms > config["max_bedrooms"]:
        return False
    if config["require_garage"] and not listing.garage:
        return False
    if listing.neighborhood not in config["neighborhoods"]:
        return False
    return True
