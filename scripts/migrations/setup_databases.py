"""
setup_databases.py — Inisialisasi dan Reset semua database proyek Skintify.
========================================================================
Script ini akan:
1. Membuat folder data/db jika belum ada.
2. Menginisialisasi data_skintify.db (User/Auth).
3. Menginisialisasi tokopedia.db (Scraping Data) dengan schema terbaru.

Jalankan: python scripts/setup_databases.py
"""

import os
import sys
import shutil
from dotenv import load_dotenv

# Load .env di awal
load_dotenv()

# Fix Pathing
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.database_manager import BasisData
from app.database.engine import init_db, engine
from app.database.models import Base

def setup():
    print("=" * 60)
    print(" 🛠️  SKINTIFY DATABASE SETUP & INITIALIZATION")
    print("=" * 60)

    # 1. Pastikan folder database ada
    db_folder = os.path.join(root_dir, "data", "db")
    if not os.path.exists(db_folder):
        print(f"📁 Membuat folder database: {db_folder}")
        os.makedirs(db_folder, exist_ok=True)

    # 2. Inisialisasi Database User (data_skintify.db)
    print("\n👤 [1/2] Menginisialisasi Database User (Auth)...")
    try:
        BasisData.inisialisasi()
        print("   ✅ Database User siap.")
    except Exception as e:
        print(f"   ❌ Gagal inisialisasi Database User: {e}")

    # 3. Inisialisasi Database Marketplace (Scraping)
    print("\n🛒 [2/2] Menginisialisasi Database Utama (Marketplace & Scraping)...")
    
    # Ambil url dari .env atau default ke skintify.db (selalu sinkron dengan engine.py)
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        db_path_actual = os.path.join(root_dir, "data", "db", "tokopedia.db")
        db_name = "tokopedia.db"
    else:
        db_name = db_url.replace("sqlite:///", "")
        if "/" not in db_name and "\\" not in db_name:
            db_path_actual = os.path.join(root_dir, "data", "db", db_name)
        else:
            db_path_actual = db_name

    if os.path.exists(db_path_actual) and os.path.getsize(db_path_actual) > 0:
        print(f"   ⚠️  Database '{db_name}' sudah ada dan terisi.")
        konfirmasi = input("      Ingin meriset ulang schema? (Data lama akan hilang!) [y/N]: ").strip().lower()
        if konfirmasi == 'y':
            try:
                # Tutup engine sebelum hapus file (penting untuk SQLite)
                engine.dispose()
                
                print(f"      🗑️  Menghapus file database '{db_name}'...")
                if os.path.exists(db_path_actual):
                    os.remove(db_path_actual)
                
                print("      🏗️  Membuat ulang database dengan skema baru...")
                init_db()
                print("   ✅ Database Utama berhasil direset total!")
            except Exception as e:
                print(f"   ❌ Gagal meriset Database Utama: {e}")
                print("      (Pastikan aplikasi NiceGUI sudah dimatikan agar file tidak terkunci)")
        else:
            print("   ⏩ Melewati reset schema.")
    else:
        try:
            init_db()
            print("   ✅ Database Utama berhasil dibuat!")
        except Exception as e:
            print(f"   ❌ Gagal membuat Database Utama: {e}")

    print("\n" + "=" * 60)
    print(" ✨ SEMUA DATABASE SIAP DIGUNAKAN!")
    print("=" * 60)
    print(" ▶️  Selanjutnya jalankan opsi ke-5 di CLI untuk mengimport data.")

if __name__ == "__main__":
    setup()
