# Home Finder Agent — Design Spec
**Date:** 2026-04-26
**Status:** Approved

---

## Overview

A daily automated agent that searches ~25 real estate sources across all major aggregators, NYC-specific platforms, and local brokerages for homes matching specific criteria in Queens and the Bronx. Results are delivered via email digest, a free hosted web dashboard, and a CLI report. The agent tracks all previously seen listings so that after the initial run it only surfaces new listings, avoiding redundant recommendations.

---

## Target Criteria

| Field | Value |
|---|---|
| Bedrooms | 2–3 |
| Max price | $900,000 |
| Garage | Required (hard filter) |
| Property condition | Fixer-uppers preferred; estate sales and as-is listings prioritized |
| Philosophy | "Worst house in the best neighborhood" — neighborhood quality and future outlook is the top priority |

**Target Neighborhoods:**

*Queens:* Forest Hills, Kew Gardens, Kew Garden Hills, Richmond Hill, South Richmond Hill

*Bronx:* Pelham Gardens, Pelham Bay, Pelham Parkway, Morris Park, Country Club

**Commute target:** 200 5th Avenue, Manhattan (Flatiron District)

---

## Architecture

```
GitHub Actions (daily trigger, 8:00am)
        │
        ▼
  ┌─────────────────────────────────────┐
  │         Data Fetcher Layer          │
  │  ~25 sources: APIs + scrapers       │
  └──────────────┬──────────────────────┘
                 │ raw listings
                 ▼
  ┌─────────────────────────────────────┐
  │           Filter Engine             │
  │  Hard filters + soft flags          │
  └──────────────┬──────────────────────┘
                 │ filtered listings
                 ▼
  ┌─────────────────────────────────────┐
  │       Seen Listings Database        │
  │  SQLite file stored in GitHub repo  │
  └──────────────┬──────────────────────┘
                 │ new listings only
                 ▼
  ┌──────────────────────────────────────────────┐
  │              Output Layer                    │
  │  Email digest · Web dashboard · CLI report   │
  └──────────────────────────────────────────────┘
```

Everything runs on GitHub's free infrastructure. No servers, no hosting fees.

---

## Data Sources (~25 total)

### Via API (stable, rarely breaks)
- **Zillow** — RapidAPI free tier (~500 calls/month)
- **Realtor.com** — RapidAPI free tier

### Via targeted scraping (NYC-critical)
- **StreetEasy** — dominant NYC listing site; often has listings 24–48hrs before Zillow
- **Redfin**
- **Homes.com**
- **FindRealEstate.com**

### Local brokerages (scraped)
- Brown Harris Stevens
- Douglas Elliman
- Corcoran
- Coldwell Banker
- Century 21
- RE/MAX
- Compass Real Estate
- Nest Seekers International
- Sotheby's International Realty
- Daniel Gale Sotheby's
- Terrace Sotheby's (Forest Hills specialist)
- The Bizzarro Agency
- Bond New York
- LivingNY
- Morrell Hirsch
- RealNYProperties / RealNY
- AlphaNYC
- Howard Hanna Rand
- Bohemia Realty Group
- Real Brokerage

### MLS Feeds
- **MLSLI.com** — Long Island MLS (covers Queens)
- **LIRealtor** — Long Island Board of Realtors MLS

Each source is an independent module. If one source is unavailable or blocked, all remaining sources continue to run and results are still delivered.

---

## Filter Engine

### Hard Filters (listing excluded if any fail)
| Filter | Criteria |
|---|---|
| Neighborhood | Must match one of the 10 target neighborhoods |
| Bedrooms | 2 or 3 |
| Price | ≤ $900,000 |
| Garage | Must be explicitly listed as included |
| Transit mode | No LIRR permitted — subway and bus only. If no subway/bus route exists within 1hr 10min, listing is excluded |

### Soft Flags (listing appears but is marked)
| Flag | Trigger |
|---|---|
| ⚠ Likely Flip | Resold within the last 12 months AND current list price is 25%+ higher than last sale price |
| ⚠ Long Commute | Estimated transit time to 200 5th Ave exceeds 1 hour 10 minutes |

