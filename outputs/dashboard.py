import json as _json
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

def _card_html(listing: Listing, is_new: bool = False) -> str:
    flags = []
    if listing.flip_flag:
        flags.append('<span class="flag flip">&#9888; Likely Flip</span>')
    if listing.commute_flag:
        flags.append('<span class="flag commute">&#9888; Long Commute</span>')
    if listing.property_type == "land":
        flags.append('<span class="flag garage">No garage (vacant lot)</span>')
    elif not listing.garage_confirmed:
        flags.append('<span class="flag garage">&#9888; Garage unconfirmed</span>')
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
    new_badge = '<span class="badge-new">NEW</span>' if is_new else ""
    transit = f"{listing.transit_minutes} min" if listing.transit_minutes else "N/A"
    score_pct = int((listing.value_score or 0) * 100)
    if listing.photo_url:
        photo_html = (
            f'<div class="card-photo-wrap">'
            f'<img class="card-photo" src="{listing.photo_url}" '
            f'loading="lazy" '
            f'onerror="this.parentElement.classList.add(\'no-photo\')" '
            f'alt=""/>'
            f'</div>'
        )
    else:
        photo_html = '<div class="card-photo-wrap no-photo"></div>'
    lid = listing.listing_id.replace('"', '')
    dismiss_btn = f'<button class="dismiss-btn" onclick="dismissListing(\'{lid}\')" title="Permanently remove this listing">&#x2715;</button>'
    neighborhood = (listing.neighborhood or "").replace('"', '')
    borough = (listing.borough or "").replace('"', '')
    return f"""
    <div class="card" id="card-{lid}" data-id="{lid}" data-neighborhood="{neighborhood}" data-borough="{borough}">
        {new_badge}
        {badges}
        <button class="fav-btn" onclick="toggleFav('{lid}')" title="Favourite this listing">&#9734;</button>
        {dismiss_btn}
        {photo_html}
        <div class="card-address">{listing.address}</div>
        <div class="card-meta">{listing.neighborhood} &middot; {listing.borough}</div>
        <div class="card-price">${listing.price:,}</div>
        <div class="card-details">&#x1F6CF; {listing.bedrooms} bed &nbsp;|&nbsp; &#x1F697; Garage &#x2713; &nbsp;|&nbsp; &#x1F687; {transit}</div>
        <div class="card-score">Value score: {score_pct}/100</div>
        <div class="card-flags">{flag_html}</div>
        <a class="card-link" href="{listing.listing_url}" target="_blank">View Listing</a>
        <a class="card-link transit-link" href="{_maps_url(listing.address)}" target="_blank">&#x1F687; Transit to Flatiron</a>
        <div class="card-source">via {listing.source}</div>
        <div class="card-seen">First seen: {listing.date_first_seen}</div>
    </div>"""


def _listing_to_json_obj(listing: Listing) -> dict:
    """Serialise a Listing to a plain dict suitable for embedding in JSON."""
    lid = listing.listing_id.replace('"', '')
    return {
        "listing_id": lid,
        "address": listing.address,
        "neighborhood": listing.neighborhood,
        "borough": listing.borough,
        "price": listing.price,
        "bedrooms": listing.bedrooms,
        "garage_confirmed": listing.garage_confirmed,
        "transit_minutes": listing.transit_minutes,
        "value_score": listing.value_score,
        "listing_url": listing.listing_url,
        "photo_url": listing.photo_url,
        "source": listing.source,
        "flip_flag": listing.flip_flag,
        "commute_flag": listing.commute_flag,
        "property_type": listing.property_type,
        "date_first_seen": listing.date_first_seen,
    }


