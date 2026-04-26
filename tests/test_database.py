import os
import pytest
from core.models import Listing
from core.database import Database

TEST_DB = "tests/test_seen.db"

@pytest.fixture(autouse=True)
def clean_db():
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def make_listing(listing_id="abc-1", price=700000):
    return Listing(
        listing_id=listing_id,
        address="123 Test St, Forest Hills, NY 11375",
        neighborhood="Forest Hills",
        borough="Queens",
        price=price,
        bedrooms=3,
        garage=True,
        source="zillow",
        listing_url="https://zillow.com/abc-1",
    )

def test_new_listing_is_not_seen():
    db = Database(TEST_DB)
    listing = make_listing()
    assert db.is_seen(listing) is False

def test_save_and_seen():
    db = Database(TEST_DB)
    listing = make_listing()
    db.save(listing)
    assert db.is_seen(listing) is True

def test_filter_new_returns_only_unseen():
    db = Database(TEST_DB)
    seen = make_listing("seen-1")
    new = make_listing("new-1")
    db.save(seen)
    result = db.filter_new([seen, new])
    assert len(result) == 1
    assert result[0].listing_id == "new-1"

def test_get_all_returns_saved_listings():
    db = Database(TEST_DB)
    db.save(make_listing("x-1"))
    db.save(make_listing("x-2"))
    all_listings = db.get_all()
    assert len(all_listings) == 2
