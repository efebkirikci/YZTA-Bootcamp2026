"""İndikatör ve strateji sinyal testleri."""

import numpy as np
import pytest

from bot.strategies.technical import ema, macd, rsi
from bot.strategies.funding_rate import FundingRateStrategy


def test_ema_smoke():
    values = np.linspace(100.0, 200.0, 50)
    out = ema(values, 9)
    assert not np.isnan(out[-1])
    assert out[-1] > 150.0


def test_ema_short_period_nan():
    assert np.isnan(ema(np.array([1.0, 2.0, 3.0]), 9)[-1])


def test_rsi_extremes():
    up = np.arange(1.0, 30.0, 0.5)
    assert rsi(up, 14) == 100.0
    down = np.arange(30.0, 1.0, -0.5)
    assert rsi(down, 14) == 0.0


def test_rsi_neutral():
    flat = np.full(30, 42.0)
    assert abs(rsi(flat, 14) - 50.0) < 0.001


def test_macd_uptrend():
    # üstel büyüme → MACD çizgisi sinyalin üstünde
    values = 100.0 * (1.015 ** np.arange(80))
    line, sig = macd(values)
    assert line > sig


def test_macd_downtrend():
    # hızlanan düşüş → MACD çizgisi sinyalin altında
    values = 300.0 - 3.0 * (1.015 ** np.arange(80))
    line, sig = macd(values)
    assert line < sig


def test_macd_insufficient_data():
    assert macd(np.array([1.0, 2.0, 3.0])) == (0.0, 0.0)


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
