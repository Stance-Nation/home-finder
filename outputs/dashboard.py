from datetime import date, timedelta
from urllib.parse import quote
from core.models import Listing

_DESTINATION = "200 5th Ave, New York, NY 10010"

def _maps_url(address: str) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote(address)}"
        f"&destination={quote(_DESTINATION)}"
        "&travelmode=transit"
    )

def _is_new(listing: Listing) -> bool:
    try:
        first_seen = date.fromisoformat(listing.date_first_seen)
        return (date.today() - first_seen).days <= 7
    except Exception:
        return False

def _card_html(listing: Listing) -> str:
    flags = []
    if listing.flip_flag:
        flags.append('<span class="flag flip">⚠ Likely Flip</span>')
    if listing.commute_flag:
        flags.append('<span class="flag commute">⚠ Long Commute</span>')
    if listing.property_type == "land":
        flags.append('<span class="flag garage">No garage (vacant lot)</span>')
    elif not listing.garage_confirmed:
        flags.append('<span class="flag garage">⚠ Garage unconfirmed</span>')
    flag_html = " ".join(flags)
    # Property type badge
    type_labels = {
        "single_family": "Detached",
        "multi_family": "Multi-Family",
        "townhouse": "Townhouse",
        "land": "Vacant Lot",
    }
    badges = ""
    if listing.property_type:
        label = type_labels.get(listing.property_type, listing.property_type.replace("_", " ").title())
        badges += f'<span class="badge badge-type">{label}</span>'
    new_badge = '<span class="badge-new">NEW</span>' if _is_new(listing) else ""
    transit = f"{listing.transit_minutes} min" if listing.transit_minutes else "N/A"
    score_pct = int((listing.value_score or 0) * 100)
    photo_html = f'<img class="card-photo" src="{listing.photo_url}" onerror="this.style.display=\'none\'" />' if listing.photo_url else ""
    lid = listing.listing_id.replace('"', '')
    dismiss_btn = f'<button class="dismiss-btn" onclick="dismissListing(\'{lid}\')" title="Permanently remove this listing">✕</button>'
    return f"""
    <div class="card" id="card-{lid}" data-id="{lid}">
        {new_badge}
        {badges}
        <button class="fav-btn" onclick="toggleFav('{lid}')" title="Favourite this listing">☆</button>
        {dismiss_btn}
        {photo_html}
        <div class="card-address">{listing.address}</div>
        <div class="card-meta">{listing.neighborhood} · {listing.borough}</div>
        <div class="card-price">${listing.price:,}</div>
        <div class="card-details">🛏 {listing.bedrooms} bed &nbsp;|&nbsp; 🚗 Garage ✓ &nbsp;|&nbsp; 🚇 {transit}</div>
        <div class="card-score">Value score: {score_pct}/100</div>
        <div class="card-flags">{flag_html}</div>
        <a class="card-link" href="{listing.listing_url}" target="_blank">View Listing</a>
        <a class="card-link transit-link" href="{_maps_url(listing.address)}" target="_blank">🚇 Transit to Flatiron</a>
        <div class="card-source">via {listing.source}</div>
        <div class="card-seen">First seen: {listing.date_first_seen}</div>
    </div>"""

