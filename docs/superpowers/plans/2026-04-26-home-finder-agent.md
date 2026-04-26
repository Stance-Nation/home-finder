# Home Finder Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily automated agent that searches ~25 NYC real estate sources, filters for matching homes in Queens/Bronx target neighborhoods, and delivers results via email digest, web dashboard, and CLI report.

**Architecture:** A Python 3.11 CLI program orchestrated by GitHub Actions. Source modules fetch listings independently; a filter+scoring pipeline narrows results; a SQLite database tracks seen listings to surface only new ones on repeat runs; three output modules render results as email, static HTML, and CLI text.

**Tech Stack:** Python 3.11, requests, BeautifulSoup4, sqlite3, smtplib, Google Maps Directions API, RapidAPI (Zillow + Realtor.com), GitHub Actions, GitHub Pages.

---

## File Map

```
home-finder/
├── run.py                          # CLI entry point and orchestrator
├── config.json                     # All user-editable settings
├── requirements.txt                # Python dependencies
├── subscribers.json                # Active email recipients list
├── core/
│   ├── __init__.py
│   ├── models.py                   # Listing dataclass
│   ├── database.py                 # SQLite seen-listings read/write
│   ├── filters.py                  # Hard filter pipeline
│   ├── flags.py                    # Soft flag logic (flip, commute)
│   ├── scorer.py                   # Value score computation
│   └── transit.py                  # Google Maps API (subway/bus only)
├── sources/
│   ├── __init__.py
│   ├── base.py                     # Abstract base class for all sources
│   ├── zillow.py                   # Zillow via RapidAPI
│   ├── realtor.py                  # Realtor.com via RapidAPI
│   ├── streeteasy.py               # StreetEasy scraper
│   ├── redfin.py                   # Redfin scraper
│   ├── homes.py                    # Homes.com scraper
│   ├── findrealestate.py           # FindRealEstate.com scraper
│   ├── mlsli.py                    # MLSLI.com scraper
│   ├── lirealtor.py                # LIRealtor MLS scraper
│   └── brokerages.py               # Config-driven scraper for all 20 brokerages
├── outputs/
│   ├── __init__.py
│   ├── cli.py                      # CLI report formatter
│   ├── email_sender.py             # HTML email builder + Gmail SMTP sender
│   └── dashboard.py                # Static HTML dashboard generator
├── reports/                        # Saved daily CLI reports (auto-created)
├── docs/index.html                 # GitHub Pages dashboard (auto-generated)
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_filters.py
│   ├── test_flags.py
│   ├── test_scorer.py
│   ├── test_database.py
│   ├── test_transit.py
│   └── test_outputs.py
├── docs/
│   └── superpowers/
│       ├── specs/2026-04-26-home-finder-agent-design.md
│       └── plans/2026-04-26-home-finder-agent.md
└── .github/
    └── workflows/
        └── daily_run.yml
```

---

## Task 1: Project Foundation

**Files:**
- Create: `requirements.txt`
- Create: `config.json`
- Create: `subscribers.json`
- Create: `core/__init__.py`, `sources/__init__.py`, `outputs/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0
pytest==8.1.1
pytest-mock==3.12.0
python-dotenv==1.0.1
```

- [ ] **Step 2: Create config.json**

```json
{
  "max_price": 900000,
  "min_bedrooms": 2,
  "max_bedrooms": 3,
  "require_garage": true,
  "commute_flag_minutes": 70,
  "commute_hard_limit_minutes": 70,
  "flip_price_increase_threshold": 0.25,
  "flip_lookback_months": 12,
  "commute_destination": "200 5th Avenue, New York, NY 10010",
  "commute_departure_time": "08:30",
  "neighborhoods": [
    "Forest Hills", "Kew Gardens", "Kew Garden Hills",
    "Richmond Hill", "South Richmond Hill",
    "Pelham Gardens", "Pelham Bay", "Pelham Parkway",
    "Morris Park", "Country Club"
  ],
  "sender_email": "RC-KBHomes@gmail.com",
  "run_time_utc": "13:00"
}
```

- [ ] **Step 3: Create subscribers.json**

```json
{
  "subscribers": [
    "richard_caron_jr@hotmail.com",
    "kathleen.j.byrnes@gmail.com"
  ]
}
```

- [ ] **Step 4: Create package init files**

Create each of these as empty files:
- `core/__init__.py`
- `sources/__init__.py`
- `outputs/__init__.py`
- `tests/__init__.py`

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt config.json subscribers.json core/__init__.py sources/__init__.py outputs/__init__.py tests/__init__.py
git commit -m "feat: project foundation — config, dependencies, package structure"
```

---

## Task 2: Core Data Model

**Files:**
- Create: `core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.models'`

- [ ] **Step 3: Implement core/models.py**

```python
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import date

@dataclass
class Listing:
    listing_id: str
    address: str
    neighborhood: str
    borough: str
    price: int
    bedrooms: int
    garage: bool
    source: str
    listing_url: str
    photo_url: Optional[str] = None
    days_on_market: Optional[int] = None
    last_sale_price: Optional[int] = None
    last_sale_date: Optional[str] = None
    transit_minutes: Optional[int] = None
    flip_flag: bool = False
    commute_flag: bool = False
    condition_keywords: list = field(default_factory=list)
    value_score: Optional[float] = None
    date_first_seen: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["garage"] = 1 if self.garage else 0
        d["flip_flag"] = 1 if self.flip_flag else 0
        d["commute_flag"] = 1 if self.commute_flag else 0
        d["condition_keywords"] = ",".join(self.condition_keywords)
        return d
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
pytest tests/test_models.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat: Listing dataclass with to_dict serialization"
```

---

## Task 3: Database Layer

**Files:**
- Create: `core/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_database.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.database'`

- [ ] **Step 3: Implement core/database.py**

```python
import sqlite3
import json
from pathlib import Path
from core.models import Listing

class Database:
    def __init__(self, path: str = "data/seen_listings.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                listing_id TEXT PRIMARY KEY,
                address TEXT,
                neighborhood TEXT,
                borough TEXT,
                price INTEGER,
                bedrooms INTEGER,
                garage INTEGER,
                source TEXT,
                listing_url TEXT,
                photo_url TEXT,
                transit_minutes INTEGER,
                flip_flag INTEGER,
                commute_flag INTEGER,
                value_score REAL,
                date_first_seen TEXT
            )
        """)
        self.conn.commit()

    def is_seen(self, listing: Listing) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seen_listings WHERE listing_id = ?",
            (listing.listing_id,)
        ).fetchone()
        return row is not None

    def save(self, listing: Listing):
        d = listing.to_dict()
        self.conn.execute("""
            INSERT OR IGNORE INTO seen_listings
            (listing_id, address, neighborhood, borough, price, bedrooms,
             garage, source, listing_url, photo_url, transit_minutes,
             flip_flag, commute_flag, value_score, date_first_seen)
            VALUES
            (:listing_id, :address, :neighborhood, :borough, :price, :bedrooms,
             :garage, :source, :listing_url, :photo_url, :transit_minutes,
             :flip_flag, :commute_flag, :value_score, :date_first_seen)
        """, d)
        self.conn.commit()

    def filter_new(self, listings: list) -> list:
        return [l for l in listings if not self.is_seen(l)]

    def get_all(self) -> list:
        rows = self.conn.execute("SELECT * FROM seen_listings").fetchall()
        results = []
        for row in rows:
            listing = Listing(
                listing_id=row["listing_id"],
                address=row["address"],
                neighborhood=row["neighborhood"],
                borough=row["borough"],
                price=row["price"],
                bedrooms=row["bedrooms"],
                garage=bool(row["garage"]),
                source=row["source"],
                listing_url=row["listing_url"],
                photo_url=row["photo_url"],
                transit_minutes=row["transit_minutes"],
                flip_flag=bool(row["flip_flag"]),
                commute_flag=bool(row["commute_flag"]),
                value_score=row["value_score"],
                date_first_seen=row["date_first_seen"],
            )
            results.append(listing)
        return results
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_database.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/database.py tests/test_database.py
git commit -m "feat: SQLite seen-listings database with filter_new"
```

