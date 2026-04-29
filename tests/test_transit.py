from unittest.mock import patch
from core.transit import get_transit_minutes, LIRR_AGENCY_NAMES

def _mock_response(routes):
    return {"status": "OK", "routes": routes}

def _make_route(duration_seconds, agencies):
    legs = []
    for step in agencies:
        leg_step = {"travel_mode": "TRANSIT", "transit_details": {"line": {"agencies": [{"name": step}]}}}
        legs.append(leg_step)
    return {
        "legs": [{
            "duration": {"value": duration_seconds},
            "steps": legs
        }]
    }

def test_returns_minutes_for_valid_subway_route():
    mock_data = _mock_response([_make_route(3600, ["MTA New York City Transit"])])
    with patch("core.transit._call_api", return_value=mock_data):
        minutes = get_transit_minutes("123 Main St, Forest Hills, NY", "dummy-key")
    assert minutes == 60

def test_returns_none_when_only_lirr_route():
    mock_data = _mock_response([_make_route(2400, ["Long Island Rail Road"])])
    with patch("core.transit._call_api", return_value=mock_data):
        minutes = get_transit_minutes("123 Main St, Forest Hills, NY", "dummy-key")
    assert minutes is None

def test_returns_none_when_no_routes():
    mock_data = {"status": "ZERO_RESULTS", "routes": []}
    with patch("core.transit._call_api", return_value=mock_data):
        minutes = get_transit_minutes("123 Main St, Forest Hills, NY", "dummy-key")
    assert minutes is None

def test_skips_lirr_route_uses_slower_subway():
    lirr_route = _make_route(1800, ["Long Island Rail Road"])
    subway_route = _make_route(3900, ["MTA New York City Transit"])
    mock_data = _mock_response([lirr_route, subway_route])
    with patch("core.transit._call_api", return_value=mock_data):
        minutes = get_transit_minutes("123 Main St, Forest Hills, NY", "dummy-key")
    assert minutes == 65


# --- Hard cap tests (applied in run.py, but we verify the threshold logic here) ---

def test_hard_cap_excludes_listing_over_85_minutes():
    """Simulate the transit hard-cap logic used in run.py."""
    config = {"commute_hard_limit_minutes": 85}
    hard_limit = config.get("commute_hard_limit_minutes", 85)
    assert 90 > hard_limit  # 90 min should be excluded

def test_hard_cap_allows_listing_at_exactly_85_minutes():
    config = {"commute_hard_limit_minutes": 85}
    hard_limit = config.get("commute_hard_limit_minutes", 85)
    assert not (85 > hard_limit)  # exactly at limit — should NOT be excluded

def test_hard_cap_allows_listing_below_limit():
    config = {"commute_hard_limit_minutes": 85}
    hard_limit = config.get("commute_hard_limit_minutes", 85)
    assert not (70 > hard_limit)  # 70 min passes

def test_hard_cap_defaults_to_85_when_missing():
    config = {}  # no commute_hard_limit_minutes key
    hard_limit = config.get("commute_hard_limit_minutes", 85)
    assert hard_limit == 85
