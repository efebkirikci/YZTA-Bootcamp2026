# Mimari

```
┌─────────────────────────────── Docker Container ───────────────────────────────┐
│                                                                                │
│  ┌─────────────┐   public REST   ┌─────────────────────────────────────────┐   │
│  │   Binance   │◄────────────────┤  bot.main — CopyTraderApp (asyncio)     │   │
│  │  (key yok)  │                 │                                         │   │
│  └─────────────┘                 │  ├─ market_loop (3s)                    │   │
│                                  │  │   fiyat / funding / klines           │   │
│                                  │  ├─ scan_loop (15s)                     │   │
│                                  │  │   ├─ strategies/  (MASTER)           │   │
│                                  │  │   │   ├─ funding_rate                │   │
│                                  │  │   │   └─ technical (EMA+RSI+MACD)    │   │
│                                  │  │   ├─ trading/risk (limitler)         │   │
│                                  │  │   └─ trading/engine (COPIER)         │   │
│                                  │  │       └─ paper (SQLite simülasyon)   │   │
│                                  │  ├─ funding_loop (60s)                  │   │
│                                  │  │   8 saatlik slot odemeleri            │   │
│                                  │  └─ dashboard (FastAPI :8000)           │   │
│                                  └─────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Copy Trading Akisi

1. **Master** — aktif stratejiler canli market verisinden sinyal uretir
   (LONG/SHORT + gerekce + guven skoru)
2. **Risk** — RiskManager limitleri kontrol eder (max pozisyon, portfoy risk %)
3. **Copier** — uygun sinyal pozisyona cevrilir (paper: SQLite simülasyon)
4. **Bakim** — her taramada funding odemeleri + equity noktasi kaydi

## Funding Mekanigi

Binance funding **sabit 8 saatlik slotlarda** kesilir: 00/08/16 UTC.
Pozisyon acilis saatine gore degil, slot gecisine gore odeme islenir.
LONG pozisyon negatif funding'de odeme alir (-rate × size).