def build_dashboard(all_listings: list, new_listing_ids: set) -> str:
    today = date.today().strftime("%B %d, %Y")
    new_listings = [l for l in all_listings if l.listing_id in new_listing_ids]
    older_listings = [l for l in all_listings if l.listing_id not in new_listing_ids]
    new_cards = "".join(_card_html(l, is_new=True) for l in new_listings)
    older_cards = "".join(_card_html(l, is_new=False) for l in older_listings)

    new_section = f"""
    <section>
        <h2>New Today ({len(new_listings)})</h2>
        <div class="grid">{new_cards if new_cards else "<p>No new listings this week.</p>"}</div>
    </section>""" if new_listings else ""

    # Build filter bar from available boroughs and neighbourhoods
    boroughs = sorted(set(l.borough for l in all_listings if l.borough))
    neighborhoods = sorted(set(l.neighborhood for l in all_listings if l.neighborhood))

    borough_btns = "".join(
        f'<button class="filter-btn borough" onclick="filterBy(\'{b}\', true)">{b}</button>'
        for b in boroughs
    )
    neighborhood_btns = "".join(
        f'<button class="filter-btn" onclick="filterBy(\'{n}\', false)">{n}</button>'
        for n in neighborhoods
    )
    filter_bar = f"""
<div class="filter-bar">
  <span class="filter-label">Filter:</span>
  <button class="filter-btn active" onclick="filterBy(null)">All</button>
  {borough_btns}
  {neighborhood_btns}
</div>"""

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
  .card-photo-wrap{{width:100%;height:180px;border-radius:6px;margin-bottom:10px;overflow:hidden;background:#f0f0f0;}}
  .card-photo-wrap.no-photo{{background:#e8e8e8;display:flex;align-items:center;justify-content:center;}}
  .card-photo-wrap.no-photo::after{{content:'No photo';color:#bbb;font-size:13px;}}
  .card-photo{{width:100%;height:100%;object-fit:cover;object-position:center 30%;display:block;}}
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
  .fav-page-link{{display:inline-block;background:#f5a623;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:bold;}}
  .sync-panel{{background:#fff;border-radius:8px;padding:16px 20px;margin-top:32px;border:1px solid #ddd;}}
  .sync-panel h3{{margin:0 0 8px;color:#333;font-size:15px;}}
  .sync-panel p{{color:#666;font-size:13px;margin:0 0 10px;}}
  .sync-panel textarea{{width:100%;font-family:monospace;font-size:12px;border:1px solid #ddd;border-radius:4px;padding:8px;resize:vertical;}}
  .sync-btn{{background:#1a73e8;color:#fff;border:none;padding:7px 14px;border-radius:4px;cursor:pointer;font-size:13px;margin-top:8px;}}
  .filter-bar{{background:#fff;border-radius:8px;padding:12px 16px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;flex-wrap:wrap;gap:8px;align-items:center;}}
  .filter-label{{color:#666;font-size:13px;font-weight:bold;margin-right:4px;}}
  .filter-btn{{padding:5px 12px;border-radius:20px;border:1px solid #ddd;background:#fff;cursor:pointer;font-size:12px;color:#555;}}
  .filter-btn.active{{background:#1a73e8;color:#fff;border-color:#1a73e8;}}
  .filter-btn.borough{{font-weight:bold;}}
</style>
</head>
<body>
<h1>&#x1F3E0; RC-KB Home Finder &mdash; NYC</h1>
<div class="meta-bar">
  <span>&#x1F4C5; Last updated: {today}</span>
  <span>&#x1F3D8; {len(all_listings)} total matches</span>
  <span>&#x1F195; {len(new_listings)} new today</span>
  <span>&#x1F4CD; Queens &amp; Bronx | &le;$900k | 2&ndash;3 bed | Garage required</span>
  <a class="fav-page-link" href="favourites.html">&#11088; View Favourites</a>
</div>
{filter_bar}
{new_section}
<section>
  <h2>All Active Matches ({len(all_listings)})</h2>
  <div class="grid">{(new_cards + older_cards) if (new_cards or older_cards) else "<p>No listings found.</p>"}</div>
</section>
<div class="sync-panel" id="sync-panel" style="display:none">
  <h3>&#11088; Save Your Favourites</h3>
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
      btn.textContent = favs.includes(id) ? '⭐' : '✴';
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

  function filterBy(value, isBoroughFilter) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {{
      if (!value) {{
        card.style.display = '';
      }} else {{
        const match = isBoroughFilter
          ? card.dataset.borough === value
          : card.dataset.neighborhood === value;
        card.style.display = match ? '' : 'none';
      }}
    }});
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


def save_favourites_page(all_listings: list, new_listing_ids: set, path: str = "docs/favourites.html"):
    """Generate a standalone favourites page that reads from localStorage."""
    import os
    listings_json = _json.dumps([_listing_to_json_obj(l) for l in all_listings], indent=None)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>RC-KB Home Finder — Favourites</title>
<style>
  body{font-family:sans-serif;max-width:1100px;margin:auto;padding:20px;background:#f5f5f5;}
  h1{color:#1a1a1a;} h2{color:#333;border-bottom:2px solid #ddd;padding-bottom:6px;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px;}
  .card{background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.08);position:relative;}
  .card-photo-wrap{width:100%;height:180px;border-radius:6px;margin-bottom:10px;overflow:hidden;background:#f0f0f0;}
  .card-photo-wrap.no-photo{background:#e8e8e8;display:flex;align-items:center;justify-content:center;}
  .card-photo-wrap.no-photo::after{content:'No photo';color:#bbb;font-size:13px;}
  .card-photo{width:100%;height:100%;object-fit:cover;object-position:center 30%;display:block;}
  .card-address{font-size:16px;font-weight:bold;margin-bottom:4px;padding-right:36px;}
  .card-meta{color:#888;font-size:13px;margin-bottom:6px;}
  .card-price{font-size:22px;color:#2c7a2c;font-weight:bold;margin-bottom:6px;}
  .card-details{color:#444;font-size:13px;margin-bottom:4px;}
  .card-score{color:#555;font-size:13px;margin-bottom:6px;}
  .card-flags{margin-bottom:8px;}
  .card-seen{color:#bbb;font-size:11px;margin-top:6px;}
  .flag{font-size:12px;font-weight:bold;padding:2px 6px;border-radius:4px;margin-right:4px;}
  .flag.flip{background:#ffe0cc;color:#a03000;}
  .flag.commute{background:#fff3cd;color:#856404;}
  .flag.garage{background:#e8f0fe;color:#1a56db;}
  .card-link{display:inline-block;background:#1a73e8;color:#fff;padding:7px 14px;border-radius:4px;text-decoration:none;font-size:13px;margin-right:6px;margin-bottom:6px;}
  .transit-link{background:#1e6b3e;}
  .card-source{color:#aaa;font-size:11px;margin-top:6px;}
  .badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:bold;margin-right:4px;margin-bottom:4px;}
  .badge-type{background:#6b7280;color:#fff;}
  .fav-btn{position:absolute;top:10px;right:10px;background:none;border:none;font-size:22px;cursor:pointer;line-height:1;padding:2px;color:#f5a623;}
  .meta-bar{background:#fff;border-radius:8px;padding:12px 20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.06);display:flex;gap:24px;align-items:center;flex-wrap:wrap;}
  .meta-bar span{color:#555;font-size:14px;}
  .back-link{display:inline-block;background:#6b7280;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:bold;}
  .empty-msg{color:#888;font-size:15px;padding:40px 0;text-align:center;}
</style>
</head>
<body>
<h1>&#11088; RC-KB Home Finder &mdash; Favourites</h1>
<div class="meta-bar">
  <span id="fav-count">Loading...</span>
  <a class="back-link" href="index.html">&#8592; Back to all listings</a>
</div>
<div id="fav-grid" class="grid"></div>
<script>
const FAV_KEY = 'hf_favourites';
const DEST = '200 5th Ave, New York, NY 10010';
""" + f"const ALL_LISTINGS = {listings_json};" + """

function mapsUrl(address) {
  return 'https://www.google.com/maps/dir/?api=1&origin=' + encodeURIComponent(address) +
    '&destination=' + encodeURIComponent(DEST) + '&travelmode=transit';
}

function typeLabel(pt) {
  const map = {single_family:'Detached',multi_family:'Multi-Family',townhouse:'Townhouse',land:'Vacant Lot'};
  return map[pt] || (pt ? pt.replace(/_/g,' ') : '');
}

function buildCard(l) {
  const transit = l.transit_minutes ? l.transit_minutes + ' min' : 'N/A';
  const scorePct = Math.round((l.value_score || 0) * 100);
  let flags = '';
  if (l.flip_flag) flags += '<span class="flag flip">&#9888; Likely Flip</span> ';
  if (l.commute_flag) flags += '<span class="flag commute">&#9888; Long Commute</span> ';
  if (l.property_type === 'land') flags += '<span class="flag garage">No garage (vacant lot)</span>';
  else if (!l.garage_confirmed) flags += '<span class="flag garage">&#9888; Garage unconfirmed</span>';

  let photo = '<div class="card-photo-wrap no-photo"></div>';
  if (l.photo_url) {
    photo = '<div class="card-photo-wrap"><img class="card-photo" src="' + l.photo_url +
      '" loading="lazy" onerror="this.parentElement.classList.add(\'no-photo\')" alt=""/></div>';
  }

  let badge = '';
  const lbl = typeLabel(l.property_type);
  if (lbl) badge = '<span class="badge badge-type">' + lbl + '</span>';

  const lid = l.listing_id.replace(/"/g, '');
  return '<div class="card" id="card-' + lid + '" data-id="' + lid + '">' +
    badge +
    '<button class="fav-btn" onclick="removeFav(\'' + lid + '\')" title="Remove from favourites">&#11088;</button>' +
    photo +
    '<div class="card-address">' + l.address + '</div>' +
    '<div class="card-meta">' + (l.neighborhood || '') + ' &middot; ' + (l.borough || '') + '</div>' +
    '<div class="card-price">$' + (l.price || 0).toLocaleString() + '</div>' +
    '<div class="card-details">&#x1F6CF; ' + (l.bedrooms || '?') + ' bed &nbsp;|&nbsp; &#x1F687; ' + transit + '</div>' +
    '<div class="card-score">Value score: ' + scorePct + '/100</div>' +
    '<div class="card-flags">' + flags + '</div>' +
    '<a class="card-link" href="' + l.listing_url + '" target="_blank">View Listing</a> ' +
    '<a class="card-link transit-link" href="' + mapsUrl(l.address) + '" target="_blank">&#x1F687; Transit to Flatiron</a>' +
    '<div class="card-source">via ' + (l.source || '') + '</div>' +
    '<div class="card-seen">First seen: ' + (l.date_first_seen || '') + '</div>' +
    '</div>';
}

function getFavs() { return JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); }
function saveFavs(favs) { localStorage.setItem(FAV_KEY, JSON.stringify(favs)); }

function removeFav(id) {
  let favs = getFavs().filter(f => f !== id);
  saveFavs(favs);
  renderFavs();
}

function renderFavs() {
  const favs = getFavs();
  const byId = {};
  ALL_LISTINGS.forEach(l => { byId[l.listing_id] = l; });
  const grid = document.getElementById('fav-grid');
  const countEl = document.getElementById('fav-count');
  const favListings = favs.map(id => byId[id]).filter(Boolean);
  countEl.textContent = favListings.length + ' favourite' + (favListings.length !== 1 ? 's' : '');
  if (favListings.length === 0) {
    grid.innerHTML = '<p class="empty-msg">No favourites yet. Star listings on the <a href="index.html">main page</a>.</p>';
  } else {
    grid.innerHTML = favListings.map(buildCard).join('');
  }
}

document.addEventListener('DOMContentLoaded', renderFavs);
</script>
</body></html>"""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(html)
    print(f"[dashboard] Favourites page saved to {path}")


def save_dashboard(all_listings: list, new_listing_ids: set, path: str = "docs/index.html"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(build_dashboard(all_listings, new_listing_ids))
    print(f"[dashboard] Saved to {path}")
    save_favourites_page(all_listings, new_listing_ids)
