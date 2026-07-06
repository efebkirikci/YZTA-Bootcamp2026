"""Paper trading engine v1 — SQLite tabanlı pozisyon simülasyonu.

Pozisyon aç/kapa, gerçekleşen/gerçekleşmemiş PnL ve equity takibi.
Funding slot mekaniği bir sonraki adımda eklenecek.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("paper")

INITIAL_CAPITAL = 1000.0


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
                status TEXT DEFAULT 'open',
                opened_at TEXT DEFAULT (datetime('now')),
                closed_at TEXT,
                close_price REAL,
                realized_pnl REAL DEFAULT 0,
                reason TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                size_usd REAL NOT NULL,
                price REAL NOT NULL,
                pnl_usd REAL DEFAULT 0,
                kind TEXT DEFAULT 'open',
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO paper_meta (key, value) VALUES ('initial_capital', ?)",
            (str(self._initial_capital),),
        )
        self._conn.commit()

    def initial_capital(self) -> float:
        row = self._conn.execute(
            "SELECT value FROM paper_meta WHERE key='initial_capital'").fetchone()
        return float(row["value"]) if row else self._initial_capital

    def realized_pnl(self) -> float:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(realized_pnl),0) FROM paper_positions "
            "WHERE status='closed'").fetchone()
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

    def open_positions(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM paper_positions WHERE status='open' ORDER BY id").fetchall()

    def position_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM paper_positions WHERE status='open'").fetchone()
        return int(row[0])

    def open_position_for(self, symbol: str, strategy: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM paper_positions WHERE status='open' AND symbol=? AND strategy=?",
            (symbol, strategy)).fetchone()

    def open_position(self, symbol: str, side: str, strategy: str, size_usd: float,
                      price: float, funding_rate: float = 0.0, reason: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO paper_positions (symbol, side, strategy, size_usd, entry_price, reason) "
            "VALUES (?,?,?,?,?,?)",
            (symbol, side, strategy, size_usd, price, reason))
        pos_id = cur.lastrowid
        self._conn.execute(
            "INSERT INTO paper_trades (position_id, symbol, side, size_usd, price, kind) "
            "VALUES (?,?,?,?,?, 'open')",
            (pos_id, symbol, side, size_usd, price))
        self._conn.commit()
        return pos_id

    def close_position(self, position_id: int, price: float, reason: str = "manual") -> dict:
        p = self._conn.execute(
            "SELECT * FROM paper_positions WHERE id=?", (position_id,)).fetchone()
        if p is None or p["status"] == "closed":
            return {"ok": False, "error": "pozisyon yok / zaten kapalı"}
        pnl = self._pnl_for(p, price)
        self._conn.execute(
            "UPDATE paper_positions SET status='closed', close_price=?, realized_pnl=?, "
            "closed_at=datetime('now') WHERE id=?",
            (price, pnl, position_id))
        self._conn.execute(
            "INSERT INTO paper_trades (position_id, symbol, side, size_usd, price, pnl_usd, kind) "
            "VALUES (?,?,?,?,?,?, 'close')",
            (position_id, p["symbol"], p["side"], p["size_usd"], price, pnl))
        self._conn.commit()
        return {"ok": True, "pnl": pnl, "reason": reason}

    @staticmethod
    def _pnl_for(p: sqlite3.Row, price: float) -> float:
        if p["side"] == "LONG":
            ret = (price - p["entry_price"]) / p["entry_price"] if p["entry_price"] else 0
        else:
            ret = (p["entry_price"] - price) / p["entry_price"] if p["entry_price"] else 0
        return p["size_usd"] * ret

    def recent_trades(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
