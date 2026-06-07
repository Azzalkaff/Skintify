import os
import shutil
import logging
from app.database.database_manager import BasisData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResetDB")

def reset_sekarang():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    db_file = os.path.join(root_dir, 'data', 'db', 'tokopedia.db')
    
    print("⚠️  SEDANG MERESET DATABASE KE SETELAN PABRIK...")
    
    # 1. Hapus database lama
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            logger.info(f"Berhasil menghapus {db_file}")
        except Exception as e:
            logger.error(f"Gagal menghapus database: {e}")
            print("❌ Error: Tutup aplikasi Skintify dulu sebelum reset!")
            return

    # 2. Inisialisasi ulang tabel
    try:
        BasisData.inisialisasi()
        print("✅ DATABASE BERHASIL DIRESET!")
        print("Sekarang kalian bisa menjalankan 'python main.py' dengan data bersih.")
    except Exception as e:
        logger.error(f"Gagal inisialisasi: {e}")

if __name__ == "__main__":
    reset_sekarang()
