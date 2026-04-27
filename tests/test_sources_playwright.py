"""
Tests for the Playwright-based sources: StreetEasy, MLSLI, LIRealtor.

All tests call _parse_html() directly — no browser is launched.
The fetch() methods are tested by mocking sync_playwright so the
browser code path is exercised without actually opening Chromium.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from sources.streeteasy import _parse_html as se_parse_html, StreetEasySource
from sources.mlsli import _parse_html as mlsli_parse_html, MLSLISource
from sources.lirealtor import _parse_html as lirealtor_parse_html, LIRealtorSource


# ---------------------------------------------------------------------------
# Shared sample HTML (StreetEasy card structure)
# ---------------------------------------------------------------------------

SE_CARD_HTML = """
<html><body>
  <article class="listingCard">
    <a class="listingCard-globalLink" href="/listing/12345"></a>
    <span data-price="750000">$750,000</span>
    <div class="listingDetailDefinitions-item--beds">3 beds</div>
    <div class="listingCard-addressLabel">12 Main St, Forest Hills</div>
    <img class="listingCard-image" src="https://example.com/photo.jpg">
  </article>
  <article class="listingCard">
    <a class="listingCard-globalLink" href="/listing/67890"></a>
    <span data-price="850000">$850,000</span>
    <div class="listingDetailDefinitions-item--beds">4 beds</div>
    <div class="listingCard-addressLabel">45 Oak Ave, Forest Hills</div>
    <img class="listingCard-image" src="https://example.com/photo2.jpg">
  </article>
</body></html>
"""

SE_JSON_LD_HTML = """
<html><head>
  <script type="application/ld+json">
  {
    "@type": "ItemList",
    "itemListElement": [
      {
        "item": {
          "@type": "SingleFamilyResidence",
          "url": "/building/99999",
          "name": "55 Elm St",
          "address": {
            "streetAddress": "55 Elm St",
            "addressLocality": "Kew Gardens",
            "addressRegion": "NY"
          },
          "offers": {"price": 680000},
          "numberOfBedrooms": 3
        }
      }
    ]
  }
  </script>
</head><body></body></html>
"""

SE_EMPTY_HTML = "<html><body><div>No listings found</div></body></html>"


# ---------------------------------------------------------------------------
# StreetEasy _parse_html tests
# ---------------------------------------------------------------------------

class TestStreetEasyParseHtml:

    def test_parses_listing_cards(self):
        listings = se_parse_html(SE_CARD_HTML, "Forest Hills", "Queens")
        assert len(listings) == 2

    def test_listing_fields_first_card(self):
        listings = se_parse_html(SE_CARD_HTML, "Forest Hills", "Queens")
        l = listings[0]
        assert l.listing_id == "se-12345"
        assert l.price == 750_000
        assert l.bedrooms == 3
        assert l.neighborhood == "Forest Hills"
        assert l.borough == "Queens"
        assert l.source == "streeteasy"
        assert l.garage is True
        assert l.garage_confirmed is False
        assert l.listing_url == "https://streeteasy.com/listing/12345"
        assert l.photo_url == "https://example.com/photo.jpg"

    def test_listing_fields_second_card(self):
        listings = se_parse_html(SE_CARD_HTML, "Forest Hills", "Queens")
        l = listings[1]
        assert l.listing_id == "se-67890"
        assert l.price == 850_000
        assert l.bedrooms == 4
        assert "45 Oak Ave" in l.address

    def test_no_duplicate_ids(self):
        listings = se_parse_html(SE_CARD_HTML, "Forest Hills", "Queens")
        ids = [l.listing_id for l in listings]
        assert len(ids) == len(set(ids))

    def test_json_ld_strategy(self):
        listings = se_parse_html(SE_JSON_LD_HTML, "Kew Gardens", "Queens")
        assert len(listings) == 1
        l = listings[0]
        assert l.listing_id == "se-99999"
        assert l.price == 680_000
        assert l.bedrooms == 3
        assert l.neighborhood == "Kew Gardens"
        assert "55 Elm St" in l.address

    def test_empty_html_returns_empty_list(self):
        listings = se_parse_html(SE_EMPTY_HTML, "Forest Hills", "Queens")
        assert listings == []

    def test_data_testid_selector(self):
        html = """
        <html><body>
          <div data-testid="listing-card">
            <a href="/listing/11111"></a>
            <span data-price="500000">$500,000</span>
            <span class="beds">2 beds</span>
            <span class="address">1 Test St</span>
          </div>
        </body></html>
        """
        listings = se_parse_html(html, "Richmond Hill", "Queens")
        assert len(listings) == 1
        assert listings[0].listing_id == "se-11111"
        assert listings[0].price == 500_000


# ---------------------------------------------------------------------------
# MLSLI sample HTML
# ---------------------------------------------------------------------------

MLSLI_CARD_HTML = """
<html><body>
  <ul>
    <li data-listingid="MLS-001" class="idx-listing">
      <a href="/listing/MLS-001">123 Queens Blvd</a>
      <span class="listing-price">$699,000</span>
      <span class="listing-beds">3 beds</span>
      <span class="listing-address">123 Queens Blvd, Forest Hills</span>
    </li>
    <li data-listingid="MLS-002" class="idx-listing">
      <a href="/listing/MLS-002">456 Austin St</a>
      <span class="listing-price">$799,000</span>
      <span class="listing-beds">4 beds</span>
      <span class="listing-address">456 Austin St, Forest Hills</span>
    </li>
  </ul>
