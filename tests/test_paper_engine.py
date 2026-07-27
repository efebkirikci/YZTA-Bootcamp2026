"""Paper engine testleri — pozisyon yaşam döngüsü, PnL, funding."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from bot.trading.paper_engine import PaperEngine


def dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


@pytest.fixture()
def engine(tmp_path: Path) -> PaperEngine:
    return PaperEngine(tmp_path / "test.db", initial_capital=1000.0)


def _backdate_opened_at(engine: PaperEngine, pos_id: int, iso: str) -> None:
    """Pozisyon açılışını geçmişe çek — slot geçişini simüle et."""
    engine._conn.execute(
        "UPDATE paper_positions SET opened_at=? WHERE id=?", (iso, pos_id))
    engine._conn.commit()


def test_open_and_close_pnl_long(engine):
    pos_id = engine.open_position("BTCUSDT", "LONG", "funding", 100.0, price=60000.0)
    assert pos_id > 0
    assert engine.position_count() == 1

    res = engine.close_position(pos_id, price=63000.0, reason="test")
    assert res["ok"] is True
    assert res["pnl"] == pytest.approx(5.0, abs=0.01)
    assert engine.position_count() == 0


def test_close_pnl_short(engine):
    pos_id = engine.open_position("ETHUSDT", "SHORT", "funding", 100.0, price=2000.0)
    res = engine.close_position(pos_id, price=1900.0, reason="test")
    assert res["pnl"] == pytest.approx(5.0, abs=0.01)


def test_double_close_rejected(engine):
    pos_id = engine.open_position("SOLUSDT", "LONG", "technical", 50.0, price=100.0)
    engine.close_position(pos_id, price=105.0)
    res = engine.close_position(pos_id, price=105.0)
    assert res["ok"] is False


def test_stop_loss_fires(engine):
    engine._conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
        ("stop_loss_pct", "5.0", ""))
    engine._conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
        ("take_profit_pct", "8.0", ""))
    engine._conn.commit()
    pos_id = engine.open_position("BTCUSDT", "LONG", "funding", 100.0, price=60000.0)
    closed = engine.check_exits({"BTCUSDT": 60000.0 * 0.94})  # %6 dusus → SL (%5)
    assert len(closed) == 1
    assert closed[0]["reason"] == "stop_loss"
    assert engine.position_count() == 0


def test_take_profit_fires(engine):
    engine._conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
        ("stop_loss_pct", "5.0", ""))
    engine._conn.execute(
        "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?,?,?)",
        ("take_profit_pct", "8.0", ""))
    engine._conn.commit()
    pos_id = engine.open_position("BTCUSDT", "LONG", "funding", 100.0, price=60000.0)
    closed = engine.check_exits({"BTCUSDT": 60000.0 * 1.09})  # %9 artis → TP (%8)
    assert len(closed) == 1
    assert closed[0]["reason"] == "take_profit"


def test_equity_moves_with_market(engine):
    engine.open_position("BTCUSDT", "LONG", "funding", 100.0, price=60000.0)
    assert engine.equity({"BTCUSDT": 63000.0}) > 1000.0
    assert engine.equity({"BTCUSDT": 57000.0}) < 1000.0


def test_funding_payment_long_negative_rate(engine):
    pos_id = engine.open_position("SOLUSDT", "LONG", "funding", 100.0, price=100.0,
                                  funding_rate=-0.0001)
    # 12:08'de açıldı → 16:00 slotu geçti
    _backdate_opened_at(engine, pos_id, "2026-07-01T12:08:00+00:00")
    paid = engine.process_funding_payments(
        {"SOLUSDT": -0.0001}, now=dt("2026-07-01T16:00:30+00:00"))
    assert paid >= 1
    # LONG negatif funding'de ödeme ALIR: -rate × size = +$0.01
    assert engine.funding_collected(pos_id) == pytest.approx(0.01, abs=1e-6)


def test_funding_payment_short_positive_rate(engine):
    pos_id = engine.open_position("SOLUSDT", "SHORT", "funding", 100.0, price=100.0,
                                  funding_rate=0.0001)
    _backdate_opened_at(engine, pos_id, "2026-07-01T12:08:00+00:00")
    paid = engine.process_funding_payments(
        {"SOLUSDT": 0.0001}, now=dt("2026-07-01T16:00:30+00:00"))
    assert paid >= 1
    assert engine.funding_collected(pos_id) == pytest.approx(0.01, abs=1e-6)


def test_technical_positions_get_no_funding(engine):
    pos_id = engine.open_position("SOLUSDT", "LONG", "technical", 100.0, price=100.0)
    assert engine.process_funding_payments({"SOLUSDT": -0.0001}) == 0
    assert engine.funding_collected(pos_id) == 0.0
