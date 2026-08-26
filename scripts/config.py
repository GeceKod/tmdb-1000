"""
Güneş TV Z-Stream & TMDB Katalog Yapılandırma ve Sabitleri
"""

import os

# TMDB API Yapılandırması
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "1865f43a0549ca50d341dd9ab8b29f49")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_EXPORTS_URL = "http://files.tmdb.org/p/exports"

# Z-Stream Yapılandırması
ZSTREAM_BASE_URL = "https://zstream.mov/media"

# TMDB Tür ID'leri -> Türkçe Kategori İsimleri Eşlemesi
TMDB_GENRES = {
    # Film Türleri
    28: "Aksiyon",
    12: "Macera",
    16: "Animasyon",
    35: "Komedi",
    80: "Suç",
    99: "Belgesel",
    18: "Dram",
    10751: "Aile",
    14: "Fantastik",
    36: "Tarih",
    27: "Korku",
    10402: "Müzik",
    9648: "Gizem",
    10749: "Romantik",
    878: "Bilim Kurgu",
    10770: "TV Filmi",
    53: "Gerilim",
    10752: "Savaş",
    37: "Vahşi Batı",
    # Dizi Türleri (Özel ID'ler)
    10759: "Aksiyon & Macera",
    10762: "Çocuk",
    10763: "Haber",
    10764: "Reality",
    10765: "Bilim Kurgu & Fantastik",
    10766: "Pembe Dizi",
    10767: "Talk Show",
    10768: "Savaş & Politik"
}

# Platform Eşleme Sözlüğü (Keywords / Networks / Production)
PLATFORM_KEYWORDS = {
    "netflix": "Netflix",
    "disney": "Disney+",
    "hbo": "HBO",
    "max": "HBO Max",
    "amazon": "Amazon Prime",
    "prime": "Amazon Prime",
    "apple": "Apple TV+",
    "blutv": "BluTV",
    "gain": "GAİN",
    "exxen": "Exxen",
    "tod": "TOD",
    "tabii": "tabii",
    "puhutv": "puhutv"
}

# Türkçe Ay İsimleri (Tarih Formatlama İçin)
TURKISH_MONTHS = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık"
}
