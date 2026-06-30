# Mimari (taslak)

```
Binance public API
      │  REST
      ▼
┌─────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  market     │──▶│  strategies      │──▶│  trading         │
│  feed       │   │  (master sinyal) │   │  (copier)        │
└─────────────┘   └──────────────────┘   └──────────────────┘
                          │                       │
                          ▼                       ▼
                   ┌──────────────────────────────────┐
                   │  dashboard (FastAPI + web UI)    │
                   └──────────────────────────────────┘
```

- `bot/api` — Binance REST istemcisi (public)
- `bot/strategies` — sinyal üreten strateji motorları
- `bot/trading` — pozisyon yönetimi (paper/live) + risk
- `bot/brain` — opsiyonel AI karar filtresi
- `bot/dashboard` — FastAPI + statik frontend

Detaylar geliştirme sırasında netleşecek.
