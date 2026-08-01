"""Risk manager tests — position sizing and portfolio guards."""

import sqlite3
from pathlib import Path

import pytest

from bot.config import RUNTIME_SETTINGS, SettingsStore, init_db
from bot.trading.risk import RiskManager


@pytest.fixture()
def settings(tmp_path: Path) -> SettingsStore:
    db = tmp_path / "test.db"
    conn = sqlite3.connect(str(db))
    for key, (default, desc, _t) in RUNTIME_SETTINGS.items():
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, description TEXT)"
        )
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT, description TEXT
        );
        """
    )
    for key, (default, desc, _t) in RUNTIME_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
                     (key, default, desc))
    conn.commit()
    conn.close()

    store = SettingsStore.__new__(SettingsStore)
    store.db_path = db
    return store


def test_can_open_under_limits(settings):
    rm = RiskManager(settings)
    ok, reason = rm.can_open(equity=1000.0, open_count=0, today_loss=0.0, size_usd=25.0)
    assert ok is True
    assert reason == "ok"


def test_rejects_over_max_positions(settings):
    rm = RiskManager(settings)
    ok, _ = rm.can_open(equity=1000.0, open_count=3, today_loss=0.0, size_usd=25.0)
    assert ok is False


def test_rejects_over_size_limit(settings):
    rm = RiskManager(settings)
    ok, reason = rm.can_open(equity=1000.0, open_count=0, today_loss=0.0, size_usd=500.0)
    assert ok is False
    assert "limit" in reason.lower()


def test_rejects_over_portfolio_risk(settings):
    rm = RiskManager(settings)
    # %50 risk × $1000 = $500 limit; 3 pozisyon × $25 + $25 = $100 — geçer
    ok, _ = rm.can_open(equity=1000.0, open_count=3, today_loss=0.0, size_usd=25.0)
    assert ok is False  # önce max_positions reddeder — limitler öncelikli


def test_rejects_daily_loss_breaker(settings):
    rm = RiskManager(settings)
    ok, reason = rm.can_open(equity=1000.0, open_count=0, today_loss=25.0, size_usd=25.0)
    assert ok is False
    assert "kayıp" in reason.lower()


def test_size_position_clamps(settings):
    rm = RiskManager(settings)
    assert rm.size_position(1000.0, default_size=999.0) == 25.0
    assert rm.size_position(1000.0, default_size=10.0) == 10.0
    assert rm.size_position(1000.0) == 25.0
