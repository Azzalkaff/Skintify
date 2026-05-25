"""
app/scraping/shopee_scraper.py
==============================
File tunggal Shopee scraper Skintify-C4.

Menggabungkan:
  - Konfigurasi endpoint, header, cookie  (sebelumnya: core/config.py)
  - ShopeeScraper class                   (sebelumnya: core/shopee.py)
  - ambil_top_toko() wrapper publik       (sebelumnya: shopee_scraper.py)

Cara pakai dari mana saja:
    from app.scraping.shopee_scraper import ambil_top_toko
    products, shops = ambil_top_toko("emina sunscreen", top_n=5)
"""

import logging
import os
import sys
import codecs
import time
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

logger = logging.getLogger(__name__)

# ======================================================================
# Fix UnicodeEncodeError pada Windows / PyInstaller saat mencetak emoji
# ======================================================================
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach(), errors="backslashreplace")
        except Exception:
            pass

if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach(), errors="backslashreplace")
        except Exception:
            pass

# Pastikan root directory ada di sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


# ======================================================================
# BAGIAN 1 — KONFIGURASI
# (sebelumnya: app/scraping/core/config.py)
# ======================================================================

_SHOPEE_ENDPOINT = "https://shopee.co.id/api/v4/search/search_items"
_SLEEP_RANGE     = (4.0, 8.0)  # Delay lebih lama untuk menghindari rate-limit
_OUTPUT_DIR      = Path("data/raw")
_MAX_RETRIES     = 3  # Jumlah maksimal retry untuk request yang gagal
_RETRY_BACKOFF   = 7  # Detik, akan diperbesar exponentially per attempt

# Pool user agents untuk bypass bot detection
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


def _get_headers() -> dict:
    """Header HTTP dengan rotating user agent untuk bypass bot detection."""
    user_agent = random.choice(_USER_AGENTS)
    
    return {
        "User-Agent":                  user_agent,
        "Accept":                      "application/json, text/plain, */*",
        "Accept-Language":             "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding":             "gzip, deflate, br",
        "Referer":                     "https://shopee.co.id/",
        "Origin":                      "https://shopee.co.id",
        "X-Requested-With":            "XMLHttpRequest",
        "X-Api-Source":                "pc",
        "Connection":                  "keep-alive",
        "Sec-Fetch-Dest":              "empty",
        "Sec-Fetch-Mode":              "cors",
        "Sec-Fetch-Site":              "same-origin",
        "Sec-Fetch-User":              "?1",
        "Sec-Ch-Ua":                   '"Not A(Brand";v="99", "Google Chrome";v="125", "Chromium";v="125"',
        "Sec-Ch-Ua-Mobile":            "?0",
        "Sec-Ch-Ua-Platform":          '"Windows"',
        "Cache-Control":               "max-age=0",
        "Pragma":                      "no-cache",
        "Upgrade-Insecure-Requests":   "1",
        "DNT":                         "1",
    }


