from core.models import Listing

def apply_hard_filters(listings: list, config: dict) -> list:
    passed = []
    fail_neighborhood = 0
    fail_price = 0
    fail_type = 0
    fail_hoa = 0
    fail_beds = 0
    fail_garage = 0

    for l in listings:
        if l.neighborhood not in config["neighborhoods"]:
            fail_neighborhood += 1
        elif l.price > config["max_price"]:
            fail_price += 1
        # Exclude known bad property types
        elif l.property_type and l.property_type in config.get("excluded_property_types", []):
            fail_type += 1
        # Exclude if known type is not in the allowed list (unknown type = let it through)
        elif l.property_type and config.get("allowed_property_types") and l.property_type not in config["allowed_property_types"]:
            fail_type += 1
        elif l.hoa_fee is not None and l.hoa_fee > 0:
            fail_hoa += 1
        elif l.property_type != "land" and (l.bedrooms < config["min_bedrooms"] or l.bedrooms > config["max_bedrooms"]):
            fail_beds += 1
        elif l.garage_confirmed and not l.garage and l.property_type != "land":
            fail_garage += 1
        else:
            passed.append(l)

    print(f"[filters] neighborhood={fail_neighborhood} price={fail_price} type={fail_type} hoa={fail_hoa} beds={fail_beds} garage={fail_garage} passed={len(passed)}")
    return passed

def _passes(listing: Listing, config: dict) -> bool:
    if listing.neighborhood not in config["neighborhoods"]:
        return False
    if listing.price > config["max_price"]:
        return False
    # Exclude known bad property types
    if listing.property_type and listing.property_type in config.get("excluded_property_types", []):
        return False
    # Exclude if known type is not in the allowed list (unknown type = let it through)
    if listing.property_type and config.get("allowed_property_types") and listing.property_type not in config["allowed_property_types"]:
        return False
    if listing.hoa_fee is not None and listing.hoa_fee > 0:
        return False
    if listing.property_type != "land" and (listing.bedrooms < config["min_bedrooms"] or listing.bedrooms > config["max_bedrooms"]):
        return False
    if listing.garage_confirmed and not listing.garage and listing.property_type != "land":
        return False
    return True
