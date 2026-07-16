"""Binance public API client — REST, API anahtari gerekmez."""

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

    async def get_24h_tickers(self) -> dict[str, dict]:
        r = await self._client.get(f"{SPOT_BASE}/api/v3/ticker/24hr")
        r.raise_for_status()
        out = {}
        for item in r.json():
            out[item["symbol"]] = {
                "price": float(item["lastPrice"]),
                "change_pct": float(item["priceChangePercent"]),
                "volume": float(item["volume"]),
                "high": float(item["highPrice"]),
                "low": float(item["lowPrice"]),
            }
        return out

    async def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> list[dict]:
        r = await self._client.get(
            f"{SPOT_BASE}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit})
        r.raise_for_status()
        return [
            {"open_time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
             "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
            for k in r.json()
        ]

    async def get_funding_rates(self) -> dict[str, float]:
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
