# Ürün Fikri — CopyTrader

## Problem

Copy trading, piyasada popüler bir kavram: iyi trader'ların işlemlerini
otomatik kopyalayarak yatırım yapmak. Ancak çoğu çözüm kapalı, pahalı veya
API anahtarı gerektiriyor. Bootcamp projesi olarak bunu **herkesin
çalıştırabileceği**, **şeffaf** ve **modüler** bir sistemle kurmak istiyoruz.

## Çözüm

Kendi "master" sinyal motorumuzu yazıyoruz:

1. **Veri katmanı** — Binance public API (fiyat, funding rate, mum verisi)
2. **Sinyal motoru (master)** — stratejiler piyasa verisinden LONG/SHORT kararı üretir
3. **Kopyalayıcı (copier)** — sinyalleri risk kontrollerinden geçirip pozisyon açar
4. **Dashboard** — süreci canlı görüntüleme ve ayar yapma

## Öne Çıkanlar

- API anahtarı olmadan tam çalışma (public veri)
- İki strateji: funding rate + teknik indikatörler
- Paper mod ile risksiz deneme
- Docker ile tek komut kurulum

## Hedef Kitle

- Kripto otomasyonu öğrenen geliştirici adayları
- Sinyal üretici + icra mimarisini inceleyenler
- Stratejilerini risksiz test etmek isteyenler