</body></html>
"""

MLSLI_JSON_HTML = """
<html><body>
  <script>
    window.__IDX_LISTINGS__ = [
      {"id": "MLS-JSON-1", "price": 650000, "bedrooms": 3,
       "address": "77 Park Dr", "url": "/listing/MLS-JSON-1"},
      {"id": "MLS-JSON-2", "price": 720000, "bedrooms": 4,
       "address": "88 Maple Ave", "url": "/listing/MLS-JSON-2"}
    ];
  </script>
</body></html>
"""

MLSLI_EMPTY_HTML = "<html><body><p>No results</p></body></html>"


# ---------------------------------------------------------------------------
# MLSLI _parse_html tests
# ---------------------------------------------------------------------------

class TestMLSLIParseHtml:

    def test_parses_listing_cards(self):
        listings = mlsli_parse_html(MLSLI_CARD_HTML, "Forest Hills", "Queens")
        assert len(listings) == 2

    def test_listing_fields_first_card(self):
        listings = mlsli_parse_html(MLSLI_CARD_HTML, "Forest Hills", "Queens")
        l = listings[0]
        assert l.listing_id == "mlsli-MLS-001"
        assert l.price == 699_000
        assert l.bedrooms == 3
        assert l.neighborhood == "Forest Hills"
        assert l.borough == "Queens"
        assert l.source == "MLSLI"
        assert l.garage is True
        assert l.garage_confirmed is False
        assert "mlsli.com" in l.listing_url

    def test_listing_fields_second_card(self):
        listings = mlsli_parse_html(MLSLI_CARD_HTML, "Forest Hills", "Queens")
        l = listings[1]
        assert l.listing_id == "mlsli-MLS-002"
        assert l.price == 799_000
        assert l.bedrooms == 4

    def test_no_duplicate_ids(self):
        listings = mlsli_parse_html(MLSLI_CARD_HTML, "Forest Hills", "Queens")
        ids = [l.listing_id for l in listings]
        assert len(ids) == len(set(ids))

    def test_embedded_json_strategy(self):
        listings = mlsli_parse_html(MLSLI_JSON_HTML, "Kew Gardens", "Queens")
        assert len(listings) == 2
        ids = {l.listing_id for l in listings}
        assert "mlsli-MLS-JSON-1" in ids
        assert "mlsli-MLS-JSON-2" in ids
        prices = {l.listing_id: l.price for l in listings}
        assert prices["mlsli-MLS-JSON-1"] == 650_000
        assert prices["mlsli-MLS-JSON-2"] == 720_000

    def test_empty_html_returns_empty_list(self):
        listings = mlsli_parse_html(MLSLI_EMPTY_HTML, "Forest Hills", "Queens")
        assert listings == []


# ---------------------------------------------------------------------------
# LIRealtor sample HTML
# ---------------------------------------------------------------------------

LIR_CARD_HTML = """
<html><body>
  <div class="property-card">
    <a href="/listing/LIR-001">200 Lefferts Blvd</a>
    <span class="price">$675,000</span>
    <span class="beds">3 beds</span>
    <span class="address">200 Lefferts Blvd, Richmond Hill</span>
  </div>
  <div class="property-card">
    <a href="/listing/LIR-002">10 Jamaica Ave</a>
    <span class="price">$580,000</span>
    <span class="beds">2 beds</span>
    <span class="address">10 Jamaica Ave, Richmond Hill</span>
  </div>
