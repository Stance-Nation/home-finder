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
