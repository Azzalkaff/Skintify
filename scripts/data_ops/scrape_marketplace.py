import sys
import os
from pathlib import Path

# Fix Pathing - Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.scraping.scraper_manager import ScraperManager
from app.scraping.core.services import KeywordService
from app.scraping.core.config import DEFAULT_TOP_N

def main():
    print("\n" + "="*40)
    print("   SKINTIFY UNIFIED MARKETPLACE SCRAPER")
    print("="*40)
    
    # 1. Resolve Keywords
    if len(sys.argv) > 1:
        keywords = sys.argv[1:]
    else:
        keywords = KeywordService.get_keywords_from_sociolla()
        if keywords:
            print(f"[Info] Ditemukan {len(keywords)} produk dari Sociolla.")
            if len(keywords) > 5:
                ans = input(f"Lanjutkan batch scrape {len(keywords)} produk? (y/n): ")
                if ans.lower() != 'y': return
        else:
            raw_input = input("Masukkan keyword (pisah koma): ")
            keywords = [k.strip() for k in raw_input.split(",") if k.strip()]

    if not keywords:
        print("[!] Tidak ada keyword untuk diproses.")
        return

    # 2. Run Scraping
    try:
        manager = ScraperManager()
        path = manager.run_batch(keywords, top_n=DEFAULT_TOP_N)
        print(f"\n[Selesai] Data tersimpan di: {path}")
    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh pengguna.")
    except Exception as e:
        print(f"\n[Error] Terjadi kesalahan fatal: {e}")

if __name__ == "__main__":
    main()
