import urllib.request
import urllib.parse
import json
import re
import csv
import sys
import argparse
import time

# Reconfigure stdout for utf-8 on Windows
sys.stdout.reconfigure(encoding='utf-8')

# TMDB API Key (zstream'in kullandığı API anahtarı)
TMDB_API_KEY = "1865f43a0549ca50d341dd9ab8b29f49"
BASE_ZSTREAM_URL = "https://zstream.mov/media"

def slugify(text):
    """zstream / movie-web slug formatı oluşturur."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text

def tmdb_request(endpoint, params=None):
    """TMDB API'sine GET isteği atar."""
    if params is None:
        params = {}
    params['api_key'] = TMDB_API_KEY
    query_string = urllib.parse.urlencode(params)
    url = f"https://api.themoviedb.org/3/{endpoint.lstrip('/')}?{query_string}"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"[-] API Hatası ({endpoint}): {e}", file=sys.stderr)
        return None

def get_movie_link(movie_id, title=None):
    """Bir film için Z-Stream sayfa linkini üretir."""
    if not title:
        data = tmdb_request(f"/movie/{movie_id}")
        if not data:
            return None
        title = data.get("title") or data.get("original_title") or ""
    
    slug = slugify(title)
    if slug:
        return f"{BASE_ZSTREAM_URL}/tmdb-movie-{movie_id}-{slug}"
    return f"{BASE_ZSTREAM_URL}/tmdb-movie-{movie_id}"

def get_tv_links(tv_id, show_name=None, include_specials=False):
    """Bir dizinin tüm sezon ve bölüm Z-Stream linklerini üretir."""
    show_data = tmdb_request(f"/tv/{tv_id}")
    if not show_data:
        return []
    
    if not show_name:
        show_name = show_data.get("name") or show_data.get("original_name") or ""
    
    slug = slugify(show_name)
    media_base = f"tmdb-tv-{tv_id}-{slug}" if slug else f"tmdb-tv-{tv_id}"
    
    episodes_list = []
    seasons = show_data.get("seasons", [])
    
    for season in seasons:
        season_num = season.get("season_number")
        if season_num == 0 and not include_specials:
            continue  # Özel bölümleri atla
            
        season_id = season.get("id")
        season_details = tmdb_request(f"/tv/{tv_id}/season/{season_num}")
        if not season_details:
            continue
            
        actual_season_id = season_details.get("id", season_id)
        
        for ep in season_details.get("episodes", []):
            ep_num = ep.get("episode_number")
            ep_id = ep.get("id")
            ep_name = ep.get("name")
            
            page_url = f"{BASE_ZSTREAM_URL}/{media_base}/{actual_season_id}/{ep_id}"
            
            episodes_list.append({
                "type": "tv",
                "show_id": tv_id,
                "show_name": show_name,
                "season_number": season_num,
                "season_id": actual_season_id,
                "episode_number": ep_num,
                "episode_id": ep_id,
                "episode_name": ep_name,
                "url": page_url
            })
            
    return episodes_list

def search_media(query):
    """TMDB üzerinde arama yapar."""
    data = tmdb_request("/search/multi", {"query": query, "include_adult": False})
    if not data or "results" not in data:
        return []
    return [r for r in data["results"] if r.get("media_type") in ("movie", "tv")]

def fetch_popular(media_type="movie", pages=1):
    """Popüler film veya dizileri çeker."""
    results = []
    endpoint = f"/discover/{media_type}"
    for page in range(1, pages + 1):
        data = tmdb_request(endpoint, {
            "page": page,
            "sort_by": "popularity.desc",
            "vote_count.gte": 50,
            "include_adult": False
        })
        if data and "results" in data:
            results.extend(data["results"])
        time.sleep(0.1)
    return results

