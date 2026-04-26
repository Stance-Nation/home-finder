import sqlite3
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
