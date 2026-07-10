"""CopyTrader orchestrator — market feed + sinyal kopyalama.

Tek asyncio process: market verisini tazele, stratejilerden sinyal topla,
risk kontrolunden gecir, pozisyonlari kopyala. Ayarlar runtime'da
DB'den okunuyor (dashboard hazir olunca canli degisebilecek).
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from . import config
from .api.binance_client import BinanceClient
from .strategies.funding_rate import FundingRateStrategy
from .strategies.technical import TechnicalStrategy
from .trading.paper_engine import PaperEngine
from .trading.risk import RiskManager

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("orchestrator")


class MarketSnapshot:
    def __init__(self):
        self.symbols: list[str] = []
        self.prices: dict[str, float] = {}
        self.funding_rates: dict[str, float] = {}
        self.klines: dict[str, list] = {}
        self.last_update: str = ""
        self.api_ok: bool = False


class CopyTraderApp:
    def __init__(self):
        config.init_db()
        self.settings = config.SettingsStore()
        self.market = MarketSnapshot()
        self.binance = BinanceClient()
        self.engine = PaperEngine(config.DB_PATH)
        self.risk = RiskManager(self.settings)
        self.strategies = {
            "funding": FundingRateStrategy(self.settings),
            "technical": TechnicalStrategy(self.settings),
        }
        self.state = {
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "scan_count": 0,
            "last_scan": "",
        }

    async def market_loop(self) -> None:
        while True:
            try:
                self.market.symbols = self.settings.symbols()
                prices = await self.binance.get_all_prices()
                self.market.prices = {k: v for k, v in prices.items() if k in self.market.symbols}
                self.market.funding_rates = await self.binance.get_funding_rates()
                self.market.api_ok = True
                self.market.last_update = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                self.market.api_ok = False
                logger.error("Market guncelleme hatasi: %s", e)
            await asyncio.sleep(config.PRICE_REFRESH_SEC)

    async def refresh_klines(self) -> None:
        for symbol in self.market.symbols:
            try:
                self.market.klines[symbol] = await self.binance.get_klines(symbol, "1h", 120)
            except Exception:
                pass

    async def scan_loop(self) -> None:
        await asyncio.sleep(2)
        while True:
            self.state["scan_count"] += 1
            self.state["last_scan"] = datetime.now(timezone.utc).isoformat()
            try:
                await self.refresh_klines()
                await self.scan_once()
            except Exception as e:
                logger.exception("Tarama hatasi: %s", e)
            await asyncio.sleep(int(self.settings.get_typed("scan_interval_sec") or 15))

    async def scan_once(self) -> None:
        signals = []
        for name, strat in self.strategies.items():
            if self.settings.strategy_enabled(name):
                signals.extend(await strat.scan(self.market))

        for s in signals:
            price = self.market.prices.get(s.symbol, s.price)
            if not price:
                continue
            if self.engine.open_position_for(s.symbol, s.strategy):
                continue
            size = self.risk.size_position(self.engine.equity(self.market.prices))
            ok, reason = self.risk.can_open(
                equity=self.engine.equity(self.market.prices),
                open_count=self.engine.position_count(),
                today_loss=0.0,
                size_usd=size,
            )
            if not ok:
                logger.info("Reddedildi %s %s: %s", s.symbol, s.side, reason)
                continue
            pos_id = self.engine.open_position(
                s.symbol, s.side, s.strategy, size, price,
                self.market.funding_rates.get(s.symbol, 0.0), s.reason)
            logger.info("Acildi #%s %s %s ($%.2f) @ %.4f", pos_id, s.symbol, s.side, size, price)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    app = CopyTraderApp()
    await asyncio.gather(app.market_loop(), app.scan_loop())


if __name__ == "__main__":
    asyncio.run(main())
