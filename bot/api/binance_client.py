"""Binance public API client — REST only, no API key required.

Covers everything the copy-trading engine needs from the public market:
24h tickers (price), klines (indicators), funding rates (perp premiumIndex).
All endpoints are public; live trading (optional) uses the same client with
API keys for order placement only.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("binance")

SPOT_BASE = "https://api.binance.com"
FUTURES_BASE = "https://fapi.binance.com"


class BinanceError(Exception):
    pass


class BinanceClient:
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── public market data ────────────────────────────────────────────
    async def get_ticker_price(self, symbol: str) -> float:
        """Last trade price for a spot symbol."""
        client = await self._get_client()
        r = await client.get(f"{SPOT_BASE}/api/v3/ticker/price", params={"symbol": symbol})
        r.raise_for_status()
        return float(r.json()["price"])

    async def get_all_prices(self) -> dict[str, float]:
        """Price map for all spot symbols (one request, cached server-side)."""
        client = await self._get_client()
        r = await client.get(f"{SPOT_BASE}/api/v3/ticker/price")
        r.raise_for_status()
        return {item["symbol"]: float(item["price"]) for item in r.json()}

    async def get_24h_tickers(self) -> dict[str, dict]:
        """24h stats for all symbols: lastPrice, priceChangePercent, volume."""
        client = await self._get_client()
        r = await client.get(f"{SPOT_BASE}/api/v3/ticker/24hr")
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
        """OHLCV candles. interval: 5m|15m|1h|4h|1d …"""
        client = await self._get_client()
        r = await client.get(
            f"{SPOT_BASE}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        r.raise_for_status()
        return [
            {
                "open_time": int(k[0]),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            for k in r.json()
        ]

    async def get_funding_rates(self) -> dict[str, float]:
        """Current funding rate for every USDT perpetual (premiumIndex)."""
        client = await self._get_client()
        r = await client.get(f"{FUTURES_BASE}/fapi/v1/premiumIndex")
        r.raise_for_status()
        out = {}
        for item in r.json():
            symbol = item.get("symbol", "")
            if symbol.endswith("USDT"):
                out[symbol] = float(item.get("lastFundingRate", 0.0))
        return out

    async def get_funding_rate_history(self, symbol: str, limit: int = 20) -> list[dict]:
        """Recent funding rate history for a symbol."""
        client = await self._get_client()
        r = await client.get(
            f"{FUTURES_BASE}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
        r.raise_for_status()
        return [
            {"time": int(item["fundingTime"]), "rate": float(item["fundingRate"])}
            for item in r.json()
        ]

    # ── authenticated (live mode only) ────────────────────────────────
    def _sign(self, params: dict) -> str:
        """HMAC-SHA256 signature. NEVER sort params — Binance requires
        insertion order (paper mode never catches this; -1022 on live)."""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()

    async def _signed_request(self, method: str, path: str, params: dict | None = None) -> dict:
        if not self.api_key or not self.api_secret:
            raise BinanceError("Live işlem için BINANCE_API_KEY gerekli")
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000
        params["signature"] = self._sign(params)
        client = await self._get_client()
        r = await client.request(
            method,
            f"{FUTURES_BASE}{path}",
            params=params,
            headers={"X-MBX-APIKEY": self.api_key},
        )
        if r.status_code == 401:
            raise BinanceError("Binance API key geçersiz (401)")
        r.raise_for_status()
        return r.json()

    async def get_futures_balance(self) -> float:
        """USDT available balance in futures wallet (live mode)."""
        data = await self._signed_request("GET", "/fapi/v2/balance")
        for asset in data:
            if asset.get("asset") == "USDT":
                return float(asset.get("availableBalance", 0.0))
        return 0.0

    async def open_market_order(self, symbol: str, side: str, qty: float) -> dict:
        """Open a futures market order. side: BUY (LONG) | SELL (SHORT)."""
        return await self._signed_request(
            "POST", "/fapi/v1/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": qty,
            },
        )

    async def close_market_order(self, symbol: str, side: str, qty: float) -> dict:
        """Close with reduceOnly to avoid accidental position flip."""
        return await self._signed_request(
            "POST", "/fapi/v1/order",
            {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": qty,
                "reduceOnly": "true",
            },
        )

    async def get_futures_position(self, symbol: str) -> dict | None:
        data = await self._signed_request(
            "GET", "/fapi/v2/positionRisk", {"symbol": symbol}
        )
        for p in data:
            if abs(float(p.get("positionAmt", 0))) > 0:
                return p
        return None

    # ── shared helpers ────────────────────────────────────────────────
    @staticmethod
    def qty_from_notional(notional_usd: float, price: float, step_size: float = 0.001) -> float:
        qty = notional_usd / price
        # floor to step size
        qty = int(qty / step_size) * step_size
        return round(qty, 8)
