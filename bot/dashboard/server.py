"""FastAPI dashboard — localhost UI + JSON API + CSV export + WebSocket."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, Response
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

    @app.get("/api/positions")
    async def api_positions():
        prices = engine.market.prices
        return [
            {**dict(p),
             "unrealized_pnl": round(
                 engine.engine._pnl_for(p, prices.get(p["symbol"], p["entry_price"])), 2),
             "funding_collected": round(engine.engine.funding_collected(p["id"]), 4)}
            for p in engine.engine.open_positions()
        ]

    @app.get("/api/signals")
    async def api_signals(limit: int = 50):
        rows = engine.engine._conn.execute(
            "SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    @app.get("/api/market")
    async def api_market():
        return engine.market.to_dict(engine.settings.symbols())

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

    @app.post("/api/trade/close/{position_id}")
    async def api_close_position(position_id: int):
        price = engine.market.prices.get(
            next((p["symbol"] for p in engine.engine.open_positions()
                  if p["id"] == position_id), ""), 0.0)
        if not price:
            return JSONResponse({"ok": False, "error": "fiyat yok"}, status_code=400)
        res = engine.engine.close_position(position_id, price, "dashboard")
        if res.get("ok"):
            engine.push_event("close", f"#{position_id} dashboard'dan kapatildi (PnL: ${res['pnl']:.2f})")
        return res

    def _csv_response(headers: list[str], rows: list[list]) -> Response:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        w.writerows(rows)
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment"})

    @app.get("/api/export/positions.csv")
    async def export_positions():
        rows = engine.engine._conn.execute(
            "SELECT * FROM paper_positions ORDER BY id").fetchall()
        return _csv_response(list(rows[0].keys()) if rows else ["id", "symbol"],
                             [list(r) for r in rows])

    @app.get("/api/export/signals.csv")
    async def export_signals():
        rows = engine.engine._conn.execute(
            "SELECT * FROM signals ORDER BY id").fetchall()
        return _csv_response(list(rows[0].keys()) if rows else ["id", "symbol"],
                             [list(r) for r in rows])

    @app.get("/api/export/equity.csv")
    async def export_equity():
        rows = engine.engine._conn.execute(
            "SELECT * FROM equity_curve ORDER BY id").fetchall()
        return _csv_response(list(rows[0].keys()) if rows else ["ts", "equity"],
                             [list(r) for r in rows])

    @app.get("/api/export/trades.csv")
    async def export_trades():
        rows = engine.engine._conn.execute(
            "SELECT * FROM paper_trades ORDER BY id").fetchall()
        return _csv_response(list(rows[0].keys()) if rows else ["id"],
                             [list(r) for r in rows])

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
