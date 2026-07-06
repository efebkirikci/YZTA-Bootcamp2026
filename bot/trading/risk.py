"""Risk yönetimi — pozisyon büyüklüğü ve portföy limitleri (v1).

Kurallar basit başlar; dashboard ayarları geldiğinde runtime'da
değiştirilebilir hale gelecek.
"""

import logging

logger = logging.getLogger("risk")

MAX_OPEN_POSITIONS = 3
MAX_POSITION_SIZE_USD = 25.0
MAX_PORTFOLIO_RISK_PCT = 50.0
MAX_DAILY_LOSS_USD = 20.0


class RiskManager:
    def can_open(self, equity: float, open_count: int, today_loss: float,
                 size_usd: float) -> tuple[bool, str]:
        if open_count >= MAX_OPEN_POSITIONS:
            return False, f"Açık pozisyon limiti ({MAX_OPEN_POSITIONS}) doldu"
        if size_usd > MAX_POSITION_SIZE_USD:
            return False, f"Pozisyon boyutu ${size_usd:.2f} limiti aşıyor"
        deployed = MAX_POSITION_SIZE_USD * open_count
        limit_usd = equity * MAX_PORTFOLIO_RISK_PCT / 100.0
        if deployed + size_usd > limit_usd:
            return False, f"Portföy risk limiti aşıldı"
        if today_loss >= MAX_DAILY_LOSS_USD:
            return False, "Günlük kayıp limiti aşıldı"
        return True, "ok"

    def size_position(self, equity: float, default_size: float | None = None) -> float:
        max_size = MAX_POSITION_SIZE_USD
        base = default_size if default_size and default_size > 0 else max_size
        return min(base, max_size)