Flagged listings are never hidden. They appear in all outputs with a clear visual warning so the user makes the final call.

### Value Score (used for sorting)

Listings are sorted highest-to-lowest by a composite value score. Priority order:

1. **Neighborhood quality** (weight: highest) — based on school ratings, safety data, transit access, and future development outlook
2. **Transit time** (weight: high) — shorter commute scores higher; listings over 1:10 scored lower and flagged
3. **Price vs. neighborhood median** (weight: medium) — below-median price scores higher
4. **Days on market** (weight: low) — longer on market = more negotiating leverage
5. **Condition signals** (weight: low) — keywords like "as-is," "estate sale," "needs TLC," "fixer-upper" boost score

---

## Seen Listings Database

**Technology:** SQLite (a self-contained file stored in the GitHub repository)

**Behavior:**
- First run: all matching listings are shown and recorded as "seen"
- All subsequent runs: only listings NOT already in the database are surfaced
- If a listing is removed and relisted at a different price, it is treated as a new listing

**Fields stored per listing:**
| Field | Description |
|---|---|
| listing_id | Unique identifier from source |
| address | Full street address |
| source | Which platform/brokerage it came from |
| price | Listed price at time of discovery |
| bedrooms | Number of bedrooms |
| garage | Boolean — confirmed garage |
| transit_minutes | Estimated transit time to 200 5th Ave |
| flip_flag | Boolean — triggered by flip detection logic |
| commute_flag | Boolean — triggered if transit > 70 minutes |
| value_score | Computed composite score |
| listing_url | Direct link to the listing on source site |
| date_first_seen | Date the agent first recorded this listing |

---

## Output Layer

### Email Digest

- **Sender:** RC-KBHomes@gmail.com
- **Recipients:** richard_caron_jr@hotmail.com, kathleen.j.byrnes@gmail.com
- **Frequency:** Daily at ~8:00am; no email sent if there are zero new listings
- **Subject:** `🏠 [X] New Listings Match Your Search — [Date]`
- **Content:** Summary header, listing cards for new listings only, link to full dashboard
- **Listing card includes:** Photo (if available), address, price, bedrooms, garage confirmation, neighborhood, transit time, value score, any flags, "View Listing" button (direct URL)
- **Unsubscribe:** Every email footer includes a "Reply STOP to unsubscribe" instruction. Replies go to RC-KBHomes@gmail.com; the repo owner removes that address from `config.json` to stop future emails. Each address is managed independently. Re-subscribing is the same process in reverse.

### Web Dashboard

- **Hosting:** GitHub Pages (free, no server required)
- **URL:** Automatically assigned when GitHub Pages is enabled (e.g., `https://username.github.io/home-finder`)
- **Sections:**
  - "New Today" — listings added since the last run, highlighted at the top
  - "All Active Matches" — all listings currently matching criteria, sorted by value score
- **Listing card includes:** Photo, address, price, beds, garage, neighborhood, transit time, value score, flags, "View Listing" link
- **Updates:** Dashboard regenerates and publishes automatically on every agent run
- **Setup effort:** ~5 minutes (one checkbox in GitHub settings)

### CLI Report

- **Command:** `python run.py` — full agent run (fetch, filter, update DB, send email, publish dashboard)
- **Command:** `python run.py --report` — print current matched listings without fetching or sending
- **Output format:** Formatted text with value score stars, flags, transit time, source, and direct URL per listing
- **Saved output:** Each report is also written to `reports/YYYY-MM-DD.txt` for permanent history

---

## Transit Time Estimation

- **API:** Google Maps Platform — Directions API (transit mode)
- **Destination:** 200 5th Avenue, New York, NY 10010
- **Timing:** Estimated for a weekday morning departure (~8:30am) to reflect realistic commute conditions
- **Transit mode restriction:** Subway and bus only. The API query explicitly excludes LIRR. If the only route within 1hr 10min requires LIRR, the listing fails the hard filter and is excluded entirely.
- **Free tier:** Covers daily usage for this use case
- **Soft flag threshold:** > 70 minutes estimated transit time (subway/bus route)
- **Score impact:** Transit time is the second-highest weighted factor in the value score

