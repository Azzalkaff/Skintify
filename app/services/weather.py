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
        Mengambil cuaca real-time & forecast 10 hari menggunakan Open-Meteo API.
        Hasil di-cache 30 menit agar tidak memblokir server setiap navigasi halaman.
        Jika terjadi kesalahan koneksi/limitasi, sistem otomatis beralih ke Fallback Mock.
        """
        if not city:
            return {"status": "error", "msg": "City not provided"}

        city_clean = city.strip()
        city_key   = city_clean.lower()

        # ── Cek cache terlebih dahulu ──────────────────────────────────────
        cached = cls._get_cached(city_key)
        if cached is not None:
            return cached
        
        try:
            # 1. Geocoding API: Ubah nama kota menjadi Latitude & Longitude
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_clean}&count=1&language=id&format=json"
            geo_res = requests.get(geo_url, timeout=4)
            
            if geo_res.status_code != 200 or not geo_res.json().get("results"):
                raise ValueError("Kota tidak ditemukan di Geocoding API")
            
            loc = geo_res.json()["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            resolved_city = loc.get("name", city_clean)
            
            # 2. Forecast API: Ambil cuaca saat ini & 10 hari prakiraan
            forecast_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,uv_index,weather_code"
                f"&daily=temperature_2m_max,temperature_2m_min,uv_index_max,relative_humidity_2m_max,weather_code"
                f"&timezone=auto&forecast_days=10"
            )
            
            res = requests.get(forecast_url, timeout=4)
            if res.status_code != 200:
                raise ValueError("Gagal mengambil data dari Open-Meteo Forecast")
                
            data = res.json()
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            # Map Current Weather
            curr_code = current.get("weather_code", 0)
            curr_mapped = WeatherService._get_wmo_description(curr_code)
            
            # Map 10-day Daily Forecast
            days_id = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            months_id = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
            
            forecast_list = []
            dates = daily.get("time", [])
            temp_maxs = daily.get("temperature_2m_max", [])
            temp_mins = daily.get("temperature_2m_min", [])
            uv_maxs = daily.get("uv_index_max", [])
            hum_maxs = daily.get("relative_humidity_2m_max", [])
            wcodes = daily.get("weather_code", [])
            
            for i in range(len(dates)):
                date_str = dates[i]
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                day_name = days_id[dt.weekday()]
                month_name = months_id[dt.month - 1]
                date_label = f"{day_name}, {dt.day} {month_name}"
                
                day_mapped = WeatherService._get_wmo_description(wcodes[i] if i < len(wcodes) else 0)
                
                forecast_list.append({
                    "date": date_str,
                    "date_label": date_label,
                    "temp_min": int(temp_mins[i]) if i < len(temp_mins) else 24,
                    "temp_max": int(temp_maxs[i]) if i < len(temp_maxs) else 32,
                    "humidity": int(hum_maxs[i]) if i < len(hum_maxs) else 70,
                    "uv_index": int(uv_maxs[i]) if i < len(uv_maxs) else 4,
                    "condition": day_mapped["desc"],
                    "icon": day_mapped["icon"]
                })
                
            result = {
                "status": "success",
                "city": resolved_city,
                "temp": int(current.get("temperature_2m", 28)),
                "humidity": int(current.get("relative_humidity_2m", 60)),
                "uv_index": int(current.get("uv_index", 4)),
                "condition": curr_mapped["desc"],
                "icon": curr_mapped["icon"],
                "forecast": forecast_list
            }
            cls._set_cache(city_key, result)
            return result
            
        except Exception as e:
            logger.warning(f"Gagal memuat cuaca online untuk '{city}', beralih ke fallback: {e}")
            
            # Gunakan fallback mock jika offline atau gagal request
            mock_forecast = WeatherService._generate_fallback_forecast(city_clean)
            
            # Map data cuaca saat ini dari hari pertama forecast fallback
            today_weather = mock_forecast[0]
            
            result = {
                "status": "success",
                "city": city_clean,
                "temp": today_weather["temp_max"], # representasi suhu saat ini
                "humidity": today_weather["humidity"],
                "uv_index": today_weather["uv_index"],
                "condition": today_weather["condition"],
                "icon": today_weather["icon"],
                "forecast": mock_forecast
            }
            # Cache fallback lebih singkat — 5 menit agar cepat retry
            cls._cache[city_key] = (time.monotonic() - cls._CACHE_TTL_SECONDS + 300, result)
            return result
