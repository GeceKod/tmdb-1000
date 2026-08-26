# 🎬 Güneş TV - Z-Stream & TMDB Otomatik Katalog Sistemi

Bu depo; TMDB üzerindeki en popüler ve yeni **100.000 Film** ile **100.000 Diziyi** (%100 Türk yapımı öncelikli, çift dilli, zengin kategorili ve Z-Stream doğrudan sayfa oynatma linkli) **minimal JSON formatında** üreten ve **GitHub Actions** ile her gün otomatik olarak güncelleyen tam otomatik bir katalog sistemidir.

---

## 🚀 Temel Özellikler

* **⚡ Ultra Hafif JSON:** Detaylar kullanıcı sayfaya girene kadar çekilmez; dosya boyutu %95 daha küçüktür (100k içerik $\approx$ 15 MB).
* **🇹🇷 %100 Yerli Önceliklendirme (TR Boost):** Yeşilçam'dan 2026'nın en yeni Türk dizilerine kadar tüm yerli içerikler istisnasız ilk sırada yer alır.
* **🌐 Çift Dilli Arama:** Hem Türkçe (`title`) hem orijinal/İngilizce (`original_title`) adlar tutulur; arama motoru her iki dilde de bulur.
* **🏷️ Zengin Kategoriler:** `Türk Yapımı`, `Kore Yapımı`, `Animasyon`, `Anime`, `Netflix`, `Disney+`, `Aksiyon`, `Korku`, `Dram` vb.
* **🔄 Akıllı Sıralama & Güncel Bölümler:** Yeni bölümü çıkan dizi anında listenin **en başına (Index 0)** taşınır; uygulama vitrininde 1. sırada parlar.
* **🤖 Sıfır Bakım (GitHub Actions):** Her sabah saat `08:30 UTC`'de yeni çıkan filmler ve yeni bölümler bota düşer, JSON güncellenip otomatik commit edilir.

---

## 📂 Dosya Yapısı

```text
├── .github/
│   └── workflows/
│       └── daily_sync.yml          # Her gün 08:30 UTC'de çalışan GitHub Action
├── data/
│   ├── catalog.json                # 🌟 Birleşik Tüm Katalog (Film + Dizi - 4.000 İçerik)
│   ├── movies.json                 # Sadece Filmler (2.000 İçerik)
│   └── series.json                 # Sadece Diziler (2.000 İçerik)
├── scripts/
│   ├── config.py                   # TMDB ve Z-Stream sabitleri
│   ├── tmdb_client.py              # TMDB API istemcisi & URL oluşturucu
│   ├── seed_initial.py             # İlk büyük arşivi üreten betik
│   └── update_daily.py             # Günlük yeni bölümleri en başa ekleyen bot
├── tests/
│   └── test_catalog.py             # Otomatik testler
└── README.md
```

---

## 📦 JSON Veri Modeli

```json
{
  "type": "dizi",
  "title": "The Walking Dead: Dead City",
  "original_title": "The Walking Dead: Dead City",
  "category": "Korku, Dram, Bilim Kurgu",
  "platform": "AMC",
  "imdb_id": "tt18546730",
  "imdb": "8.2",
  "year": "2026",
  "added_date": "26 Ağustos, 2026",
  "poster": "https://image.tmdb.org/t/p/w500/7gaq7sOWLa70fzUxdM21hf3RWP7.jpg",
  "url": "https://zstream.mov/media/tmdb-tv-194583-the-walking-dead-dead-city"
}
```

---

## 🛠️ Yerel Kullanım (Manuel Çalıştırma)

### 1. İlk Kataloğu Üretme (Seed):
```powershell
# Örnek test verisi (100 film + 100 dizi):
python scripts/seed_initial.py --sample

# 100.000 Film ve 100.000 Dizi Üretimi:
python scripts/seed_initial.py --movies 100000 --series 100000
```

### 2. Günlük Değişiklikleri Çekme (Update):
```powershell
python scripts/update_daily.py --limit 100
```

### 3. Testleri Çalıştırma:
```powershell
python -m unittest tests/test_catalog.py
```

---

## 📱 Güneş TV Entegrasyonu

Güneş TV uygulamanızda VOD kaynak listesi eklerken doğrudan aşağıdaki **Raw bağlantıları** kullanabilirsiniz:

* **🌟 Birleşik Tüm Katalog (100.000 Film + 100.000 Dizi = 200.000 İçerik):**
  ```text
  https://raw.githubusercontent.com/GeceKod/tmdb-1000/main/data/catalog.json
  ```

* **🎬 Sadece Film Kaynağı (Movies - 100.000 Film):**
  ```text
  https://raw.githubusercontent.com/GeceKod/tmdb-1000/main/data/movies.json
  ```

* **📺 Sadece Dizi Kaynağı (Series - 100.000 Dizi):**
  ```text
  https://raw.githubusercontent.com/GeceKod/tmdb-1000/main/data/series.json
  ```

Kullanıcı kartı tıkladığında `TmdbMetadataFetcher.kt` eksik olan tüm detayları (oyuncular, fragman, Türkçe özet, bölüm listesi) anında cihazın sistem dilinde canlı olarak çekecektir.