---

## Flip Detection

- **Data source:** Price history pulled from Zillow API and StreetEasy where available
- **Trigger:** Last sale date within 12 months of current listing AND current list price is 25% or more above the last recorded sale price
- **Behavior:** Soft flag only — listing appears in all outputs with a `⚠ Likely Flip` warning
- **User action required:** User decides whether to investigate further or ignore the listing

---

## Configuration

A single `config.json` file controls all user-adjustable settings. No coding required to modify:

```json
{
  "max_price": 900000,
  "min_bedrooms": 2,
  "max_bedrooms": 3,
  "require_garage": true,
  "commute_flag_minutes": 70,
  "flip_price_increase_threshold": 0.25,
  "flip_lookback_months": 12,
  "neighborhoods": [
    "Forest Hills", "Kew Gardens", "Kew Garden Hills",
    "Richmond Hill", "South Richmond Hill",
    "Pelham Gardens", "Pelham Bay", "Pelham Parkway",
    "Morris Park", "Country Club"
  ],
  "email_recipients": [
    "richard_caron_jr@hotmail.com",
    "kathleen.j.byrnes@gmail.com"
  ],
  "sender_email": "RC-KBHomes@gmail.com",
  "run_time_utc": "13:00"
}
```

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Agent language | Python 3.11 | Most beginner-readable; best library ecosystem for scraping and APIs |
| Scheduling | GitHub Actions | Free, always-on, no Mac required to be running |
| Database | SQLite | Zero setup, single file, no server needed |
| Web dashboard | Static HTML/CSS (Python-generated) | No framework needed; GitHub Pages hosts it free |
| Email sending | Gmail SMTP + App Password | Free, reliable, no third-party email service needed |
| API calls | RapidAPI (Zillow, Realtor.com) | Free tiers sufficient for daily use |
| Transit estimation | Google Maps Directions API | Free tier covers daily usage |
| Web scraping | Python `requests` + `BeautifulSoup` | Simple, widely documented, beginner-friendly to troubleshoot |

---

## Setup Steps (One-Time)

All steps include exact copy-paste instructions in the setup guide:

1. Create GitHub repository (user already has GitHub account)
2. Create `RC-KBHomes@gmail.com` Gmail account + generate App Password
3. Create free RapidAPI account → subscribe to Zillow and Realtor.com free plans
4. Create free Google Cloud account → enable Maps Directions API → copy API key
5. Add API keys to GitHub Secrets (encrypted storage, never visible in code)
6. Enable GitHub Pages on the repository (one checkbox)
7. Run agent manually for the first time to generate the initial listings inventory

**Estimated setup time:** 30–45 minutes with the step-by-step guide

---

## File Structure

```
home-finder/
├── run.py                  # Main entry point
├── config.json             # All user settings (edit this to change criteria)
├── requirements.txt        # Python dependencies
├── data/
│   └── seen_listings.db    # SQLite database of all seen listings
├── sources/
│   ├── zillow.py           # Zillow API fetcher
│   ├── realtor.py          # Realtor.com API fetcher
│   ├── streeteasy.py       # StreetEasy scraper
│   ├── redfin.py           # Redfin scraper
│   ├── homes.py            # Homes.com scraper
│   └── brokerages/         # One file per brokerage
├── core/
│   ├── filters.py          # Hard filters
│   ├── flags.py            # Soft flag logic (flip, commute)
│   ├── scorer.py           # Value score computation
│   ├── transit.py          # Google Maps API integration
│   └── database.py         # Seen listings DB read/write
├── outputs/
│   ├── email.py            # Email digest builder and sender
│   ├── dashboard.py        # HTML dashboard generator
│   └── cli.py              # CLI report formatter
├── reports/                # Saved daily CLI reports
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-26-home-finder-agent-design.md
└── .github/
    └── workflows/
        └── daily_run.yml   # GitHub Actions schedule config
```

---

## Out of Scope

- Mobile app
- Push notifications
- Automatic scheduling of viewings
- Mortgage or affordability calculations
- Rental listings