def main():
    parser = argparse.ArgumentParser(description="Z-Stream (zstream.mov) Dizi ve Film Link Kazıyıcı")
    parser.add_argument("--search", "-s", type=str, help="Dizi veya film ismi ile arama yap")
    parser.add_argument("--popular-movies", type=int, default=0, help="Çekilecek popüler film sayfa sayısı (her sayfa 20 film)")
    parser.add_argument("--popular-shows", type=int, default=0, help="Çekilecek popüler dizi sayfa sayısı (her sayfa 20 dizi)")
    parser.add_argument("--output", "-o", type=str, default="zstream_links.csv", help="Çıktı dosyası (CSV veya JSON)")
    parser.add_argument("--specials", action="store_true", help="Dizilerde özel bölümleri (Season 0) de dahil et")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        # Parametre verilmediyse demo çalıştır
        print("=== Z-STREAM LİNK TESTİ ===")
        print("Hedef: The Walking Dead: Dead City (TMDB ID: 194583)")
        links = get_tv_links(194583, include_specials=args.specials)
        print(f"Toplam {len(links)} bölüm linki başarıyla üretildi.\n")
        
        print("İlk 3 Bölüm Örneği:")
        for ep in links[:3]:
            print(f"  - S{ep['season_number']:02d}E{ep['episode_number']:02d}: {ep['url']}")
            
        print("\nKullanıcının Verdiği 3. Sezon 1. Bölüm Doğrulaması:")
        s3e1 = [ep for ep in links if ep['season_number'] == 3 and ep['episode_number'] == 1]
        if s3e1:
            print("  Üretilen :", s3e1[0]['url'])
            print("  Beklenen : https://zstream.mov/media/tmdb-tv-194583-the-walking-dead-dead-city/516724/7280505")
            print("  Doğruluk :", "TAM EŞLEŞTİ (100% OK)" if s3e1[0]['url'] == "https://zstream.mov/media/tmdb-tv-194583-the-walking-dead-dead-city/516724/7280505" else "HATA")
            
        print("\nÖrnek Film Linki (Fight Club):")
        fc_link = get_movie_link(550, "Fight Club")
        print("  Film Linki:", fc_link)
        
        print("\nKullanım Seçenekleri:")
        print("  python zstream_scraper.py --search \"Breaking Bad\"")
        print("  python zstream_scraper.py --popular-movies 5 -o filmler.csv")
        print("  python zstream_scraper.py --popular-shows 5 -o diziler.csv")
        return

    all_links = []
    
    if args.search:
        print(f"[*] '{args.search}' aranıyor...")
        results = search_media(args.search)
        if not results:
            print("[-] Sonuç bulunamadı.")
            return
            
        for item in results:
            m_type = item.get("media_type")
            m_id = item.get("id")
            name = item.get("title") if m_type == "movie" else item.get("name")
            print(f"\n[+] Bulundu: [{m_type.upper()}] {name} (ID: {m_id})")
            
            if m_type == "movie":
                url = get_movie_link(m_id, name)
                print(f"    Link: {url}")
                all_links.append({
                    "type": "movie",
                    "id": m_id,
                    "title": name,
                    "season": "",
                    "episode": "",
                    "episode_title": "",
                    "url": url
                })
            else:
                eps = get_tv_links(m_id, name, include_specials=args.specials)
                print(f"    Toplam {len(eps)} bölüm linki üretildi.")
                for ep in eps:
                    all_links.append({
                        "type": "tv",
                        "id": m_id,
                        "title": name,
                        "season": ep["season_number"],
                        "episode": ep["episode_number"],
                        "episode_title": ep["episode_name"],
                        "url": ep["url"]
                    })
                    
    if args.popular_movies > 0:
        print(f"[*] Popüler filmler çekiliyor ({args.popular_movies} sayfa)...")
        movies = fetch_popular("movie", args.popular_movies)
        for m in movies:
            m_id = m.get("id")
            title = m.get("title") or m.get("original_title")
            url = get_movie_link(m_id, title)
            all_links.append({
                "type": "movie",
                "id": m_id,
                "title": title,
                "season": "",
                "episode": "",
                "episode_title": "",
                "url": url
            })
            
    if args.popular_shows > 0:
        print(f"[*] Popüler diziler çekiliyor ({args.popular_shows} sayfa)...")
        shows = fetch_popular("tv", args.popular_shows)
        for s in shows:
            s_id = s.get("id")
            name = s.get("name") or s.get("original_name")
            print(f"    -> {name} bölümleri işleniyor...")
            eps = get_tv_links(s_id, name, include_specials=args.specials)
            for ep in eps:
                all_links.append({
                    "type": "tv",
                    "id": s_id,
                    "title": name,
                    "season": ep["season_number"],
                    "episode": ep["episode_number"],
                    "episode_title": ep["episode_name"],
                    "url": ep["url"]
                })

    # Kaydet
    if all_links:
        if args.output.endswith(".json"):
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(all_links, f, ensure_ascii=False, indent=2)
        else:
            with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["type", "id", "title", "season", "episode", "episode_title", "url"])
                writer.writeheader()
                writer.writerows(all_links)
        print(f"\n[✓] Başarıyla {len(all_links)} adet link '{args.output}' dosyasına kaydedildi!")

if __name__ == "__main__":
    main()
