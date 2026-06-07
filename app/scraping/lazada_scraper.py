import os
import sys
import codecs
import argparse
from typing import List, Dict, Any, Tuple

# Fix UnicodeEncodeError on Windows / PyInstaller executables when printing emojis
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

# Fix Pathing - Pastikan root directory ada di sys.path agar 'from app' bisa terbaca
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.scraping.core.lazada import LazadaScraper

def ambil_top_toko(keyword: str, top_n: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Cari produk Lazada untuk keyword, kembalikan list produk & toko teratas 
    yang sudah dinormalisasi ke format yang didukung oleh Skintify-C4.
    """
    scraper = LazadaScraper()
    
    # Menjalankan scraper Lazada yang sesungguhnya
    filtered_products, shops = scraper.scrape(keyword, top_n=top_n)
    
    # Normalisasi format ke format produk & toko Skintify-C4 (untuk kompatibilitas dengan database & UI)
    normalized_products = []
    for p in filtered_products:
        # Tentukan status official dan label COD
        is_official = False
        shop_match = next((s for s in shops if s["shop_id"] == p["shop_id"]), None)
        if shop_match:
            is_official = shop_match.get("is_lazmall", False)
            
        badge_label = "LazMall" if is_official else ""
        if p.get("is_cod"):
            badge_label = f"{badge_label} | COD" if badge_label else "Bisa COD"
            
        normalized_products.append({
            "product_id":      p["product_id"],
            "keyword":         keyword,
            "nama":            p["name"],
            "url":             p["url"],
            "gambar":          p["image"],
            "harga":           p["price"],
            "harga_teks":      f"Rp {int(p['price']):,}" if p["price"] > 0 else "Hubungi Toko",
            "harga_asli":      p["price_original"],
            "diskon_persen":   p["discount"],
            "rating":          p["rating"],
            "terjual":         p.get("terjual", 0),  # Meneruskan jumlah pembelian yang berhasil diekstrak
            "kategori":        "",
            "label_badge":     badge_label,
            "free_ongkir":     0,
            "shop_id":         p["shop_id"],
        })
        
    normalized_shops = []
    for s in shops:
        normalized_shops.append({
            "shop_id":     s["shop_id"],
            "nama":        s["name"],
            "kota":        s["city"],  # Meneruskan city agar normalizer di engine.py/gui bisa membacanya
            "city":        s["city"],  # Duplikasi demi keandalan penuh
            "tier":        None,
            "is_lazmall":  s.get("is_lazmall", False),
            "is_official": s.get("is_lazmall", False),
            "url":         s.get("url", ""),
        })
        
    return normalized_products, normalized_shops

def main():
    parser = argparse.ArgumentParser(description="Lazada Live API Scraper CLI")
    parser.add_argument("keyword", type=str, nargs="?", default="skintify moisturizer", help="Kata kunci pencarian")
    parser.add_argument("--top-n", type=int, default=5, help="Jumlah toko teratas untuk diambil")
    args = parser.parse_args()
    
    print("[RUN] Menjalankan Lazada Scraper langsung dari CLI...")
    print(f"[INFO] Keyword: '{args.keyword}' | Top N Toko: {args.top_n}")
    
    try:
        products, shops = ambil_top_toko(args.keyword, top_n=args.top_n)
        print("\n[SUCCESS] SCRAPING SELESAI!")
        print(f"[INFO] Ditemukan {len(products)} produk dari {len(shops)} toko teratas.")
        print("-" * 50)
        for i, p in enumerate(products[:5], 1):
            print(f"{i}. [Lazada] {p['nama'][:60]}...")
            print(f"   Harga: {p['harga_teks']} | Rating: {p['rating']} | Shop ID: {p['shop_id']}")
            print(f"   URL  : {p['url']}")
    except Exception as e:
        print(f"[ERROR] Terjadi kesalahan saat menjalankan scraper Lazada: {e}")

if __name__ == "__main__":
    main()