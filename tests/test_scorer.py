from core.models import Listing
from core.scorer import score_listing, score_all, NEIGHBORHOOD_SCORES

def make_listing(**kwargs):
    defaults = dict(
        listing_id="t1", address="1 A St, Forest Hills, NY",
        neighborhood="Forest Hills", borough="Queens",
        price=750000, bedrooms=3, garage=True,
        source="zillow", listing_url="https://zillow.com/t1",
        transit_minutes=50,
    )
    defaults.update(kwargs)
    return Listing(**defaults)

def test_forest_hills_scores_higher_than_south_richmond_hill():
    fh = make_listing(neighborhood="Forest Hills", price=800000)
    srh = make_listing(neighborhood="South Richmond Hill", price=800000)
    assert score_listing(fh).value_score > score_listing(srh).value_score

def test_shorter_transit_scores_higher():
    fast = make_listing(transit_minutes=30)
    slow = make_listing(transit_minutes=65)
    assert score_listing(fast).value_score > score_listing(slow).value_score

def test_lower_price_scores_higher():
    cheap = make_listing(price=500000)
    expensive = make_listing(price=850000)
    assert score_listing(cheap).value_score > score_listing(expensive).value_score

def test_fixer_upper_keywords_boost_score():
    plain = make_listing()
    fixer = make_listing(condition_keywords=["as-is", "needs tlc"])
    assert score_listing(fixer).value_score > score_listing(plain).value_score

def test_score_all_sorts_descending():
    listings = [make_listing(price=850000), make_listing(price=600000), make_listing(price=700000)]
    scored = score_all(listings)
    scores = [l.value_score for l in scored]
    assert scores == sorted(scores, reverse=True)

def test_all_neighborhoods_have_score():
    neighborhoods = [
        "Forest Hills", "Kew Gardens", "Kew Garden Hills",
        "Richmond Hill", "South Richmond Hill",
        "Pelham Gardens", "Pelham Bay", "Pelham Parkway",
        "Morris Park", "Country Club"
    ]
    for n in neighborhoods:
        assert n in NEIGHBORHOOD_SCORES
