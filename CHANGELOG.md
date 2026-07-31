# Changelog

Tüm önemli değişiklikler bu dosyada tutulur. Format: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/)
tabanlı, [SemVer](https://semver.org/) uyumlu.

## [v1.0.0] — 2026-08-01

### Eklenen
- Dockerfile + docker-compose ile tek komut kurulum (`docker compose up --build`)
- GitHub Actions CI: lint + test (Python 3.11)
- `scripts/demo.py` — video/demo için hızlı sinyal gösterimi
- CSV dışa aktarım: pozisyonlar, sinyaller, özsermaye, trade geçmişi
- MIT lisansı, CHANGELOG, Makefile (run/test/build hedefleri)

### Değişen
- README: kurulum, sprint planı, hedef kitle detaylandırıldı
- `VIDEO_NOTLARI.md` — sahne sahne video anlatım akışı eklendi

### Düzeltilen
- Paper engine `initial_capital` attribute/metod isim çakışması
- Funding slot hesaplamasında saat dilimi tutarlılığı

## [v0.9.0] — 2026-07-28

### Eklenen
- Live mod: Binance futures emirleri (market + reduceOnly kapanış)
- Opsiyonel AI sinyal filtresi (`AI_ENABLED=true` + API key)

## [v0.8.0] — 2026-07-20

### Eklenen
- FastAPI dashboard: JSON API, WebSocket canlı akış, modern tek sayfa UI
- Ayarları botu durdurmadan değiştirme (strateji, semboller, risk limitleri)
- Özsermaye eğrisi grafiği (Chart.js)

## [v0.5.0] — 2026-07-13

### Eklenen
- Teknik strateji: EMA cross + RSI + MACD üçlü momentum onayı
- Pytest test paketi (funding slotları, risk, stratejiler, paper engine)

## [v0.3.0] — 2026-07-06

### Eklenen
- Copy trading çekirdeği: market feed → sinyal üretimi → risk kontrolü →
  pozisyon kopyalama
- 8 saatlik sabit funding slotları (00/08/16 UTC) ile ödeme mekaniği

## [v0.1.0] — 2026-06-28

### Eklenen
- Proje iskeleti: paket yapısı, config, .env şablonu
- Binance public API istemcisi (fiyat, funding rate, klines)
- Funding rate stratejisi (ilk sürüm)
