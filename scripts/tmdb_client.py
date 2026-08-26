"""
TMDB API ve Veri Dönüştürücü İstemcisi
"""

import urllib.request
import urllib.parse
import gzip
import json
import re
import sys
import time
from datetime import datetime, timedelta

from config import (
    TMDB_API_KEY,
    TMDB_BASE_URL,
    TMDB_IMAGE_BASE_URL,
    TMDB_EXPORTS_URL,
    ZSTREAM_BASE_URL,
    TMDB_GENRES,
    PLATFORM_KEYWORDS,
    TURKISH_MONTHS
)

def slugify(text):
    """Metni Z-Stream / movie-web URL slug formatına dönüştürür."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def format_turkish_date(dt=None):
    """Tarihi Türkçe formatta döndürür: '26 Ağustos, 2026'."""
    if dt is None:
        dt = datetime.now()
    day = dt.day
    month = TURKISH_MONTHS.get(dt.month, "")
    year = dt.year
    return f"{day} {month}, {year}"

def tmdb_request(endpoint, params=None, retries=3):
    """TMDB REST API'sine istek atar."""
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    query_string = urllib.parse.urlencode(params)
    url = f"{TMDB_BASE_URL}/{endpoint.lstrip('/')}?{query_string}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Rate limit
                time.sleep(1.5 * (attempt + 1))
                continue
            elif e.code == 404:
                return None
            time.sleep(1)
        except Exception as e:
            time.sleep(1)
            
    return None

def build_zstream_movie_url(tmdb_id, title):
    """Film için Z-Stream sayfa adresini oluşturur."""
    slug = slugify(title)
    if slug:
        return f"{ZSTREAM_BASE_URL}/tmdb-movie-{tmdb_id}-{slug}"
    return f"{ZSTREAM_BASE_URL}/tmdb-movie-{tmdb_id}"

def build_zstream_tv_url(tmdb_id, title):
    """Dizi için Z-Stream sayfa adresini oluşturur."""
    slug = slugify(title)
    if slug:
        return f"{ZSTREAM_BASE_URL}/tmdb-tv-{tmdb_id}-{slug}"
    return f"{ZSTREAM_BASE_URL}/tmdb-tv-{tmdb_id}"

def resolve_categories(item, media_type="movie"):
    """
    TMDB öğesinden kategorileri oluşturur:
    - Türk Yapımı (original_language=tr veya origin_country=[TR])
    - Kore Yapımı (original_language=ko)
    - Anime (original_language=ja + Animasyon)
    - Türler (Aksiyon, Dram, Korku, vb.)
    """
    categories = []
    orig_lang = item.get("original_language", "").lower()
    origin_country = item.get("origin_country", [])
    if isinstance(origin_country, str):
        origin_country = [origin_country]
    
    # 1. Kültür / Ülke Etiketleri
    is_turkish = (orig_lang == "tr") or ("TR" in origin_country)
    is_korean = (orig_lang == "ko") or ("KR" in origin_country)
    is_japanese = (orig_lang == "ja") or ("JP" in origin_country)

    if is_turkish:
        categories.append("Türk Yapımı")
    elif is_korean:
        categories.append("Kore Yapımı")

    # 2. Türler
    genre_ids = item.get("genre_ids", [])
    if not genre_ids and "genres" in item:
        genre_ids = [g["id"] for g in item["genres"] if isinstance(g, dict) and "id" in g]

    is_animation = 16 in genre_ids
    if is_japanese and is_animation:
        categories.append("Anime")
    elif is_animation:
        categories.append("Animasyon")

    for gid in genre_ids:
        if gid == 16:
            continue  # Animasyon zaten yukarıda eklendi
        genre_name = TMDB_GENRES.get(gid)
        if genre_name and genre_name not in categories:
            categories.append(genre_name)

    if not categories:
        categories.append("Film" if media_type == "movie" else "Dizi")

    return ", ".join(categories), categories

def resolve_platform(item):
    """Yayıncı ağ veya platformu belirler."""
    networks = item.get("networks", [])
    for net in networks:
        name = net.get("name", "").lower() if isinstance(net, dict) else str(net).lower()
        for kw, platform_name in PLATFORM_KEYWORDS.items():
            if kw in name:
                return platform_name

    orig_lang = item.get("original_language", "").lower()
    if orig_lang == "tr":
        return "Yerli"
        
    return "Platform Dışı"

def fetch_details_for_imdb(tmdb_id, media_type="movie"):
    """Dış ID'leri (özellikle IMDb ID ve vote_average) çeker."""
    data = tmdb_request(f"/{media_type}/{tmdb_id}", {"append_to_response": "external_ids"})
    if not data:
        return None, None
    
    ext_ids = data.get("external_ids", {})
    imdb_id = ext_ids.get("imdb_id") or data.get("imdb_id")
    return imdb_id, data

def download_daily_export(export_type="movie_ids", target_date=None):
    """
    TMDB Günlük Export dosyasını indirir ve JSON satırlarını yield eder.
    export_type: 'movie_ids' veya 'tv_series_ids'
    """
    if target_date is None:
        target_date = datetime.utcnow() - timedelta(days=1)
        
    date_str = target_date.strftime("%m_%d_%Y")
    url = f"{TMDB_EXPORTS_URL}/{export_type}_{date_str}.json.gz"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for line in gz:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str:
                        yield json.loads(line_str)
    except Exception as e:
        # Bir önceki günü dene
        prev_date = target_date - timedelta(days=1)
        date_str_prev = prev_date.strftime("%m_%d_%Y")
        url_prev = f"{TMDB_EXPORTS_URL}/{export_type}_{date_str_prev}.json.gz"
        print(f"[-] {url} indirilemedi ({e}), bir önceki gün ({url_prev}) deneniyor...", file=sys.stderr)
        req_prev = urllib.request.Request(url_prev, headers=headers)
        with urllib.request.urlopen(req_prev, timeout=30) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for line in gz:
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str:
                        yield json.loads(line_str)
