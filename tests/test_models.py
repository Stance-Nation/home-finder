from core.models import Listing

def test_listing_creation():
    listing = Listing(
        listing_id="test-123",
        address="123 Main St, Forest Hills, NY 11375",
        neighborhood="Forest Hills",
        borough="Queens",
        price=750000,
        bedrooms=3,
        garage=True,
        source="zillow",
        listing_url="https://zillow.com/homes/test-123",
    )
    assert listing.listing_id == "test-123"
    assert listing.price == 750000
    assert listing.garage is True
    assert listing.flip_flag is False
    assert listing.commute_flag is False
    assert listing.transit_minutes is None
    assert listing.value_score is None

def test_listing_to_dict():
    listing = Listing(
        listing_id="test-456",
        address="456 Oak Ave, Pelham Bay, NY 10461",
        neighborhood="Pelham Bay",
        borough="Bronx",
        price=600000,
        bedrooms=2,
        garage=True,
        source="streeteasy",
        listing_url="https://streeteasy.com/test-456",
    )
    d = listing.to_dict()
    assert d["listing_id"] == "test-456"
    assert d["garage"] == 1
