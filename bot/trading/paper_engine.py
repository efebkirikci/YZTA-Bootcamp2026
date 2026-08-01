"""Paper trading engine — SQLite-backed position/pnl simulation.

The copier writes positions here in paper mode. It simulates:
- entry/exit at live market prices (filled at snapshot price)
- unrealized PnL marked at each price refresh
- fixed 8h funding slots (00/08/16 UTC) for funding-rate positions
- stop-loss / take-profit exits

Live mode swaps this engine for Binance order placement (see main.py).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("paper")

INITIAL_CAPITAL = 1000.0


def funding_slots_between(start: datetime, end: datetime) -> list[datetime]:
    """Fixed 8h UTC funding slots (00, 08, 16) in (start, end]."""
    slots: list[datetime] = []
    cursor = start
    # walk forward day by day until past the end window
    for _ in range(16):
        for h in (0, 8, 16):
            slot = cursor.replace(hour=h, minute=0, second=0, microsecond=0)
            if start < slot <= end:
                slots.append(slot)
        cursor = (cursor.replace(hour=0, minute=0, second=0, microsecond=0)
                  + timedelta(days=1))
        if cursor > end + timedelta(days=1):
            break
    return sorted(set(slots))


class PaperEngine:
    def __init__(self, db_path: Path, initial_capital: float = INITIAL_CAPITAL):
        self.db_path = db_path
        self._initial_capital = initial_capital
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS paper_meta (
                key TEXT PRIMARY KEY, value TEXT
            );
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                strategy TEXT NOT NULL,
                size_usd REAL NOT NULL,
                entry_price REAL NOT NULL,
                entry_funding_rate REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                opened_at TEXT DEFAULT (datetime('now')),
                closed_at TEXT,
                close_price REAL,
                realized_pnl REAL DEFAULT 0,
                stop_loss_price REAL,
                take_profit_price REAL,
                reason TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                strategy TEXT NOT NULL,
                size_usd REAL NOT NULL,
                price REAL NOT NULL,
                pnl_usd REAL DEFAULT 0,
                kind TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS paper_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                slot_time TEXT NOT NULL,
                rate REAL NOT NULL,
                amount_usd REAL NOT NULL
            );
            """
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO paper_meta (key, value) VALUES ('initial_capital', ?)",
            (str(self._initial_capital),),
        )
        self._conn.commit()

    # ── capital / equity ──────────────────────────────────────────────
    def initial_capital(self) -> float:
        row = self._conn.execute(
            "SELECT value FROM paper_meta WHERE key='initial_capital'"
        ).fetchone()
        return float(row["value"]) if row else self._initial_capital

    def realized_pnl(self) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(realized_pnl),0) FROM paper_positions WHERE status='closed'"
        ).fetchone()
        return float(row[0])

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        total = 0.0
        for p in self.open_positions():
            price = prices.get(p["symbol"])
            if not price:
                continue
            total += self._pnl_for(p, price)
        return total

    def equity(self, prices: dict[str, float]) -> float:
        return self.initial_capital() + self.realized_pnl() + self.unrealized_pnl(prices)

    def today_realized_pnl(self) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(realized_pnl),0) FROM paper_positions "
            "WHERE status='closed' AND date(closed_at)=date('now')"
        ).fetchone()
        return float(row[0])

    # ── positions ─────────────────────────────────────────────────────
    def open_positions(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM paper_positions WHERE status='open' ORDER BY id"
        ).fetchall()

    def position_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM paper_positions WHERE status='open'"
        ).fetchone()
        return int(row[0])

    def open_position_for(self, symbol: str, strategy: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM paper_positions WHERE status='open' AND symbol=? AND strategy=?",
            (symbol, strategy),
        ).fetchone()

    def open_position(self, symbol: str, side: str, strategy: str, size_usd: float,
                      price: float, funding_rate: float = 0.0, reason: str = "") -> int:
        sl_pct = float(self._conn.execute(
            "SELECT value FROM settings WHERE key='stop_loss_pct'"
        ).fetchone()[0])
        tp_pct = float(self._conn.execute(
            "SELECT value FROM settings WHERE key='take_profit_pct'"
        ).fetchone()[0])
        if side == "LONG":
            sl = price * (1 - sl_pct / 100.0)
            tp = price * (1 + tp_pct / 100.0)
        else:
            sl = price * (1 + sl_pct / 100.0)
            tp = price * (1 - tp_pct / 100.0)
        cur = self._conn.execute(
            "INSERT INTO paper_positions (symbol, side, strategy, size_usd, entry_price, "
            "entry_funding_rate, stop_loss_price, take_profit_price, reason) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (symbol, side, strategy, size_usd, price, funding_rate, sl, tp, reason),
        )
        pos_id = cur.lastrowid
        self._conn.execute(
            "INSERT INTO paper_trades (position_id, symbol, side, strategy, size_usd, "
            "price, kind) VALUES (?,?,?,?,?,?, 'open')",
            (pos_id, symbol, side, strategy, size_usd, price),
        )
        self._conn.commit()
        return pos_id

    def close_position(self, position_id: int, price: float, reason: str = "manual") -> dict:
        p = self._conn.execute(
            "SELECT * FROM paper_positions WHERE id=?", (position_id,)
        ).fetchone()
        if p is None or p["status"] == "closed":
            return {"ok": False, "error": "pozisyon yok / zaten kapalı"}
        pnl = self._pnl_for(p, price)
        self._conn.execute(
            "UPDATE paper_positions SET status='closed', close_price=?, realized_pnl=?, "
            "closed_at=datetime('now') WHERE id=?",
            (price, pnl, position_id),
        )
        self._conn.execute(
            "INSERT INTO paper_trades (position_id, symbol, side, strategy, size_usd, "
            "price, pnl_usd, kind) VALUES (?,?,?,?,?,?,?, 'close')",
            (position_id, p["symbol"], p["side"], p["strategy"], p["size_usd"], price, pnl),
        )
        self._conn.commit()
        return {"ok": True, "pnl": pnl, "reason": reason}

    @staticmethod
    def _pnl_for(p: sqlite3.Row, price: float) -> float:
        """PnL in USD for a position at the given price."""
        if p["side"] == "LONG":
            ret = (price - p["entry_price"]) / p["entry_price"] if p["entry_price"] else 0
        else:
            ret = (p["entry_price"] - price) / p["entry_price"] if p["entry_price"] else 0
        return p["size_usd"] * ret

    # ── funding payments (fixed 8h slots) ─────────────────────────────
    def process_funding_payments(self, rates: dict[str, float], now: datetime | None = None) -> int:
        """Credit funding for open positions for every 8h slot crossed."""
        now = now or datetime.now(timezone.utc)
        paid = 0
        for p in self.open_positions():
            if p["strategy"] != "funding":
                continue
            rate = rates.get(p["symbol"])
            if rate is None:
                continue
            last = self._conn.execute(
                "SELECT slot_time FROM paper_payments WHERE position_id=? "
                "ORDER BY slot_time DESC LIMIT 1", (p["id"],)
            ).fetchone()
            start = datetime.fromisoformat(last["slot_time"]) if last else \
                datetime.fromisoformat(p["opened_at"])
            for slot in funding_slots_between(start, now):
                # LONG collects when rate negative, SHORT collects when positive
                if p["side"] == "LONG":
                    amount = -rate * p["size_usd"]
                else:
                    amount = rate * p["size_usd"]
                self._conn.execute(
                    "INSERT INTO paper_payments (position_id, slot_time, rate, amount_usd) "
                    "VALUES (?,?,?,?)",
                    (p["id"], slot.isoformat(), rate, amount),
                )
                paid += 1
        if paid:
            self._conn.commit()
        return paid

    def funding_collected(self, position_id: int) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(amount_usd),0) FROM paper_payments WHERE position_id=?",
            (position_id,),
        ).fetchone()
        return float(row[0])

    def total_funding_collected(self) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(amount_usd),0) FROM paper_payments"
        ).fetchone()
        return float(row[0])

    # ── exits & mark-to-market ────────────────────────────────────────
    def check_exits(self, prices: dict[str, float]) -> list[dict]:
        """Auto-close on stop-loss / take-profit. Returns closed list."""
        closed = []
        for p in self.open_positions():
            price = prices.get(p["symbol"])
            if not price:
                continue
            if p["side"] == "LONG":
                if p["stop_loss_price"] and price <= p["stop_loss_price"]:
                    r = self.close_position(p["id"], price, "stop_loss")
                    closed.append({"symbol": p["symbol"], "reason": "stop_loss", **r})
                elif p["take_profit_price"] and price >= p["take_profit_price"]:
                    r = self.close_position(p["id"], price, "take_profit")
                    closed.append({"symbol": p["symbol"], "reason": "take_profit", **r})
            else:
                if p["stop_loss_price"] and price >= p["stop_loss_price"]:
                    r = self.close_position(p["id"], price, "stop_loss")
                    closed.append({"symbol": p["symbol"], "reason": "stop_loss", **r})
                elif p["take_profit_price"] and price <= p["take_profit_price"]:
                    r = self.close_position(p["id"], price, "take_profit")
                    closed.append({"symbol": p["symbol"], "reason": "take_profit", **r})
        return closed

    def recent_trades(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def history(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM paper_positions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def record_equity_point(self, equity: float) -> None:
        self._conn.execute(
            "INSERT INTO equity_curve (equity) VALUES (?)", (equity,)
        )
        self._conn.commit()

    def equity_curve(self, limit: int = 500) -> list[dict]:
        rows = self._conn.execute(
            "SELECT ts, equity FROM equity_curve ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