def build_dashboard(all_listings: list, new_listing_ids: set) -> str:
    today = date.today().strftime("%B %d, %Y")
    new_listings = [l for l in all_listings if _is_new(l)]
    older_listings = [l for l in all_listings if not _is_new(l)]
    new_cards = "".join(_card_html(l) for l in new_listings)
    older_cards = "".join(_card_html(l) for l in older_listings)

    new_section = f"""
    <section>
        <h2>New This Week ({len(new_listings)})</h2>
        <div class="grid">{new_cards if new_cards else "<p>No new listings this week.</p>"}</div>
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
  .card-address{{font-size:16px;font-weight:bold;margin-bottom:4px;padding-right:36px;}}
  .card-meta{{color:#888;font-size:13px;margin-bottom:6px;}}
  .card-price{{font-size:22px;color:#2c7a2c;font-weight:bold;margin-bottom:6px;}}
  .card-details{{color:#444;font-size:13px;margin-bottom:4px;}}
  .card-score{{color:#555;font-size:13px;margin-bottom:6px;}}
  .card-flags{{margin-bottom:8px;}}
  .card-seen{{color:#bbb;font-size:11px;margin-top:6px;}}
  .flag{{font-size:12px;font-weight:bold;padding:2px 6px;border-radius:4px;margin-right:4px;}}
  .flag.flip{{background:#ffe0cc;color:#a03000;}}
  .flag.commute{{background:#fff3cd;color:#856404;}}
  .flag.garage{{background:#e8f0fe;color:#1a56db;}}
  .card-link{{display:inline-block;background:#1a73e8;color:#fff;padding:7px 14px;border-radius:4px;text-decoration:none;font-size:13px;margin-right:6px;margin-bottom:6px;}}
  .transit-link{{background:#1e6b3e;}}
  .card-source{{color:#aaa;font-size:11px;margin-top:6px;}}
  .badge-new{{position:absolute;top:12px;left:12px;background:#2c7a2c;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;}}
  .badge{{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;margin-right:4px;margin-bottom:4px;}}
  .badge-type{{background:#6b7280;color:#fff;}}
  .fav-btn{{position:absolute;top:10px;right:10px;background:none;border:none;font-size:22px;cursor:pointer;line-height:1;padding:2px;}}
  .fav-btn.active{{color:#f5a623;}}
  .dismiss-btn{{position:absolute;top:10px;right:38px;background:none;border:none;font-size:16px;cursor:pointer;color:#bbb;line-height:1;padding:2px;}}
  .dismiss-btn:hover{{color:#e53e3e;}}
  .meta-bar{{background:#fff;border-radius:8px;padding:12px 20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;gap:24px;align-items:center;flex-wrap:wrap;}}
  .meta-bar span{{color:#555;font-size:14px;}}
  .sync-panel{{background:#fff;border-radius:8px;padding:16px 20px;margin-top:32px;border:1px solid #ddd;}}
  .sync-panel h3{{margin:0 0 8px;color:#333;font-size:15px;}}
  .sync-panel p{{color:#666;font-size:13px;margin:0 0 10px;}}
  .sync-panel textarea{{width:100%;font-family:monospace;font-size:12px;border:1px solid #ddd;border-radius:4px;padding:8px;resize:vertical;}}
  .sync-btn{{background:#1a73e8;color:#fff;border:none;padding:7px 14px;border-radius:4px;cursor:pointer;font-size:13px;margin-top:8px;}}
</style>
</head>
<body>
<h1>🏠 RC-KB Home Finder &mdash; NYC</h1>
<div class="meta-bar">
  <span>📅 Last updated: {today}</span>
  <span>🏘 {len(all_listings)} total matches</span>
  <span>🆕 {len(new_listings)} new this week</span>
  <span>📍 Queens &amp; Bronx | ≤$900k | 2–3 bed | Garage required</span>
</div>
{new_section}
<section>
  <h2>All Active Matches ({len(all_listings)})</h2>
  <div class="grid">{(new_cards + older_cards) if (new_cards or older_cards) else "<p>No listings found.</p>"}</div>
</section>
<div class="sync-panel" id="sync-panel" style="display:none">
  <h3>⭐ Save Your Favourites</h3>
  <p>You've starred some listings. To make sure they never expire, copy the JSON below and paste it into <strong>favourites.json</strong> in your GitHub repo (click the pencil icon to edit it).</p>
  <textarea id="fav-json" rows="4" readonly></textarea>
  <button class="sync-btn" onclick="copyFavJson()">Copy to clipboard</button>
</div>
<div class="sync-panel">
  <h3>Sync Dismissed Listings (<span id="dismissed-count">0</span>)</h3>
  <p>Copy this JSON and paste it into <code>dismissed.json</code> in your GitHub repo to permanently prevent dismissed listings from reappearing.</p>
  <textarea id="dismissed-output" readonly rows="4" style="width:100%;font-size:12px;font-family:monospace;"></textarea>
  <button onclick="navigator.clipboard.writeText(document.getElementById('dismissed-output').value).then(()=>alert('Copied!'))">Copy to clipboard</button>
</div>
<script>
  const FAV_KEY = 'hf_favourites';
  function getFavs() {{ return JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); }}
  function saveFavs(favs) {{ localStorage.setItem(FAV_KEY, JSON.stringify(favs)); }}

  function toggleFav(id) {{
    let favs = getFavs();
    const idx = favs.indexOf(id);
    if (idx === -1) {{ favs.push(id); }} else {{ favs.splice(idx, 1); }}
    saveFavs(favs);
    renderFavs();
  }}

  function renderFavs() {{
    const favs = getFavs();
    document.querySelectorAll('.fav-btn').forEach(btn => {{
      const id = btn.closest('.card').dataset.id;
      btn.textContent = favs.includes(id) ? '⭐' : '☆';
      btn.classList.toggle('active', favs.includes(id));
    }});
    const panel = document.getElementById('sync-panel');
    if (favs.length > 0) {{
      panel.style.display = 'block';
      document.getElementById('fav-json').value = JSON.stringify({{"favourites": favs}}, null, 2);
    }} else {{
      panel.style.display = 'none';
    }}
  }}

  function copyFavJson() {{
    const ta = document.getElementById('fav-json');
    ta.select();
    document.execCommand('copy');
    event.target.textContent = 'Copied!';
    setTimeout(() => event.target.textContent = 'Copy to clipboard', 2000);
  }}

  function dismissListing(id) {{
    if (!confirm('Permanently remove this listing? It will never appear again.')) return;
    let dismissed = JSON.parse(localStorage.getItem('dismissed') || '[]');
    if (!dismissed.includes(id)) dismissed.push(id);
    localStorage.setItem('dismissed', JSON.stringify(dismissed));
    const card = document.getElementById('card-' + id);
    if (card) card.style.display = 'none';
    updateDismissedOutput();
  }}

  function updateDismissedOutput() {{
    const dismissed = JSON.parse(localStorage.getItem('dismissed') || '[]');
    const el = document.getElementById('dismissed-output');
    if (el) el.textContent = JSON.stringify({{"dismissed": dismissed}}, null, 2);
    const countEl = document.getElementById('dismissed-count');
    if (countEl) countEl.textContent = dismissed.length;
  }}

  document.addEventListener('DOMContentLoaded', function() {{
    renderFavs();
    const dismissed = JSON.parse(localStorage.getItem('dismissed') || '[]');
    dismissed.forEach(id => {{
      const card = document.getElementById('card-' + id);
      if (card) card.style.display = 'none';
    }});
    updateDismissedOutput();
  }});
</script>
</body></html>"""

def save_dashboard(all_listings: list, new_listing_ids: set, path: str = "docs/index.html"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(build_dashboard(all_listings, new_listing_ids))
    print(f"[dashboard] Saved to {path}")
