"""Funding rate stratejisi (v1) — eşik bazlı sinyal üretimi.

Negatif funding → long'lar fonlama alır → LONG sinyali
Pozitif funding  → short'lar fonlama alır → SHORT sinyali
"""

import logging

from .base import Signal

logger = logging.getLogger("strategy.funding")

THRESHOLD = 0.01  # %1


async def scan_funding(market) -> list[Signal]:
    signals = []
    for symbol in market.symbols:
        rate = market.funding_rates.get(symbol)
        if rate is None:
            continue
        price = market.prices.get(symbol, 0.0)
        if rate <= -THRESHOLD:
            signals.append(Signal(
                symbol=symbol, side="LONG", strategy="funding", price=price,
                reason=f"Funding {rate*100:.4f}% negatif — long'lar fonlama alır"))
        elif rate >= THRESHOLD:
            signals.append(Signal(
                symbol=symbol, side="SHORT", strategy="funding", price=price,
                reason=f"Funding {rate*100:.4f}% pozitif — short'lar fonlama alır"))
    return signals
