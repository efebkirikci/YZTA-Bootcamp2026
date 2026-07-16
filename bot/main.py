"""CopyTrader orchestrator — market feed + sinyal kopyalama + dashboard."""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from . import config
from .api.binance_client import BinanceClient
from .dashboard.server import create_dashboard
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
        self.tickers: dict[str, dict] = {}
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
            "last_error": "",
            "latest_signals": [],
            "events": [],
        }

    def push_event(self, kind: str, text: str, **extra) -> None:
        ev = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "kind": kind, "text": text, **extra}
        self.state["events"].append(ev)
        self.state["events"] = self.state["events"][-100:]
        logger.info("[%s] %s", kind, text)

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
                self.state["last_error"] = f"market: {e}"
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
                closed = self.engine.check_exits(self.market.prices)
                for c in closed:
                    self.push_event("close", f"{c.get('symbol')} kapatildi ({c.get('reason')})")
                self.engine.process_funding_payments(self.market.funding_rates)
                self.engine.record_equity_point(self.engine.equity(self.market.prices))
            except Exception as e:
                self.state["last_error"] = f"scan: {e}"
                logger.exception("Tarama hatasi: %s", e)
            await asyncio.sleep(int(self.settings.get_typed("scan_interval_sec") or 15))

    async def funding_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                paid = self.engine.process_funding_payments(self.market.funding_rates)
                if paid:
                    self.push_event("funding", f"{paid} funding odemesi islendi")
            except Exception as e:
                logger.error("Funding isleme hatasi: %s", e)

    def _record_signal(self, s) -> None:
        self.engine._conn.execute(
            "INSERT INTO signals (symbol, side, strategy, price, reason) VALUES (?,?,?,?,?)",
            (s.symbol, s.side, s.strategy, s.price, s.reason))
        self.engine._conn.commit()

    async def scan_once(self) -> None:
        signals = []
        for name, strat in self.strategies.items():
            if self.settings.strategy_enabled(name):
                signals.extend(await strat.scan(self.market))

        for s in signals:
            self._record_signal(s)
            price = self.market.prices.get(s.symbol, s.price)
            if not price:
                continue
            if self.engine.open_position_for(s.symbol, s.strategy):
                continue
            size = self.risk.size_position(self.engine.equity(self.market.prices))
            ok, reason = self.risk.can_open(
                equity=self.engine.equity(self.market.prices),
                open_count=self.engine.position_count(),
                today_loss=abs(self.engine.today_realized_pnl()),
                size_usd=size,
            )
            if not ok:
                self.push_event("reject", f"{s.symbol} {s.side}: {reason}")
                continue
            pos_id = self.engine.open_position(
                s.symbol, s.side, s.strategy, size, price,
                self.market.funding_rates.get(s.symbol, 0.0), s.reason)
            self.push_event("open", f"{s.symbol} {s.side} acildi (${size:.2f}, {s.strategy}) @ {price:.4f}")
            self.engine._conn.execute(
                "UPDATE signals SET executed=1 WHERE symbol=? AND side=? AND strategy=? AND executed=0",
                (s.symbol, s.side, s.strategy))
            self.engine._conn.commit()

        self.state["latest_signals"] = [
            {"symbol": s.symbol, "side": s.side, "strategy": s.strategy,
             "reason": s.reason, "confidence": s.confidence, "price": s.price,
             "created_at": s.created_at}
            for s in signals[-15:]
        ]

    # ── dashboard verisi ──────────────────────────────────────────────
    def dashboard_state(self) -> dict:
        prices = self.market.prices
        equity = self.engine.equity(prices)
        open_positions = [
            {**dict(p),
             "unrealized_pnl": round(
                 self.engine._pnl_for(p, prices.get(p["symbol"], p["entry_price"])), 2),
             "funding_collected": round(self.engine.funding_collected(p["id"]), 4)}
            for p in self.engine.open_positions()
        ]
        return {
            "meta": {
                "started_at": self.state["started_at"],
                "mode": config.TRADING_MODE,
                "scan_count": self.state["scan_count"],
                "last_scan": self.state["last_scan"],
                "last_error": self.state["last_error"],
                "api_ok": self.market.api_ok,
                "last_update": self.market.last_update,
            },
            "portfolio": {
                "initial_capital": self.engine.initial_capital(),
                "equity": round(equity, 2),
                "realized_pnl": round(self.engine.realized_pnl(), 2),
                "unrealized_pnl": round(self.engine.unrealized_pnl(prices), 2),
                "total_funding_collected": round(self.engine.total_funding_collected(), 4),
                "open_positions": self.engine.position_count(),
                "today_pnl": round(self.engine.today_realized_pnl(), 2),
            },
            "market": {
                "rows": [
                    {"symbol": s, "price": prices.get(s),
                     "funding_rate": self.market.funding_rates.get(s)}
                    for s in self.market.symbols
                ],
                "last_update": self.market.last_update,
                "api_ok": self.market.api_ok,
            },
            "positions": open_positions,
            "latest_signals": self.state["latest_signals"],
            "events": self.state["events"][-30:],
            "equity_curve": self.engine.equity_curve(300),
            "settings": self.settings.all(),
            "active_strategy": self.settings.active_strategy(),
            "strategies": {
                "funding": {"label": "Funding Rate", "enabled": self.settings.strategy_enabled("funding")},
                "technical": {"label": "Teknik (EMA+RSI+MACD)", "enabled": self.settings.strategy_enabled("technical")},
            },
        }


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    app = CopyTraderApp()
    dashboard = create_dashboard(app)

    async def _serve() -> None:
        cfg = uvicorn.Config(dashboard, host=config.HOST, port=config.PORT, log_level="warning")
        server = uvicorn.Server(cfg)
        await server.serve()

    try:
        await asyncio.gather(app.market_loop(), app.scan_loop(), app.funding_loop(), _serve())
    finally:
        await app.binance.close()


if __name__ == "__main__":
    asyncio.run(main())
