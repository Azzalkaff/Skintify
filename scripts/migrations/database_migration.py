"""
migrate.py — Reset database ke schema baru (multi-platform)
=============================================================
⚠️  PERINGATAN: Script ini akan MENGHAPUS semua data lama di database!
    Jalankan SEKALI sebelum main.py jika kamu sudah punya tokopedia.db lama.

Jalankan: python migrate.py
"""

import os
from database import engine, init_db
from models import Base


def reset_db():
    db_file = "tokopedia.db"

    print("=" * 55)
    print("  Database Migration — Schema Baru (Multi-Platform)")
    print("=" * 55)
    print()
    print("⚠️  Script ini akan menghapus semua tabel lama dan")
    print("    membuat ulang dengan schema yang mendukung:")
    print("    - Kolom 'platform' (tokopedia / lazada)")
    print("    - Kolom 'terjual', 'jumlah_review', 'is_official'")
    print("    - Tabel baru: sociolla_referensi")
    print()

    if os.path.exists(db_file):
        print(f"📁 File ditemukan: {db_file}")
        konfirmasi = input("   Ketik 'ya' untuk lanjutkan (data lama akan hilang): ").strip().lower()
        if konfirmasi != "ya":
            print("   ❌ Dibatalkan.")
            return
    else:
        print(f"📁 File belum ada: {db_file} (akan dibuat baru)")

    print()
    print("🗑️  Menghapus semua tabel lama...")
    Base.metadata.drop_all(bind=engine)
    print("   ✅ Tabel lama dihapus.")

    print("🏗️  Membuat tabel baru dengan schema terbaru...")
    init_db()
    print("   ✅ Selesai! Database siap digunakan.")
    print()
    print("▶️  Selanjutnya jalankan: python main.py")


if __name__ == "__main__":
    reset_db()