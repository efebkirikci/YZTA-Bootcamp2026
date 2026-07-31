# CopyTrader — Mimari

YZTA Bootcamp 2026 · Takım 36
Copy trading bot: canlı piyasa verisini **public API**'den alır, sinyal motorları
("master") karar üretir, motor ("copier") pozisyonları kopyalar. Paper modda
varsayılan çalışır, Binance API key verilirse gerçek emir atabilir.

## Genel Bakış

```
┌─────────────────────────────── Docker Container ───────────────────────────────┐
│                                                                                │
│  ┌─────────────┐   public REST   ┌─────────────────────────────────────────┐   │
│  │   Binance   │◄────────────────┤  bot.main — CopyTraderApp (asyncio)     │   │
│  │  (API, key  │                 │                                         │   │
│  │   gerekmez) │                 │  ┌─ market_loop (3s)                    │   │
│  └─────────────┘                 │  │   fiyat / funding / 24h ticker       │   │
│                                  │  │                                     │   │
│                                  │  ├─ scan_loop (15s)                    │   │
│                                  │  │   ├─ strategies/  (MASTER)          │   │
│                                  │  │   │   ├─ funding_rate               │   │
│                                  │  │   │   └─ technical (EMA+RSI+MACD)   │   │
│                                  │  │   ├─ brain/ai_analyzer (opsiyonel)  │   │
│                                  │  │   ├─ trading/risk (limitler)        │   │
│                                  │  │   └─ trading/engine (COPIER)        │   │
│                                  │  │       ├─ paper (SQLite simülasyon)  │   │
│                                  │  │       └─ live (Binance emir, key)   │   │
│                                  │  │                                     │   │
│                                  │  ├─ funding_loop (60s)                 │   │
│                                  │  │   8 saatlik slot ödemeleri           │   │
│                                  │  │                                     │   │
│                                  │  └─ dashboard (FastAPI :8000)          │   │
│                                  │      ├─ /api/*  JSON + CSV export      │   │
│                                  │      └─ /ws     WebSocket canlı akış   │   │
│                                  └──────────────────┬──────────────────────┘   │
│                                                     │                         │
│   Tarayıcı ◄──────────────── localhost:8000 ────────┘                         │
│   (dashboard: grafik, pozisyonlar, ayarlar, log)                               │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Bileşenler

| Modül | Dosya | Sorumluluk |
|---|---|---|
| **Orchestrator** | `bot/main.py` | 3 asyncio loop + dashboard; sinyal→pozisyon kopyalama |
| **Market feed** | `bot/api/binance_client.py` | Public REST: fiyat, 24h ticker, klines, funding rate; opsiyonel imzalı emir |
| **Funding stratejisi** | `bot/strategies/funding_rate.py` | |rate| ≥ eşik → LONG (negatif) / SHORT (pozitif) |
| **Teknik strateji** | `bot/strategies/technical.py` | EMA cross + RSI + MACD üçlü onay |
| **AI filtresi** | `bot/brain/ai_analyzer.py` | Opsiyonel; JSON karar, 3 katmanlı parse, fallback = sinyaller aynen geçer |
| **Risk yönetimi** | `bot/trading/risk.py` | Max pozisyon, açık pozisyon, portföy risk %, günlük kayıp |
| **Paper engine** | `bot/trading/paper_engine.py` | SQLite pozisyon/trade/ödeme, 8 saatlik funding slotları, SL/TP |
| **Live engine** | `bot/trading/live_engine.py` | Paper ledger üstünde gerçek Binance futures emirleri |
| **Dashboard** | `bot/dashboard/server.py` + `static/` | FastAPI JSON/CSV/WS + tek sayfa modern UI |

## Copy Trading Akışı (scan_once)

1. **Master** — aktif strateji(ler) canlı market anlık görüntüsünden sinyal üretir
   (`LONG` / `SHORT` + gerekçe + güven skoru)
2. **AI filtresi** (opsiyonel) — key varsa sinyalleri onaylar/reddeder; yoksa
   veya hata olursa sinyaller aynen geçer (bot AI'a bağımlı DEĞİL)
3. **Risk** — `RiskManager.can_open()`: limitler kontrol edilir
4. **Copier** — uygun sinyal pozisyona çevrilir:
   - paper: `PaperEngine.open_position()` (fiyat anlık snapshot'tan)
   - live: `LiveEngine.open_position_live()` (Binance market emri + ledger)
5. **Bakım** — her scan'de SL/TP kontrolleri + funding ödemeleri + equity noktası

## Funding Ödeme Mekaniği

Binance funding **sabit 8 saatlik slotlarda** kesilir: **00:00 / 08:00 / 16:00 UTC**.
Pozisyon açılış saatine göre değil, slot geçişine göre ödeme işlenir:

- LONG pozisyon, negatif funding'de ödeme **alır** → `amount = -rate × size`
- SHORT pozisyon, pozitif funding'de ödeme **alır** → `amount = +rate × size`

`funding_slots_between(start, end)` geçilen slotları hesaplar; her slot için
`paper_payments` tablosuna kayıt düşülür.

## Risk Limitleri (dashboard'dan canlı değiştirilir)

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `max_open_positions` | 3 | Eşzamanlı açık pozisyon sınırı |
| `max_position_size_usd` | 25 | Pozisyon başına max USD |
| `max_portfolio_risk_pct` | 50 | Özsermayenin %X'i pozisyonda |
| `stop_loss_pct` | 5.0 | Zarar kesme |
| `take_profit_pct` | 8.0 | Kar alma |
| `max_daily_loss_usd` | 20 | Günlük kayıp devre kesici |

## Veri Akışı (Efe video / demo için)

- **Canlı market**: `GET /api/market` (fiyat, 24s değişim, funding, hacim)
- **Pozisyonlar**: `GET /api/positions` · **Sinyaller**: `GET /api/signals`
- **CSV dışa aktar**: `/api/export/positions.csv`, `/api/export/signals.csv`,
  `/api/export/equity.csv`, `/api/export/trades.csv`
- **Canlı akış**: `WS /ws` (2 saniyede bir tam state)

## Güvenlik Notları

- Binance **public** endpoint'ler API key gerektirmez; bot key'siz tam çalışır
- `TRADING_MODE=live` + key verilmedikçe **gerçek emir atılmaz**
- `BINANCE_API_KEY`/`SECRET` yalnızca `.env`'de tutulur (repo'ya asla girmez)
- HMAC imzalama parametre sırasını korur (`sorted()` YASAK — Binance -1022)
- Kapanış emirleri `reduceOnly` kullanır (yanlışlıkla ters pozisyon açmaz)
