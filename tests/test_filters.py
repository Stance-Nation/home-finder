import pytest
from core.models import Listing
from core.filters import apply_hard_filters

CONFIG = {
    "max_price": 900000,
    "min_bedrooms": 2,
    "max_bedrooms": 3,
    "require_garage": True,
    "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    "allowed_property_types": ["single_family", "multi_family", "townhouse", "land"],
    "excluded_property_types": ["condo", "apartment", "co_op", "mobile"],
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

# --- Property type filter tests ---

def test_condo_excluded_by_type():
    results = apply_hard_filters([make_listing(property_type="condo")], CONFIG)
    assert len(results) == 0

def test_apartment_excluded_by_type():
    results = apply_hard_filters([make_listing(property_type="apartment")], CONFIG)
    assert len(results) == 0

def test_unknown_type_passes():
    # Empty/unknown property_type should pass (benefit of the doubt)
    results = apply_hard_filters([make_listing(property_type="")], CONFIG)
    assert len(results) == 1

def test_single_family_passes():
    results = apply_hard_filters([make_listing(property_type="single_family")], CONFIG)
    assert len(results) == 1

# --- Land exemption tests ---

def test_land_passes_with_zero_bedrooms_and_no_garage():
    results = apply_hard_filters(
        [make_listing(property_type="land", bedrooms=0, garage=False)],
        CONFIG,
    )
    assert len(results) == 1

def test_land_passes_with_garage_false():
    # Land is exempt from garage requirement
    results = apply_hard_filters(
        [make_listing(property_type="land", bedrooms=0, garage=False)],
        CONFIG,
    )
    assert len(results) == 1

# --- HOA filter tests ---

def test_hoa_fee_positive_excluded():
    results = apply_hard_filters([make_listing(hoa_fee=250.0)], CONFIG)
    assert len(results) == 0

def test_hoa_fee_none_passes():
    # None = unknown, benefit of the doubt
    results = apply_hard_filters([make_listing(hoa_fee=None)], CONFIG)
    assert len(results) == 1

def test_hoa_fee_zero_passes():
    # 0.0 = confirmed no HOA, should pass
    results = apply_hard_filters([make_listing(hoa_fee=0.0)], CONFIG)
    assert len(results) == 1
