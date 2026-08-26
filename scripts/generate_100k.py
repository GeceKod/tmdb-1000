"""
100.000 Film ve 100.000 Dizi Toplu Katalog Üreticisi (Daily Export Engine)
TMDB'nin 1.2 milyon film ve 230 bin dizilik resmi günlük export dosyasını indirir,
popülerlik sırasına göre en iyi 100.000 Film ve 100.000 Diziyi çıkarıp
minimal JSON formatında data/ dizinine kaydeder.
"""

import os
import sys
import json
import gzip
import urllib.request
from datetime import datetime, timedelta

# Windows terminal UTF-8 ayarı
sys.stdout.reconfigure(encoding='utf-8')

# Script klasörünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TMDB_EXPORTS_URL
from tmdb_client import (
    slugify,
    build_zstream_movie_url,
    build_zstream_tv_url,
    format_turkish_date
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def download_and_sort_export(export_type="movie_ids", top_n=100000):
    """
    TMDB Daily Export dosyasını indirir, yetişkin içerikleri filtreler
    ve popülerlik sırasına göre en yüksek top_n içeriği döndürür.
    """
    target_date = datetime.utcnow() - timedelta(days=1)
    date_str = target_date.strftime("%m_%d_%Y")
    url = f"{TMDB_EXPORTS_URL}/{export_type}_{date_str}.json.gz"
    
    print(f"[*] TMDB Daily Export indiriliyor ({export_type}): {url} ...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    entries = []
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for line in gz:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if not line_str:
                        continue
                    try:
                        item = json.loads(line_str)
                        if item.get("adult", False):
                            continue
                        # Boş başlıkları atla
                        name = item.get("original_title") or item.get("original_name")
                        if not name or len(name.strip()) == 0:
                            continue
                        entries.append(item)
                    except Exception:
                        continue
    except Exception as e:
        print(f"[-] Hata ({e}), bir önceki gün deneniyor...", file=sys.stderr)
        prev_date = target_date - timedelta(days=1)
        url_prev = f"{TMDB_EXPORTS_URL}/{export_type}_{prev_date.strftime('%m_%d_%Y')}.json.gz"
        req_prev = urllib.request.Request(url_prev, headers=headers)
        with urllib.request.urlopen(req_prev, timeout=60) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for line in gz:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str:
                        try:
                            item = json.loads(line_str)
                            if not item.get("adult", False):
                                entries.append(item)
                        except Exception:
                            continue

    print(f"[✓] Toplam {len(entries)} adet geçerli içerik okundu. Popülerliğe göre sıralanıyor...")
    # Popülerliğe göre azalan sırala
    entries.sort(key=lambda x: x.get("popularity", 0.0), reverse=True)
    return entries[:top_n]

def build_100k_catalog(movies_count=100000, series_count=100000):
    os.makedirs(DATA_DIR, exist_ok=True)
    today_str = format_turkish_date()
    
    # 1. Mevcut zenginleştirilmiş verileri yükle (varsa koru)
    existing_movies = {}
    existing_series = {}
    
    movie_file = os.path.join(DATA_DIR, "movies.json")
    if os.path.exists(movie_file):
        try:
            with open(movie_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    existing_movies[item.get("tmdb_id")] = item
        except Exception:
            pass
            
    series_file = os.path.join(DATA_DIR, "series.json")
    if os.path.exists(series_file):
        try:
            with open(series_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    existing_series[item.get("tmdb_id")] = item
        except Exception:
            pass

    # 2. FİLMLERİ ÜRET (100.000)
    raw_movies = download_and_sort_export("movie_ids", movies_count)
    final_movies = []
    
    print(f"[*] {len(raw_movies)} film minimal JSON formatına dönüştürülüyor...")
    for item in raw_movies:
        m_id = item["id"]
        # Eğer elimizde zaten afişi/kategorisi olan zengin kayıt varsa onu kullan
        if m_id in existing_movies:
            item_data = existing_movies[m_id]
            if "genres" not in item_data or not item_data["genres"]:
                cat_str = item_data.get("category", "Film")
                item_data["genres"] = [g.strip() for g in cat_str.split(",") if g.strip()]
            final_movies.append(item_data)
            continue
            
        title = item.get("original_title", "")
        url = build_zstream_movie_url(m_id, title)
        
        final_movies.append({
            "type": "film",
            "tmdb_id": m_id,
            "title": title,
            "original_title": title,
            "genres": ["Film"],
            "category": "Film",
            "platform": "Platform Dışı",
            "imdb_id": "",
            "imdb": "",
            "year": "",
            "added_date": today_str,
            "poster": "",
            "url": url
        })

    with open(movie_file, "w", encoding="utf-8") as f:
        json.dump(final_movies, f, ensure_ascii=False, indent=2)
    m_size = os.path.getsize(movie_file) / (1024 * 1024)
    print(f"[✓] 'movies.json' hazırlandı: {len(final_movies)} Film ({m_size:.2f} MB)")

    # 3. DİZİLERİ ÜRET (100.000)
    raw_series = download_and_sort_export("tv_series_ids", series_count)
    final_series = []
    
    print(f"[*] {len(raw_series)} dizi minimal JSON formatına dönüştürülüyor...")
    for item in raw_series:
        s_id = item["id"]
        if s_id in existing_series:
            item_data = existing_series[s_id]
            if "genres" not in item_data or not item_data["genres"]:
                cat_str = item_data.get("category", "Dizi")
                item_data["genres"] = [g.strip() for g in cat_str.split(",") if g.strip()]
            final_series.append(item_data)
            continue
            
        name = item.get("original_name", "")
        url = build_zstream_tv_url(s_id, name)
        
        final_series.append({
            "type": "dizi",
            "tmdb_id": s_id,
            "title": name,
            "original_title": name,
            "genres": ["Dizi"],
            "category": "Dizi",
            "platform": "Platform Dışı",
            "imdb_id": "",
            "imdb": "",
            "year": "",
            "added_date": today_str,
            "poster": "",
            "url": url
        })

    with open(series_file, "w", encoding="utf-8") as f:
        json.dump(final_series, f, ensure_ascii=False, indent=2)
    s_size = os.path.getsize(series_file) / (1024 * 1024)
    print(f"[✓] 'series.json' hazırlandı: {len(final_series)} Dizi ({s_size:.2f} MB)")

    # 4. BİRLEŞİK KATALOG (catalog.json - 200.000 İçerik)
    catalog_file = os.path.join(DATA_DIR, "catalog.json")
    print(f"[*] 'catalog.json' birleşik katalog oluşturuluyor ({len(final_movies) + len(final_series)} içerik)...")
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(final_movies + final_series, f, ensure_ascii=False, indent=2)
    c_size = os.path.getsize(catalog_file) / (1024 * 1024)
    print(f"[✓] 'catalog.json' hazırlandı: {len(final_movies) + len(final_series)} İçerik ({c_size:.2f} MB)")

if __name__ == "__main__":
    print("=" * 60)
    print("100.000 FİLM & 100.000 DİZİ KATALOG ÜRETİMİ BAŞLATILDI")
    print("=" * 60)
    build_100k_catalog(100000, 100000)
    print("=" * 60)
    print("TAMAMLANDI!")
    print("=" * 60)
