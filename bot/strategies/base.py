"""Strategy taban sınıfı ve Signal modeli.

Strateji = "master": canlı piyasa verisinden copy sinyali (LONG/SHORT/FLAT)
üretir. Motor ("copier") bu sinyalleri pozisyonlara çevirir.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Signal:
    symbol: str
    side: str                 # LONG | SHORT | FLAT
    strategy: str
    price: float = 0.0
    reason: str = ""
    confidence: float = 0.0   # 0..1
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def __bool__(self) -> bool:
        return self.side in ("LONG", "SHORT")


class Strategy(ABC):
    name: str = "base"
    label: str = "Base"

    def __init__(self, settings_store):
        self.settings = settings_store

    @abstractmethod
    async def scan(self, market) -> list[Signal]:
        """Canlı market anlık görüntüsünden sinyal üret."""
