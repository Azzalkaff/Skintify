"""
migration_add_slug.py — Tambahkan kolom slug ke tabel sociolla_referensi yang sudah ada.
Jalankan sekali: python scripts/migration_add_slug.py
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv(override=True)

from app.database.engine import engine
from sqlalchemy import text, inspect

print("=" * 55)
print(" [MIGRATION] Tambah Kolom Slug ke sociolla_referensi")
print("=" * 55)

with engine.connect() as conn:
    # Cek kolom yang sudah ada
    inspector = inspect(engine)
    existing_cols = [col["name"] for col in inspector.get_columns("sociolla_referensi")]
    print(f"\nKolom yang ada saat ini: {existing_cols}")

    # Kolom-kolom baru yang perlu ditambahkan jika belum ada
    new_columns = {
        "slug":         "VARCHAR(255)",
        "brand_country": "VARCHAR(100)",
        "brand_region":  "VARCHAR(100)",
        "keyword_digunakan": "VARCHAR(500)",
        "all_categories": "JSON",
        "min_price_after_discount": "FLOAT",
        "max_price_after_discount": "FLOAT",
        "harga_setelah_diskon": "FLOAT",
        "diskon":        "VARCHAR(50)",
        "total_recommended": "INTEGER DEFAULT 0",
        "repurchase_yes":  "INTEGER DEFAULT 0",
        "repurchase_no":   "INTEGER DEFAULT 0",
        "repurchase_maybe":"INTEGER DEFAULT 0",
        "total_wishlist":  "INTEGER DEFAULT 0",
        "bpom_reg_no":     "VARCHAR(100)",
        "image_url":       "VARCHAR(500)",
        "is_flashsale":    "BOOLEAN DEFAULT 0",
        "sudah_di_scrape": "BOOLEAN DEFAULT 0",
        "description_raw": "TEXT",
        "how_to_use_raw":  "TEXT",
        "ingredients":     "TEXT",
        "variants":        "JSON",
        "reviews":         "JSON",
    }

    added = []
    skipped = []
    for col_name, col_type in new_columns.items():
        if col_name not in existing_cols:
            try:
                conn.execute(text(f"ALTER TABLE sociolla_referensi ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                added.append(col_name)
                print(f"  [+] Kolom ditambahkan: {col_name}")
            except Exception as e:
                print(f"  [!] Gagal tambah {col_name}: {e}")
        else:
            skipped.append(col_name)

print(f"\n[OK] Selesai! Ditambahkan: {len(added)} kolom, Dilewati (sudah ada): {len(skipped)} kolom.")

# Verifikasi akhir
with engine.connect() as conn:
    result = conn.execute(text("SELECT count(*) FROM sociolla_referensi"))
    count = result.scalar()
    print(f"[DB] Total data sociolla_referensi: {count} produk")
    
print("\n  Siap digunakan oleh aplikasi!")
print("=" * 55)
