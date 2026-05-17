import os
import sys
from pathlib import Path

# Add project root to path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import SessionLocal, hitung_kemiripan
from app.database.models import Produk, SociollaReferensi, Toko

def fix_links():
    print("=" * 60)
    print("[REPAIR] SKINTIFY DATABASE LINK REPAIRER & DEDUPLICATOR")
    print("=" * 60)
    
    with SessionLocal() as session:
        # Step 1: Repair missing keyword_digunakan in SociollaReferensi
        print("\n[Step 1] Memeriksa & memperbaiki keyword_digunakan di SociollaReferensi...")
        refs_to_repair = session.query(SociollaReferensi).filter(
            (SociollaReferensi.keyword_digunakan == None) | (SociollaReferensi.keyword_digunakan == "")
        ).all()
        
        repaired_refs = 0
        for r in refs_to_repair:
            r.keyword_digunakan = f"{r.brand} {r.product_name}".strip()
            repaired_refs += 1
            
        if repaired_refs > 0:
            session.commit()
            print(f"   [OK] Berhasil memperbaiki {repaired_refs} produk referensi.")
        else:
            print("   [OK] Semua produk referensi sudah memiliki keyword_digunakan.")

        # Step 2: Repair and validate links in Produk
        print("\n[Step 2] Memeriksa, menautkan, dan menyaring produk marketplace...")
        all_products = session.query(Produk).all()
        print(f"   Ditemukan {len(all_products)} produk marketplace di database.")
        
        linked_count = 0
        deleted_count = 0
        already_linked_clean = 0
        
        for p in all_products:
            # 1. Cari referensi berdasarkan keyword
            ref = session.query(SociollaReferensi).filter_by(keyword_digunakan=p.keyword).first()
            
            # Fallback: jika tidak ketemu by keyword, coba by substring nama
            if not ref:
                # Coba cari partial match
                ref = session.query(SociollaReferensi).filter(
                    (SociollaReferensi.brand.ilike(f"%{p.keyword}%")) | 
                    (SociollaReferensi.product_name.ilike(f"%{p.keyword}%"))
                ).first()

            if not ref:
                # Jika benar-benar tidak ada referensinya di DB, biarkan saja
                p.referensi_id = None
                continue

            # 2. Hitung Kemiripan (Anti-Mismatch & Duplikasi Salah Sasaran)
            score, is_match = hitung_kemiripan(p.nama, ref.brand, ref.product_name)
            
            if is_match:
                # Link valid! Simpan referensi_id
                if p.referensi_id != ref.id:
                    p.referensi_id = ref.id
                    linked_count += 1
                else:
                    already_linked_clean += 1
                ref.sudah_di_scrape = True
            else:
                # Mismatch terdeteksi! Hapus produk sampah/salah sasaran dari database
                try:
                    print(f"   [Mismatch Dihapus] '{p.nama[:45]}...' (Tidak cocok dengan '{ref.product_name[:30]}', Score: {score:.1f}%)")
                except:
                    print(f"   [Mismatch Dihapus] ID {p.id} (Tidak cocok dengan '{ref.product_name[:30]}', Score: {score:.1f}%)")
                session.delete(p)
                deleted_count += 1
        
        session.commit()
        
        # Cleanup Toko yang kosong setelah penghapusan produk
        print("\n[Step 3] Membersihkan Toko yang kosong...")
        all_shops = session.query(Toko).all()
        deleted_shops = 0
        for s in all_shops:
            prod_count = session.query(Produk).filter_by(toko_id=s.id).count()
            if prod_count == 0:
                session.delete(s)
                deleted_shops += 1
        
        if deleted_shops > 0:
            session.commit()
            print(f"   [CLEAN] Berhasil menghapus {deleted_shops} toko kosong.")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] REPAIR SELESAI!")
        print(f"   • Referensi Diperbaiki   : {repaired_refs}")
        print(f"   • Tautan Berhasil Dibuat  : {linked_count}")
        print(f"   • Produk Bersih Valid    : {already_linked_clean}")
        print(f"   • Produk Mismatch Dihapus: {deleted_count}")
        print("=" * 60 + "\n")

if __name__ == "__main__":
    fix_links()
