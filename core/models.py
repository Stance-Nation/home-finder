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
