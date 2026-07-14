"""FastAPI dashboard — localhost UI + JSON API + WebSocket."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("dashboard")

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_dashboard(engine) -> FastAPI:
    app = FastAPI(title="CopyTrader Dashboard", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/api/state")
    async def api_state():
        return engine.dashboard_state()

    @app.websocket("/ws")
    async def ws_feed(ws: WebSocket):
        await ws.accept()
        try:
            while True:
                await ws.send_json(engine.dashboard_state())
                await asyncio.sleep(2)
        except (WebSocketDisconnect, RuntimeError):
            pass

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app
