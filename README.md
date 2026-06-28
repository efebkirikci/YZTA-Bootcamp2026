# CopyTrader

Kripto copy trading botu — YZTA Bootcamp 2026 · Takım 36

Binance public API'den canlı piyasa verisi çeken, sinyal üreten ve
pozisyonları otomatik kopyalayan modüler bir trading botu.

## Fikir

- "Master" strateji motoru sinyal üretir, bot ("copier") pozisyonları kopyalar
- API anahtarı gerekmez — piyasa verisi tamamen public endpoint'lerden gelir
- Paper mod ile risksiz simülasyon; Binance API key verilirse live mod

## Yol Haritası

- [ ] Binance public veri katmanı
- [ ] Funding rate stratejisi
- [ ] Teknik indikatör stratejisi
- [ ] Paper trading motoru + risk yönetimi
- [ ] Web dashboard (canlı görüntüleme + ayar)
- [ ] Docker dağıtımı

Detay: `docs/FIKIR.md`
