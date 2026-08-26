"""
Katalog ve URL Doğrulama Testleri
"""

import os
import sys
import unittest
import json

# Scripts klasörünü path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from config import TMDB_API_KEY
from tmdb_client import (
    slugify,
    build_zstream_movie_url,
    build_zstream_tv_url,
    resolve_categories,
    resolve_platform,
    format_turkish_date,
    tmdb_request
)

class TestCatalogSystem(unittest.TestCase):

    def test_slugify(self):
        self.assertEqual(slugify("The Walking Dead: Dead City"), "the-walking-dead-dead-city")
        self.assertEqual(slugify("Dövüş Kulübü (1999)"), "d-v-kul-b-1999")
        self.assertEqual(slugify("Squid Game"), "squid-game")

    def test_zstream_urls(self):
        movie_url = build_zstream_movie_url(550, "Fight Club")
        self.assertEqual(movie_url, "https://zstream.mov/media/tmdb-movie-550-fight-club")
        
        tv_url = build_zstream_tv_url(194583, "The Walking Dead: Dead City")
        self.assertEqual(tv_url, "https://zstream.mov/media/tmdb-tv-194583-the-walking-dead-dead-city")

    def test_turkish_priority_category(self):
        # Türk yapımı kontrolü
        tr_item = {
            "original_language": "tr",
            "genre_ids": [18, 80] # Dram, Suç
        }
        categories = resolve_categories(tr_item, "tv")
        self.assertIn("Türk Yapımı", categories)
        self.assertIn("Dram", categories)
        self.assertIn("Suç", categories)

    def test_korean_category(self):
        ko_item = {
            "original_language": "ko",
            "genre_ids": [18, 53] # Dram, Gerilim
        }
        categories = resolve_categories(ko_item, "tv")
        self.assertIn("Kore Yapımı", categories)

    def test_anime_category(self):
        anime_item = {
            "original_language": "ja",
            "genre_ids": [16, 28] # Animasyon, Aksiyon
        }
        categories = resolve_categories(anime_item, "tv")
        self.assertIn("Anime", categories)

    def test_tmdb_connection(self):
        data = tmdb_request("/movie/550")
        self.assertIsNotNone(data)
        self.assertEqual(data.get("id"), 550)

    def test_turkish_date_format(self):
        date_str = format_turkish_date()
        self.assertTrue(any(month in date_str for month in ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]))

if __name__ == "__main__":
    unittest.main()
