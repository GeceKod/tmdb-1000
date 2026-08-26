"""
Günlük Fark Güncelleyici (Daily Update Bot)
GitHub Actions tarafından her gün otomatik olarak çalıştırılır.
Son 24 saatte değişen filmleri ve yeni bölümü çıkan dizileri tespit eder,
bilgilerini günceller ve JSON dizisinin EN BAŞINA (Index 0) taşır.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta

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

def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"[+] '{filename}' güncellendi: {len(data)} içerik ({file_size_mb:.2f} MB)")

def fetch_changed_ids(media_type="tv", days=1, max_results=200):
    """
    TMDB Changes API ile son N günde değişen/yeni bölüm eklenen ID'leri çeker.
    """
    today_dt = datetime.utcnow()
    start_dt = today_dt - timedelta(days=days)
    
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = today_dt.strftime("%Y-%m-%d")
    
    print(f"[*] {media_type.upper()} değişiklikleri taranıyor ({start_str} - {end_str})...")
    changed_ids = set()
    page = 1
    
    while len(changed_ids) < max_results:
        endpoint = f"/{media_type}/changes"
        params = {
            "start_date": start_str,
            "end_date": end_str,
            "page": page
        }
        data = tmdb_request(endpoint, params)
        if not data or "results" not in data or not data["results"]:
            break
            
        for item in data["results"]:
            if not item.get("adult", False):
                changed_ids.add(item["id"])
                
        if page >= data.get("total_pages", 1) or page >= 10:
            break
        page += 1
        time.sleep(0.05)
        
    print(f"[✓] {len(changed_ids)} adet değişen {media_type} tespit edildi.")
    return list(changed_ids)

def fetch_airing_today_series(max_pages=5):
    """Bugün yeni bölümü yayınlanan dizilerin ID'lerini çeker."""
    print("[*] Bugün yayınlanan diziler (/tv/airing_today) taranıyor...")
    airing_ids = set()
    for page in range(1, max_pages + 1):
        data = tmdb_request("/tv/airing_today", {"page": page, "language": "tr-TR"})
        if not data or "results" not in data or not data["results"]:
            break
        for item in data["results"]:
            airing_ids.add(item["id"])
        time.sleep(0.05)
    print(f"[✓] Bugün yayınlanan {len(airing_ids)} dizi tespit edildi.")
    return list(airing_ids)

def convert_tmdb_item_to_model(tmdb_id, media_type="movie", today_str=None):
    """Tek bir içerik için detayları çekip minimal modele dönüştürür."""
    if today_str is None:
        today_str = format_turkish_date()
        
    data = tmdb_request(f"/{media_type}/{tmdb_id}", {"language": "tr-TR", "append_to_response": "external_ids"})
    if not data:
        return None
        
    title = data.get("title") if media_type == "movie" else data.get("name")
    orig_title = data.get("original_title") if media_type == "movie" else data.get("original_name")
    release_date = data.get("release_date") if media_type == "movie" else data.get("first_air_date")
    year = release_date[:4] if release_date else ""
    vote_avg = data.get("vote_average", 0.0)
    rating = f"{vote_avg:.1f}" if vote_avg > 0 else ""
    poster_path = data.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else ""
    
    ext_ids = data.get("external_ids", {})
    imdb_id = ext_ids.get("imdb_id") or data.get("imdb_id") or ""
    
    if media_type == "movie":
        url = build_zstream_movie_url(tmdb_id, orig_title or title)
    else:
        url = build_zstream_tv_url(tmdb_id, orig_title or title)
        
    categories = resolve_categories(data, media_type)
    platform = resolve_platform(data)
    
    return {
        "type": "film" if media_type == "movie" else "dizi",
        "tmdb_id": tmdb_id,
        "title": title or orig_title or "",
        "original_title": orig_title or title or "",
        "category": categories,
        "platform": platform,
        "imdb_id": imdb_id,
        "imdb": rating,
        "year": year,
        "added_date": today_str,
        "poster": poster_url,
        "url": url
    }

def update_catalog(media_type="movie", target_ids=None):
    """
    Belirtilen ID'leri günceller ve JSON dizisinin EN BAŞINA ekler/taşır.
    """
    filename = "movies.json" if media_type == "movie" else "series.json"
    catalog = load_json(filename)
    
    # Mevcut ID index haritası
    existing_map = {item.get("tmdb_id"): item for item in catalog if "tmdb_id" in item}
    today_str = format_turkish_date()
    
    updated_items = []
    print(f"[*] {len(target_ids)} adet {media_type} güncelleniyor ve en başa taşınıyor...")
    
    for idx, tmdb_id in enumerate(target_ids):
        model = convert_tmdb_item_to_model(tmdb_id, media_type, today_str)
        if model:
            updated_items.append(model)
        if (idx + 1) % 20 == 0:
            print(f"    -> {idx + 1}/{len(target_ids)} içerik işlendi.")
        time.sleep(0.05)
        
    if not updated_items:
        print(f"[-] Güncellenecek geçerli {media_type} bulunamadı.")
        return
        
    # Güncellenen ID'leri eski listeden çıkar
    updated_id_set = {item["tmdb_id"] for item in updated_items}
    cleaned_catalog = [item for item in catalog if item.get("tmdb_id") not in updated_id_set]
    
    # Yenileri EN BAŞA ekle (Prepend / Index 0)
    new_catalog = updated_items + cleaned_catalog
    
    save_json(new_catalog, filename)
    print(f"[✓] {len(updated_items)} adet {media_type} listenin EN BAŞINA taşındı!")

def main():
    parser = argparse.ArgumentParser(description="Güneş TV Günlük Katalog Güncelleyici")
    parser.add_argument("--limit", type=int, default=50, help="İşlenecek maksimum değişen içerik sayısı")
    args = parser.parse_args()

    print("=" * 60)
    print(f"GÜNEŞ TV GÜNLÜK GÜNCELLEME BOTU ÇALIŞIYOR")
    print(f"Tarih: {format_turkish_date()}")
    print("=" * 60)

    # 1. TV Değişiklikleri ve Bugün Yayınlananlar
    tv_changes = fetch_changed_ids("tv", days=1, max_results=args.limit)
    airing_today = fetch_airing_today_series(max_pages=3)
    target_tv_ids = list(set(tv_changes + airing_today))[:args.limit]
    
    if target_tv_ids:
        update_catalog("tv", target_tv_ids)

    # 2. Film Değişiklikleri
    movie_changes = fetch_changed_ids("movie", days=1, max_results=args.limit)
    if movie_changes:
        update_catalog("movie", movie_changes[:args.limit])

    # 3. Birleşik Tüm Katalog (catalog.json) Güncelle
    all_movies = load_json("movies.json")
    all_series = load_json("series.json")
    save_json(all_movies + all_series, "catalog.json")

    print("\n" + "=" * 60)
    print("GÜNLÜK GÜNCELLEME BAŞARIYLA TAMAMLANDI!")
    print("=" * 60)

if __name__ == "__main__":
    main()
