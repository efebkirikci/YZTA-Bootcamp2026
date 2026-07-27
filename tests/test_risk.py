"""Risk yönetimi testleri."""

from bot.trading.risk import RiskManager


def test_can_open_under_limits():
    rm = RiskManager()
    ok, reason = rm.can_open(equity=1000.0, open_count=0, today_loss=0.0, size_usd=25.0)
    assert ok is True
    assert reason == "ok"


def test_rejects_over_max_positions():
    rm = RiskManager()
    ok, _ = rm.can_open(equity=1000.0, open_count=3, today_loss=0.0, size_usd=25.0)
    assert ok is False


def test_rejects_over_size_limit():
    rm = RiskManager()
    ok, _ = rm.can_open(equity=1000.0, open_count=0, today_loss=0.0, size_usd=500.0)
    assert ok is False


def test_rejects_daily_loss_breaker():
    rm = RiskManager()
    ok, reason = rm.can_open(equity=1000.0, open_count=0, today_loss=25.0, size_usd=25.0)
    assert ok is False
    assert "kayıp" in reason.lower()


def test_rejects_over_portfolio_risk():
    from bot.trading.risk import RiskManager
    import sqlite3
    from pathlib import Path
    from bot.config import RUNTIME_SETTINGS
    from bot.config import SettingsStore

    db = Path("/tmp/ct_test_risk_portfolio.db")
    conn = sqlite3.connect(str(db))
    conn.executescript("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, description TEXT)")
    for key, (default, desc, _t) in RUNTIME_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
                     (key, default, desc))
    conn.execute("UPDATE settings SET value='50' WHERE key='max_portfolio_risk_pct'")
    conn.commit()
    conn.close()
    store = SettingsStore.__new__(SettingsStore)
    store.db_path = db
    rm = RiskManager(store)
    # %50 x $1000 = $500 limit; 3 pozisyon x $25 + $25 = $100 → acik pozisyon limiti once reddeder
    ok, _ = rm.can_open(equity=1000.0, open_count=3, today_loss=0.0, size_usd=25.0)
    assert ok is False


def test_size_position_clamps():
    rm = RiskManager()
    assert rm.size_position(1000.0, default_size=999.0) == 25.0
    assert rm.size_position(1000.0, default_size=10.0) == 10.0
