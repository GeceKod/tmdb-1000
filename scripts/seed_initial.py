"""
İlk Büyük Arşiv Üretici (Seed Initial Catalog)
TMDB'deki en popüler ve yeni filmleri/dizileri (%100 Türk yapımı öncelikli)
minimal JSON formatında data/movies.json ve data/series.json dosyalarına kaydeder.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

# Windows terminal UTF-8 ayarı
sys.stdout.reconfigure(encoding='utf-8')

# Script klasörünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TMDB_IMAGE_BASE_URL
from tmdb_client import (
    tmdb_request,
    build_zstream_movie_url,
    build_zstream_tv_url,
    resolve_categories,
    resolve_platform,
    format_turkish_date
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def fetch_turkish_content(media_type="movie", max_pages=50):
    """
    TMDB'deki tüm Türk yapımı içerikleri (%100 öncelikli havuz) çeker.
    """
    print(f"[*] Türk yapımı {media_type} içerikleri taranıyor (max {max_pages} sayfa)...")
    results = []
    endpoint = f"/discover/{media_type}"
    today_str = format_turkish_date()
    
    for page in range(1, max_pages + 1):
        params = {
            "page": page,
            "sort_by": "popularity.desc",
            "with_original_language": "tr",
            "language": "tr-TR",
            "include_adult": False
        }
        data = tmdb_request(endpoint, params)
        if not data or "results" not in data or not data["results"]:
            break
            
        for item in data["results"]:
            m_id = item.get("id")
            title = item.get("title") if media_type == "movie" else item.get("name")
            orig_title = item.get("original_title") if media_type == "movie" else item.get("original_name")
            release_date = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
            year = release_date[:4] if release_date else ""
            vote_avg = item.get("vote_average", 0.0)
            rating = f"{vote_avg:.1f}" if vote_avg > 0 else ""
            poster_path = item.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else ""
            
            # Z-Stream URL
            if media_type == "movie":
                url = build_zstream_movie_url(m_id, orig_title or title)
            else:
                url = build_zstream_tv_url(m_id, orig_title or title)
                
            categories_str, genres_list = resolve_categories(item, media_type)
            platform = resolve_platform(item)
            
            results.append({
                "type": "film" if media_type == "movie" else "dizi",
                "tmdb_id": m_id,
                "title": title or orig_title or "",
                "original_title": orig_title or title or "",
                "genres": genres_list,
                "category": categories_str,
                "platform": platform,
                "imdb_id": "",
                "imdb": rating,
                "year": year,
                "added_date": today_str,
                "poster": poster_url,
                "url": url
            })
            
        if page % 10 == 0:
            print(f"    -> Sayfa {page}: Toplam {len(results)} yerli içerik toplandı.")
        time.sleep(0.05)
        
    print(f"[✓] Toplam {len(results)} adet yerli {media_type} başarıyla çekildi.")
    return results

def fetch_global_popular(media_type="movie", target_count=10000, existing_ids=None):
    """
    Dünya genelindeki en popüler ve yeni içerikleri çeker.
    """
    if existing_ids is None:
        existing_ids = set()
        
    print(f"[*] Global popüler {media_type} içerikleri çekiliyor (Hedef: {target_count})...")
    results = []
    endpoint = f"/discover/{media_type}"
    today_str = format_turkish_date()
    page = 1
    
    # TMDB Discover max 500 sayfa (10.000 içerik) verir
    max_pages = min(500, (target_count // 20) + 1)
    
    while len(results) < target_count and page <= max_pages:
        params = {
            "page": page,
            "sort_by": "popularity.desc",
            "language": "tr-TR",
            "vote_count.gte": 5,
            "include_adult": False
        }
        data = tmdb_request(endpoint, params)
        if not data or "results" not in data or not data["results"]:
            break
            
        for item in data["results"]:
            m_id = item.get("id")
            if m_id in existing_ids:
                continue
            existing_ids.add(m_id)
            
            title = item.get("title") if media_type == "movie" else item.get("name")
            orig_title = item.get("original_title") if media_type == "movie" else item.get("original_name")
            release_date = item.get("release_date") if media_type == "movie" else item.get("first_air_date")
            year = release_date[:4] if release_date else ""
            vote_avg = item.get("vote_average", 0.0)
            rating = f"{vote_avg:.1f}" if vote_avg > 0 else ""
            poster_path = item.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else ""
            
            if media_type == "movie":
                url = build_zstream_movie_url(m_id, orig_title or title)
            else:
                url = build_zstream_tv_url(m_id, orig_title or title)
                
            categories_str, genres_list = resolve_categories(item, media_type)
            platform = resolve_platform(item)
            
            results.append({
                "type": "film" if media_type == "movie" else "dizi",
                "tmdb_id": m_id,
                "title": title or orig_title or "",
                "original_title": orig_title or title or "",
                "genres": genres_list,
                "category": categories_str,
                "platform": platform,
                "imdb_id": "",
                "imdb": rating,
                "year": year,
                "added_date": today_str,
                "poster": poster_url,
                "url": url
            })
            
            if len(results) >= target_count:
                break
                
        if page % 25 == 0:
            print(f"    -> Sayfa {page}: Toplam {len(results)}/{target_count} global içerik toplandı.")
            
        page += 1
        time.sleep(0.05)
        
    print(f"[✓] Toplam {len(results)} adet global {media_type} toplandı.")
    return results

def save_json(data, filename):
    """JSON dosyasını data/ dizinine kaydeder."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"[+] '{filename}' kaydedildi: {len(data)} içerik ({file_size_mb:.2f} MB)")