</body></html>
"""

LIR_JSON_HTML = """
<html><body>
  <script>
    var listings = [
      {"id": "LIR-JSON-1", "price": 700000, "bedrooms": 3,
       "address": "5 Oak St", "url": "/listing/LIR-JSON-1"},
      {"id": "LIR-JSON-2", "price": 550000, "bedrooms": 2,
       "address": "7 Elm Rd", "url": "/listing/LIR-JSON-2"}
    ];
  </script>
</body></html>
"""

LIR_EMPTY_HTML = "<html><body><p>No results</p></body></html>"


# ---------------------------------------------------------------------------
# LIRealtor _parse_html tests
# ---------------------------------------------------------------------------

class TestLIRealtorParseHtml:

    def test_parses_listing_cards(self):
        listings = lirealtor_parse_html(LIR_CARD_HTML, "Richmond Hill", "Queens")
        assert len(listings) == 2

    def test_listing_fields_first_card(self):
        listings = lirealtor_parse_html(LIR_CARD_HTML, "Richmond Hill", "Queens")
        l = listings[0]
        # LIRealtor uses MD5 hash of href for listing_id
        assert l.listing_id.startswith("lirealtor-")
        assert l.price == 675_000
        assert l.bedrooms == 3
        assert l.neighborhood == "Richmond Hill"
        assert l.borough == "Queens"
        assert l.source == "LIRealtor"
        assert l.garage is True
        assert l.garage_confirmed is False
        assert "lirealtor.com" in l.listing_url

    def test_listing_fields_second_card(self):
        listings = lirealtor_parse_html(LIR_CARD_HTML, "Richmond Hill", "Queens")
        l = listings[1]
        assert l.price == 580_000
        assert l.bedrooms == 2

    def test_no_duplicate_ids(self):
        listings = lirealtor_parse_html(LIR_CARD_HTML, "Richmond Hill", "Queens")
        ids = [l.listing_id for l in listings]
        assert len(ids) == len(set(ids))

    def test_embedded_json_strategy(self):
        listings = lirealtor_parse_html(LIR_JSON_HTML, "Forest Hills", "Queens")
        assert len(listings) == 2
        prices = {l.price for l in listings}
        assert 700_000 in prices
        assert 550_000 in prices

    def test_empty_html_returns_empty_list(self):
        listings = lirealtor_parse_html(LIR_EMPTY_HTML, "Forest Hills", "Queens")
        assert listings == []


# ---------------------------------------------------------------------------
# fetch() method tests — mock sync_playwright
# ---------------------------------------------------------------------------

def _make_mock_playwright_ctx(html_content: str):
    """
    Build a mock context manager that simulates sync_playwright() returning
    a browser that yields the given html_content from page.content().
    """
    mock_page = MagicMock()
    mock_page.content.return_value = html_content
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.wait_for_selector.side_effect = Exception("selector not found")
    mock_page.close.return_value = None

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close.return_value = None

    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium

    # sync_playwright() returns a context manager; mock __enter__ / __exit__
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_pw)
    mock_cm.__exit__ = MagicMock(return_value=False)

    return mock_cm


CONFIG = {
    "max_price": 900_000,
    "min_bedrooms": 2,
    "max_bedrooms": 5,
}


class TestStreetEasyFetch:

    def test_fetch_returns_listings(self, mocker):
        mock_cm = _make_mock_playwright_ctx(SE_CARD_HTML)
        mocker.patch("sources.streeteasy.sync_playwright", return_value=mock_cm)
        source = StreetEasySource()
        results = source.fetch(CONFIG)
        # SE_CARD_HTML has 2 cards, but fetch iterates 10 neighborhoods
        # so we may get up to 20 (2 per neighborhood); deduplication by listing_id
        # means: same IDs across neighborhoods get deduplicated → exactly 2 unique
        assert len(results) == 2

    def test_fetch_returns_correct_source(self, mocker):
        mock_cm = _make_mock_playwright_ctx(SE_CARD_HTML)
        mocker.patch("sources.streeteasy.sync_playwright", return_value=mock_cm)
        results = StreetEasySource().fetch(CONFIG)
        assert all(r.source == "streeteasy" for r in results)

    def test_fetch_returns_empty_on_browser_error(self, mocker):
        mocker.patch("sources.streeteasy.sync_playwright", side_effect=Exception("browser crash"))
        results = StreetEasySource().fetch(CONFIG)
        assert results == []

    def test_fetch_empty_html(self, mocker):
        mock_cm = _make_mock_playwright_ctx(SE_EMPTY_HTML)
        mocker.patch("sources.streeteasy.sync_playwright", return_value=mock_cm)
        results = StreetEasySource().fetch(CONFIG)
        assert results == []


class TestMLSLIFetch:

    def test_fetch_returns_listings(self, mocker):
        mock_cm = _make_mock_playwright_ctx(MLSLI_CARD_HTML)
        mocker.patch("sources.mlsli.sync_playwright", return_value=mock_cm)
        results = MLSLISource().fetch(CONFIG)
        # 2 unique listing IDs from the sample HTML, 5 neighborhoods but deduped
        assert len(results) == 2

    def test_fetch_returns_correct_source(self, mocker):
        mock_cm = _make_mock_playwright_ctx(MLSLI_CARD_HTML)
        mocker.patch("sources.mlsli.sync_playwright", return_value=mock_cm)
        results = MLSLISource().fetch(CONFIG)
        assert all(r.source == "MLSLI" for r in results)

    def test_fetch_returns_empty_on_browser_error(self, mocker):
        mocker.patch("sources.mlsli.sync_playwright", side_effect=Exception("crash"))
        results = MLSLISource().fetch(CONFIG)
        assert results == []

    def test_fetch_empty_html(self, mocker):
        mock_cm = _make_mock_playwright_ctx(MLSLI_EMPTY_HTML)
        mocker.patch("sources.mlsli.sync_playwright", return_value=mock_cm)
        results = MLSLISource().fetch(CONFIG)
        assert results == []


class TestLIRealtorFetch:

    def test_fetch_returns_listings(self, mocker):
        mock_cm = _make_mock_playwright_ctx(LIR_CARD_HTML)
        mocker.patch("sources.lirealtor.sync_playwright", return_value=mock_cm)
        results = LIRealtorSource().fetch(CONFIG)
        # 2 unique listing IDs from the sample HTML, 4 neighborhoods but deduped
        assert len(results) == 2

    def test_fetch_returns_correct_source(self, mocker):
        mock_cm = _make_mock_playwright_ctx(LIR_CARD_HTML)
        mocker.patch("sources.lirealtor.sync_playwright", return_value=mock_cm)
        results = LIRealtorSource().fetch(CONFIG)
        assert all(r.source == "LIRealtor" for r in results)

    def test_fetch_returns_empty_on_browser_error(self, mocker):
        mocker.patch("sources.lirealtor.sync_playwright", side_effect=Exception("crash"))
        results = LIRealtorSource().fetch(CONFIG)
        assert results == []

    def test_fetch_empty_html(self, mocker):
        mock_cm = _make_mock_playwright_ctx(LIR_EMPTY_HTML)
        mocker.patch("sources.lirealtor.sync_playwright", return_value=mock_cm)
        results = LIRealtorSource().fetch(CONFIG)
        assert results == []
