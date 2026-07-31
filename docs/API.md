# CopyTrader API Referansı

Dashboard'a ek olarak bot, aynı port üzerinden JSON API ve CSV dışa aktarım
sunar. Tüm uçlar `http://localhost:8000` üzerindedir.

## Durum ve Veri

| Method | Path | Açıklama |
|---|---|---|
| GET | `/api/state` | Tam durum: meta, portföy, market, pozisyonlar, sinyaller, olaylar, özsermaye eğrisi, ayarlar |
| GET | `/api/positions` | Açık pozisyonlar (anlık PnL + toplanan funding ile) |
| GET | `/api/signals?limit=50` | Üretilen sinyal geçmişi |
| GET | `/api/market` | Canlı market anlık görüntüsü (fiyat, 24s %, funding, hacim) |
| GET | `/api/settings` | Tüm runtime ayarlar (değer + açıklama) |

## Ayarlar

| Method | Path | Açıklama |
|---|---|---|
| POST | `/api/settings` | Ayar güncelle. Body: `{"key": "max_position_size_usd", "value": "50"}` |
| POST | `/api/trade/close/{id}` | Pozisyonu kapat (paper: simülasyon, live: Binance reduceOnly emri) |

Ayarlar botu durdurmadan uygulanır — her tarama döngüsü DB'den güncel değeri okur.

## CSV Dışa Aktarım (video / analiz için)

| Method | Path | İçerik |
|---|---|---|
| GET | `/api/export/positions.csv` | Tüm pozisyonlar (açık + kapalı) |
| GET | `/api/export/signals.csv` | Tüm sinyaller |
| GET | `/api/export/equity.csv` | Özsermaye eğrisi (zaman serisi) |
| GET | `/api/export/trades.csv` | Tüm trade kayıtları (açılış + kapanış) |

## Canlı Akış

| Method | Path | Açıklama |
|---|---|---|
| WebSocket | `/ws` | 2 saniyede bir tam durum JSON'u push eder |

## Örnekler

```bash
# Tam durum
curl -s http://localhost:8000/api/state | jq '.portfolio'

# Ayar değiştir (strateji: funding | technical | both)
curl -s -X POST http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "active_strategy", "value": "both"}'

# Pozisyon kapat
curl -s -X POST http://localhost:8000/api/trade/close/1

# CSV indir
curl -s -o positions.csv http://localhost:8000/api/export/positions.csv
```
