"""Configuration — environment-based settings (v1)."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SYMBOLS = [s.strip() for s in
           os.getenv("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT").split(",") if s.strip()]
SCAN_INTERVAL_SEC = int(os.getenv("SCAN_INTERVAL_SEC", "15"))
