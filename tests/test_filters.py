import pytest
from core.models import Listing
from core.filters import apply_hard_filters

CONFIG = {
    "max_price": 900000,
    "min_bedrooms": 2,
    "max_bedrooms": 3,
    "require_garage": True,
    "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
}

def make_listing(**kwargs):
    defaults = dict(
        listing_id="t1", address="1 A St, Forest Hills, NY",
        neighborhood="Forest Hills", borough="Queens",
        price=750000, bedrooms=3, garage=True,
        source="zillow", listing_url="https://zillow.com/t1",
    )
    defaults.update(kwargs)
    return Listing(**defaults)

def test_passing_listing_survives():
    results = apply_hard_filters([make_listing()], CONFIG)
    assert len(results) == 1

def test_price_too_high_excluded():
    results = apply_hard_filters([make_listing(price=950000)], CONFIG)
    assert len(results) == 0

def test_wrong_neighborhood_excluded():
    results = apply_hard_filters([make_listing(neighborhood="Astoria")], CONFIG)
    assert len(results) == 0

def test_no_garage_excluded():
    results = apply_hard_filters([make_listing(garage=False)], CONFIG)
    assert len(results) == 0

def test_too_many_bedrooms_excluded():
    results = apply_hard_filters([make_listing(bedrooms=4)], CONFIG)
    assert len(results) == 0

def test_too_few_bedrooms_excluded():
    results = apply_hard_filters([make_listing(bedrooms=1)], CONFIG)
    assert len(results) == 0
