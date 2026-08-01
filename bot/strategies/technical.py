"""Technical indicator strategy — EMA cross + RSI + MACD momentum.

The "master" trend-following signal: all three indicators must agree on
direction before a copy signal fires. Pure numpy on public klines data —
no API key, no external service.

Signal rules (per symbol, on the 1h close):
- LONG  when EMA_fast > EMA_slow AND RSI < 70 (not yet overbought)
         AND MACD line > signal line
- SHORT when EMA_fast < EMA_slow AND RSI > 30 (not yet oversold)
         AND MACD line < signal line
- Otherwise FLAT (no signal).
"""

from __future__ import annotations

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
    """Wilder's RSI on the last value."""
    if len(values) < period + 1:
        return 50.0
    deltas = np.diff(values[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(values: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    """Returns (macd_line, signal_line) at the latest bar."""
    if len(values) < slow + signal:
        return 0.0, 0.0
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)
    macd_line = ema_fast - ema_slow
    valid = macd_line[~np.isnan(macd_line)]
    if len(valid) < signal:
        return 0.0, 0.0
    sig = ema(valid, signal)
    return float(macd_line[-1]), float(sig[-1])


class TechnicalStrategy(Strategy):
    name = "technical"
    label = "Teknik (EMA+RSI+MACD)"

    async def scan(self, market) -> list[Signal]:
        signals: list[Signal] = []
        fast_p = int(self.settings.get_typed("ema_fast") or 9)
        slow_p = int(self.settings.get_typed("ema_slow") or 21)
        rsi_p = int(self.settings.get_typed("rsi_period") or 14)
        rsi_lo = float(self.settings.get_typed("rsi_oversold") or 30)
        rsi_hi = float(self.settings.get_typed("rsi_overbought") or 70)

        for symbol in market.symbols:
            candles = market.klines.get(symbol)
            if not candles or len(candles) < slow_p + 5:
                continue
            closes = np.array([c["close"] for c in candles], dtype=float)
            price = float(closes[-1])

            ema_f = ema(closes, fast_p)
            ema_s = ema(closes, slow_p)
            if np.isnan(ema_f[-1]) or np.isnan(ema_s[-1]):
                continue
            rsi_val = rsi(closes, rsi_p)
            macd_line, sig_line = macd(closes)

            trend_up = ema_f[-1] > ema_s[-1]
            trend_down = ema_f[-1] < ema_s[-1]

            if trend_up and rsi_val < rsi_hi and macd_line > sig_line:
                signals.append(Signal(
                    symbol=symbol, side="LONG", strategy=self.name, price=price,
                    reason=(
                        f"EMA{fast_p}>EMA{slow_p} · RSI {rsi_val:.1f} · "
                        f"MACD {macd_line:+.2f}>{sig_line:+.2f} — yükseliş momentumu"
                    ),
                    confidence=0.75,
                    meta={"ema_fast": round(float(ema_f[-1]), 2),
                          "ema_slow": round(float(ema_s[-1]), 2),
                          "rsi": round(rsi_val, 1),
                          "macd": round(macd_line, 3)},
                ))
            elif trend_down and rsi_val > rsi_lo and macd_line < sig_line:
                signals.append(Signal(
                    symbol=symbol, side="SHORT", strategy=self.name, price=price,
                    reason=(
                        f"EMA{fast_p}<EMA{slow_p} · RSI {rsi_val:.1f} · "
                        f"MACD {macd_line:+.2f}<{sig_line:+.2f} — düşüş momentumu"
                    ),
                    confidence=0.75,
                    meta={"ema_fast": round(float(ema_f[-1]), 2),
                          "ema_slow": round(float(ema_s[-1]), 2),
                          "rsi": round(rsi_val, 1),
                          "macd": round(macd_line, 3)},
                ))
        return signals
