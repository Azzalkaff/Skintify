import sys
import os

# Menambahkan path project agar bisa import modul app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database.engine import SessionLocal
from app.database.models import Toko, Produk, HasilPencarian

def hapus_data_marketplace():
    """Menghapus semua data Tokopedia, Lazada, dan Shopee dari database."""
    session = SessionLocal()
    try:
        print("[*] Memulai pembersihan database...")
        
        # 1. Hapus Produk
        produk_terhapus = session.query(Produk).filter(Produk.platform.in_(['tokopedia', 'lazada', 'shopee'])).delete(synchronize_session=False)
        print(f"[OK] Berhasil menghapus {produk_terhapus} data produk.")
        
        # 2. Hapus Toko
        toko_terhapus = session.query(Toko).filter(Toko.platform.in_(['tokopedia', 'lazada', 'shopee'])).delete(synchronize_session=False)
        print(f"[OK] Berhasil menghapus {toko_terhapus} data toko.")
        
        # 3. Hapus Hasil Pencarian
        pencarian_terhapus = session.query(HasilPencarian).filter(HasilPencarian.platform.in_(['tokopedia', 'lazada', 'shopee'])).delete(synchronize_session=False)
        print(f"[OK] Berhasil menghapus {pencarian_terhapus} riwayat pencarian.")
        
        session.commit()
        print("\n[DONE] Database Tokopedia, Lazada, dan Shopee telah dikosongkan!")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Terjadi kesalahan saat menghapus data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Script ini dijalankan langsung oleh CLI
    hapus_data_marketplace()
