import sys
import os
import random
import time
import argparse
from concurrent.futures import ThreadPoolExecutor

# Menambahkan path project agar bisa import modul app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database.engine import SessionLocal, simpan_hasil, tandai_sudah_di_scrape, init_db
from app.database.models import SociollaReferensi
from app.scraping.tokopedia_scraper import ambil_top_toko as ambil_tokopedia
from app.scraping.lazada_scraper import ambil_top_toko as ambil_lazada
from app.scraping.core.shopee import ShopeeScraper

def scrape_one(ref_id, brand, product_name, keyword, platform="both"):
    print(f"\n" + "="*50)
    print(f"🔄 MENJALANKAN SCRAPING: {brand} - {product_name}")
    print(f"🔑 Keyword : '{keyword}'")
    print(f"🌐 Platform: {platform.upper()}")
    print("="*50)
    
    pt, tt = 0, 0
    pl, tl = 0, 0
    ps, ts = 0, 0
    
    def run_tokopedia():
        nonlocal pt, tt
        try:
            print("[*] Memulai scraping Tokopedia...")
            res = ambil_tokopedia(keyword, top_n=5)
            # Handle if returns 2 or 3 elements gracefully
            if isinstance(res, tuple) and len(res) == 3:
                produk_list, toko_list, total_data = res
            elif isinstance(res, tuple) and len(res) == 2:
                produk_list, toko_list = res
                total_data = len(produk_list)
            else:
                raise ValueError("Response dari Tokopedia scraper tidak valid")
            
            with SessionLocal() as s:
                simpan_hasil(s, "tokopedia", keyword, produk_list, toko_list, total_data, referensi_id=ref_id)
            pt, tt = len(produk_list), len(toko_list)
            print(f"✅ [Tokopedia] Selesai: Scrape {pt} produk dari {tt} toko.")
        except Exception as e:
            print(f"❌ [Tokopedia] Error saat scraping: {e}")
            
    def run_lazada():
        nonlocal pl, tl
        try:
            print("[*] Memulai scraping Lazada...")
            res = ambil_lazada(keyword, top_n=5)
            # Handle if returns 2 or 3 elements gracefully
            if isinstance(res, tuple) and len(res) == 3:
                produk_list, toko_list, total_data = res
            elif isinstance(res, tuple) and len(res) == 2:
                produk_list, toko_list = res
                total_data = len(produk_list)
            else:
                raise ValueError("Response dari Lazada scraper tidak valid")
                
            with SessionLocal() as s:
                simpan_hasil(s, "lazada", keyword, produk_list, toko_list, total_data, referensi_id=ref_id)
            pl, tl = len(produk_list), len(toko_list)
            print(f"✅ [Lazada] Selesai: Scrape {pl} produk dari {tl} toko.")
        except Exception as e:
            print(f"❌ [Lazada] Error saat scraping: {e}")

    def run_shopee():
        nonlocal ps, ts
        try:
            print("[*] Memulai scraping Shopee...")
            scraper = ShopeeScraper()
            produk_list, toko_list = scraper.scrape(keyword, top_n=5)
            
            with SessionLocal() as s:
                simpan_hasil(s, "shopee", keyword, produk_list, toko_list, len(produk_list), referensi_id=ref_id)
            ps, ts = len(produk_list), len(toko_list)
            print(f"✅ [Shopee] Selesai: Scrape {ps} produk dari {ts} toko.")
        except Exception as e:
            print(f"❌ [Shopee] Error saat scraping: {e}")

    # Run scraping based on choice
    if platform == "both":
        with ThreadPoolExecutor(max_workers=3) as executor:
            fut_t = executor.submit(run_tokopedia)
            fut_l = executor.submit(run_lazada)
            fut_s = executor.submit(run_shopee)
            fut_t.result()
            fut_l.result()
            fut_s.result()
    elif platform == "tokopedia":
        run_tokopedia()
    elif platform == "lazada":
        run_lazada()
    elif platform == "shopee":
        run_shopee()

    try:
        with SessionLocal() as s:
            tandai_sudah_di_scrape(s, brand, product_name)
    except Exception as e:
        print(f"⚠️ Gagal menandai produk sebagai sudah di-scrape: {e}")
    
    print(f"\n✨ Selesai memproses '{keyword}'! Hasil: Tokped={pt} produk, Lazada={pl} produk, Shopee={ps} produk.")

def main():
    parser = argparse.ArgumentParser(description="Manual Scraper Skintify")
    parser.add_argument("--ids", type=str, required=True, help="Koma terpisah ID produk master dari sociolla_referensi")
    parser.add_argument("--platform", type=str, choices=["both", "tokopedia", "lazada", "shopee"], default="both", help="Platform yang ingin di-scrape")
    args = parser.parse_args()
    
    # Inisialisasi DB jika belum ada
    init_db()
    
    # Parsing ID produk
    try:
        product_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    except Exception as e:
        print(f"❌ Gagal mem-parse list ID produk: {e}")
        sys.exit(1)
        
    if not product_ids:
        print("❌ Tidak ada ID produk yang valid untuk di-scrape.")
        sys.exit(1)
        
    print(f"⚙️ Memulai sesi manual scraping untuk {len(product_ids)} produk...")
    
    with SessionLocal() as session:
        products_to_scrape = []
        for pid in product_ids:
            p = session.query(SociollaReferensi).filter_by(id=pid).first()
            if p:
                products_to_scrape.append({
                    'id': p.id,
                    'brand': p.brand,
                    'product_name': p.product_name,
                    'keyword': p.keyword_digunakan or f"{p.brand} {p.product_name}".strip()
                })
            else:
                print(f"⚠️ Produk dengan ID {pid} tidak ditemukan di database!")
                
    if not products_to_scrape:
        print("❌ Tidak ditemukan produk yang cocok di database master.")
        sys.exit(1)
        
    # Jalankan scraping satu per satu
    for i, prod in enumerate(products_to_scrape):
        scrape_one(
            ref_id=prod['id'],
            brand=prod['brand'],
            product_name=prod['product_name'],
            keyword=prod['keyword'],
            platform=args.platform
        )
        
        # Jeda acak antar produk untuk menghindari rate limiting/IP ban
        if i < len(products_to_scrape) - 1:
            delay = random.uniform(2.0, 4.0)
            print(f"⏳ Menunggu {delay:.1f} detik sebelum memproses produk berikutnya...")
            time.sleep(delay)
            
    print("\n🎉 SEMUA MANUAL SCRAPING SELESAI!")

if __name__ == "__main__":
    main()
