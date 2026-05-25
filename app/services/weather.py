import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class WeatherService:
    """Service untuk mendapatkan data cuaca real-time & prakiraan 10 hari menggunakan Open-Meteo."""

    # ── In-memory cache dengan TTL 30 menit ──────────────────────────────────
    # Key: nama kota (lowercase). Value: (timestamp, result_dict)
    # Ini mencegah API call berulang setiap user pindah halaman.
    # Cache bersifat process-wide (shared semua user) karena cuaca per-kota
    # tidak berbeda antar user.
    _cache: Dict[str, tuple] = {}
    _CACHE_TTL_SECONDS: int = 30 * 60  # 30 menit

    @classmethod
    def _get_cached(cls, city_key: str):
        """Ambil hasil cache jika masih valid. Return None jika kedaluwarsa."""
        if city_key in cls._cache:
            cached_at, result = cls._cache[city_key]
            if (time.monotonic() - cached_at) < cls._CACHE_TTL_SECONDS:
                logger.info(f"[WeatherCache] HIT untuk '{city_key}'")
                return result
            else:
                del cls._cache[city_key]  # Buang cache kedaluwarsa
        return None

    @classmethod
    def _set_cache(cls, city_key: str, result: dict):
        """Simpan hasil ke cache."""
        cls._cache[city_key] = (time.monotonic(), result)
        logger.info(f"[WeatherCache] STORED untuk '{city_key}'")

    @classmethod
    def invalidate_cache(cls, city: str = None):
        """Paksa hapus cache (misal setelah user ubah kota di profil)."""
        if city:
            cls._cache.pop(city.lower().strip(), None)
        else:
            cls._cache.clear()
    
    @staticmethod
    def _get_wmo_description(code: int) -> Dict[str, str]:
        """Memetakan kode cuaca WMO Open-Meteo ke Deskripsi Indonesia dan Ikon Quasar."""
        mapping = {
            0: {"desc": "Cerah", "icon": "wb_sunny"},
            1: {"desc": "Cerah Berawan", "icon": "cloud"},
            2: {"desc": "Sebagian Berawan", "icon": "cloud"},
            3: {"desc": "Berawan", "icon": "cloud"},
            45: {"desc": "Berkabut", "icon": "cloud_queue"},
            48: {"desc": "Kabut Rime", "icon": "cloud_queue"},
            51: {"desc": "Gerimis Ringan", "icon": "grain"},
            53: {"desc": "Gerimis Sedang", "icon": "grain"},
            55: {"desc": "Gerimis Lebat", "icon": "grain"},
            56: {"desc": "Gerimis Beku Ringan", "icon": "grain"},
            57: {"desc": "Gerimis Beku Lebat", "icon": "grain"},
            61: {"desc": "Hujan Ringan", "icon": "grain"},
            63: {"desc": "Hujan Sedang", "icon": "umbrella"},
            65: {"desc": "Hujan Lebat", "icon": "umbrella"},
            66: {"desc": "Hujan Beku Ringan", "icon": "ac_unit"},
            67: {"desc": "Hujan Beku Lebat", "icon": "ac_unit"},
            71: {"desc": "Salju Ringan", "icon": "ac_unit"},
            73: {"desc": "Salju Sedang", "icon": "ac_unit"},
            75: {"desc": "Salju Lebat", "icon": "ac_unit"},
            77: {"desc": "Butiran Salju", "icon": "ac_unit"},
            80: {"desc": "Hujan Pancar Ringan", "icon": "umbrella"},
            81: {"desc": "Hujan Pancar Sedang", "icon": "umbrella"},
            82: {"desc": "Hujan Pancar Lebat", "icon": "umbrella"},
            85: {"desc": "Hujan Salju Ringan", "icon": "ac_unit"},
            86: {"desc": "Hujan Salju Lebat", "icon": "ac_unit"},
            95: {"desc": "Badai Petir", "icon": "thunderstorm"},
            96: {"desc": "Badai Petir Ringan", "icon": "thunderstorm"},
            99: {"desc": "Badai Petir Lebat", "icon": "thunderstorm"}
        }
        return mapping.get(code, {"desc": "Cerah", "icon": "wb_sunny"})

    @staticmethod
    def _generate_fallback_forecast(city: str) -> List[Dict[str, Any]]:
        """Menghasilkan mock data forecast 10 hari yang dinamis jika offline/gagal API."""
        from datetime import datetime, timedelta
        
        days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        months_id = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        
        # Variasi suhu default berdasarkan nama kota
        city_lower = city.lower()
        base_temp = 32
        if "bandung" in city_lower:
            base_temp = 24
        elif "surabaya" in city_lower:
            base_temp = 34
        elif "jakarta" in city_lower:
            base_temp = 32
        elif "jogja" in city_lower:
            base_temp = 29
            
        mock_forecast = []
        today = datetime.now()
        
        for i in range(10):
            future_date = today + timedelta(days=i)
            day_name = days_id[future_date.weekday()]
            month_name = months_id[future_date.month - 1]
            date_label = f"{day_name}, {future_date.day} {month_name}"
            
            # Pola cuaca simulasi agar bervariasi setiap hari
            patterns = [
                {"desc": "Cerah", "icon": "wb_sunny", "offset_min": -8, "offset_max": 0, "uv": 8, "hum": 70},
                {"desc": "Cerah Berawan", "icon": "cloud", "offset_min": -7, "offset_max": 1, "uv": 6, "hum": 75},
                {"desc": "Berawan", "icon": "cloud", "offset_min": -6, "offset_max": -1, "uv": 5, "hum": 80},
                {"desc": "Hujan Ringan", "icon": "grain", "offset_min": -8, "offset_max": -3, "uv": 3, "hum": 85},
                {"desc": "Hujan Sedang", "icon": "umbrella", "offset_min": -9, "offset_max": -4, "uv": 2, "hum": 90},
            ]
            p = patterns[i % len(patterns)]
            
            mock_forecast.append({
                "date": future_date.strftime("%Y-%m-%d"),
                "date_label": date_label,
                "temp_min": int(base_temp + p["offset_min"]),
                "temp_max": int(base_temp + p["offset_max"]),
                "humidity": p["hum"],
                "uv_index": p["uv"],
                "condition": p["desc"],
                "icon": p["icon"]
            })
            
        return mock_forecast

    @classmethod
    def fetch_weather(cls, city: str) -> Dict[str, Any]:
        """
        Fitur cuaca dinonaktifkan untuk mengurangi beban aplikasi (bottleneck).
        """
        return {"status": "disabled", "msg": "Fitur cuaca dinonaktifkan."}
