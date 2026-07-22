"""Live engine — ayni paper ledger uzerinde gercek Binance emirleri.

TRADING_MODE=live + API key verildiginde aktif olur. Her pozisyon yine
SQLite'a kaydedilir (denetim + dashboard), ama acilis/kapanis gercek
futures emirleriyle yapilir.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .paper_engine import PaperEngine

logger = logging.getLogger("live")


class LiveEngine(PaperEngine):
    def __init__(self, db_path: Path, binance, initial_capital: float = 1000.0):
        super().__init__(db_path, initial_capital)
        self.binance = binance

    async def open_position_live(self, symbol: str, side: str, strategy: str,
                                 size_usd: float, price: float,
                                 funding_rate: float = 0.0, reason: str = "") -> int | None:
        try:
            balance = await self.binance.get_futures_balance()
            if balance <= 0:
                logger.warning("Futures cuzdaninda USDT yok — live acilis iptal")
                return None
            qty = self.binance.qty_from_notional(size_usd, price)
            order_side = "BUY" if side == "LONG" else "SELL"
            order = await self.binance.open_market_order(symbol, order_side, qty)
            logger.info("LIVE acilis %s %s qty=%s orderId=%s",
                        symbol, order_side, qty, order.get("orderId"))
        except Exception as e:  # noqa: BLE001
            logger.error("LIVE acilis basarisiz: %s", e)
            return None
        return self.open_position(symbol, side, strategy, size_usd, price,
                                  funding_rate, reason)

    async def close_position_live(self, position_id: int, price: float,
                                  reason: str = "manual") -> dict:
        p = self._conn.execute(
            "SELECT * FROM paper_positions WHERE id=?", (position_id,)).fetchone()
        if p is None or p["status"] == "closed":
            return {"ok": False, "error": "pozisyon yok / zaten kapali"}
        try:
            qty = self.binance.qty_from_notional(p["size_usd"], price)
            order_side = "SELL" if p["side"] == "LONG" else "BUY"
            order = await self.binance.close_market_order(p["symbol"], order_side, qty)
            logger.info("LIVE kapanis %s %s qty=%s orderId=%s",
                        p["symbol"], order_side, qty, order.get("orderId"))
        except Exception as e:  # noqa: BLE001
            logger.error("LIVE kapanis basarisiz: %s", e)
            return {"ok": False, "error": f"kapanis emri hatasi: {e}"}
        return self.close_position(position_id, price, reason)
