"""Indicator and strategy signal tests — EMA/RSI/MACD on synthetic data."""

import numpy as np
import pytest

from bot.strategies.technical import ema, macd, rsi


def test_ema_smoke():
    values = np.linspace(100.0, 200.0, 50)
    out = ema(values, 9)
    assert not np.isnan(out[-1])
    # yükselen seride EMA son değere yakın ve serinin üst yarısında
    assert out[-1] > 150.0


def test_ema_short_period_nan():
    values = np.array([1.0, 2.0, 3.0])
    out = ema(values, 9)
    assert np.isnan(out[-1])  # yeterli veri yok


def test_rsi_extremes():
    # hep artan → RSI 100
    up = np.arange(1.0, 30.0, 0.5)
    assert rsi(up, 14) == 100.0
    # hep azalan → RSI 0
    down = np.arange(30.0, 1.0, -0.5)
    assert rsi(down, 14) == 0.0


def test_rsi_neutral():
    # düz seri → 50 civarı
    flat = np.full(30, 42.0)
    assert abs(rsi(flat, 14) - 50.0) < 0.001


def test_macd_uptrend():
    # üstel büyüme → MACD çizgisi yükselir, sinyalin üstünde kalır
    values = 100.0 * (1.015 ** np.arange(80))
    line, sig = macd(values)
    assert line > sig


def test_macd_downtrend():
    # hızlanan düşüş → MACD çizgisi düşer, sinyalin altında kalır
    values = 300.0 - 3.0 * (1.015 ** np.arange(80))
    line, sig = macd(values)
    assert line < sig


def test_macd_insufficient_data():
    line, sig = macd(np.array([1.0, 2.0, 3.0]))
    assert line == 0.0 and sig == 0.0


# ── funding strategy signal direction ─────────────────────────────────
from bot.strategies.funding_rate import FundingRateStrategy


class _FakeSettings:
    def get_typed(self, key):
        return {"funding_rate_threshold": 0.01}[key]


class _Market:
    def __init__(self, rates, prices, symbols):
        self.funding_rates = rates
        self.prices = prices
        self.symbols = symbols


@pytest.mark.asyncio
async def test_funding_negative_gives_long():
    strat = FundingRateStrategy(_FakeSettings())
    market = _Market({"BTCUSDT": -0.02}, {"BTCUSDT": 60000.0}, ["BTCUSDT"])
    signals = await strat.scan(market)
    assert len(signals) == 1
    assert signals[0].side == "LONG"


@pytest.mark.asyncio
async def test_funding_positive_gives_short():
    strat = FundingRateStrategy(_FakeSettings())
    market = _Market({"BTCUSDT": 0.02}, {"BTCUSDT": 60000.0}, ["BTCUSDT"])
    signals = await strat.scan(market)
    assert len(signals) == 1
    assert signals[0].side == "SHORT"


@pytest.mark.asyncio
async def test_funding_below_threshold_no_signal():
    strat = FundingRateStrategy(_FakeSettings())
    market = _Market({"BTCUSDT": 0.00005}, {"BTCUSDT": 60000.0}, ["BTCUSDT"])
    assert await strat.scan(market) == []
