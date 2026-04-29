import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
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
            <a href="{listing.listing_url}" style="background:#1a73e8;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:14px;margin-right:8px;">View Listing</a>
            <a href="{_maps_url(listing.address)}" style="background:#1e6b3e;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;font-size:14px;">🚇 Transit to Flatiron</a>
            <div style="color:#888;font-size:12px;margin-top:6px;">via {listing.source}</div>
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
    if not password:
        raise ValueError(
            "GMAIL_APP_PASSWORD environment variable is not set. "
            "Generate a Gmail App Password at myaccount.google.com → Security → App passwords."
        )
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
