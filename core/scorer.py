from core.models import Listing

NEIGHBORHOOD_SCORES = {
    "Forest Hills": 9,
    "Kew Gardens": 8,
    "Kew Garden Hills": 7,
    "Richmond Hill": 6,
    "South Richmond Hill": 5,
    "Pelham Gardens": 8,
    "Pelham Bay": 7,
    "Pelham Parkway": 7,
    "Morris Park": 7,
    "Country Club": 8,
}

CONDITION_KEYWORDS = {"as-is", "needs tlc", "fixer", "fixer-upper", "estate sale", "handyman"}

_MAX_PRICE = 900000
_MAX_TRANSIT = 70
_WEIGHTS = {"neighborhood": 0.40, "transit": 0.30, "price": 0.20, "dom": 0.05, "condition": 0.05}

def score_listing(listing: Listing) -> Listing:
    neighborhood_score = NEIGHBORHOOD_SCORES.get(listing.neighborhood, 5) / 10.0

    if listing.transit_minutes is not None:
        transit_score = max(0.0, 1.0 - (listing.transit_minutes / _MAX_TRANSIT))
    else:
        transit_score = 0.5

    price_score = max(0.0, 1.0 - (listing.price / _MAX_PRICE))

    dom = listing.days_on_market or 0
    dom_score = min(1.0, dom / 60.0)

    kw_set = {k.lower() for k in listing.condition_keywords}
    condition_score = 1.0 if kw_set & CONDITION_KEYWORDS else 0.0

    listing.value_score = round(
        _WEIGHTS["neighborhood"] * neighborhood_score
        + _WEIGHTS["transit"] * transit_score
        + _WEIGHTS["price"] * price_score
        + _WEIGHTS["dom"] * dom_score
        + _WEIGHTS["condition"] * condition_score,
        4
    )
    return listing

def score_all(listings: list) -> list:
    scored = [score_listing(l) for l in listings]
    return sorted(scored, key=lambda l: l.value_score or 0, reverse=True)
