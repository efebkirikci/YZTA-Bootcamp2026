# CopyTrader

Kripto copy trading botu — YZTA Bootcamp 2026 · Takim 36

Binance **public API**'sinden canli piyasa verisi ceken, sinyal motorlari
("master") ile karar ureten ve bu kararlari otomatik olarak pozisyonlara
kopyalayan ("copier") moduler bir trading botu.

## Ozellikler

- API anahtari gerektirmez — veri tamamen public endpoint'lerden gelir
- Iki strateji: **Funding Rate** (fonlama oranina gore LONG/SHORT) ve
  **Teknik** (EMA + RSI + MACD uclu momentum onayi)
- Paper mod ile risksiz simulasyon (SQLite kayitli)
- Runtime ayarlar: strateji, semboller, risk limitleri DB'den okunur
- 8 saatlik sabit funding slotlari (00/08/16 UTC) ile odeme mekanigi

## Kurulum

```bash
git clone https://github.com/efebkirikci/YZTA-Bootcamp2026.git
cd YZTA-Bootcamp2026

python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

Ozel ayar istersen: `cp .env.example .env`

## Test

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Yol Haritasi

- [x] Faz 1 — konsept ve iskelet (28 Haz - 4 Tem)
- [x] Faz 2 — cekirdek motor (5 - 12 Tem)
- [ ] Faz 3 — web dashboard (13 - 19 Tem)
- [ ] Faz 4 — Docker, AI, live mod (20 - 27 Tem)
- [ ] Faz 5 — finalize, video notlari (28 Tem - 1 Agu)

Detay: `docs/FIKIR.md` · `docs/ARCHITECTURE.md` · `docs/ROADMAP.md`
