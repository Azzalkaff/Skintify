
import json
import os
import sys
from pathlib import Path

# Fix Pathing - Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import SessionLocal, simpan_hasil, tandai_sudah_di_scrape, init_db
from app.database.models import SociollaReferensi

def run_import():
    # Inisialisasi database (buat tabel jika belum ada)
    init_db()
    print("=" * 55)
    print("🚀 IMPORT DATA MARKETPLACE (JSON -> SQLITE)")
    print("=" * 55)

    JSON_FILE = Path(root_dir) / "data" / "merged_scraped_results.json"

    if not JSON_FILE.exists():
        print(f"❌ ERROR: File {JSON_FILE} tidak ditemukan!")
        print("Harap jalankan 'Gabungkan Hasil Scraping' di CLI terlebih dahulu.")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        content = json.load(f)
        data_list = content.get("data", [])

    if not data_list:
        print("⚠ Data scraping kosong.")
        return

    print(f"📦 Memproses {len(data_list)} keyword dari JSON...\n")

    with SessionLocal() as session:
        berhasil = 0
        for entry in data_list:
            keyword = entry.get("keyword")
            marketplaces = entry.get("marketplaces", {})

            for platform, results in marketplaces.items():
                prods = results.get("products", [])
                shops = results.get("shops", [])
                
                if not prods:
                    continue
                
                try:
                    # Cari referensi_id berdasarkan keyword
                    ref = session.query(SociollaReferensi).filter_by(keyword_digunakan=keyword).first()
                    ref_id = ref.id if ref else None

                    # Gunakan fungsi internal engine untuk simpan
                    simpan_hasil(
                        session=session,
                        platform=platform,
                        keyword=keyword,
                        produk_list=prods,
                        toko_list=shops,
                        total_data=len(prods),
                        referensi_id=ref_id
                    )
                    
                    if ref:
                        ref.sudah_di_scrape = True
                    
                    session.commit()
                    berhasil += 1
                except Exception as e:
                    print(f"   [!] Gagal simpan '{keyword}' [{platform}]: {e}")
                    session.rollback()

        # Final commit for any pending changes
        session.commit()

    print("\n" + "=" * 55)
    print(f"✅ IMPORT SELESAI!")
    print(f"   {berhasil} sesi pencarian berhasil dimasukkan ke database.")
    print("=" * 55)

if __name__ == "__main__":
    run_import()
