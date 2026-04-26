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
