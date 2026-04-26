from datetime import date, timedelta
from core.models import Listing
from core.flags import apply_flip_flag, apply_commute_flag

CONFIG = {
    "flip_price_increase_threshold": 0.25,
    "flip_lookback_months": 12,
    "commute_flag_minutes": 70,
    "commute_hard_limit_minutes": 70,
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

def test_flip_flag_set_when_recent_and_large_increase():
    recent = (date.today() - timedelta(days=180)).isoformat()
    listing = make_listing(last_sale_price=500000, last_sale_date=recent, price=700000)
    result = apply_flip_flag(listing, CONFIG)
    assert result.flip_flag is True

def test_flip_flag_not_set_when_increase_below_threshold():
    recent = (date.today() - timedelta(days=180)).isoformat()
    listing = make_listing(last_sale_price=600000, last_sale_date=recent, price=700000)
    result = apply_flip_flag(listing, CONFIG)
    assert result.flip_flag is False

def test_flip_flag_not_set_when_old_sale():
    old = (date.today() - timedelta(days=400)).isoformat()
    listing = make_listing(last_sale_price=400000, last_sale_date=old, price=700000)
    result = apply_flip_flag(listing, CONFIG)
    assert result.flip_flag is False

def test_flip_flag_not_set_when_no_history():
    listing = make_listing()
    result = apply_flip_flag(listing, CONFIG)
    assert result.flip_flag is False

def test_commute_flag_set_over_limit():
    listing = make_listing(transit_minutes=80)
    result = apply_commute_flag(listing, CONFIG)
    assert result.commute_flag is True

def test_commute_flag_not_set_under_limit():
    listing = make_listing(transit_minutes=60)
    result = apply_commute_flag(listing, CONFIG)
    assert result.commute_flag is False

def test_commute_flag_not_set_when_no_transit_data():
    listing = make_listing()
    result = apply_commute_flag(listing, CONFIG)
    assert result.commute_flag is False
