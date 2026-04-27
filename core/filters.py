from core.models import Listing

def apply_hard_filters(listings: list, config: dict) -> list:
    passed = []
    fail_neighborhood = 0
    fail_price = 0
    fail_beds = 0
    fail_garage = 0

    for l in listings:
        if l.neighborhood not in config["neighborhoods"]:
            fail_neighborhood += 1
        elif l.price > config["max_price"]:
            fail_price += 1
        elif l.bedrooms < config["min_bedrooms"] or l.bedrooms > config["max_bedrooms"]:
            fail_beds += 1
        elif config["require_garage"] and not l.garage:
            fail_garage += 1
        else:
            passed.append(l)

    print(f"[filters] neighborhood={fail_neighborhood} price={fail_price} beds={fail_beds} garage={fail_garage} passed={len(passed)}")
    return passed

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
