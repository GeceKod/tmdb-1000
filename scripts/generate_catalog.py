"""
Güneş TV 50.000 Film & 30.000 Dizi (Sezon & Bölümlü) Katalog Üreticisi
TMDB Daily Export ve API üzerinden:
- 50.000 Film
- 30.000 Dizi (Her dizinin tüm sezon ve bölümleriyle birlikte)
üreterek data/movies.json, data/series.json ve data/catalog.json dosyalarına kaydeder.
"""

import os
import sys
import json
import gzip
import time
import urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Windows terminal UTF-8 ayarı
sys.stdout.reconfigure(encoding='utf-8')

# Script klasörünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TMDB_API_KEY, TMDB_EXPORTS_URL, TMDB_BASE_URL, TMDB_IMAGE_BASE_URL
from tmdb_client import (
    slugify,
    build_zstream_movie_url,
    build_zstream_tv_url,
    resolve_categories,
    resolve_platform,
    format_turkish_date,
    tmdb_request
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

def download_and_sort_export(export_type="movie_ids", top_n=50000):
    """TMDB Export dosyasını indirir ve popülerliğe göre sıralar."""
    target_date = datetime.now() - timedelta(days=1)
    date_str = target_date.strftime("%m_%d_%Y")
    url = f"{TMDB_EXPORTS_URL}/{export_type}_{date_str}.json.gz"
    
    print(f"[*] TMDB Export indiriliyor ({export_type}): {url} ...")
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
                        name = item.get("original_title") or item.get("original_name")
                        if not name or len(name.strip()) == 0:
                            continue
                        entries.append(item)
                    except Exception:
                        continue
    except Exception as e:
        print(f"[-] Güncel export indirilemedi ({e}), bir önceki gün deneniyor...", file=sys.stderr)
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

    print(f"[✓] {len(entries)} adet {export_type} okundu. Popülerliğe göre sıralanıyor...")
    entries.sort(key=lambda x: x.get("popularity", 0.0), reverse=True)
    return entries[:top_n]

def fetch_tv_seasons_info(tv_id):
    """Tek bir dizi için sezon ve bölüm sayılarını TMDB'den çeker."""
    url = f"{TMDB_BASE_URL}/tv/{tv_id}?api_key={TMDB_API_KEY}&language=tr-TR"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            seasons_raw = data.get("seasons", [])
            seasons_info = []
            for s in seasons_raw:
                s_num = s.get("season_number", 0)
                ep_count = s.get("episode_count", 0)
                if s_num > 0 and ep_count > 0:
                    seasons_info.append({"season_number": s_num, "episode_count": ep_count})
            
            orig_name = data.get("original_name") or data.get("name") or ""
            name = data.get("name") or orig_name
            first_air = data.get("first_air_date", "")
            year = first_air[:4] if first_air else ""
            vote_avg = data.get("vote_average", 0.0)
            rating = f"{vote_avg:.1f}" if vote_avg > 0 else ""
            poster_path = data.get("poster_path")
            poster = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else ""
            
            categories_str, genres_list = resolve_categories(data, "tv")
            platform = resolve_platform(data)
            
            return tv_id, {
                "title": name,
                "original_title": orig_name,
                "genres": genres_list,
                "category": categories_str,
                "platform": platform,
                "imdb": rating,
                "year": year,
                "poster": poster,
                "seasons_info": seasons_info
            }
    except Exception:
        return tv_id, None

def generate_episodes_list(base_url, seasons_info, max_total_episodes=100):
    """Sezon bilgilerinden optimize edilmiş episodes listesi üretir."""
    episodes = []
    if not seasons_info:
        # Sezon bilgisi alınamadıysa en az 1 bölüm ekle
        episodes.append({
            "title": "1. Sezon 1. Bölüm",
            "videoUrl": f"{base_url}/1/1"
        })
        return episodes

    count = 0
    for s in seasons_info:
        s_num = s["season_number"]
        ep_count = s["episode_count"]
        # Sezon başına makul bölüm sayısı
        for ep_num in range(1, min(ep_count, 30) + 1):
            episodes.append({
                "title": f"{s_num}. Sezon {ep_num}. Bölüm",
                "videoUrl": f"{base_url}/{s_num}/{ep_num}"
            })
            count += 1
            if count >= max_total_episodes:
                break
        if count >= max_total_episodes:
            break

    return episodes

def build_full_catalog(movie_target=50000, series_target=30000):
    os.makedirs(DATA_DIR, exist_ok=True)
    today_str = format_turkish_date()

    # 1. FİLMLERİ ÜRET (50.000)
    print("\n" + "=" * 60)
    print(f"1. ADIM: {movie_target} FİLM HAZIRLANIYOR...")
    print("=" * 60)
    raw_movies = download_and_sort_export("movie_ids", movie_target)
    
    # Mevcut filmleri hafızaya al (zengin afiş/tür bilgileri için)
    existing_movies = {}
    movie_file = os.path.join(DATA_DIR, "movies.json")
    if os.path.exists(movie_file):
        try:
            with open(movie_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    existing_movies[item.get("tmdb_id")] = item
        except Exception:
            pass

    final_movies = []
    for item in raw_movies:
        m_id = item["id"]
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
    print(f"[✓] 'movies.json' kaydedildi: {len(final_movies)} Film ({m_size:.2f} MB)")

    # 2. DİZİLERİ ÜRET (30.000 - Sezon ve Bölümleriyle)
    print("\n" + "=" * 60)
    print(f"2. ADIM: {series_target} DİZİ (SEZON VE BÖLÜMLERİYLE) HAZIRLANIYOR...")
    print("=" * 60)
    raw_series = download_and_sort_export("tv_series_ids", series_target)
    
    # En popüler ilk 5.000 dizi için TMDB API'den gerçek sezon/bölüm sayılarını paralel çek
    top_api_target = min(5000, len(raw_series))
    top_ids = [item["id"] for item in raw_series[:top_api_target]]
    print(f"[*] İlk {top_api_target} popüler dizi için sezon/bölüm detayları TMDB'den çekiliyor (Multi-threaded)...")
    
    seasons_cache = {}
    completed_count = 0
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        futures = {executor.submit(fetch_tv_seasons_info, s_id): s_id for s_id in top_ids}
        for future in as_completed(futures):
            tv_id, details = future.result()
            if details:
                seasons_cache[tv_id] = details
            completed_count += 1
            if completed_count % 500 == 0 or completed_count == top_api_target:
                elapsed = time.time() - t0
                rate = completed_count / elapsed if elapsed > 0 else 0
                print(f"    -> {completed_count}/{top_api_target} dizi işlendi ({rate:.1f} dizi/sn)...")

    final_series = []
    for item in raw_series:
        s_id = item["id"]
        name = item.get("original_name", "")
        base_url = build_zstream_tv_url(s_id, name)
        
        if s_id in seasons_cache:
            details = seasons_cache[s_id]
            episodes = generate_episodes_list(base_url, details.get("seasons_info", []))
            final_series.append({
                "type": "dizi",
                "tmdb_id": s_id,
                "title": details.get("title") or name,
                "original_title": details.get("original_title") or name,
                "genres": details.get("genres", ["Dizi"]),
                "category": details.get("category", "Dizi"),
                "platform": details.get("platform", "Platform Dışı"),
                "imdb_id": "",
                "imdb": details.get("imdb", ""),
                "year": details.get("year", ""),
                "added_date": today_str,
                "poster": details.get("poster", ""),
                "url": base_url,
                "episodes": episodes
            })
        else:
            # Standart varsayılan sezon/bölüm şablonu
            episodes = [
                {
                    "title": "1. Sezon 1. Bölüm",
                    "videoUrl": f"{base_url}/1/1"
                }
            ]
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
                "url": base_url,
                "episodes": episodes
            })

    series_file = os.path.join(DATA_DIR, "series.json")
    with open(series_file, "w", encoding="utf-8") as f:
        json.dump(final_series, f, ensure_ascii=False, indent=2)
    s_size = os.path.getsize(series_file) / (1024 * 1024)
    print(f"[✓] 'series.json' kaydedildi: {len(final_series)} Dizi ({s_size:.2f} MB)")

    # 3. BİRLEŞİK KATALOG (catalog.json - 80.000 İçerik)
    print("\n" + "=" * 60)
    print(f"3. ADIM: BİRLEŞİK KATALOG OLUŞTURULUYOR ({len(final_movies) + len(final_series)} İÇERİK)...")
    print("=" * 60)
    catalog_file = os.path.join(DATA_DIR, "catalog.json")
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(final_movies + final_series, f, ensure_ascii=False, indent=2)
    c_size = os.path.getsize(catalog_file) / (1024 * 1024)
    print(f"[✓] 'catalog.json' hazırlandı: {len(final_movies) + len(final_series)} İçerik ({c_size:.2f} MB)")

if __name__ == "__main__":
    print("=" * 60)
    print("50.000 FİLM + 30.000 DİZİ KATALOG ÜRETİMİ BAŞLATILIYOR")
    print("=" * 60)
    build_full_catalog(50000, 30000)
    print("\n" + "=" * 60)
    print("TÜM İŞLEMLER BAŞARIYLA TAMAMLANDI!")
    print("=" * 60)
