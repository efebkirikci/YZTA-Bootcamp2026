"""Funding rate strategy — the classic "collect the funding" copy signal.

Logic (v3, corrected fixed-slot mechanics):
- Read live funding rates from Binance futures premiumIndex (public API).
- |rate| above threshold → signal:
    * negative funding → longs get paid → LONG signal
    * positive funding → shorts get paid → SHORT signal
- The engine holds the position across the fixed 8h slots (00/08/16 UTC)
  and the paper engine credits funding payments per slot crossed.
"""

from __future__ import annotations

import logging

from .base import Signal, Strategy

logger = logging.getLogger("strategy.funding")


class FundingRateStrategy(Strategy):
    name = "funding"
    label = "Funding Rate"

    async def scan(self, market) -> list[Signal]:
        if not market.funding_rates:
            return []
        threshold = float(self.settings.get_typed("funding_rate_threshold") or 0.01)
        signals: list[Signal] = []
        for symbol in market.symbols:
            rate = market.funding_rates.get(symbol)
            if rate is None:
                continue
            price = market.prices.get(symbol, 0.0)
            if rate <= -threshold:
                confidence = min(1.0, abs(rate) / (threshold * 3))
                signals.append(Signal(
                    symbol=symbol, side="LONG", strategy=self.name, price=price,
                    reason=f"Funding {rate*100:.4f}% negatif — long'lar fonlama alır",
                    confidence=round(confidence, 3),
                    meta={"funding_rate": rate},
                ))
            elif rate >= threshold:
                confidence = min(1.0, abs(rate) / (threshold * 3))
                signals.append(Signal(
                    symbol=symbol, side="SHORT", strategy=self.name, price=price,
                    reason=f"Funding {rate*100:.4f}% pozitif — short'lar fonlama alır",
                    confidence=round(confidence, 3),
                    meta={"funding_rate": rate},
                ))
        return signals