def _get_cookies() -> dict:
    """Cookie dasar untuk sesi Shopee tanpa login."""
    # Baca dari environment variable, gunakan default jika tidak ada
    default_cookie = "_fbp=fb.2.1737036500863.743660935782422230; REC7iLP4Q=975a3955-83e4-4d82-baf6-c701bdfab6ac; SPC_CLIENTID=bm9vajNndnMyNnJitmalbqqhcqcbxezi; language=id; _QPWSDCXHZQA=e92f0910-5d76-44e6-e6c6-0eb0457be399; SPC_F=AELXJtOO1NxnR7wGtRfIT7brlKrubr7F; REC_T_ID=ed703cb0-0fd0-11f1-98c8-36570494acc6; _gcl_au=1.1.583648685.1772026699; _gcl_gs=2.1.k1$i1773757821$u81977812; _ga=GA1.1.653446549.1737036505; _gcl_aw=GCL.1773757830.Cj0KCQjw9-PNBhDfARIsABHN6-0BgGdaU191T_4-bJWdwWydCzJlbkt7IE3ovxOwYVEAEEsrtWnQASMaAt9kEALw_wcB; ssr-tz=Asia/Jakarta; _med=cpc; SPC_EC=-; SPC_U=-; SPC_R_T_ID=/+j2x70yrQNO/ASjefKDFUFQtiaxus2CuVvhVWm79LZVT5nX6fANh6gIc79rHES7lJ6u8idxWC4JoWXefZrnwQMEQgkht5tUr6HNyp71zqjN8GUoRjqLP4u01SRd+1klo6TUlgaUGIglAaBPQHjPWr4XIBLEEhIzoA3mXTJM1is=; SPC_R_T_IV=VTZPUUJkbHpoSlFUUm1Kaw==; SPC_T_ID=/+j2x70yrQNO/ASjefKDFUFQtiaxus2CuVvhVWm79LZVT5nX6fANh6gIc79rHES7lJ6u8idxWC4JoWXefZrnwQMEQgkht5tUr6HNyp71zqjN8GUoRjqLP4u01SRd+1klo6TUlgaUGIglAaBPQHjPWr4XIBLEEhIzoA3mXTJM1is=; SPC_T_IV=VTZPUUJkbHpoSlFUUm1Kaw==; _sapid=830c9068561e190f86515c6a565c920e0dc1df672e7ef9df89722c8b; csrftoken=xPbJMBaBvfYv618VEMZz9l8Mop0yIzSM; SPC_SI=WYwFagAAAABwMmFFejRjT0/yUAAAAAAAOGFzNmEwdDM=; SPC_SEC_SI=v1-S0JhYUIzOVp6Y05qWkVKWOle3CTpSHOkAd2KGg7VsGzoKVJypk7kLoxggrWMIn+1dxCmK5e5Qlm8fB8+GvlIOw7bis6onEMf0OOZlIPbDJk=; shopee_webUnique_ccd=thbrz3kLLXxqvnzaDPUNdg%3D%3D%7Cx1FJVJ4ZXisoW3X5F%2FhbRJbu2EmzrPjAOBMFQoxaS7CA3cTsxcRduNGbgRqnQRGMR2Q3viHMih9bmNT7%7CRRCrs9s06w0W4TCl%7C08%7C3; ds=eb85d00d1667d57dd94a86663f70035c; _ga_SW6D8G0HXK=GS2.1.s1779063990$o143$g1$t1779064023$j27$l1$h1736160923"
    spc_f_cookie = os.getenv("SHOPEE_COOKIE", default_cookie)
    
    if os.getenv("SHOPEE_COOKIE"):
        logger.debug("[Shopee] Menggunakan cookie dari environment variable SHOPEE_COOKIE")
    else:
        logger.debug("[Shopee] Menggunakan default cookie (SHOPEE_COOKIE tidak ditemukan)")
    
    return {
        "SPC_F":    spc_f_cookie,
        "REC_T_ID": "",
        "language": "id",
        "currency": "IDR",
    }


# ======================================================================
# BAGIAN 2 — SCRAPER CLASS
# (sebelumnya: app/scraping/core/shopee.py)
# ======================================================================

