"""FastAPI dashboard — localhost UI + JSON API + WebSocket."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("dashboard")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SettingUpdate(BaseModel):
    key: str
    value: str


def create_dashboard(engine) -> FastAPI:
    app = FastAPI(title="CopyTrader Dashboard", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/api/state")
    async def api_state():
        return engine.dashboard_state()

    @app.get("/api/settings")
    async def api_settings():
        return engine.settings.all()

    @app.post("/api/settings")
    async def api_setting_update(body: SettingUpdate):
        key, value = body.key.strip(), body.value.strip()
        if key not in engine.settings.all():
            return JSONResponse({"ok": False, "error": "bilinmeyen ayar"}, status_code=400)
        engine.settings.set(key, value)
        engine.push_event("settings", f"Ayar guncellendi: {key} = {value}")
        return {"ok": True}

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
