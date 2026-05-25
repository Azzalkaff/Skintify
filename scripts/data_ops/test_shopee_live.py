import sys
import os
from pathlib import Path
import logging

# Setup Pathing agar script dapat mengimpor dari root folder 'app'
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Aktifkan Logger untuk melacak aktivitas scraping di terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from app.scraping.core.shopee import ShopeeScraper

def test_live():
    print("\n" + "="*60)
    print("   SKINTIFY DIAGNOSTIC LIVE TRACE: SHOPEE API SCRAPER")
    print("="*60)
    
    # 1. Inisialisasi Scraper
    print("\n[1] Menginisialisasi ShopeeScraper...")
    try:
        scraper = ShopeeScraper()
        print("    [OK] Scraper berhasil diinisialisasi.")
    except Exception as e:
        print(f"    [ERR] Gagal inisialisasi scraper: {e}")
        return

    # 2. Ambil data pencarian dari Shopee
    keyword = "wardah moisturizer"
    print(f"\n[2] Mengambil data mentah Shopee untuk keyword: '{keyword}'...")
    try:
        raw_response = scraper._fetch(keyword)
        if not raw_response:
            print("    [ERR] Gagal: Tidak ada data/respons dari Shopee API (Terblokir atau Timeout).")
            print("    [INFO] Tips: Shopee memblokir IP server cloud. Anda mungkin perlu menggunakan VPN atau melampirkan cookie valid.")
            return
        
        items = raw_response.get("items", []) or []
        print(f"    [OK] Sukses! Diterima {len(items)} entri produk mentah dari Shopee.")
    except Exception as e:
        print(f"    [ERR] Terjadi error saat fetching: {e}")
        return

    # 3. Trace data mentah vs normalisasi untuk 2 entri pertama
    print("\n[3] Mentrasir dan Membandingkan Data Mentah vs Hasil Normalisasi...")
    
    products, shops = scraper._parse(raw_response, keyword)
    
    # Trace 2 produk teratas
    for i, entry in enumerate(items[:2]):
        item = entry.get("item_basic", {}) if isinstance(entry, dict) else {}
        if not item:
            continue
        print(f"\n--- [ENTRI PRODUK MENTAH #{i+1}] ---")
        print(f"    - itemid        : {item.get('itemid')}")
        print(f"    - shopid        : {item.get('shopid')}")
        print(f"    - name          : {item.get('name')}")
        print(f"    - price (mentah): {item.get('price')} (ini adalah Rp{float(item.get('price', 0))/100000.0:,.2f})")
        print(f"    - price_before  : {item.get('price_before_discount')} (ini adalah Rp{float(item.get('price_before_discount', 0))/100000.0:,.2f})")
        print(f"    - raw_discount  : {item.get('raw_discount')}%")
        print(f"    - rating_star   : {item.get('item_rating', {}).get('rating_star')}")
        print(f"    - image (hash)  : {item.get('image')}")
        print(f"    - shop_location : {item.get('shop_location')}")
        
        # Cari data hasil normalisasi yang bersangkutan
        product_id_str = str(item.get('itemid'))
        normalized_prod = next((p for p in products if p["product_id"] == product_id_str), None)
        
        if normalized_prod:
            print(f"\n--- [HASIL NORMALISASI PRODUK #{i+1}] ---")
            print(f"    - platform       : {normalized_prod.get('platform')}")
            print(f"    - product_id     : {normalized_prod.get('product_id')}")
            print(f"    - shop_id        : {normalized_prod.get('shop_id')}")
            print(f"    - nama           : {normalized_prod.get('name')}")
            print(f"    - url            : {normalized_prod.get('url')}")
            print(f"    - gambar (CDN URL): {normalized_prod.get('image')}")
            print(f"    - harga (Live DB): Rp{normalized_prod.get('price'):,.2f}  <-- SUDAH DIKONVERSI")
            print(f"    - harga_asli     : Rp{normalized_prod.get('price_original'):,.2f}")
            print(f"    - diskon_persen  : {normalized_prod.get('discount')}%")
            print(f"    - rating         : {normalized_prod.get('rating')} / 5.0")
            print(f"    - terjual        : {normalized_prod.get('sold')}")
        else:
            print("    [ERR] Hasil normalisasi tidak ditemukan untuk item ini.")

    # 4. Trace data toko
    print("\n[4] Mentrasir Hasil Normalisasi Toko...")
    for i, shop in enumerate(shops[:2]):
        print(f"\n--- [HASIL NORMALISASI TOKO #{i+1}] ---")
        print(f"    - shop_id        : {shop.get('shop_id')}")
        print(f"    - nama           : {shop.get('name')}")
        print(f"    - kota           : {shop.get('city')}")
        print(f"    - is_official    : {shop.get('is_official')} (Star/Star+/Mall)")

    print("\n" + "="*60)
    print("   DIAGNOSTIC TRACE SELESAI DENGAN SUKSES!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_live()