class ShopeeScraper:
    """
    Scraper untuk platform Shopee Indonesia.

    Mengambil data produk skincare dari Shopee Search API v4
    dan mengembalikannya dalam format unified Skintify-C4.

    Tidak lagi mewarisi BaseScraper — semua helper ada di dalam class ini
    agar file ini berdiri sendiri tanpa dependensi internal lain.
    """

    name = "shopee"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_get_headers())
        self.session.cookies.update(_get_cookies())
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Metode Publik
    # ------------------------------------------------------------------

    def scrape(
        self,
        keyword: str,
        top_n: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Titik masuk utama scraping.

        Parameter
        ---------
        keyword : str
            Kata kunci pencarian produk, misal "emina moisturizer".
        top_n : int
            Jumlah toko teratas yang dikembalikan.

        Kembalian
        ---------
        Tuple (products, shops[:top_n]).
        """
        logger.info("[Shopee] Memulai scraping keyword: '%s'", keyword)

        raw_data = self._fetch(keyword)
        if not raw_data:
            logger.warning("[Shopee] Tidak ada data yang diterima dari API.")
            return [], []

        products, shops = self._parse(raw_data, keyword)

        self._save_to_json(
            {"keyword": keyword, "raw_items": raw_data.get("items", [])},
            f"shopee_{keyword.replace(' ', '_')}",
        )

        logger.info(
            "[Shopee] Selesai — %d produk, %d toko ditemukan.",
            len(products), len(shops),
        )
        return products, shops[:top_n]

    # ------------------------------------------------------------------
    # Metode Privat
    # ------------------------------------------------------------------

    def _fetch(self, keyword: str) -> Dict[str, Any]:
        """Kirim GET ke Shopee Search API v4 dengan retry logic dan rotating headers."""
        params = {
            "by":        "relevancy",
            "keyword":   keyword,
            "limit":     40,
            "newest":    0,
            "order":     "desc",
            "page_type": "search",
            "scenario":  "PAGE_GLOBAL_SEARCH",
            "version":   2,
        }

        for attempt in range(_MAX_RETRIES):
            try:
                # Update headers setiap attempt dengan user agent baru
                self.session.headers.update(_get_headers())
                
                self._random_sleep()
                logger.debug(
                    "[Shopee] Request ke API (attempt %d/%d) untuk '%s'",
                    attempt + 1, _MAX_RETRIES, keyword
                )
                
                response = self.session.get(
                    _SHOPEE_ENDPOINT,
                    params=params,
                    timeout=15,
                )
                
                # Log response status
                logger.debug(
                    "[Shopee] Response status: %d untuk '%s'",
                    response.status_code, keyword
                )
                
                # Jika 403/429, coba retry dengan backoff
                if response.status_code in (403, 429):
                    # Log response body & headers untuk debugging
                    try:
                        resp_text = response.text[:500] if response.text else "(empty)"
                        logger.warning(
                            "[Shopee] HTTP %d - Response preview: %s",
                            response.status_code, resp_text
                        )
                    except:
                        pass
                    
                    if attempt < _MAX_RETRIES - 1:
                        wait_time = _RETRY_BACKOFF * (2 ** attempt)  # exponential backoff
                        # Add random jitter untuk lebih human-like
                        jitter = random.uniform(0.5, 2.0)
                        total_wait = wait_time + jitter
                        
                        logger.warning(
                            "[Shopee] HTTP %d untuk '%s'. Retry dalam %.1f detik (attempt %d/%d)...",
                            response.status_code, keyword, total_wait, attempt + 1, _MAX_RETRIES
                        )
                        time.sleep(total_wait)
                        continue
                    else:
                        logger.error(
                            "[Shopee] HTTP %d - Max retry tercapai. Kemungkinan: IP blocked, cookie invalid, atau bot detection.",
                            response.status_code
                        )
                        return {}
                
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                logger.error(
                    "[Shopee] Timeout saat mengambil data untuk '%s' (attempt %d/%d).",
                    keyword, attempt + 1, _MAX_RETRIES
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF + random.uniform(0.5, 1.5))
                    
            except requests.exceptions.HTTPError as exc:
                logger.error(
                    "[Shopee] HTTP error %s untuk '%s' (attempt %d/%d).",
                    exc.response.status_code, keyword, attempt + 1, _MAX_RETRIES
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF + random.uniform(0.5, 1.5))
                    
            except requests.exceptions.RequestException as exc:
                logger.error(
                    "[Shopee] Kesalahan jaringan: %s (attempt %d/%d)",
                    exc, attempt + 1, _MAX_RETRIES
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF + random.uniform(0.5, 1.5))
                    
            except ValueError:
                logger.error(
                    "[Shopee] Gagal mem-parse JSON response untuk '%s' (attempt %d/%d).",
                    keyword, attempt + 1, _MAX_RETRIES
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_BACKOFF + random.uniform(0.5, 1.5))

        logger.error(
            "[Shopee] Semua retry gagal untuk '%s'. IP mungkin blocked atau bot detection terpicu. Solusi: cek cookie, gunakan proxy, atau tunggu beberapa jam.",
            keyword
        )
        return {}

    def _parse(
        self,
        raw_data: Dict[str, Any],
        keyword: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Ekstrak dan bersihkan data produk & toko dari JSON response Shopee.

        Aturan wajib harga:
            Shopee mengirim harga dalam satuan x100.000.
            Selalu bagi dengan 100_000.0 sebelum menyimpan!
        """
        items: list = raw_data.get("items", [])
        if not items:
            return [], []

        filtered_products: List[Dict[str, Any]] = []
        shops_map: Dict[str, Dict[str, Any]] = {}  # deduplikasi toko by shop_id

        for entry in items:
            item = entry.get("item_basic", {})
            if not item:
                continue

            item_id = item.get("itemid")
            shop_id = item.get("shopid")
            if not item_id or not shop_id:
                continue

            item_id_str = str(item_id)
            shop_id_str = str(shop_id)

            # --- Harga (WAJIB dibagi 100.000) ---
            raw_price          = item.get("price", 0) or 0
            raw_price_original = item.get("price_before_discount", 0) or 0
            price              = float(raw_price) / 100_000.0
            price_original     = float(raw_price_original) / 100_000.0
            if price_original <= 0:
                price_original = price

            # --- Diskon ---
            discount = self._safe_int(item.get("raw_discount"), fallback=0)

            # --- Rating ---
            rating = 0.0
            try:
                rating_data = item.get("item_rating") or {}
                rating = float(rating_data.get("rating_star", 0.0) or 0.0)
            except (TypeError, ValueError):
                pass

            # --- Penjualan ---
            sold = self._safe_int(item.get("historical_sold"), fallback=0)

            # --- URL & Gambar ---
            url        = f"https://shopee.co.id/product-i.{shop_id_str}.{item_id_str}"
            image_hash = item.get("image", "")
            image_url  = (
                f"https://down-id.img.susercontent.com/file/{image_hash}"
                if image_hash else ""
            )

            filtered_products.append({
                "source":         "shopee",
                "product_id":     item_id_str,
                "name":           item.get("name", "").strip(),
                "url":            url,
                "image":          image_url,
                "price":          price,
                "price_original": price_original,
                "discount":       discount,
                "rating":         rating,
                "sold":           sold,
                "shop_id":        shop_id_str,
                "keyword":        keyword,
            })

            # --- Toko (deduplikasi) ---
            if shop_id_str not in shops_map:
                is_official = bool(
                    item.get("is_official_shop") or item.get("shopee_verified")
                )
                shops_map[shop_id_str] = {
                    "shop_id":     shop_id_str,
                    "name":        item.get("shop_name", "").strip(),
                    "city":        item.get("shop_location", "").strip(),
                    "tier":        None,
                    "is_official": is_official,
                    "url":         "",
                }

        return filtered_products, list(shops_map.values())

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _random_sleep(self):
        """Jeda acak untuk menghindari rate-limit Shopee."""
        delay = random.uniform(*_SLEEP_RANGE)
        logger.debug("[Shopee] Jeda %.2f detik sebelum request.", delay)
        time.sleep(delay)
        
        # Extra delay dengan probabilitas untuk lebih aman
        if random.random() < 0.3:  # 30% chance untuk delay tambahan
            extra_delay = random.uniform(1.0, 3.0)
            logger.debug("[Shopee] Extra delay %.2f detik.", extra_delay)
            time.sleep(extra_delay)

    def _save_to_json(self, data: Any, filename: str):
        """Simpan data mentah ke file JSON untuk audit/debug."""
        try:
            path = _OUTPUT_DIR / f"{filename}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("[Shopee] Data mentah disimpan di: %s", path)
        except Exception as exc:
            logger.warning("[Shopee] Gagal menyimpan JSON: %s", exc)

    @staticmethod
    def _safe_int(value: Any, fallback: int = 0) -> int:
        """Konversi nilai ke int dengan aman."""
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return fallback


# ======================================================================
# BAGIAN 3 — WRAPPER PUBLIK
# (sebelumnya: shopee_scraper.py terpisah)
# ======================================================================

def ambil_top_toko(
    keyword: str,
    top_n: int = 5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Wrapper publik — titik masuk tunggal Shopee untuk seluruh aplikasi.

    Dipanggil oleh:
      - wishlist_page.py  → scrape_marketplace_live()
      - scraper_manager.py (opsional)
      - cli.py

    Kembalian
    ---------
    Tuple (normalized_products, normalized_shops) —
    langsung kompatibel dengan simpan_hasil() di engine.py.
    """
    scraper = ShopeeScraper()

    try:
        products, shops = scraper.scrape(keyword, top_n=top_n)
    except Exception as exc:
        logger.error("[shopee_scraper] Gagal scraping '%s': %s", keyword, exc)
        return [], []

    # --- Normalisasi produk → format unified Skintify-C4 ---
    normalized_products: List[Dict[str, Any]] = []
    for p in products:
        normalized_products.append({
            # Kunci yang dibaca _normalize_produk(platform="shopee") di engine.py
            "product_id":     p["product_id"],
            "shop_id":        p["shop_id"],
            "keyword":        keyword,
            "name":           p["name"],
            "nama":           p["name"],            # alias
            "url":            p["url"],
            "image":          p["image"],
            "gambar":         p["image"],            # alias
            "price":          p["price"],
            "price_original": p["price_original"],
            "discount":       p["discount"],
            "rating":         p["rating"],
            "sold":           p.get("sold", 0),
            # Kunci tambahan untuk UI wishlist
            "harga_teks":     f"Rp {int(p['price']):,}".replace(",", ".") if p["price"] > 0 else "Hubungi Toko",
            "price_original": p["price_original"],
            "discount":       p["discount"],
            "sold":           p.get("sold", 0),
            "kategori":       "",
            "label_badge":    "Shopee Mall" if p.get("is_official") else "",
            "free_ongkir":    0,
            "source":         "shopee",
        })

    # --- Normalisasi toko → format unified Skintify-C4 ---
    normalized_shops: List[Dict[str, Any]] = []
    for s in shops:
        normalized_shops.append({
            "shop_id":     s["shop_id"],
            "name":        s["name"],
            "nama":        s["name"],                # alias
            "city":        s.get("city", ""),
            "kota":        s.get("city", ""),        # alias
            "tier":        None,
            "is_official": s.get("is_official", False),
            "url":         s.get("url", ""),
        })

    logger.info(
        "[shopee_scraper] '%s' → %d produk, %d toko",
        keyword, len(normalized_products), len(normalized_shops),
    )
    return normalized_products, normalized_shops


# ======================================================================
# CLI — test langsung dari terminal
# python -m app.scraping.shopee_scraper "emina sunscreen" --top-n 5
# ======================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Shopee Scraper CLI — Skintify-C4")
    parser.add_argument("keyword", type=str, nargs="?", default="skintify moisturizer")
    parser.add_argument("--top-n", type=int, default=5)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    print(f"[RUN] Keyword: '{args.keyword}' | Top N: {args.top_n}")
    products, shops = ambil_top_toko(args.keyword, top_n=args.top_n)

    if not products:
        print("[WARN] Tidak ada produk ditemukan.")
    else:
        print(f"\n[OK] {len(products)} produk dari {len(shops)} toko:\n")
        for i, p in enumerate(products[:5], 1):
            print(f"  {i}. {p['nama'][:60]}")
            print(f"     Harga : {p['harga_teks']} | Rating: {p['rating']} | Terjual: {p['sold']}")
            print(f"     URL   : {p['url']}\n")