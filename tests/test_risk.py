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


def test_size_position_clamps():
    rm = RiskManager()
    assert rm.size_position(1000.0, default_size=999.0) == 25.0
    assert rm.size_position(1000.0, default_size=10.0) == 10.0
