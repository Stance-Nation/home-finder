from core.models import Listing
from outputs.cli import format_report

def make_listing(**kwargs):
    defaults = dict(
        listing_id="t1", address="123 Main St, Forest Hills, NY",
        neighborhood="Forest Hills", borough="Queens",
        price=750000, bedrooms=3, garage=True,
        source="zillow", listing_url="https://zillow.com/t1",
        transit_minutes=52, value_score=0.72,
    )
    defaults.update(kwargs)
    return Listing(**defaults)

def test_format_report_contains_address():
    report = format_report([make_listing()], new_count=1)
    assert "123 Main St" in report

def test_format_report_contains_price():
    report = format_report([make_listing()], new_count=1)
    assert "$750,000" in report

def test_format_report_shows_flip_flag():
    report = format_report([make_listing(flip_flag=True)], new_count=1)
    assert "Likely Flip" in report

def test_format_report_shows_commute_flag():
    report = format_report([make_listing(commute_flag=True, transit_minutes=75)], new_count=1)
    assert "Long Commute" in report

def test_format_report_empty_list():
    report = format_report([], new_count=0)
    assert "No new listings" in report