def main():
    parser = argparse.ArgumentParser(description="Güneş TV Katalog İlk Üretici")
    parser.add_argument("--movies", type=int, default=1000, help="Çekilecek film sayısı (varsayılan: 1000)")
    parser.add_argument("--series", type=int, default=1000, help="Çekilecek dizi sayısı (varsayılan: 1000)")
    parser.add_argument("--sample", action="store_true", help="Hızlı test için küçük örnek veri seti üret (100 film + 100 dizi)")
    args = parser.parse_args()

    if args.sample:
        max_tr_pages = 2
        tr_movies_limit = 50
        tr_series_limit = 50
        global_movies_target = 50
        global_series_target = 50
    else:
        max_tr_pages = 50 # 1000 Türk içeriği
        tr_movies_limit = 1000
        tr_series_limit = 1000
        global_movies_target = args.movies
        global_series_target = args.series

    print("=" * 60)
    print(f"GÜNEŞ TV KATALOG ÜRETİMİ BAŞLATILIYOR")
    print(f"Hedef: {tr_movies_limit} Yerli + {global_movies_target} Global Film | {tr_series_limit} Yerli + {global_series_target} Global Dizi")
    print(f"Tarih: {format_turkish_date()}")
    print("=" * 60)

    # 1. FİLMLER
    turkish_movies = fetch_turkish_content("movie", max_pages=max_tr_pages)[:tr_movies_limit]
    existing_movie_ids = {m["tmdb_id"] for m in turkish_movies}
    global_movies = fetch_global_popular("movie", global_movies_target, existing_movie_ids)
    
    all_movies = turkish_movies + global_movies
    save_json(all_movies, "movies.json")

    # 2. DİZİLER
    turkish_series = fetch_turkish_content("tv", max_pages=max_tr_pages)[:tr_series_limit]
    existing_series_ids = {s["tmdb_id"] for s in turkish_series}
    global_series = fetch_global_popular("tv", global_series_target, existing_series_ids)
    
    all_series = turkish_series + global_series
    save_json(all_series, "series.json")

    # 3. Birleşik Tüm Katalog (Movies + Series)
    full_catalog = all_movies + all_series
    save_json(full_catalog, "catalog.json")

    print("\n" + "=" * 60)
    print("KATALOG ÜRETİMİ TAMAMLANDI!")
    print(f"Toplam Film: {len(all_movies)}")
    print(f"Toplam Dizi: {len(all_series)}")
    print(f"Toplam Birleşik Katalog: {len(full_catalog)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
