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


# --- Address normalisation / deduplication tests ---

def test_get_normalized_addresses_empty_db():
    db = Database(TEST_DB)
    result = db.get_normalized_addresses()
    assert result == set()

def test_get_normalized_addresses_returns_street_part():
    db = Database(TEST_DB)
    db.save(make_listing("addr-1"))  # address = "123 Test St, Forest Hills, NY 11375"
    result = db.get_normalized_addresses()
    assert "123 test st" in result

def test_get_normalized_addresses_strips_punctuation():
    """Addresses with different punctuation should normalise the same."""
    from core.models import Listing
    listing = Listing(
        listing_id="addr-2",
        address="456 Oak Ave., Queens, NY",
        neighborhood="Kew Gardens",
        borough="Queens",
        price=700000,
        bedrooms=3,
        garage=True,
        source="zillow",
        listing_url="https://zillow.com/addr-2",
    )
    db = Database(TEST_DB)
    db.save(listing)
    result = db.get_normalized_addresses()
    assert "456 oak ave" in result

def test_normalize_addr_function():
    """Test the module-level _normalize_addr helper in run.py."""
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from run import _normalize_addr
    assert _normalize_addr("123 Main St, Forest Hills, NY 11375") == "123 main st"
    assert _normalize_addr("456 Oak Ave., Queens, NY") == "456 oak ave"
    assert _normalize_addr("789 ELM BLVD, Bronx, NY") == "789 elm blvd"
    assert _normalize_addr("") == ""

def test_normalize_addr_deduplicates_same_address_different_format():
    from run import _normalize_addr
    addr1 = "123 Main St, Forest Hills, NY 11375"
    addr2 = "123 Main St., Forest Hills, NY"
    assert _normalize_addr(addr1) == _normalize_addr(addr2)
