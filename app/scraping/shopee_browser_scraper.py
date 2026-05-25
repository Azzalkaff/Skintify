"""
app/scraping/shopee_browser_scraper.py
======================================
Shopee Scraper menggunakan Playwright headless browser.
Lebih mampu bypass bot detection dibanding plain HTTP requests.

Cara pakai:
    from app.scraping.shopee_browser_scraper import ambil_top_toko_browser
    products, shops = ambil_top_toko_browser("emina sunscreen", top_n=5)

Install: pip install playwright
Setup: playwright install chromium
"""

import logging
import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    logger.warning("[Shopee Browser] Playwright not installed. Install with: pip install playwright")
    sync_playwright = None


# ======================================================================
# KONFIGURASI
# ======================================================================

_OUTPUT_DIR = Path("data/raw")
_MAX_RETRIES = 2
_HEADLESS = True  # Set False untuk debugging (lihat browser window)


def _ambil_cookies_dari_env() -> str:
    """Baca cookie dari environment variable."""
    return os.getenv("SHOPEE_COOKIE", "")


# ======================================================================
# BROWSER SCRAPER CLASS
# ======================================================================

class ShopeeBrowserScraper:
    """
    Scraper Shopee menggunakan Playwright headless browser.
    
    Keuntungan vs plain HTTP:
    - Terlihat seperti real browser (bypass bot detection)
    - JavaScript dijalankan (API calls inside page)
    - Cookie & session management otomatis
    """

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def scrape(
        self,
        keyword: str,
        top_n: int = 5,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Titik masuk utama scraping dengan browser.

        Parameter
        ---------
        keyword : str
            Kata kunci pencarian produk.
        top_n : int
            Jumlah toko teratas yang dikembalikan.

        Kembalian
        ---------
        Tuple (products, shops[:top_n]).
        """
        if sync_playwright is None:
            logger.error("[Shopee Browser] Playwright tidak terinstall.")
            return [], []

        logger.info("[Shopee Browser] Memulai scraping keyword: '%s'", keyword)

        for attempt in range(_MAX_RETRIES):
            try:
                return self._scrape_with_browser(keyword, top_n, attempt)
            except Exception as exc:
                logger.error(
                    "[Shopee Browser] Error pada attempt %d/%d: %s",
                    attempt + 1, _MAX_RETRIES, exc
                )
                if attempt < _MAX_RETRIES - 1:
                    wait_time = random.uniform(5, 10)
                    logger.warning("[Shopee Browser] Retry dalam %.1f detik...", wait_time)
                    time.sleep(wait_time)

        logger.error("[Shopee Browser] Semua retry gagal untuk '%s'.", keyword)
        return [], []

    def _scrape_with_browser(
        self,
        keyword: str,
        top_n: int,
        attempt: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Internal method untuk scrape dengan browser."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=_HEADLESS)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="id-ID",
                timezone_id="Asia/Jakarta",
                extra_http_headers={
                    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                },
            )

            # Add cookies dari environment
            cookies_str = _ambil_cookies_dari_env()
            if cookies_str:
                try:
                    # Parse cookie string dan add ke context
                    cookie_dicts = self._parse_cookies(cookies_str)
                    if cookie_dicts:
                        context.add_cookies(cookie_dicts)
                        logger.debug("[Shopee Browser] %d cookies loaded dari env.", len(cookie_dicts))
                except Exception as exc:
                    logger.warning("[Shopee Browser] Gagal load cookies: %s", exc)

            page = context.new_page()

            try:
                # Navigate to Shopee search
                search_url = f"https://shopee.co.id/search?keyword={keyword}"
                logger.debug("[Shopee Browser] Navigate ke: %s", search_url)

                page.goto(search_url, wait_until="networkidle", timeout=30000)

                # Wait untuk search results muncul
                logger.debug("[Shopee Browser] Waiting untuk search results...")
                page.wait_for_selector('div[data-testid="product-item"]', timeout=15000)

                # Extract products dari page
                products_data = page.evaluate("""
                    () => {
                        const items = [];
                        const productElements = document.querySelectorAll('div[data-testid="product-item"]');
                        
                        productElements.forEach(el => {
                            try {
                                const productLink = el.querySelector('a[href*="/product/"]');
                                const priceEl = el.querySelector('[data-testid="product-price-final"]');
                                const originalPriceEl = el.querySelector('[data-testid="product-price-original"]');
                                const ratingEl = el.querySelector('[data-testid="product-rating"]');
                                const soldEl = el.querySelector('span:has-text("Terjual")');
                                const imageEl = el.querySelector('img');
                                
                                if (productLink && priceEl) {
                                    items.push({
                                        url: productLink.href,
                                        name: productLink.getAttribute('title') || '',
                                        price: priceEl.textContent || '',
                                        price_original: originalPriceEl?.textContent || '',
                                        rating: ratingEl?.textContent || '0',
                                        sold: soldEl?.textContent || '',
                                        image: imageEl?.src || '',
                                    });
                                }
                            } catch(e) {
                                console.log('Error parsing product:', e);
                            }
                        });
                        
                        return items;
                    }
                """)

                logger.info(
                    "[Shopee Browser] Ditemukan %d produk untuk '%s'",
                    len(products_data), keyword
                )

                # Parse dan normalize products
                products, shops = self._parse_products(products_data, keyword)

                # Save to JSON
                self._save_to_json(
                    {"keyword": keyword, "products": products},
                    f"shopee_browser_{keyword.replace(' ', '_')}",
                )

                return products, shops[:top_n]

            finally:
                page.close()
                context.close()
                browser.close()

    def _parse_cookies(self, cookie_str: str) -> List[Dict[str, Any]]:
        """Parse Shopee cookie string ke format Playwright."""
        cookies = []
        try:
            # Simple cookie parsing (format: name=value; name2=value2; ...)
            for cookie_pair in cookie_str.split(";"):
                cookie_pair = cookie_pair.strip()
                if "=" in cookie_pair:
                    name, value = cookie_pair.split("=", 1)
                    cookies.append({
                        "name": name.strip(),
                        "value": value.strip(),
                        "url": "https://shopee.co.id",
                    })
        except Exception as exc:
            logger.warning("[Shopee Browser] Error parsing cookies: %s", exc)

        return cookies

    def _parse_products(
        self,
        products_data: List[Dict[str, Any]],
        keyword: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Parse dan normalize product data."""
        normalized_products: List[Dict[str, Any]] = []
        shops_map: Dict[str, Dict[str, Any]] = {}

        for p in products_data:
            try:
                # Extract price (remove Rp, dots, etc)
                price_str = p.get("price", "").replace("Rp", "").replace(".", "").strip()
                price = float(price_str) if price_str else 0.0

                # Extract original price
                price_original_str = p.get("price_original", "").replace("Rp", "").replace(".", "").strip()
                price_original = float(price_original_str) if price_original_str else price

                # Extract rating (e.g., "4.5" dari "★★★★☆ 4.5")
                rating_str = p.get("rating", "0").split()[-1]
                try:
                    rating = float(rating_str)
                except:
                    rating = 0.0

                # Extract shop from URL
                url = p.get("url", "")
                shop_id = url.split("/product-i.")[-1].split(".")[0] if url else ""

                normalized_products.append({
                    "source": "shopee_browser",
                    "product_id": url.split(".")[-1] if url else "",
                    "name": p.get("name", "").strip(),
                    "url": url,
                    "image": p.get("image", ""),
                    "price": price,
                    "price_original": price_original,
                    "discount": int((1 - price / price_original) * 100) if price_original > 0 else 0,
                    "rating": rating,
                    "sold": int(p.get("sold", "0").split()[0]) if p.get("sold") else 0,
                    "keyword": keyword,
                })

                # Track shops
                if shop_id and shop_id not in shops_map:
                    shops_map[shop_id] = {
                        "shop_id": shop_id,
                        "name": "Shop",  # Dapat diupdate jika ada info shop
                        "url": "",
                    }

            except Exception as exc:
                logger.warning("[Shopee Browser] Error parsing product: %s", exc)
                continue

        return normalized_products, list(shops_map.values())

    def _save_to_json(self, data: Any, filename: str):
        """Simpan data ke file JSON."""
        try:
            path = _OUTPUT_DIR / f"{filename}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("[Shopee Browser] Data disimpan di: %s", path)
        except Exception as exc:
            logger.warning("[Shopee Browser] Gagal simpan JSON: %s", exc)


# ======================================================================
# WRAPPER PUBLIK
# ======================================================================

def ambil_top_toko_browser(
    keyword: str,
    top_n: int = 5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Wrapper publik untuk scrape Shopee menggunakan browser.
    
    Direkomendasikan saat plain HTTP scraping di-block (error 90309999).
    """
    scraper = ShopeeBrowserScraper()

    try:
        products, shops = scraper.scrape(keyword, top_n=top_n)
        return products, shops
    except Exception as exc:
        logger.error("[shopee_browser_scraper] Gagal scraping '%s': %s", keyword, exc)
        return [], []


# ======================================================================
# CLI TEST
# ======================================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Shopee Browser Scraper CLI")
    parser.add_argument("keyword", type=str, nargs="?", default="wardah sunscreen")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--headless", type=bool, default=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s — %(message)s")

    print(f"[RUN] Keyword: '{args.keyword}' | Top N: {args.top_n}")
    print("[INFO] Install Playwright: pip install playwright")
    print("[INFO] Setup browser: playwright install chromium\n")

    products, shops = ambil_top_toko_browser(args.keyword, top_n=args.top_n)

    if not products:
        print("[WARN] Tidak ada produk ditemukan.")
    else:
        print(f"\n[OK] {len(products)} produk dari {len(shops)} toko:\n")
        for i, p in enumerate(products[:5], 1):
            print(f"  {i}. {p['name'][:60]}")
            print(f"     Harga : Rp {int(p['price']):,} | Rating: {p['rating']} | Terjual: {p['sold']}")
            print(f"     URL   : {p['url']}\n")
