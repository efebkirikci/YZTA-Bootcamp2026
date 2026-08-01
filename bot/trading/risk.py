"""Risk manager — position sizing and portfolio guards.

All limits are runtime settings editable from the dashboard. Checks:
- max open positions
- max position size (USD)
- max portfolio risk (% of equity deployed)
- max daily loss (USD) — circuit breaker
"""

from __future__ import annotations

import logging

logger = logging.getLogger("risk")


class RiskManager:
    def __init__(self, settings):
        self.settings = settings

    def can_open(self, equity: float, open_count: int, today_loss: float,
                 size_usd: float) -> tuple[bool, str]:
        max_positions = int(self.settings.get_typed("max_open_positions") or 3)
        max_size = float(self.settings.get_typed("max_position_size_usd") or 25)
        risk_pct = float(self.settings.get_typed("max_portfolio_risk_pct") or 50)
        max_daily_loss = float(self.settings.get_typed("max_daily_loss_usd") or 20)

        if open_count >= max_positions:
            return False, f"Açık pozisyon limiti ({max_positions}) doldu"
        if size_usd > max_size:
            return False, f"Pozisyon boyutu ${size_usd:.2f} limiti aşıyor (${max_size:.2f})"
        deployed = max_size * open_count  # worst case
        limit_usd = equity * risk_pct / 100.0
        if deployed + size_usd > limit_usd:
            return False, (
                f"Portföy risk limiti aşıldı: ${deployed + size_usd:.2f} "
                f"> ${limit_usd:.2f} (%{risk_pct:.0f} × ${equity:.2f})"
            )
        if today_loss >= max_daily_loss:
            return False, f"Günlük kayıp limiti aşıldı (${today_loss:.2f} ≥ ${max_daily_loss:.2f})"
        return True, "ok"

    def size_position(self, equity: float, default_size: float | None = None) -> float:
        """Clamp a position size to the configured maximum."""
        max_size = float(self.settings.get_typed("max_position_size_usd") or 25)
        base = default_size if default_size and default_size > 0 else max_size
        return min(base, max_size)