---

## Task 4: Hard Filter Pipeline

**Files:**
- Create: `core/filters.py`
- Create: `tests/test_filters.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_filters.py
import json
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_filters.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.filters'`

- [ ] **Step 3: Implement core/filters.py**

```python
from core.models import Listing

def apply_hard_filters(listings: list, config: dict) -> list:
    return [l for l in listings if _passes(l, config)]

def _passes(listing: Listing, config: dict) -> bool:
    if listing.price > config["max_price"]:
        return False
    if listing.bedrooms < config["min_bedrooms"]:
        return False
    if listing.bedrooms > config["max_bedrooms"]:
        return False
    if config["require_garage"] and not listing.garage:
        return False
    if listing.neighborhood not in config["neighborhoods"]:
        return False
    return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_filters.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/filters.py tests/test_filters.py
git commit -m "feat: hard filter pipeline (price, beds, garage, neighborhood)"
```

---

## Task 5: Soft Flags (Flip Detection + Commute)

**Files:**
- Create: `core/flags.py`
- Create: `tests/test_flags.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_flags.py
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
    from core.models import Listing
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_flags.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.flags'`

- [ ] **Step 3: Implement core/flags.py**

```python
from datetime import date, timedelta
from core.models import Listing

def apply_flip_flag(listing: Listing, config: dict) -> Listing:
    if not listing.last_sale_price or not listing.last_sale_date:
        return listing
    threshold = config["flip_price_increase_threshold"]
    lookback_days = config["flip_lookback_months"] * 30
    try:
        sale_date = date.fromisoformat(listing.last_sale_date)
    except ValueError:
        return listing
    cutoff = date.today() - timedelta(days=lookback_days)
    if sale_date < cutoff:
        return listing
    increase = (listing.price - listing.last_sale_price) / listing.last_sale_price
    if increase >= threshold:
        listing.flip_flag = True
    return listing

def apply_commute_flag(listing: Listing, config: dict) -> Listing:
    if listing.transit_minutes is None:
        return listing
    if listing.transit_minutes > config["commute_flag_minutes"]:
        listing.commute_flag = True
    return listing

def apply_all_flags(listings: list, config: dict) -> list:
    result = []
    for listing in listings:
        listing = apply_flip_flag(listing, config)
        listing = apply_commute_flag(listing, config)
        result.append(listing)
    return result
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_flags.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/flags.py tests/test_flags.py
git commit -m "feat: soft flags for flip detection (25%/12mo) and commute limit"
```

---

## Task 6: Transit Module

**Files:**
- Create: `core/transit.py`
- Create: `tests/test_transit.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_transit.py
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_transit.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.transit'`

- [ ] **Step 3: Implement core/transit.py**

```python
import requests
from typing import Optional

DESTINATION = "200 5th Avenue, New York, NY 10010"
LIRR_AGENCY_NAMES = {"long island rail road", "lirr"}

def _call_api(origin: str, api_key: str) -> dict:
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": DESTINATION,
        "mode": "transit",
        "transit_mode": "subway|bus",
        "departure_time": "next_monday_0830",
        "alternatives": "true",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def _uses_lirr(route: dict) -> bool:
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            if step.get("travel_mode") != "TRANSIT":
                continue
            agencies = step.get("transit_details", {}).get("line", {}).get("agencies", [])
            for agency in agencies:
                if agency.get("name", "").lower() in LIRR_AGENCY_NAMES:
                    return True
    return False

def get_transit_minutes(address: str, api_key: str) -> Optional[int]:
    try:
        data = _call_api(address, api_key)
    except Exception:
        return None
    if data.get("status") != "OK":
        return None
    for route in data.get("routes", []):
        if _uses_lirr(route):
            continue
        for leg in route.get("legs", []):
            seconds = leg.get("duration", {}).get("value")
            if seconds:
                return seconds // 60
    return None
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_transit.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/transit.py tests/test_transit.py
git commit -m "feat: Google Maps transit module with LIRR exclusion"
```

---

## Task 7: Value Scorer

**Files:**
- Create: `core/scorer.py`
- Create: `tests/test_scorer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scorer.py
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
    fh_scored = score_listing(fh)
    srh_scored = score_listing(srh)
    assert fh_scored.value_score > srh_scored.value_score

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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_scorer.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.scorer'`

- [ ] **Step 3: Implement core/scorer.py**

```python
from core.models import Listing

# Neighborhood quality ratings 1-10 (school scores, safety, transit, future outlook)
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_scorer.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/scorer.py tests/test_scorer.py
git commit -m "feat: value scorer with neighborhood/transit/price/condition weights"
```

---

## Task 8: Source Base Class

**Files:**
- Create: `sources/base.py`

- [ ] **Step 1: Create sources/base.py**

```python
from abc import ABC, abstractmethod
from core.models import Listing

class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, config: dict) -> list:
        """Fetch listings matching config criteria. Returns list of Listing objects.
        Must not raise — catch all exceptions internally and return empty list."""
        ...

    def safe_fetch(self, config: dict) -> list:
        try:
            return self.fetch(config)
        except Exception as e:
            print(f"[{self.name}] fetch failed: {e}")
            return []
```

- [ ] **Step 2: Commit**

```bash
git add sources/base.py
git commit -m "feat: abstract BaseSource with safe_fetch error isolation"
```

---

## Task 9: Zillow Source (RapidAPI)

**Files:**
- Create: `sources/zillow.py`

- [ ] **Step 1: Create sources/zillow.py**

```python
import os
import requests
from core.models import Listing
from sources.base import BaseSource

class ZillowSource(BaseSource):
    name = "zillow"
    _BASE_URL = "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch"
    _HEADERS = {
        "X-RapidAPI-Key": "",
        "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com",
    }

    _NEIGHBORHOOD_ZIPCODES = {
        "Forest Hills": ["11375"],
        "Kew Gardens": ["11415"],
        "Kew Garden Hills": ["11367"],
        "Richmond Hill": ["11418"],
        "South Richmond Hill": ["11419"],
        "Pelham Gardens": ["10469"],
        "Pelham Bay": ["10461"],
        "Pelham Parkway": ["10461", "10462"],
        "Morris Park": ["10462"],
        "Country Club": ["10464"],
    }

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        headers = {**self._HEADERS, "X-RapidAPI-Key": api_key}
        listings = []
        seen_zpids = set()

        for neighborhood, zipcodes in self._NEIGHBORHOOD_ZIPCODES.items():
            for zipcode in zipcodes:
                params = {
                    "location": zipcode,
                    "home_type": "Houses",
                    "minBeds": config["min_bedrooms"],
                    "maxBeds": config["max_bedrooms"],
                    "maxPrice": config["max_price"],
                    "status_type": "ForSale",
                }
                resp = requests.get(self._BASE_URL, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                for prop in data.get("props", []):
                    zpid = str(prop.get("zpid", ""))
                    if not zpid or zpid in seen_zpids:
                        continue
                    seen_zpids.add(zpid)
                    garage = any(
                        "garage" in (prop.get(f) or "").lower()
                        for f in ["parkingType", "description"]
                    )
                    listings.append(Listing(
                        listing_id=f"zillow-{zpid}",
                        address=prop.get("address", ""),
                        neighborhood=neighborhood,
                        borough="Queens" if zipcode[:3] in ["113", "114"] else "Bronx",
                        price=int(prop.get("price", 0)),
                        bedrooms=int(prop.get("bedrooms", 0)),
                        garage=garage,
                        source="zillow",
                        listing_url=f"https://www.zillow.com/homedetails/{zpid}_zpid/",
                        photo_url=prop.get("imgSrc"),
                        days_on_market=prop.get("daysOnZillow"),
                    ))
        return listings
```

- [ ] **Step 2: Commit**

```bash
git add sources/zillow.py
git commit -m "feat: Zillow source via RapidAPI with neighborhood-to-zipcode mapping"
```

---

