"""Signal model — strateji motorlarının ortak çıktısı."""

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
