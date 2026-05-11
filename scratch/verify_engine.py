"""
Verifikasi engine.py setelah perubahan .env
"""
import sys, os
sys.path.insert(0, '.')

# Load .env dulu
from dotenv import load_dotenv
load_dotenv(override=True)

db_url_raw = os.getenv("DATABASE_URL", "")
print(f"DATABASE_URL di .env: {db_url_raw}")

from app.database.engine import engine, SessionLocal
print(f"Engine URL aktif: {engine.url}")

from app.database.models import SociollaReferensi
with SessionLocal() as session:
    count = session.query(SociollaReferensi).count()
    print(f"sociolla_referensi rows: {count}")
    
    if count > 0:
        sample = session.query(SociollaReferensi).first()
        print(f"Sample produk: {sample.brand} - {sample.product_name}")
        print(f"  image_url: {sample.image_url[:60] if sample.image_url else 'KOSONG'}")
        print(f"  rating: {sample.rating_sociolla}")
        print(f"  ingredients snippet: {str(sample.ingredients)[:80] if sample.ingredients else 'KOSONG'}")
        print()
        print("Engine berfungsi! Halaman akan menampilkan data.")
    else:
        print("WARNING: Tabel ada tapi tidak ada data!")
