import json
import os
import sys
import traceback

# Fix Pathing
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import engine, SessionLocal
from app.database.models import Base, SociollaReferensi

# File JSON sumber
JSON_FILE = os.path.join(root_dir, "data", "products_sociolla.json")

def normalize_category(raw_cat: str) -> str:
    """Konversi kategori berantakan dari Sociolla ke kategori bersih UI."""
    if not raw_cat:
        return "Lainnya"
    
    cat = str(raw_cat).lower()
    
    # Mapping Rules
    if "serum" in cat:
        return "Serum"
    if "moisturizer" in cat or "gel" in cat or "cream" in cat:
        return "Moisturizer"
    if "sunscreen" in cat or "sun care" in cat or "sun" in cat:
        return "Sunscreen"
    if "toner" in cat or "mist" in cat:
        return "Toner"
    if "wash" in cat or "cleanser" in cat or "micellar" in cat or "cleansing" in cat:
        return "Cleanser"
        
    return "Lainnya"

def run_migration():
    print("\n" + "=" * 50)
    print("🚀 RE-IMPORTING SOCIOLLA DATA (ROBUST MODE)")
    print("=" * 50)

    Base.metadata.create_all(bind=engine)
    
    if not os.path.exists(JSON_FILE):
        print(f"❌ ERROR: File {JSON_FILE} tidak ditemukan!")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        products = data.get("products", [])

    if not products:
        print("⚠ File JSON kosong.")
        return

    print(f"📦 Total produk di JSON: {len(products)}")
    
    berhasil = 0
    gagal = 0
    lewati = 0

    # Gunakan satu session untuk seluruh proses
    session = SessionLocal()

    for i, p in enumerate(products):
        try:
            slug = p.get("slug")
            if not slug:
                lewati += 1
                continue

            # Cek duplikat
            exists = session.query(SociollaReferensi).filter_by(slug=slug).first()
            if exists:
                lewati += 1
                continue

            # Mapping dengan proteksi nilai None
            db_product = SociollaReferensi(
                slug=slug,
                product_name=p.get("product_name", "Unknown Product"),
                brand=p.get("brand", "Unknown Brand"),
                brand_country=p.get("brand_country"),
                brand_region=p.get("brand_region"),
                category=normalize_category(p.get("category")),
                all_categories=p.get("all_categories", []),
                
                # Harga (Konversi ke float aman)
                min_price=float(p.get("min_price") or 0),
                max_price=float(p.get("max_price") or 0),
                min_price_after_discount=float(p.get("min_price_after_discount") or 0),
                max_price_after_discount=float(p.get("max_price_after_discount") or 0),
                
                # Performa
                rating_sociolla=float(p.get("average_rating") or 0),
                total_reviews=int(p.get("total_reviews") or 0),
                total_recommended=int(p.get("total_recommended") or 0),
                repurchase_yes=int(p.get("repurchase_yes") or 0),
                repurchase_no=int(p.get("repurchase_no") or 0),
                repurchase_maybe=int(p.get("repurchase_maybe") or 0),
                total_wishlist=int(p.get("total_wishlist") or 0),
                
                # Metadata
                bpom_reg_no=p.get("bpom_reg_no"),
                url_sociolla=p.get("url"),
                image_url=p.get("image_url"),
                is_in_stock=bool(p.get("is_in_stock", True)),
                is_flashsale=bool(p.get("is_flashsale", False)),
                
                # Raw Texts
                description_raw=p.get("description_raw", ""),
                how_to_use_raw=p.get("how_to_use_raw", ""),
                ingredients=p.get("ingredients", ""),
                
                # JSON Nested
                variants=p.get("variants", []),
                reviews=p.get("reviews", [])
            )
            
            session.add(db_product)
            
            # Commit setiap 50 item agar tidak berat di memory, 
            # tapi flush setiap item agar id ter-generate
            session.flush()
            
            if (berhasil + 1) % 50 == 0:
                session.commit()
                print(f"   🔹 Progress: {berhasil + 1} produk tersimpan...")
            
            berhasil += 1

        except Exception as e:
            session.rollback()
            print(f"❌ Gagal import [Index {i}] {p.get('product_name')}: {e}")
            # print(traceback.format_exc()) # Uncomment jika butuh detail stacktrace
            gagal += 1

    session.commit()
    session.close()

    print("\n" + "=" * 50)
    print(f"✅ HASIL IMPORT:")
    print(f"   Berhasil : {berhasil}")
    print(f"   Dilewati : {lewati} (Sudah ada/Tanpa Slug)")
    print(f"   Gagal    : {gagal}")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    run_migration()