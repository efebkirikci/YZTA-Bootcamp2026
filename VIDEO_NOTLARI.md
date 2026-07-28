# 🎬 Video Notları — CopyTrader (Efe için)

Bu doküman video çekimi sırasında sahne sahne anlatım akışını ve her sahnede
ekranda ne gösterileceğini içerir. Amaç: **Docker'da çalışan bir botun canlı
piyasa verisiyle ne yaptığını** izleyiciye net göstermek.

---

## Sahne 0 — Giriş (30 sn)

**Ekranda:** Repo (GitHub) + README

- Proje adı: **CopyTrader** — copy trading botu
- Ne yapar: Binance **public API**'den canlı piyasa verisi çeker, sinyal
  motorları ("master") karar üretir, bot ("copier") pozisyonları otomatik
  kopyalar. Paper modda simüle eder, key verilirse gerçek emir atar.
- Takım 36 · YZTA Bootcamp 2026

**Konuşma notu:** "Kripto copy trading botu. API anahtarı olmadan, tamamen
public veriyle çalışıyor. Docker ile tek komutta ayağa kalkıyor."

---

## Sahne 1 — Docker ile Kurulum (45 sn)

**Ekranda:** Terminal

```bash
git clone https://github.com/efebkirikci/YZTA-Bootcamp2026.git
cd YZTA-Bootcamp2026
docker compose up --build
```

- `docker compose up` → image build edilir, bot + dashboard başlar
- `.env` oluşturmaya gerek yok — default'larla çalışır (özel ayar istersen
  `.env.example`'ı kopyala)

**Konuşma notu:** "Tek komut. Container içinde bot dönüyor, dashboard
localhost'ta."

---

## Sahne 2 — Dashboard Açılışı (60 sn)

**Ekranda:** Tarayıcı → `http://localhost:8000`

- Üst barda: **mode: paper**, **API canlı** rozeti, tarama sayısı
- 6 stat kartı: Özsermaye, Gerçekleşen PnL, Gerçekleşmemiş PnL, Açık Pozisyon,
  Funding Toplam, Tarama
- **Canlı Piyasa** tablosu: BTC/ETH/SOL/BNB/XRP/DOGE fiyatları her 3 saniyede
  güncelleniyor (24s değişim, funding rate, hacim)
- Özsermaye eğrisi grafiği zamanla büyüyor

**Konuşma notu:** "Veriler Binance public API'den canlı geliyor. Fiyatlar
3 saniyede bir tazeleniyor. API key yok — herkes çalıştırabilir."

---

## Sahne 3 — Strateji Seçimi + Ayar Değiştirme (45 sn)

**Ekranda:** Ayarlar paneli (dashboard sağ kart)

1. Strateji dropdown'ı: `Funding Rate` → `Teknik (EMA+RSI+MACD)` → `İkisi Birden`
2. Kaydet'e bas → sağ üstte "ayar kaydedildi" onayı
3. Örn. `max_position_size_usd` 25 → 50 yap, kaydet

**Konuşma notu:** "Stratejiyi ve risk limitlerini botu durdurmadan, canlı
olarak değiştirebiliyoruz. Ayarlar SQLite'te saklanıyor, bot her taramada
güncel değeri okuyor."

---

## Sahne 4 — Sinyal Üretimi (60 sn)

**Ekranda:** Son Sinyaller listesi + Pozisyonlar tablosu

- Sinyal örneği: `XRPUSDT SHORT · EMA9<EMA21 · RSI 32.8 · MACD -0.00<-0.00 —
  düşüş momentumu`
- Funding sinyali örneği: `SOLUSDT LONG · Funding -0.0071% negatif — long'lar
  fonlama alır`
- Açılan pozisyon tabloda görünür: sembol, yön, strateji, boyut, giriş fiyatı,
  anlık PnL

**Konuşma notu:** "Bu bir 'master' sinyali — strateji motoru üretti, bot
kopyaladı. Her sinyalin gerekçesi ve güven skoru var."

---

## Sahne 5 — Canlı Veri + Olay Akışı (45 sn)

**Ekranda:** Olay Akışı (alt kart) + Canlı Piyasa tablosu

- Olaylar: `SOLUSDT LONG açıldı ($25.00, funding) @ 71.43`, funding ödemeleri,
  stop-loss/take-profit kapanışları
- Funding rate sütununun canlı değiştiğini göster

**Konuşma notu:** "Bot her 15 saniyede tarıyor; olay akışı her aksiyonu
kaydediyor. Funding ödemeleri Binance'in sabit 8 saatlik slotlarına göre
işleniyor."

---

## Sahne 6 — Veri Çekme / Export (30 sn)

**Ekranda:** Dashboard'daki export butonları (veya doğrudan URL)

- `http://localhost:8000/api/export/positions.csv` — tüm pozisyonlar
- `http://localhost:8000/api/export/signals.csv` — tüm sinyaller
- `http://localhost:8000/api/export/equity.csv` — özsermaye eğrisi
- Alternatif: `GET /api/state` → tam JSON

**Konuşma notu:** "Video analizi veya rapor için tüm veriyi CSV olarak
çekebiliyoruz. Ayrıca `/api/state` tam durum JSON'u döner."

---

## Sahne 7 — Kapanış (30 sn)

**Ekranda:** Terminal → `docker compose down`

- Özet: public API verisi → sinyal motoru → risk kontrolü → copy execution
  → canlı dashboard
- Gelecek: AI filtresi (`AI_ENABLED=true` + key ile), daha fazla strateji,
  live mod (`TRADING_MODE=live` + Binance key)

**Konuşma notu:** "Mimari modüler: yeni strateji eklemek için
`strategies/` klasörüne bir sınıf yazmak yeterli."

---

## Demo Sırasında Dikkat

- Botu başlatınca **ilk 15-30 saniye** içinde ilk sinyaller/pozisyonlar görünür
  (market feed ısınır, ilk scan çalışır)
- Funding sinyali için eşik varsayılan `%0.01` — piyasa durumuna göre sinyal
  az/çok olabilir; göstermek istersen `funding_rate_threshold` değerini
  düşürebilirsin (örn. `0.005`)
- Teknik sinyal garantisi yok — trend olmayan piyasada sinyal üretmeyebilir;
  o an başka bir sembolde sinyal çıkması muhtemel (6 sembol izleniyor)
- Dashboard'a erişim: `http://localhost:8000` (Docker portu değiştirdiysen
  `docker-compose.yml`'daki `8000:8000` kısmını güncelle)
