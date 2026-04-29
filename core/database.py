import sqlite3
from pathlib import Path
from datetime import date, timedelta
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
                garage_confirmed INTEGER,
                source TEXT,
                listing_url TEXT,
                photo_url TEXT,
                transit_minutes INTEGER,
                flip_flag INTEGER,
                commute_flag INTEGER,
                value_score REAL,
                date_first_seen TEXT,
                is_favourite INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()
        for col, definition in [
            ("is_favourite", "INTEGER DEFAULT 0"),
            ("garage_confirmed", "INTEGER DEFAULT 0"),
            ("property_type", "TEXT DEFAULT ''"),
            ("hoa_fee", "REAL"),
        ]:
            try:
                self.conn.execute(f"ALTER TABLE seen_listings ADD COLUMN {col} {definition}")
                self.conn.commit()
            except Exception:
                pass  # column already exists

    def is_seen(self, listing: Listing) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM seen_listings WHERE listing_id = ?",
            (listing.listing_id,)
        ).fetchone()
        return row is not None

    def save(self, listing: Listing):
        d = listing.to_dict()
        d.setdefault("is_favourite", 0)
        self.conn.execute("""
            INSERT OR IGNORE INTO seen_listings
            (listing_id, address, neighborhood, borough, price, bedrooms,
             garage, garage_confirmed, source, listing_url, photo_url, transit_minutes,
             flip_flag, commute_flag, value_score, date_first_seen, is_favourite,
             property_type, hoa_fee)
            VALUES
            (:listing_id, :address, :neighborhood, :borough, :price, :bedrooms,
             :garage, :garage_confirmed, :source, :listing_url, :photo_url, :transit_minutes,
             :flip_flag, :commute_flag, :value_score, :date_first_seen, :is_favourite,
             :property_type, :hoa_fee)
        """, d)
        self.conn.commit()

    def cleanup_expired(self, days: int = 7, favourite_ids: set = None):
        favourite_ids = favourite_ids or set()
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        # Mark known favourites in DB
        for fid in favourite_ids:
            self.conn.execute(
                "UPDATE seen_listings SET is_favourite = 1 WHERE listing_id = ?", (fid,)
            )
        # Delete expired non-favourites
        self.conn.execute(
            "DELETE FROM seen_listings WHERE date_first_seen < ? AND is_favourite = 0",
            (cutoff,)
        )
        self.conn.commit()

    def remove_dismissed(self, dismissed_ids: set):
        for did in dismissed_ids:
            self.conn.execute("DELETE FROM seen_listings WHERE listing_id = ?", (did,))
        self.conn.commit()

    def filter_new(self, listings: list) -> list:
        return [l for l in listings if not self.is_seen(l)]

    def get_normalized_addresses(self) -> set:
        import re
        rows = self.conn.execute("SELECT address FROM seen_listings").fetchall()
        result = set()
        for row in rows:
            addr = row["address"] or ""
            part = addr.split(",")[0].lower()
            part = re.sub(r"[^a-z0-9\s]", "", part)
            normalized = " ".join(part.split())
            if normalized:
                result.add(normalized)
        return result

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
                garage_confirmed=bool(row["garage_confirmed"]),
                source=row["source"],
                listing_url=row["listing_url"],
                photo_url=row["photo_url"],
                transit_minutes=row["transit_minutes"],
                flip_flag=bool(row["flip_flag"]),
                commute_flag=bool(row["commute_flag"]),
                value_score=row["value_score"],
                date_first_seen=row["date_first_seen"],
                property_type=row["property_type"] or "",
                hoa_fee=row["hoa_fee"],
            )
            results.append(listing)
        return results
