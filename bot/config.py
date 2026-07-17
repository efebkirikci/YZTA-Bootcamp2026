"""Central configuration — env default'lari + SQLite runtime ayarlari."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "copytrader.db"

load_dotenv(BASE_DIR / ".env")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
PRICE_REFRESH_SEC = int(os.getenv("PRICE_REFRESH_SEC", "3"))
SCAN_INTERVAL_SEC = int(os.getenv("SCAN_INTERVAL_SEC", "15"))

DEFAULT_SYMBOLS = [s.strip() for s in os.getenv(
    "SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT"
).split(",") if s.strip()]

TRADING_MODE = os.getenv("TRADING_MODE", "paper").lower()
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() == "true"

RUNTIME_SETTINGS: dict[str, tuple] = {
    "active_strategy": ("both", "Strateji: funding | technical | both", "str"),
    "symbols": (",".join(DEFAULT_SYMBOLS), "Izlenecek semboller (virgullu)", "str"),
    "funding_rate_threshold": ("0.01", "Funding rate esigi", "float"),
    "ema_fast": ("9", "EMA kisa periyot", "int"),
    "ema_slow": ("21", "EMA uzun periyot", "int"),
    "rsi_period": ("14", "RSI periyodu", "int"),
    "rsi_oversold": ("30", "RSI asiri satim", "int"),
    "rsi_overbought": ("70", "RSI asiri alim", "int"),
    "max_open_positions": ("3", "Maksimum acik pozisyon", "int"),
    "max_position_size_usd": ("25", "Pozisyon basina max USD", "float"),
    "max_portfolio_risk_pct": ("50", "Portfoy risk yuzdesi", "float"),
    "stop_loss_pct": ("5.0", "Stop-loss (%)", "float"),
    "take_profit_pct": ("8.0", "Take-profit (%)", "float"),
    "max_daily_loss_usd": ("20", "Gunluk max kayip (USD)", "float"),
    "scan_interval_sec": (str(SCAN_INTERVAL_SEC), "Tarama araligi (sn)", "int"),
}


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT DEFAULT '',
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            strategy TEXT NOT NULL,
            price REAL,
            reason TEXT DEFAULT '',
            executed INTEGER DEFAULT 0
        );
        """
    )
    for key, (default, desc, _typ) in RUNTIME_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?, ?, ?)",
            (key, default, desc),
        )
    conn.commit()
    conn.close()


class SettingsStore:
    """Runtime ayarlari DB'den okur/yazar (dashboard odakli)."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, key: str) -> str:
        conn = self._conn()
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()
        if row is None:
            return RUNTIME_SETTINGS.get(key, ("", "", "str"))[0]
        return row["value"]

    def get_typed(self, key: str):
        typ = RUNTIME_SETTINGS.get(key, ("", "", "str"))[2]
        raw = self.get(key)
        try:
            if typ == "int":
                return int(float(raw))
            if typ == "float":
                return float(raw)
        except (TypeError, ValueError):
            return RUNTIME_SETTINGS[key][0]
        return raw

    def all(self) -> dict:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM settings ORDER BY key").fetchall()
        conn.close()
        out = {}
        for r in rows:
            out[r["key"]] = {
                "value": r["value"],
                "description": r["description"],
                "updated_at": r["updated_at"],
            }
        return out

    def set(self, key: str, value: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO settings (key, value, description, updated_at) "
            "VALUES (?, ?, COALESCE((SELECT description FROM settings WHERE key=?), ''), datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (key, value, key),
        )
        conn.commit()
        conn.close()

    def symbols(self) -> list[str]:
        return [s.strip() for s in self.get("symbols").split(",") if s.strip()]

    def active_strategy(self) -> str:
        return self.get("active_strategy").strip().lower()

    def strategy_enabled(self, name: str) -> bool:
        mode = self.active_strategy()
        return mode == "both" or mode == name
