"""Binance public API client (v1) — read-only market data.

Sadece public endpoint'ler: fiyat ve funding rate. API anahtarı gerekmez.
"""

import httpx

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"


class BinanceClient:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_ticker_price(self, symbol: str) -> float:
        r = await self._client.get(
            f"{SPOT_BASE}/api/v3/ticker/price", params={"symbol": symbol})
        r.raise_for_status()
        return float(r.json()["price"])

    async def get_all_prices(self) -> dict[str, float]:
        r = await self._client.get(f"{SPOT_BASE}/api/v3/ticker/price")
        r.raise_for_status()
        return {item["symbol"]: float(item["price"]) for item in r.json()}

    async def get_funding_rates(self) -> dict[str, float]:
        """Tüm USDT perpetual'ların anlık funding rate'i."""
        r = await self._client.get(f"{FUTURES_BASE}/fapi/v1/premiumIndex")
        r.raise_for_status()
        out = {}
        for item in r.json():
            symbol = item.get("symbol", "")
            if symbol.endswith("USDT"):
                out[symbol] = float(item.get("lastFundingRate", 0.0))
        return out

    async def close(self) -> None:
        await self._client.aclose()
