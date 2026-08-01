"""CopyTrader orchestrator — market feed, signal engine (copy), execution.

One asyncio process runs three loops + the FastAPI dashboard:
  1. market loop   — refresh public Binance prices/funding/klines (3s)
  2. scan loop     — run active strategies -> copy signals -> risk -> execute
  3. funding loop  — credit fixed 8h funding slots for open positions
  4. dashboard     — FastAPI + WebSocket on the same port (localhost)

The dashboard reads live state from `self.state` (a plain dict) — no
locking needed beyond the GIL for the small payloads we share.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from . import config
from .api.binance_client import BinanceClient
from .brain.ai_analyzer import AIAnalyzer
from .dashboard.server import create_dashboard
from .strategies.funding_rate import FundingRateStrategy
from .strategies.technical import TechnicalStrategy
from .trading.live_engine import LiveEngine
from .trading.paper_engine import PaperEngine
from .trading.risk import RiskManager

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("orchestrator")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MarketSnapshot:
    """Latest public market data, refreshed by the market loop."""

    def __init__(self):
        self.symbols: list[str] = []
        self.prices: dict[str, float] = {}
        self.funding_rates: dict[str, float] = {}
        self.klines: dict[str, list] = {}
        self.tickers: dict[str, dict] = {}
        self.last_update: str = ""
        self.api_ok: bool = False

    def to_dict(self, symbols: list[str]) -> dict:
        rows = []
        for s in symbols:
            t = self.tickers.get(s, {})
            rows.append({
                "symbol": s,
                "price": self.prices.get(s),
                "change_pct": t.get("change_pct"),
                "volume": t.get("volume"),
                "high": t.get("high"),
                "low": t.get("low"),
                "funding_rate": self.funding_rates.get(s),
            })
        return {
            "rows": rows,
            "last_update": self.last_update,
            "api_ok": self.api_ok,
        }


class CopyTraderApp:
    def __init__(self):
        config.init_db()
        self.settings = config.SettingsStore()
        self.state: dict = {
            "started_at": _now_iso(),
            "scan_count": 0,
            "last_scan": "",
            "last_error": "",
            "mode": config.TRADING_MODE,
            "ai_enabled": config.AI_ENABLED,
            "latest_signals": [],
            "events": [],
        }
        self.market = MarketSnapshot()
        self.binance = BinanceClient(
            api_key=config.BINANCE_API_KEY,
            api_secret=config.BINANCE_API_SECRET,
        )
        self.is_live = config.TRADING_MODE == "live" and bool(config.BINANCE_API_KEY)
        if self.is_live:
            self.engine = LiveEngine(config.DB_PATH, self.binance)
            logger.warning("🔴 LIVE mod aktif — gerçek Binance emirleri gönderilecek")
        else:
            self.engine = PaperEngine(config.DB_PATH)
            logger.info("🟢 Paper mod aktif — simülasyon (API key gerekmez)")

        self.risk = RiskManager(self.settings)
        self.strategies = {
            "funding": FundingRateStrategy(self.settings),
            "technical": TechnicalStrategy(self.settings),
        }
        self.ai = AIAnalyzer(
            api_key=config.AI_API_KEY,
            base_url=config.AI_BASE_URL,
            model=config.AI_MODEL,
            enabled=config.AI_ENABLED,
        )

    # ── event log (dashboard feed) ────────────────────────────────────
    def push_event(self, kind: str, text: str, **extra) -> None:
        ev = {
            "ts": _now_iso(),
            "kind": kind,
            "text": text,
            **extra,
        }
        self.state["events"].append(ev)
        self.state["events"] = self.state["events"][-100:]
        logger.info("[%s] %s", kind, text)

    # ── loop 1: market feed ───────────────────────────────────────────
    async def market_loop(self) -> None:
        price_interval = max(3, config.PRICE_REFRESH_SEC)
        while True:
            try:
                symbols = self.settings.symbols()
                self.market.symbols = symbols
                prices = await self.binance.get_all_prices()
                self.market.prices = {k: v for k, v in prices.items() if k in symbols}
                try:
                    self.market.funding_rates = await self.binance.get_funding_rates()
                except Exception:  # noqa: BLE001 — funding optional
                    pass
                try:
                    self.market.tickers = await self.binance.get_24h_tickers()
                except Exception:  # noqa: BLE001
                    pass
                self.market.api_ok = True
                self.market.last_update = _now_iso()
            except Exception as e:  # noqa: BLE001
                self.market.api_ok = False
                self.state["last_error"] = f"market: {e}"
                logger.error("Market güncelleme hatası: %s", e)
            await asyncio.sleep(price_interval)

    async def refresh_klines(self) -> None:
        for symbol in self.settings.symbols():
            try:
                self.market.klines[symbol] = await self.binance.get_klines(symbol, "1h", 120)
            except Exception:  # noqa: BLE001
                pass

    # ── loop 2: strategy scan (copy engine) ───────────────────────────
    async def scan_loop(self) -> None:
        await asyncio.sleep(2)  # let the market feed warm up
        while True:
            interval = max(5, int(self.settings.get_typed("scan_interval_sec") or 15))
            try:
                await self.refresh_klines()
                await self.scan_once()
            except Exception as e:  # noqa: BLE001
                self.state["last_error"] = f"scan: {e}"
                logger.exception("Tarama hatası")
            await asyncio.sleep(interval)

    async def scan_once(self) -> None:
        self.state["scan_count"] += 1
        self.state["last_scan"] = _now_iso()
        symbols = self.settings.symbols()

        # 1) collect signals from every enabled strategy
        signals: list = []
        for name, strat in self.strategies.items():
            if self.settings.strategy_enabled(name):
                try:
                    signals.extend(await strat.scan(self.market))
                except Exception as e:  # noqa: BLE001
                    logger.error("Strateji %s hatası: %s", name, e)

        # 2) optional AI filter (fallback = pass-through)
        portfolio = {
            "equity": self.engine.equity(self.market.prices),
            "open_positions": self.engine.position_count(),
            "realized_pnl": self.engine.realized_pnl(),
        }
        signals = await self.ai.filter_signals(signals, portfolio)

        # 3) persist + record
        for s in signals:
            self._record_signal(s)
        self.state["latest_signals"] = [
            {"symbol": s.symbol, "side": s.side, "strategy": s.strategy,
             "reason": s.reason, "confidence": s.confidence, "price": s.price,
             "created_at": s.created_at}
            for s in signals[-15:]
        ]

        # 4) execute: mirror signals into positions (the "copy" step)
        await self.execute_signals(signals)

        # 5) exits (stop-loss / take-profit) + funding payments
        closed = self.engine.check_exits(self.market.prices)
        for c in closed:
            self.push_event("close", f"{c.get('symbol')} kapatıldı ({c.get('reason')})", **c)
        paid = self.engine.process_funding_payments(self.market.funding_rates)
        if paid:
            self.push_event("funding", f"{paid} funding ödemesi işlendi")

        # 6) equity curve point (once per scan is enough)
        self.engine.record_equity_point(self.engine.equity(self.market.prices))

    def _record_signal(self, s) -> None:
        conn = self.engine._conn
        conn.execute(
            "INSERT INTO signals (symbol, side, strategy, price, reason) VALUES (?,?,?,?,?)",
            (s.symbol, s.side, s.strategy, s.price, s.reason),
        )
        conn.commit()

    async def execute_signals(self, signals: list) -> None:
        for s in signals:
            price = self.market.prices.get(s.symbol, s.price)
            if not price:
                continue
            existing = self.engine.open_position_for(s.symbol, s.strategy)
            if existing:
                continue  # already copied this master signal

            # sizing
            default_size = float(self.settings.get_typed("max_position_size_usd") or 25)
            size = self.risk.size_position(
                self.engine.equity(self.market.prices), default_size
            )
            ok, reason = self.risk.can_open(
                equity=self.engine.equity(self.market.prices),
                open_count=self.engine.position_count(),
                today_loss=abs(self.engine.today_realized_pnl()),
                size_usd=size,
            )
            if not ok:
                self.push_event("reject", f"{s.symbol} {s.side}: {reason}")
                continue

            funding_rate = self.market.funding_rates.get(s.symbol, 0.0)
            if self.is_live:
                pos_id = await self.engine.open_position_live(
                    s.symbol, s.side, s.strategy, size, price, funding_rate, s.reason)
            else:
                pos_id = self.engine.open_position(
                    s.symbol, s.side, s.strategy, size, price, funding_rate, s.reason)
            if pos_id:
                self.push_event(
                    "open",
                    f"{s.symbol} {s.side} açıldı (${size:.2f}, {s.strategy}) @ {price:.4f}",
                    symbol=s.symbol, side=s.side, strategy=s.strategy,
                    size_usd=size, price=price,
                )
                # mark signal executed
                self.engine._conn.execute(
                    "UPDATE signals SET executed=1 WHERE symbol=? AND side=? "
                    "AND strategy=? AND executed=0",
                    (s.symbol, s.side, s.strategy),
                )
                self.engine._conn.commit()

    # ── loop 3: funding slot payments ─────────────────────────────────
    async def funding_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                self.engine.process_funding_payments(self.market.funding_rates)
            except Exception as e:  # noqa: BLE001
                logger.error("Funding işleme hatası: %s", e)

    # ── API state views (used by dashboard) ───────────────────────────
    def dashboard_state(self) -> dict:
        prices = self.market.prices
        open_positions = [
            {**dict(p),
             "unrealized_pnl": round(
                 self.engine._pnl_for(p, prices.get(p["symbol"], p["entry_price"])), 2),
             "funding_collected": round(self.engine.funding_collected(p["id"]), 4)}
            for p in self.engine.open_positions()
        ]
        equity = self.engine.equity(prices)
        return {
            "meta": {
                "started_at": self.state["started_at"],
                "mode": self.state["mode"],
                "ai_enabled": self.state["ai_enabled"],
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
            "market": self.market.to_dict(self.settings.symbols()),
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
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(str(BASE_DIR / "data" / "copytrader.log")),
        ],
    )
    app = CopyTraderApp()
    dashboard = create_dashboard(app)

    async def _serve() -> None:
        cfg = uvicorn.Config(
            dashboard,
            host=config.HOST,
            port=config.PORT,
            log_level="warning",
        )
        server = uvicorn.Server(cfg)
        await server.serve()

    try:
        await asyncio.gather(
            app.market_loop(),
            app.scan_loop(),
            app.funding_loop(),
            _serve(),
        )
    finally:
        await app.binance.close()


if __name__ == "__main__":
    asyncio.run(main())
