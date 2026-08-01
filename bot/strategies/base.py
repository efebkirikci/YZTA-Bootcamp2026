"""Strategy base classes and the Signal model.

A strategy is the "master" signal producer: it reads live market data and
produces copy signals (LONG/SHORT/FLAT). The engine (copier) then mirrors
those signals into paper or live positions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Signal:
    symbol: str
    side: str            # LONG | SHORT | FLAT
    strategy: str
    price: float = 0.0
    reason: str = ""
    confidence: float = 0.0      # 0..1
    meta: dict = field(default_factory=dict)
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
    async def scan(self, market: "MarketSnapshot") -> list[Signal]:
        """Produce copy signals from the latest market snapshot."""

    def _sizing_hint(self, size_usd: float | None) -> float | None:
        """Strategy-level position size override (None = use risk defaults)."""
        return size_usd