## Task 10: Realtor.com Source (RapidAPI)

**Files:**
- Create: `sources/realtor.py`

- [ ] **Step 1: Create sources/realtor.py**

```python
import os
import requests
from core.models import Listing
from sources.base import BaseSource

class RealtorSource(BaseSource):
    name = "realtor"
    _BASE_URL = "https://realty-in-us.p.rapidapi.com/properties/v3/list"
    _HEADERS = {
        "X-RapidAPI-Key": "",
        "X-RapidAPI-Host": "realty-in-us.p.rapidapi.com",
    }

    _NEIGHBORHOOD_CITIES = [
        ("Forest Hills", "Queens", "NY"),
        ("Kew Gardens", "Queens", "NY"),
        ("Richmond Hill", "Queens", "NY"),
        ("South Richmond Hill", "Queens", "NY"),
        ("Pelham Bay", "Bronx", "NY"),
        ("Morris Park", "Bronx", "NY"),
        ("Country Club", "Bronx", "NY"),
    ]

    def fetch(self, config: dict) -> list:
        api_key = os.environ.get("RAPIDAPI_KEY", "")
        headers = {**self._HEADERS, "X-RapidAPI-Key": api_key}
        listings = []
        seen_ids = set()

        for neighborhood, borough, state in self._NEIGHBORHOOD_CITIES:
            payload = {
                "limit": 50,
                "offset": 0,
                "filters": {
                    "list_price": {"max": config["max_price"]},
                    "beds": {"min": config["min_bedrooms"], "max": config["max_bedrooms"]},
                    "prop_type": ["single_family"],
                },
                "city": neighborhood,
                "state_code": state,
                "sort": {"direction": "desc", "field": "list_date"},
            }
            resp = requests.post(self._BASE_URL, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for prop in (data.get("data", {}).get("home_search", {}).get("results") or []):
                prop_id = prop.get("property_id", "")
                if not prop_id or prop_id in seen_ids:
                    continue
                seen_ids.add(prop_id)
                desc = (prop.get("description") or {})
                garage = bool(desc.get("garage")) or "garage" in str(desc).lower()
                location = prop.get("location", {}).get("address", {})
                price = (prop.get("list_price") or 0)
                listings.append(Listing(
                    listing_id=f"realtor-{prop_id}",
                    address=f"{location.get('line','')}, {location.get('city','')}, {state}",
                    neighborhood=neighborhood,
                    borough=borough,
                    price=int(price),
                    bedrooms=int(desc.get("beds") or 0),
                    garage=garage,
                    source="realtor",
                    listing_url=f"https://www.realtor.com/realestateandhomes-detail/{prop_id}",
                    photo_url=(prop.get("primary_photo") or {}).get("href"),
                    days_on_market=prop.get("list_date_delta"),
                ))
        return listings
```

- [ ] **Step 2: Commit**

```bash
git add sources/realtor.py
git commit -m "feat: Realtor.com source via RapidAPI"
```

---

## Task 11: StreetEasy Scraper

**Files:**
- Create: `sources/streeteasy.py`

