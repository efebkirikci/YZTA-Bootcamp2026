"""Binance API client — public REST + opsiyonel imzali emirler."""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"


class BinanceError(Exception):
    pass


class BinanceClient:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self._client = httpx.AsyncClient(timeout=15.0)

    # ── public market verisi ──────────────────────────────────────────
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

    # ── imzali (yalnizca live mod) ────────────────────────────────────
    def _sign(self, params: dict) -> str:
        """HMAC-SHA256 imza. Parametre sirasi korunur — sorted() YASAK
        (Binance -1022 hatasi; paper mod bunu asla yakalamaz)."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    async def _signed_request(self, method: str, path: str, params: dict | None = None) -> dict:
        if not self.api_key or not self.api_secret:
            raise BinanceError("Live islem icin BINANCE_API_KEY gerekli")
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        params["signature"] = self._sign(params)
        r = await self._client.request(
            method, f"{FUTURES_BASE}{path}", params=params,
            headers={"X-MBX-APIKEY": self.api_key})
        if r.status_code == 401:
            raise BinanceError("Binance API key gecersiz (401)")
        r.raise_for_status()
        return r.json()

    async def get_futures_balance(self) -> float:
        data = await self._signed_request("GET", "/fapi/v2/balance")
        for asset in data:
            if asset.get("asset") == "USDT":
                return float(asset.get("availableBalance", 0.0))
        return 0.0

    async def open_market_order(self, symbol: str, side: str, qty: float) -> dict:
        return await self._signed_request(
            "POST", "/fapi/v1/order",
            {"symbol": symbol, "side": side, "type": "MARKET", "quantity": qty})

    async def close_market_order(self, symbol: str, side: str, qty: float) -> dict:
        return await self._signed_request(
            "POST", "/fapi/v1/order",
            {"symbol": symbol, "side": side, "type": "MARKET",
             "quantity": qty, "reduceOnly": "true"})

    async def get_futures_position(self, symbol: str) -> dict | None:
        data = await self._signed_request("GET", "/fapi/v2/positionRisk", {"symbol": symbol})
        for p in data:
            if abs(float(p.get("positionAmt", 0))) > 0:
                return p
        return None

    @staticmethod
    def qty_from_notional(notional_usd: float, price: float, step_size: float = 0.001) -> float:
        qty = int((notional_usd / price) / step_size) * step_size
        return round(qty, 8)

    async def close(self) -> None:
        await self._client.aclose()
