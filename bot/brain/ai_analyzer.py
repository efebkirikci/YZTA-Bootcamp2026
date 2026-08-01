"""Optional AI signal filter (OpenAI-compatible, e.g. DeepSeek).

When AI_ENABLED=true and a valid key is present, the engine asks the model
to review the strategy signals and return a JSON decision. When disabled
or on any failure, the rule-based signals pass through untouched — the bot
never depends on the AI to function (bootcamp/demo safe).

The JSON parser uses a 3-tier fallback (direct -> markdown block -> first
brace pair) because LLM JSON output is notoriously unreliable.
"""

from __future__ import annotations

import json
import logging
import re

import httpx

logger = logging.getLogger("brain.ai")


class AIAnalyzer:
    def __init__(self, api_key: str, base_url: str, model: str, enabled: bool = False):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.enabled = enabled and bool(api_key)
        if not self.enabled:
            logger.info("AI devre dışı — kural bazlı sinyal üretimi aktif")

    async def filter_signals(self, signals: list, portfolio: dict) -> list:
        """Ask the AI which signals to execute. Returns the approved subset.
        On any error: return signals unchanged (fallback, never blocks)."""
        if not self.enabled or not signals:
            return signals
        try:
            payload = {
                "symbols": [s.symbol for s in signals],
                "signals": [
                    {"symbol": s.symbol, "side": s.side, "reason": s.reason,
                     "confidence": s.confidence}
                    for s in signals
                ],
                "portfolio": portfolio,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": (
                                "You are a crypto copy-trading risk filter. "
                                "Given signals and portfolio state, return JSON: "
                                '{"approved":[symbols to execute],"rejected":[{"symbol":..,"reason":".."}]}. '
                                "Reject anything that would over-leverage the portfolio."
                            )},
                            {"role": "user", "content": json.dumps(payload)},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 800,
                        "response_format": {"type": "json_object"},
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                data = self._parse_json(content)
                if data is None:
                    logger.warning("AI JSON parse edilemedi — sinyaller aynen geçti")
                    return signals
                approved = set(data.get("approved", []))
                out = [s for s in signals if s.symbol in approved]
                logger.info("AI %d/%d sinyali onayladı", len(out), len(signals))
                return out
        except Exception as e:  # noqa: BLE001 — fallback is the contract
            logger.warning("AI filtresi çalışmadı (%s) — sinyaller aynen geçti", e)
            return signals

    @staticmethod
    def _parse_json(content: str) -> dict | None:
        if not content:
            return None
        # Tier 1: direct
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass
        # Tier 2: markdown code block
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except (json.JSONDecodeError, TypeError):
                pass
        # Tier 3: first brace pair
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return json.loads(m.group(0))
            except (json.JSONDecodeError, TypeError):
                pass
        return None
