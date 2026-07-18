# CopyTrader API Referansi

Dashboard'a ek olarak bot, ayni port uzerinden JSON API ve CSV disa aktarim
sunar. Tum uclar `http://localhost:8000` uzerindedir.

## Durum ve Veri

| Method | Path | Aciklama |
|---|---|---|
| GET | `/api/state` | Tam durum: meta, portfoy, market, pozisyonlar, sinyaller, olaylar, ozsermaye egrisi, ayarlar |
| GET | `/api/positions` | Acik pozisyonlar (anlik PnL + toplanan funding ile) |
| GET | `/api/signals?limit=50` | Uretilen sinyal gecmisi |
| GET | `/api/market` | Canli market anlik goruntusu |
| GET | `/api/settings` | Tum runtime ayarlar |

## Ayarlar

| Method | Path | Aciklama |
|---|---|---|
| POST | `/api/settings` | Ayar guncelle. Body: `{"key": "max_position_size_usd", "value": "50"}` |
| POST | `/api/trade/close/{id}` | Pozisyonu kapat |

Ayarlar botu durdurmadan uygulanir — her tarama dongusu DB'den guncel degeri okur.

## CSV Disa Aktarim

| Method | Path | Icerik |
|---|---|---|
| GET | `/api/export/positions.csv` | Tum pozisyonlar |
| GET | `/api/export/signals.csv` | Tum sinyaller |
| GET | `/api/export/equity.csv` | Ozsermaye egrisi |
| GET | `/api/export/trades.csv` | Tum trade kayitlari |

## Canli Akis

| Method | Path | Aciklama |
|---|---|---|
| WebSocket | `/ws` | 2 saniyede bir tam durum JSON'u push eder |

## Ornekler

```bash
curl -s http://localhost:8000/api/state | jq '.portfolio'
curl -s -X POST http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "active_strategy", "value": "both"}'
curl -s -o positions.csv http://localhost:8000/api/export/positions.csv
```
