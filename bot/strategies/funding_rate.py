"""Funding rate stratejisi — eşik bazlı sinyal üretimi.

Negatif funding → long'lar fonlama alır → LONG sinyali
Pozitif funding  → short'lar fonlama alır → SHORT sinyali
"""

import logging

from .base import Signal, Strategy

logger = logging.getLogger("strategy.funding")


class FundingRateStrategy(Strategy):
    name = "funding"
    label = "Funding Rate"

    async def scan(self, market) -> list[Signal]:
        threshold = 0.01  # %1 — ileride ayarlanabilir olacak
        signals = []
        for symbol in market.symbols:
            rate = market.funding_rates.get(symbol)
            if rate is None:
                continue
            price = market.prices.get(symbol, 0.0)
            if rate <= -threshold:
                signals.append(Signal(
                    symbol=symbol, side="LONG", strategy=self.name, price=price,
                    reason=f"Funding {rate*100:.4f}% negatif — long'lar fonlama alır",
                    confidence=min(1.0, abs(rate) / (threshold * 3))))
            elif rate >= threshold:
                signals.append(Signal(
                    symbol=symbol, side="SHORT", strategy=self.name, price=price,
                    reason=f"Funding {rate*100:.4f}% pozitif — short'lar fonlama alır",
                    confidence=min(1.0, abs(rate) / (threshold * 3))))
        return signals
