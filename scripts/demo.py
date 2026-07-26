"""Demo — tek seferlik canli sinyal gosterimi (video / sunum icin).

Binance public API'den canli veri ceker, aktif stratejilerin urettigi
sinyalleri tablo halinde basar. Botu baslatmadan stratejilerin canli
piyasada ne urettigini gostermenin en hizli yolu.

Kullanim:
    python scripts/demo.py                 # tum semboller, her iki strateji
    python scripts/demo.py --symbols BTCUSDT,ETHUSDT
    python scripts/demo.py --strategy funding
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.api.binance_client import BinanceClient  # noqa: E402
from bot.config import DEFAULT_SYMBOLS, SettingsStore  # noqa: E402
from bot.main import MarketSnapshot  # noqa: E402
from bot.strategies.funding_rate import FundingRateStrategy  # noqa: E402
from bot.strategies.technical import TechnicalStrategy  # noqa: E402


def _fmt_row(signal) -> str:
    conf = f"%{signal.confidence*100:.0f}"
    return f"  {signal.symbol:<10} {signal.side:<6} {signal.strategy:<9} " \
           f"{signal.price:>12.4f}  {conf:>4}  {signal.reason[:70]}"


async def run(symbols: list[str], strategy: str | None) -> None:
    settings = SettingsStore()
    market = MarketSnapshot()
    client = BinanceClient()

    print("CopyTrader demo — canli sinyal gosterimi")
    print("=" * 110)
    print("Market verisi cekiliyor (Binance public API)…")

    market.symbols = symbols
    prices = await client.get_all_prices()
    market.prices = {k: v for k, v in prices.items() if k in symbols}
    market.funding_rates = await client.get_funding_rates()
    for s in symbols:
        market.klines[s] = await client.get_klines(s, "1h", 120)

    print(f"  {len(symbols)} sembol · fiyatlar canli\n")

    strategies = {
        "funding": FundingRateStrategy(settings),
        "technical": TechnicalStrategy(settings),
    }
    if strategy:
        strategies = {strategy: strategies[strategy]}

    total = 0
    for name, strat in strategies.items():
        print(f"-- {strat.label} --")
        signals = await strat.scan(market)
        if not signals:
            print("  (sinyal yok — piyasa esiklerin altinda)")
        for s in signals:
            print(_fmt_row(s))
            total += 1
        print()

    print(f"Toplam {total} sinyal. Dashboard: python -m bot.main → http://localhost:8000")
    await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CopyTrader canli sinyal demo")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--strategy", choices=["funding", "technical"], default=None)
    args = parser.parse_args()
    asyncio.run(run([s.strip() for s in args.symbols.split(",") if s.strip()],
                    args.strategy))


if __name__ == "__main__":
    main()
