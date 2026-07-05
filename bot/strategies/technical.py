"""Teknik indikatör stratejisi v1 — EMA cross + RSI.

EMA hızlı/slow cross yönü + RSI aşırı alım/satım filtresi birlikte
çalışır. MACD momentum onayı bir sonraki adımda eklenecek.
"""

import logging

import numpy as np

from .base import Signal, Strategy

logger = logging.getLogger("strategy.technical")


def ema(values: np.ndarray, period: int) -> np.ndarray:
    if len(values) < period:
        return np.full(len(values), np.nan)
    out = np.empty_like(values, dtype=float)
    out[:] = np.nan
    out[period - 1] = float(np.mean(values[:period]))
    k = 2.0 / (period + 1)
    for i in range(period, len(values)):
        out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


def rsi(values: np.ndarray, period: int = 14) -> float:
    """Wilder RSI — son değer."""
    if len(values) < period + 1:
        return 50.0
    deltas = np.diff(values[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class TechnicalStrategy(Strategy):
    name = "technical"
    label = "Teknik (EMA+RSI)"

    async def scan(self, market) -> list[Signal]:
        signals = []
        for symbol in market.symbols:
            candles = market.klines.get(symbol)
            if not candles or len(candles) < 25:
                continue
            closes = np.array([c["close"] for c in candles], dtype=float)
            price = float(closes[-1])

            ema_f = ema(closes, 9)
            ema_s = ema(closes, 21)
            if np.isnan(ema_f[-1]) or np.isnan(ema_s[-1]):
                continue
            rsi_val = rsi(closes, 14)

            if ema_f[-1] > ema_s[-1] and rsi_val < 70:
                signals.append(Signal(
                    symbol=symbol, side="LONG", strategy=self.name, price=price,
                    reason=f"EMA9>EMA21 · RSI {rsi_val:.1f} — yükseliş",
                    confidence=0.7))
            elif ema_f[-1] < ema_s[-1] and rsi_val > 30:
                signals.append(Signal(
                    symbol=symbol, side="SHORT", strategy=self.name, price=price,
                    reason=f"EMA9<EMA21 · RSI {rsi_val:.1f} — düşüş",
                    confidence=0.7))
        return signals