- [ ] **Step 1: Create sources/streeteasy.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class StreetEasySource(BaseSource):
    name = "streeteasy"
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-queens"),
        ("Kew Gardens", "Queens", "kew-gardens-queens"),
        ("Kew Garden Hills", "Queens", "kew-garden-hills-queens"),
        ("Richmond Hill", "Queens", "richmond-hill-queens"),
        ("South Richmond Hill", "Queens", "south-richmond-hill-queens"),
        ("Pelham Gardens", "Bronx", "pelham-gardens-bronx"),
        ("Pelham Bay", "Bronx", "pelham-bay-bronx"),
        ("Pelham Parkway", "Bronx", "pelham-parkway-bronx"),
        ("Morris Park", "Bronx", "morris-park-bronx"),
        ("Country Club", "Bronx", "country-club-bronx"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = (
                f"https://streeteasy.com/for-sale/{slug}"
                f"?price=-{config['max_price']}"
                f"&beds={config['min_bedrooms']}-{config['max_bedrooms']}"
                f"&amenities=garage"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("article.ListingCard"):
                link_tag = card.select_one("a.listingCard-globalLink")
                if not link_tag:
                    continue
                href = link_tag.get("href", "")
                listing_id = f"se-{href.split('/')[-1].split('?')[0]}"
                if listing_id in seen:
                    continue
                seen.add(listing_id)
                price_tag = card.select_one("[data-price]")
                price = int(price_tag["data-price"]) if price_tag else 0
                beds_tag = card.select_one(".listingDetailDefinitions-item--beds")
                beds_text = beds_tag.get_text() if beds_tag else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                addr_tag = card.select_one(".listingCard-addressLabel")
                address = addr_tag.get_text(strip=True) if addr_tag else ""
                photo_tag = card.select_one("img.listingCard-image")
                photo = photo_tag.get("src") if photo_tag else None
                listings.append(Listing(
                    listing_id=listing_id,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="streeteasy",
                    listing_url=f"https://streeteasy.com{href}",
                    photo_url=photo,
                ))
        return listings
```

- [ ] **Step 2: Commit**

```bash
git add sources/streeteasy.py
git commit -m "feat: StreetEasy scraper with garage filter and neighborhood slugs"
```

---

## Task 12: Redfin + Homes.com + FindRealEstate Scrapers

**Files:**
- Create: `sources/redfin.py`
- Create: `sources/homes.py`
- Create: `sources/findrealestate.py`

- [ ] **Step 1: Create sources/redfin.py**

```python
import requests
from core.models import Listing
from sources.base import BaseSource

class RedfinSource(BaseSource):
    name = "redfin"
    _REGION_IDS = {
        "Forest Hills": ("Queens", "30466"),
        "Kew Gardens": ("Queens", "30467"),
        "Kew Garden Hills": ("Queens", "30468"),
        "Richmond Hill": ("Queens", "30478"),
        "South Richmond Hill": ("Queens", "30479"),
        "Pelham Bay": ("Bronx", "30391"),
        "Morris Park": ("Bronx", "30392"),
    }
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, (borough, region_id) in self._REGION_IDS.items():
            url = (
                f"https://www.redfin.com/stingray/api/gis?al=1&has_garage=1"
                f"&max_price={config['max_price']}"
                f"&min_beds={config['min_bedrooms']}&max_beds={config['max_bedrooms']}"
                f"&region_id={region_id}&region_type=neighborhood&num_homes=50"
                f"&sf=1,2,3,4,5,6,7&status=1&uipt=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            text = resp.text
            if text.startswith("{}&&"):
                text = text[4:]
            import json
            try:
                data = json.loads(text)
            except Exception:
                continue
            for home in (data.get("payload", {}).get("homes") or []):
                home_id = str(home.get("id", ""))
                if not home_id or home_id in seen:
                    continue
                seen.add(home_id)
                listings.append(Listing(
                    listing_id=f"redfin-{home_id}",
                    address=home.get("streetLine", {}).get("value", ""),
                    neighborhood=neighborhood,
                    borough=borough,
                    price=int(home.get("price", {}).get("value", 0)),
                    bedrooms=int(home.get("beds", 0)),
                    garage=True,
                    source="redfin",
                    listing_url=f"https://www.redfin.com{home.get('url','')}",
                    photo_url=home.get("smallPhotoUrl"),
                    days_on_market=home.get("dom", {}).get("value"),
                ))
        return listings
```

- [ ] **Step 2: Create sources/homes.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class HomesSource(BaseSource):
    name = "homes"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-queens-ny"),
        ("Kew Gardens", "Queens", "kew-gardens-queens-ny"),
        ("Richmond Hill", "Queens", "richmond-hill-queens-ny"),
        ("Pelham Bay", "Bronx", "pelham-bay-bronx-ny"),
        ("Morris Park", "Bronx", "morris-park-bronx-ny"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = f"https://www.homes.com/for-sale/{slug}/p1/?garage=true&price=0-{config['max_price']}&beds={config['min_bedrooms']}-{config['max_bedrooms']}"
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("[data-testid='listing-card']"):
                link = card.select_one("a")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"homes-{href.split('/')[-2] if href else ''}"
                if lid in seen or lid == "homes-":
                    continue
                seen.add(lid)
                price_el = card.select_one("[data-testid='price']")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one("[data-testid='beds']")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                addr_el = card.select_one("[data-testid='address']")
                address = addr_el.get_text(strip=True) if addr_el else ""
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="homes",
                    listing_url=f"https://www.homes.com{href}",
                ))
        return listings
```

- [ ] **Step 3: Create sources/findrealestate.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class FindRealEstateSource(BaseSource):
    name = "findrealestate"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "forest-hills-ny"),
        ("Kew Gardens", "Queens", "kew-gardens-ny"),
        ("Richmond Hill", "Queens", "richmond-hill-ny"),
        ("Pelham Bay", "Bronx", "pelham-bay-ny"),
        ("Morris Park", "Bronx", "morris-park-ny"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, slug in self._SEARCHES:
            url = f"https://www.findrealestate.com/homes-for-sale/{slug}/?garage=1&max_price={config['max_price']}&min_beds={config['min_bedrooms']}"
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".listing-item, .property-card"):
                link = card.select_one("a[href*='/homes-for-sale/']")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"fre-{hash(href)}"
                if lid in seen:
                    continue
                seen.add(lid)
                price_el = card.select_one(".price, .listing-price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                addr_el = card.select_one(".address, .listing-address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                beds_el = card.select_one(".beds, [class*='bed']")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds = int(re.search(r"\d+", beds_text).group()) if re.search(r"\d+", beds_text) else 0
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="findrealestate",
                    listing_url=href if href.startswith("http") else f"https://www.findrealestate.com{href}",
                ))
        return listings
```

- [ ] **Step 4: Commit**

```bash
git add sources/redfin.py sources/homes.py sources/findrealestate.py
git commit -m "feat: Redfin, Homes.com, FindRealEstate.com scrapers"
```

---

## Task 13: Brokerage Scrapers (Config-Driven)

**Files:**
- Create: `sources/brokerages.py`

All 20 brokerages use a single config-driven scraper. Each brokerage entry defines its search URL template and CSS selectors for address, price, beds, and listing link.

- [ ] **Step 1: Create sources/brokerages.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

BROKERAGE_CONFIGS = [
    {
        "name": "brown_harris_stevens",
        "display": "Brown Harris Stevens",
        "search_url": "https://www.bhsusa.com/search#?Status=For+Sale&PropertyType=House&MinPrice=0&MaxPrice={max_price}&MinBeds={min_beds}&MaxBeds={max_beds}&Neighborhoods={neighborhood}",
        "card_selector": ".property-card, .listing-card",
        "address_selector": ".property-address, .address",
        "price_selector": ".property-price, .price",
        "beds_selector": ".property-beds, .beds",
        "link_selector": "a",
        "base_url": "https://www.bhsusa.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "douglas_elliman",
        "display": "Douglas Elliman",
        "search_url": "https://www.elliman.com/new-york/search/for-sale-in-{neighborhood_slug}/priceto-{max_price}/beds-{min_beds}-{max_beds}",
        "card_selector": ".listing-card, .property-item",
        "address_selector": ".listing-address, h3",
        "price_selector": ".listing-price, .price",
        "beds_selector": ".listing-beds, .beds",
        "link_selector": "a.listing-link, a",
        "base_url": "https://www.elliman.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "corcoran",
        "display": "Corcoran",
        "search_url": "https://www.corcoran.com/nyc/for-sale?neighborhoods={neighborhood}&maxPrice={max_price}&minBeds={min_beds}&propertyType=house",
        "card_selector": "[data-testid='listing-card'], .listing",
        "address_selector": "[data-testid='address'], .address",
        "price_selector": "[data-testid='price'], .price",
        "beds_selector": "[data-testid='beds'], .beds",
        "link_selector": "a",
        "base_url": "https://www.corcoran.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    },
    {
        "name": "compass",
        "display": "Compass Real Estate",
        "search_url": "https://www.compass.com/homes-for-sale/{neighborhood_slug}-new-york/?price_max={max_price}&beds_min={min_beds}&beds_max={max_beds}&property_type=single_family",
        "card_selector": ".uc-listingCard, .listing-card",
        "address_selector": ".uc-listingCard-address, .address",
        "price_selector": ".uc-listingCard-price, .price",
        "beds_selector": ".uc-listingCard-beds, .beds",
        "link_selector": "a",
        "base_url": "https://www.compass.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "nest_seekers",
        "display": "Nest Seekers International",
        "search_url": "https://www.nestseekers.com/sale/{neighborhood_slug}?MaxPrice={max_price}&MinBeds={min_beds}&Type=House",
        "card_selector": ".listing-item, .property-card",
        "address_selector": ".listing-address, .address",
        "price_selector": ".listing-price, .price",
        "beds_selector": ".listing-beds, .beds",
        "link_selector": "a",
        "base_url": "https://www.nestseekers.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    },
    {
        "name": "sothebys",
        "display": "Sotheby's International Realty",
        "search_url": "https://www.sothebysrealty.com/eng/sales/li-usa/pr-0-{max_price}/be-{min_beds}-{max_beds}/hse/{neighborhood_slug}",
        "card_selector": ".property-item, .listing-card",
        "address_selector": ".property-address, .address",
        "price_selector": ".property-price, .price",
        "beds_selector": ".property-beds, .beds",
        "link_selector": "a",
        "base_url": "https://www.sothebysrealty.com",
        "neighborhoods": ["Forest Hills", "Pelham Bay", "Country Club"],
    },
    {
        "name": "coldwell_banker",
        "display": "Coldwell Banker",
        "search_url": "https://www.coldwellbanker.com/for-sale/homes/{neighborhood_slug}-ny?price=0_{max_price}&beds={min_beds}_{max_beds}&garage=true",
        "card_selector": ".listing-card, [data-testid='property-card']",
        "address_selector": ".listing-address, address",
        "price_selector": ".listing-price, .price",
        "beds_selector": ".listing-beds, .beds",
        "link_selector": "a",
        "base_url": "https://www.coldwellbanker.com",
        "neighborhoods": ["Forest Hills", "Richmond Hill", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "century21",
        "display": "Century 21",
        "search_url": "https://www.century21.com/real-estate/homes-for-sale/filterQS=pg~1|sid~{neighborhood_slug}|prc~0_{max_price}|bd~{min_beds}_{max_beds}|gsr~t/",
        "card_selector": ".property-card, .listing",
        "address_selector": ".property-address, .address",
        "price_selector": ".property-price, .price",
        "beds_selector": ".beds, .bedrooms",
        "link_selector": "a",
        "base_url": "https://www.century21.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay"],
    },
    {
        "name": "remax",
        "display": "RE/MAX",
        "search_url": "https://www.remax.com/homes-for-sale/{neighborhood_slug}-ny-usa/type_sfr/pr_0-{max_price}/bd_{min_beds}-{max_beds}",
        "card_selector": ".listing-card, [class*='listing']",
        "address_selector": "[class*='address']",
        "price_selector": "[class*='price']",
        "beds_selector": "[class*='bed']",
        "link_selector": "a",
        "base_url": "https://www.remax.com",
        "neighborhoods": ["Forest Hills", "Richmond Hill", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "bizzarro",
        "display": "The Bizzarro Agency",
        "search_url": "https://www.bizzarroagency.com/listings/?max_price={max_price}&min_beds={min_beds}&neighborhood={neighborhood}",
        "card_selector": ".listing-item, .property",
        "address_selector": ".listing-address, .address",
        "price_selector": ".listing-price, .price",
        "beds_selector": ".beds, .bedrooms",
        "link_selector": "a",
        "base_url": "https://www.bizzarroagency.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay"],
    },
    {
        "name": "bond_new_york",
        "display": "Bond New York",
        "search_url": "https://www.bondnewyork.com/listings/for-sale?neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing-card, .property-card",
        "address_selector": ".listing-address, .address",
        "price_selector": ".listing-price, .price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.bondnewyork.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    },
    {
        "name": "livingny",
        "display": "LivingNY",
        "search_url": "https://www.livingny.com/search?type=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing, .property-card",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.livingny.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "morrell_hirsch",
        "display": "Morrell Hirsch",
        "search_url": "https://www.morrellhirsch.com/listings/?status=for-sale&max_price={max_price}&beds={min_beds}&neighborhood={neighborhood}",
        "card_selector": ".listing-item, .property",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.morrellhirsch.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill"],
    },
    {
        "name": "realny",
        "display": "RealNY / RealNYProperties",
        "search_url": "https://www.realny.com/sale?neighborhood={neighborhood}&max_price={max_price}&beds_min={min_beds}",
        "card_selector": ".listing-card, .property",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.realny.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Richmond Hill", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "alphanyc",
        "display": "AlphaNYC",
        "search_url": "https://www.alphanyc.com/listings?status=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing, .property-card",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.alphanyc.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    },
    {
        "name": "howard_hanna_rand",
        "display": "Howard Hanna Rand",
        "search_url": "https://www.howardhannarand.com/listing-search/?status=active&type=house&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing-card, .property",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.howardhannarand.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "bohemia",
        "display": "Bohemia Realty Group",
        "search_url": "https://www.bohemiarealty.com/listings?sale=true&neighborhood={neighborhood}&max_price={max_price}&beds={min_beds}",
        "card_selector": ".listing, .property-card",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.bohemiarealty.com",
        "neighborhoods": ["Pelham Bay", "Morris Park", "Pelham Gardens", "Country Club"],
    },
    {
        "name": "real_brokerage",
        "display": "Real Brokerage",
        "search_url": "https://www.joinreal.com/listings?type=sale&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing-card, .property",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.joinreal.com",
        "neighborhoods": ["Forest Hills", "Pelham Bay", "Morris Park"],
    },
    {
        "name": "terrace_sothebys",
        "display": "Terrace Sotheby's",
        "search_url": "https://www.terracesothebysrealty.com/listings?type=sale&neighborhood={neighborhood}&max_price={max_price}&beds_min={min_beds}",
        "card_selector": ".listing-item, .property-card",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.terracesothebysrealty.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Kew Garden Hills"],
    },
    {
        "name": "daniel_gale",
        "display": "Daniel Gale Sotheby's",
        "search_url": "https://www.danielgale.com/search?status=active&type=SF&neighborhood={neighborhood}&max_price={max_price}&min_beds={min_beds}",
        "card_selector": ".listing-card, .property",
        "address_selector": ".address",
        "price_selector": ".price",
        "beds_selector": ".beds",
        "link_selector": "a",
        "base_url": "https://www.danielgale.com",
        "neighborhoods": ["Forest Hills", "Kew Gardens", "Pelham Bay"],
    },
]

_NEIGHBORHOOD_SLUGS = {
    "Forest Hills": "forest-hills",
    "Kew Gardens": "kew-gardens",
    "Kew Garden Hills": "kew-garden-hills",
    "Richmond Hill": "richmond-hill",
    "South Richmond Hill": "south-richmond-hill",
    "Pelham Gardens": "pelham-gardens",
    "Pelham Bay": "pelham-bay",
    "Pelham Parkway": "pelham-parkway",
    "Morris Park": "morris-park",
    "Country Club": "country-club",
}

_BOROUGHS = {
    "Forest Hills": "Queens", "Kew Gardens": "Queens", "Kew Garden Hills": "Queens",
    "Richmond Hill": "Queens", "South Richmond Hill": "Queens",
    "Pelham Gardens": "Bronx", "Pelham Bay": "Bronx", "Pelham Parkway": "Bronx",
    "Morris Park": "Bronx", "Country Club": "Bronx",
}

class BrokerageSource(BaseSource):
    name = "brokerages"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    def __init__(self, brokerage_config: dict):
        self.cfg = brokerage_config
        self.name = brokerage_config["name"]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood in self.cfg["neighborhoods"]:
            slug = _NEIGHBORHOOD_SLUGS.get(neighborhood, neighborhood.lower().replace(" ", "-"))
            url = self.cfg["search_url"].format(
                max_price=config["max_price"],
                min_beds=config["min_bedrooms"],
                max_beds=config["max_bedrooms"],
                neighborhood=neighborhood,
                neighborhood_slug=slug,
            )
            try:
                resp = requests.get(url, headers=self._HEADERS, timeout=15)
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "lxml")
                for card in soup.select(self.cfg["card_selector"]):
                    link_el = card.select_one(self.cfg["link_selector"])
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    lid = f"{self.name}-{hash(href)}"
                    if lid in seen or not href:
                        continue
                    seen.add(lid)
                    price_el = card.select_one(self.cfg["price_selector"])
                    price_text = price_el.get_text(strip=True) if price_el else "0"
                    price = int(re.sub(r"[^\d]", "", price_text) or 0)
                    beds_el = card.select_one(self.cfg["beds_selector"])
                    beds_text = beds_el.get_text() if beds_el else "0"
                    beds_match = re.search(r"\d+", beds_text)
                    beds = int(beds_match.group()) if beds_match else 0
                    addr_el = card.select_one(self.cfg["address_selector"])
                    address = addr_el.get_text(strip=True) if addr_el else ""
                    full_url = href if href.startswith("http") else f"{self.cfg['base_url']}{href}"
                    listings.append(Listing(
                        listing_id=lid,
                        address=address,
                        neighborhood=neighborhood,
                        borough=_BOROUGHS.get(neighborhood, "Queens"),
                        price=price,
                        bedrooms=beds,
                        garage=True,
                        source=self.cfg["display"],
                        listing_url=full_url,
                    ))
            except Exception as e:
                print(f"[{self.name}] {neighborhood} failed: {e}")
                continue
        return listings


def get_all_brokerage_sources() -> list:
    return [BrokerageSource(cfg) for cfg in BROKERAGE_CONFIGS]
```

- [ ] **Step 2: Commit**

```bash
git add sources/brokerages.py
git commit -m "feat: config-driven brokerage scraper covering all 20 local brokerages"
```

---

## Task 14: MLS Feed Scrapers

**Files:**
- Create: `sources/mlsli.py`
- Create: `sources/lirealtor.py`

- [ ] **Step 1: Create sources/mlsli.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class MLSLISource(BaseSource):
    name = "mlsli"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "Forest+Hills"),
        ("Kew Gardens", "Queens", "Kew+Gardens"),
        ("Kew Garden Hills", "Queens", "Kew+Garden+Hills"),
        ("Richmond Hill", "Queens", "Richmond+Hill"),
        ("South Richmond Hill", "Queens", "South+Richmond+Hill"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, search_term in self._SEARCHES:
            url = (
                f"https://www.mlsli.com/listing/search/results?"
                f"Address={search_term}&PropertyType=Single+Family&"
                f"PriceMax={config['max_price']}&"
                f"BedsMin={config['min_bedrooms']}&BedsMax={config['max_bedrooms']}&"
                f"GarageSpacesMin=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".listing-item, .property-listing"):
                link = card.select_one("a[href*='/listing/']")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"mlsli-{href.split('/')[-1]}"
                if lid in seen:
                    continue
                seen.add(lid)
                price_el = card.select_one(".listing-price, .price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one(".listing-beds, .beds")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds_match = re.search(r"\d+", beds_text)
                beds = int(beds_match.group()) if beds_match else 0
                addr_el = card.select_one(".listing-address, .address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                full_url = href if href.startswith("http") else f"https://www.mlsli.com{href}"
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="MLSLI",
                    listing_url=full_url,
                ))
        return listings
```

- [ ] **Step 2: Create sources/lirealtor.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from sources.base import BaseSource

class LIRealtorSource(BaseSource):
    name = "lirealtor"
    _HEADERS = {"User-Agent": "Mozilla/5.0 (compatible)"}
    _SEARCHES = [
        ("Forest Hills", "Queens", "Forest+Hills"),
        ("Kew Gardens", "Queens", "Kew+Gardens"),
        ("Richmond Hill", "Queens", "Richmond+Hill"),
        ("South Richmond Hill", "Queens", "South+Richmond+Hill"),
    ]

    def fetch(self, config: dict) -> list:
        listings = []
        seen = set()
        for neighborhood, borough, search_term in self._SEARCHES:
            url = (
                f"https://www.lirealtor.com/listing/search?"
                f"location={search_term}&type=residential&"
                f"max_price={config['max_price']}&"
                f"min_beds={config['min_bedrooms']}&max_beds={config['max_bedrooms']}&"
                f"garage=1"
            )
            resp = requests.get(url, headers=self._HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select(".property-card, .listing-card"):
                link = card.select_one("a")
                if not link:
                    continue
                href = link.get("href", "")
                lid = f"lirealtor-{hash(href)}"
                if lid in seen or not href:
                    continue
                seen.add(lid)
                price_el = card.select_one(".price")
                price_text = price_el.get_text(strip=True) if price_el else "0"
                price = int(re.sub(r"[^\d]", "", price_text) or 0)
                beds_el = card.select_one(".beds")
                beds_text = beds_el.get_text() if beds_el else "0"
                beds_match = re.search(r"\d+", beds_text)
                beds = int(beds_match.group()) if beds_match else 0
                addr_el = card.select_one(".address")
                address = addr_el.get_text(strip=True) if addr_el else ""
                full_url = href if href.startswith("http") else f"https://www.lirealtor.com{href}"
                listings.append(Listing(
                    listing_id=lid,
                    address=address,
                    neighborhood=neighborhood,
                    borough=borough,
                    price=price,
                    bedrooms=beds,
                    garage=True,
                    source="LIRealtor",
                    listing_url=full_url,
                ))
        return listings
```

- [ ] **Step 3: Commit**

```bash
git add sources/mlsli.py sources/lirealtor.py
git commit -m "feat: MLSLI and LIRealtor MLS feed scrapers"
```

---

## Task 15: CLI Output

**Files:**
- Create: `outputs/cli.py`
- Create: `tests/test_outputs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_outputs.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_outputs.py -v
```

Expected: `ModuleNotFoundError: No module named 'outputs.cli'`

- [ ] **Step 3: Implement outputs/cli.py**

```python
from datetime import date
from core.models import Listing

def _stars(score: float) -> str:
    if score is None:
        return "☆☆☆☆☆"
    filled = round(score * 5)
    return "★" * filled + "☆" * (5 - filled)

def format_listing(listing: Listing) -> str:
    flags = []
    if listing.flip_flag:
        flags.append("⚠ Likely Flip")
    if listing.commute_flag:
        flags.append("⚠ Long Commute")
    flag_str = "  " + " | ".join(flags) if flags else ""
    transit = f"{listing.transit_minutes}min" if listing.transit_minutes else "N/A"
    score = f"{_stars(listing.value_score)} ({listing.value_score:.2f})" if listing.value_score else "Unscored"
    return (
        f"\n[{score}] {listing.address}\n"
        f"  {listing.bedrooms} bed · ${listing.price:,} · Garage ✓ · Transit: {transit}\n"
        f"  Source: {listing.source}{flag_str}\n"
        f"  {listing.listing_url}"
    )

def format_report(listings: list, new_count: int) -> str:
    today = date.today().strftime("%B %d, %Y")
    header = (
        f"\nHOME FINDER — Queens & Bronx\n"
        f"{'=' * 50}\n"
        f"Report date: {today} | Total matches: {len(listings)} | New today: {new_count}\n"
        f"{'=' * 50}"
    )
    if not listings:
        return header + "\n\nNo new listings today.\n"
    body = "\n".join(format_listing(l) for l in listings)
    footer = f"\n{'─' * 50}\n"
    return header + "\n" + body + footer

def save_report(listings: list, new_count: int, path: str):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(format_report(listings, new_count))
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_outputs.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add outputs/cli.py tests/test_outputs.py
git commit -m "feat: CLI report formatter with star ratings and flags"
```

---

## Task 16: Email Output

**Files:**
- Create: `outputs/email_sender.py`

- [ ] **Step 1: Create outputs/email_sender.py**

```python
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from core.models import Listing

SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers() -> list:
    with open(SUBSCRIBERS_FILE) as f:
        return json.load(f)["subscribers"]

def remove_subscriber(email: str):
    data = json.load(open(SUBSCRIBERS_FILE))
    data["subscribers"] = [s for s in data["subscribers"] if s != email]
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _listing_card_html(listing: Listing) -> str:
    flags_html = ""
    if listing.flip_flag:
        flags_html += '<span style="color:#e65c00;font-weight:bold;">⚠ Likely Flip</span> '
    if listing.commute_flag:
        flags_html += '<span style="color:#e65c00;font-weight:bold;">⚠ Long Commute</span>'
    transit = f"{listing.transit_minutes} min" if listing.transit_minutes else "N/A"
    photo_html = (
        f'<img src="{listing.photo_url}" style="width:100%;border-radius:6px;margin-bottom:8px;" />'
        if listing.photo_url else ""
    )
    score_pct = int((listing.value_score or 0) * 100)
    return f"""
    <div style="border:1px solid #ddd;border-radius:8px;padding:16px;margin-bottom:16px;font-family:sans-serif;">
        {photo_html}
        <div style="font-size:18px;font-weight:bold;">{listing.address}</div>
        <div style="color:#555;margin:4px 0;">{listing.neighborhood} · {listing.borough}</div>
        <div style="font-size:22px;color:#2c7a2c;font-weight:bold;">${listing.price:,}</div>
        <div style="margin:6px 0;">🛏 {listing.bedrooms} bed &nbsp;|&nbsp; 🚗 Garage ✓ &nbsp;|&nbsp; 🚇 {transit} transit</div>
        <div style="margin:4px 0;color:#555;">Value score: {score_pct}/100</div>
        {flags_html}
        <div style="margin-top:12px;">
            <a href="{listing.listing_url}" style="background:#1a73e8;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:14px;">View Listing</a>
            &nbsp;<span style="color:#888;font-size:12px;">via {listing.source}</span>
        </div>
    </div>"""

def build_email_html(new_listings: list, all_count: int, dashboard_url: str) -> str:
    today = date.today().strftime("%B %d, %Y")
    cards = "".join(_listing_card_html(l) for l in new_listings)
    return f"""
    <html><body style="font-family:sans-serif;max-width:640px;margin:auto;padding:20px;">
        <h1 style="color:#1a1a1a;">🏠 {len(new_listings)} New Listing{"s" if len(new_listings)!=1 else ""} — {today}</h1>
        <p style="color:#555;">{all_count} total active matches across all neighborhoods. Only new listings shown below.</p>
        <hr/>
        {cards}
        <hr/>
        <p style="text-align:center;">
            <a href="{dashboard_url}" style="color:#1a73e8;">View full dashboard →</a>
        </p>
        <p style="color:#aaa;font-size:11px;text-align:center;">
            Sent by RC-KBHomes Home Finder Agent.<br/>
            To unsubscribe, reply to this email with the word STOP.
        </p>
    </body></html>"""

def send_email(new_listings: list, all_count: int, dashboard_url: str, config: dict):
    if not new_listings:
        return
    subscribers = load_subscribers()
    if not subscribers:
        return
    sender = config["sender_email"]
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    today = date.today().strftime("%B %d, %Y")
    subject = f"🏠 {len(new_listings)} New Listing{'s' if len(new_listings)!=1 else ''} Match Your Search — {today}"
    html_body = build_email_html(new_listings, all_count, dashboard_url)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        for recipient in subscribers:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"RC-KBHomes Home Finder <{sender}>"
            msg["To"] = recipient
            msg.attach(MIMEText(html_body, "html"))
            smtp.sendmail(sender, recipient, msg.as_string())
            print(f"[email] Sent to {recipient}")
```

- [ ] **Step 2: Commit**

```bash
git add outputs/email_sender.py
git commit -m "feat: HTML email digest builder with unsubscribe footer and Gmail SMTP"
```

---

## Task 17: Web Dashboard Output

**Files:**
- Create: `outputs/dashboard.py`

- [ ] **Step 1: Create outputs/dashboard.py**

```python
from datetime import date
from core.models import Listing

def _card_html(listing: Listing, is_new: bool) -> str:
    flags = []
    if listing.flip_flag:
        flags.append('<span class="flag flip">⚠ Likely Flip</span>')
    if listing.commute_flag:
        flags.append('<span class="flag commute">⚠ Long Commute</span>')
    flag_html = " ".join(flags)
    new_badge = '<span class="badge-new">NEW</span>' if is_new else ""
    transit = f"{listing.transit_minutes} min" if listing.transit_minutes else "N/A"
    score_pct = int((listing.value_score or 0) * 100)
    photo_html = f'<img class="card-photo" src="{listing.photo_url}" />' if listing.photo_url else ""
    return f"""
    <div class="card">
        {new_badge}
        {photo_html}
        <div class="card-address">{listing.address}</div>
        <div class="card-meta">{listing.neighborhood} · {listing.borough}</div>
        <div class="card-price">${listing.price:,}</div>
        <div class="card-details">🛏 {listing.bedrooms} bed &nbsp;|&nbsp; 🚗 Garage ✓ &nbsp;|&nbsp; 🚇 {transit}</div>
        <div class="card-score">Value score: {score_pct}/100</div>
        <div class="card-flags">{flag_html}</div>
        <a class="card-link" href="{listing.listing_url}" target="_blank">View Listing</a>
        <div class="card-source">via {listing.source}</div>
    </div>"""

def build_dashboard(all_listings: list, new_listing_ids: set) -> str:
    today = date.today().strftime("%B %d, %Y")
    new_listings = [l for l in all_listings if l.listing_id in new_listing_ids]
    new_cards = "".join(_card_html(l, True) for l in new_listings)
    all_cards = "".join(_card_html(l, l.listing_id in new_listing_ids) for l in all_listings)
    new_section = f"""
    <section>
        <h2>New Today ({len(new_listings)})</h2>
        <div class="grid">{new_cards if new_cards else "<p>No new listings today.</p>"}</div>
    </section>""" if new_listings else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>RC-KB Home Finder — NYC</title>
<style>
  body{{font-family:sans-serif;max-width:1100px;margin:auto;padding:20px;background:#f5f5f5;}}
  h1{{color:#1a1a1a;}} h2{{color:#333;border-bottom:2px solid #ddd;padding-bottom:6px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;}}
  .card{{background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.08);position:relative;}}
  .card-photo{{width:100%;border-radius:6px;margin-bottom:10px;object-fit:cover;height:180px;}}
  .card-address{{font-size:16px;font-weight:bold;margin-bottom:4px;}}
  .card-meta{{color:#888;font-size:13px;margin-bottom:6px;}}
  .card-price{{font-size:22px;color:#2c7a2c;font-weight:bold;margin-bottom:6px;}}
  .card-details{{color:#444;font-size:13px;margin-bottom:4px;}}
  .card-score{{color:#555;font-size:13px;margin-bottom:6px;}}
  .card-flags{{margin-bottom:8px;}}
  .flag{{font-size:12px;font-weight:bold;padding:2px 6px;border-radius:4px;margin-right:4px;}}
  .flag.flip{{background:#ffe0cc;color:#a03000;}}
  .flag.commute{{background:#fff3cd;color:#856404;}}
  .card-link{{display:inline-block;background:#1a73e8;color:#fff;padding:7px 14px;border-radius:4px;text-decoration:none;font-size:13px;}}
  .card-source{{color:#aaa;font-size:11px;margin-top:6px;}}
  .badge-new{{position:absolute;top:12px;right:12px;background:#2c7a2c;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;}}
  .meta-bar{{background:#fff;border-radius:8px;padding:12px 20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;gap:24px;align-items:center;flex-wrap:wrap;}}
  .meta-bar span{{color:#555;font-size:14px;}}
</style>
</head>
<body>
<h1>🏠 RC-KB Home Finder &mdash; NYC</h1>
<div class="meta-bar">
  <span>📅 Last updated: {today}</span>
  <span>🏘 {len(all_listings)} total matches</span>
  <span>🆕 {len(new_listings)} new today</span>
  <span>📍 Queens &amp; Bronx | ≤$900k | 2–3 bed | Garage required</span>
</div>
{new_section}
<section>
  <h2>All Active Matches ({len(all_listings)})</h2>
  <div class="grid">{all_cards if all_cards else "<p>No listings found.</p>"}</div>
</section>
</body></html>"""

def save_dashboard(all_listings: list, new_listing_ids: set, path: str = "docs/index.html"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(build_dashboard(all_listings, new_listing_ids))
    print(f"[dashboard] Saved to {path}")
```

- [ ] **Step 2: Commit**

```bash
git add outputs/dashboard.py
git commit -m "feat: static HTML dashboard generator for GitHub Pages"
```

---

## Task 18: Main Orchestrator

**Files:**
- Create: `run.py`

- [ ] **Step 1: Create run.py**

```python
#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import date

def load_config():
    with open("config.json") as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="NYC Home Finder Agent")
    parser.add_argument("--report", action="store_true", help="Print current listings without fetching")
    parser.add_argument("--no-email", action="store_true", help="Skip sending email")
    args = parser.parse_args()

    config = load_config()

    if args.report:
        from core.database import Database
        from outputs.cli import format_report
        db = Database()
        all_listings = db.get_all()
        print(format_report(all_listings, new_count=0))
        return

    print("[agent] Starting Home Finder Agent...")

    # 1. Fetch from all sources
    from sources.zillow import ZillowSource
    from sources.realtor import RealtorSource
    from sources.streeteasy import StreetEasySource
    from sources.redfin import RedfinSource
    from sources.homes import HomesSource
    from sources.findrealestate import FindRealEstateSource
    from sources.mlsli import MLSLISource
    from sources.lirealtor import LIRealtorSource
    from sources.brokerages import get_all_brokerage_sources

    sources = [
        ZillowSource(), RealtorSource(), StreetEasySource(),
        RedfinSource(), HomesSource(), FindRealEstateSource(),
        MLSLISource(), LIRealtorSource(),
        *get_all_brokerage_sources(),
    ]

    raw_listings = []
    for source in sources:
        fetched = source.safe_fetch(config)
        print(f"[{source.name}] fetched {len(fetched)} listings")
        raw_listings.extend(fetched)
    print(f"[agent] Total raw listings: {len(raw_listings)}")

    # 2. Apply hard filters
    from core.filters import apply_hard_filters
    filtered = apply_hard_filters(raw_listings, config)
    print(f"[agent] After hard filters: {len(filtered)}")

    # 3. Fetch transit times and apply transit hard filter (no LIRR / must have subway route)
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    from core.transit import get_transit_minutes
    transit_passed = []
    for listing in filtered:
        minutes = get_transit_minutes(listing.address, api_key)
        if minutes is None:
            print(f"[transit] No subway route: {listing.address} — excluded")
            continue
        listing.transit_minutes = minutes
        transit_passed.append(listing)
    print(f"[agent] After transit filter: {len(transit_passed)}")

    # 4. Apply soft flags
    from core.flags import apply_all_flags
    flagged = apply_all_flags(transit_passed, config)

    # 5. Score and sort
    from core.scorer import score_all
    scored = score_all(flagged)

    # 6. Deduplicate against seen listings DB
    from core.database import Database
    db = Database()
    new_listings = db.filter_new(scored)
    print(f"[agent] New listings (not seen before): {len(new_listings)}")

    # 7. Save new listings to DB
    for listing in new_listings:
        db.save(listing)

    # 8. Get full active list for dashboard
    all_db_listings = db.get_all()
    new_ids = {l.listing_id for l in new_listings}

    # 9. CLI report
    from outputs.cli import format_report, save_report
    report_text = format_report(new_listings, new_count=len(new_listings))
    print(report_text)
    today = date.today().isoformat()
    save_report(new_listings, len(new_listings), f"reports/{today}.txt")

    # 10. Dashboard
    from outputs.dashboard import save_dashboard
    save_dashboard(all_db_listings, new_ids)

    # 11. Email
    if not args.no_email and new_listings:
        from outputs.email_sender import send_email
        dashboard_url = os.environ.get("DASHBOARD_URL", "")
        send_email(new_listings, len(all_db_listings), dashboard_url, config)

    print(f"[agent] Done. {len(new_listings)} new listings processed.")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add run.py
git commit -m "feat: main orchestrator — fetch, filter, score, dedupe, output"
```

---

## Task 19: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/daily_run.yml`

- [ ] **Step 1: Create .github/workflows/daily_run.yml**

```yaml
name: Daily Home Finder Run

on:
  schedule:
    - cron: '0 13 * * *'   # 8:00am EST (13:00 UTC)
  workflow_dispatch:         # allows manual trigger from GitHub website

permissions:
  contents: write            # needed to push dashboard + DB back to repo

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run agent
        env:
          RAPIDAPI_KEY: ${{ secrets.RAPIDAPI_KEY }}
          GOOGLE_MAPS_API_KEY: ${{ secrets.GOOGLE_MAPS_API_KEY }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          DASHBOARD_URL: ${{ secrets.DASHBOARD_URL }}
        run: python run.py

      - name: Commit updated database and dashboard
        run: |
          git config user.name "Home Finder Bot"
          git config user.email "actions@github.com"
          git add data/seen_listings.db docs/index.html reports/ || true
          git diff --staged --quiet || git commit -m "chore: daily run $(date +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: Create .github/workflows directory and commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/daily_run.yml
git commit -m "feat: GitHub Actions daily schedule at 8am EST with secrets"
```

---

## Task 20: Setup Guide

**Files:**
- Create: `SETUP.md`

- [ ] **Step 1: Create SETUP.md**

```markdown
# Home Finder Agent — Setup Guide

Complete these steps once. After setup, the agent runs itself every morning at 8am.

---

## Step 1: Create the RC-KBHomes Gmail Account

1. Go to https://accounts.google.com/signup
2. Choose a username — use **RC-KBHomes** (or similar if taken)
3. Complete account creation
4. Once logged in, go to: https://myaccount.google.com/security
5. Turn on **2-Step Verification** (required for App Passwords)
6. After enabling 2-Step Verification, go to: https://myaccount.google.com/apppasswords
7. Under "Select app" choose **Mail**, under "Select device" choose **Other** and type `HomeFinder`
8. Click **Generate** — copy the 16-character password shown (you'll need it in Step 4)

---

## Step 2: Create a Free RapidAPI Account

1. Go to https://rapidapi.com and click **Sign Up**
2. Once logged in, search for **"Zillow"** → find "Zillow Com1" → click **Subscribe to Test** (Basic/Free plan)
3. Search for **"Realty in US"** → find "Realty In US" → click **Subscribe to Test** (Basic/Free plan)
4. Go to https://rapidapi.com/developer/apps → click your app → copy the **X-RapidAPI-Key** value

---

## Step 3: Create a Free Google Cloud Account

1. Go to https://console.cloud.google.com and sign in with any Google account
2. Click **Create Project** → name it `HomeFinder`
3. In the search bar at top, type **Directions API** → click it → click **Enable**
4. In the left menu, go to **APIs & Services → Credentials**
5. Click **Create Credentials → API Key** → copy the key shown

---

## Step 4: Create the GitHub Repository

1. Log into your GitHub account
2. Click the **+** button (top right) → **New repository**
3. Name it `home-finder` → set to **Private** → click **Create repository**
4. Follow the instructions shown to push this project folder to that repo:
   ```
   git remote add origin https://github.com/YOUR-USERNAME/home-finder.git
   git push -u origin main
   ```

---

## Step 5: Add Your Secret Keys to GitHub

1. In your GitHub repository, click **Settings** (top menu)
2. In the left sidebar, click **Secrets and variables → Actions**
3. Click **New repository secret** for each of the following:

| Name | Value |
|---|---|
| `RAPIDAPI_KEY` | Your RapidAPI key from Step 2 |
| `GOOGLE_MAPS_API_KEY` | Your Google Maps API key from Step 3 |
| `GMAIL_APP_PASSWORD` | The 16-character password from Step 1 |
| `DASHBOARD_URL` | Leave blank for now — fill in after Step 6 |

---

## Step 6: Enable GitHub Pages (Your Free Website)

1. In your GitHub repository, click **Settings**
2. In the left sidebar, click **Pages**
3. Under "Source", select **Deploy from a branch**
4. Under "Branch", select **main** and folder **/ (root)** → click **Save**
5. Wait 2 minutes, then your dashboard URL will appear at the top of the Pages settings page
6. Copy that URL (looks like `https://YOUR-USERNAME.github.io/home-finder`)
7. Go back to **Settings → Secrets and variables → Actions**
8. Edit the `DASHBOARD_URL` secret and paste that URL

---

## Step 7: Run the Agent for the First Time

1. In your GitHub repository, click **Actions** (top menu)
2. Click **Daily Home Finder Run** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Wait 3–5 minutes for it to finish
5. Click the completed run to see the log output
6. Check your email — your first digest will arrive shortly after

From this point on, the agent runs automatically every morning at 8am and emails you only new listings.

---

## How to Change Settings

Open `config.json` in your repository and edit any values. Click the pencil icon on GitHub to edit directly — no software needed. Changes take effect on the next daily run.

## How to Add or Remove Email Recipients

Open `subscribers.json` and add or remove email addresses from the list. Edit directly on GitHub with the pencil icon.

## To Unsubscribe

Reply to any digest email with the word **STOP**. The sender (RC-KBHomes@gmail.com) will receive it and remove your address from `subscribers.json`.
```

- [ ] **Step 2: Commit**

```bash
git add SETUP.md
git commit -m "docs: beginner-friendly setup guide with copy-paste instructions"
```

---

## Task 21: Run Full Test Suite

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests PASS. Count should be 22+.

- [ ] **Step 2: Run agent in dry-run mode (no email, no real API keys needed)**

```bash
python run.py --report
```

Expected: Prints "No listings yet — run without --report to fetch." or similar (DB is empty).

- [ ] **Step 3: Verify GitHub Actions workflow syntax**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/daily_run.yml'))"
```

Expected: No output (valid YAML).

- [ ] **Step 4: Final commit**

```bash
git add -A
git status
git commit -m "chore: final integration — all tests passing, setup guide complete"
```

---

## Self-Review Against Spec

| Spec Requirement | Task Covered |
|---|---|
| ~25 sources (APIs + scrapers + brokerages + MLS) | Tasks 9–14 |
| 10 target neighborhoods (Queens + Bronx) | Tasks 9–14 (neighborhood maps) |
| Hard filters: beds, price, garage | Task 4 |
| Hard filter: LIRR exclusion | Task 6 (transit.py) + Task 18 (orchestrator) |
| Soft flag: flip (25%/12mo) | Task 5 |
| Soft flag: commute >70min | Task 5 |
| Value score: neighborhood → transit → price → DOM → condition | Task 7 |
| SQLite seen-listings DB (first run = all, after = new only) | Task 3 |
| Direct listing URL stored and surfaced | Tasks 2, 15, 16, 17 |
| Email digest with reply-STOP unsubscribe | Task 16 |
| Sender: RC-KBHomes@gmail.com, recipients: richard + kathleen | Task 1 (config) |
| No email on zero new listings | Task 16 (email_sender.py) |
| GitHub Pages web dashboard | Task 17 |
| CLI report saved to reports/ | Task 15 |
| GitHub Actions daily at 8am | Task 19 |
| Beginner-friendly setup guide | Task 20 |
| config.json for all user settings | Task 1 |
```
