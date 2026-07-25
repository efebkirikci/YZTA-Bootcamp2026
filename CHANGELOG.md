# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) tabanli,
[SemVer](https://semver.org/) uyumlu.

## [v0.8.0] — 2026-07-20

### Eklenen
- FastAPI dashboard: JSON API, WebSocket canli akis, modern tek sayfa UI
- Ayarlari botu durdurmadan degistirme (strateji, semboller, risk limitleri)
- Ozsermaye egrisi grafigi (Chart.js)
- CSV disa aktarim uclari

## [v0.5.0] — 2026-07-13

### Eklenen
- Teknik strateji: EMA cross + RSI + MACD uclu momentum onayi
- Pytest test paketi (funding slotlari, risk, stratejiler, paper engine)

## [v0.3.0] — 2026-07-06

### Eklenen
- Copy trading cekirdegi: market feed → sinyal uretimi → risk kontrolu →
  pozisyon kopyalama
- 8 saatlik sabit funding slotlari (00/08/16 UTC) ile odeme mekanigi
- Stop-loss / take-profit otomatik cikislar

## [v0.1.0] — 2026-06-28

### Eklenen
- Proje iskeleti: paket yapisi, config, .env sablonu
- Binance public API istemcisi (fiyat, funding rate, klines)
- Funding rate stratejisi (ilk surum)
