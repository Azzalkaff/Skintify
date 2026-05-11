import sys
import os

# Menambahkan path project agar bisa import modul app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi

def reset_scrape_status():
    """Mengubah semua status sudah_di_scrape menjadi False."""
    session = SessionLocal()
    try:
        print("[*] Mengakses database...")
        
        # Update semua record di tabel sociolla_referensi
        total_updated = session.query(SociollaReferensi).update({SociollaReferensi.sudah_di_scrape: False})
        
        session.commit()
        print(f"[OK] Berhasil mereset status scrape untuk {total_updated} produk.")
        print("[DONE] Sekarang bot akan mendeteksi semua produk sebagai produk baru.")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Terjadi kesalahan saat mereset status: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    reset_scrape_status()
