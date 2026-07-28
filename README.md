# **Takım İsmi**

Takım 36

# Ürün İle İlgili Bilgiler

## Takım Elemanları

- Samet Yılmaz Temel (Adli Bilişim Mühendisliği, Fırat Üniversitesi)
- _(diğer üyeler buraya eklenecek)_

## Ürün İsmi

**CopyTrader** — Kripto Copy Trading Botu

## Ürün Açıklaması

CopyTrader, Binance'in **public API**'sinden canlı piyasa verisi çeken, sinyal
motorları ("master") ile karar üreten ve bu kararları otomatik olarak
pozisyonlara kopyalayan ("copier") modüler bir kripto copy trading botudur.

- **API anahtarı gerektirmez** — piyasa verisi tamamen public endpoint'lerden
  alınır; bot sıfır konfigürasyonla çalışır
- **Docker ile tek komutta kurulur** — `docker compose up --build`
- **Modern web dashboard** — localhost'ta çalışır: canlı fiyatlar, özsermaye
  grafiği, pozisyonlar, sinyaller, olay akışı ve canlı ayar değiştirme
- **İki strateji motoru**: Funding Rate (fonlama oranına göre LONG/SHORT) ve
  Teknik (EMA + RSI + MACD üçlü momentum onayı) — dashboard'dan seçilir
- **Paper mod varsayılan** (simülasyon, risksiz); Binance API key verilirse
  **live mod** ile gerçek emir atar
- **Opsiyonel AI filtresi** — key tanımlanırsa sinyalleri yapay zeka onaylar;
  tanımlanmazsa kural bazlı motor aynen çalışır

## Ürün Özellikleri

- Canlı piyasa verisi: fiyat, 24s değişim, hacim, funding rate (3 sn tazeleme)
- Funding rate stratejisi: 8 saatlik sabit slotlara göre fonlama toplama
- Teknik strateji: EMA cross + RSI + MACD üçlü onay ile LONG/SHORT sinyali
- Risk yönetimi: max pozisyon, portföy risk %, stop-loss/take-profit, günlük
  kayıp devre kesici
- WebSocket ile 2 saniyede bir güncellenen canlı dashboard
- Ayarları botu durdurmadan değiştirme (strateji, semboller, risk limitleri)
- CSV dışa aktarım: pozisyonlar, sinyaller, özsermaye, trade geçmişi
- JSON API: `/api/state`, `/api/positions`, `/api/market`, `/api/signals`
- SQLite kalıcılık: tüm pozisyon/trade/sinyal geçmişi restart'ta korunur

## Hedef Kitle

- Kripto copy trading kavramını öğrenmek isteyen geliştirici adayları
- Piyasa verisiyle çalışan otomasyon sistemlerine ilgi duyan öğrenciler
- Sinyal üretici + otomatik icra mimarisini incelemek isteyenler
- Backtest/paper trading ile strateji denemek isteyen yatırımcılar
- Bootcamp jürisi: modüler mimari, Docker dağıtımı, canlı veri entegrasyonu

## Product Backlog URL

https://github.com/efebkirikci/YZTA-Bootcamp2026

---

# Sprint 1

- [x] Proje konsepti: copy trading modeli (master sinyal → copier pozisyon)
- [x] Binance public API entegrasyonu (fiyat, funding rate, klines)
- [x] Funding rate strateji motoru
- [x] Paper trading engine (SQLite) + risk yönetimi
- [x] Orchestrator (asyncio: market feed + tarama + funding slotları)

# Sprint 2

- [x] Teknik strateji motoru (EMA + RSI + MACD)
- [x] FastAPI dashboard + WebSocket canlı akış
- [x] Modern frontend (grafik, tablolar, ayarlar, olay akışı)
- [x] Dockerfile + docker-compose (tek komut kurulum)
- [x] CSV export + JSON API uçları

# Sprint 3

- [x] Opsiyonel AI sinyal filtresi (fallback = kural bazlı)
- [x] Live mod (Binance futures emirleri, reduceOnly kapanış)
- [x] Dokümantasyon: mimari, video notları, kurulum
- [x] Docker'da uçtan uca doğrulama (canlı veri + pozisyon açma)

---

## Hızlı Başlangıç

```bash
git clone https://github.com/efebkirikci/YZTA-Bootcamp2026.git
cd YZTA-Bootcamp2026

# Docker ile (önerilen):
docker compose up --build
# → http://localhost:8000

# Docker olmadan (Python 3.11+):
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python -m bot.main
# → http://localhost:8000
```

Detaylı mimari: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
Video anlatım notları: [VIDEO_NOTLARI.md](VIDEO_NOTLARI.md)
