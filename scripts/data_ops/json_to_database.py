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

# File JSON sumber (Hasil gabungan dari sociolla_scraper.py)
JSON_FILE = os.path.join(root_dir, "data", "products_sociolla_ALL.json")

def normalize_category(raw_cat: str) -> str:
    """Konversi kategori berantakan dari Sociolla ke kategori bersih UI."""
    if not raw_cat:
        return "Lainnya"
    
    cat = str(raw_cat).lower()
    
    # 1. Cek custom categories dari data/categories_to_scrape.json secara dinamis!
    categories_file = os.path.join(root_dir, "data", "categories_to_scrape.json")
    if os.path.exists(categories_file):
        try:
            with open(categories_file, "r", encoding="utf-8") as f:
                custom_cats = json.load(f)
                # Cek case-insensitive exact or substring match
                for cc in custom_cats:
                    cc_name = cc["name"]
                    if cc_name.lower() in cat or cat in cc_name.lower():
                        return cc_name
        except Exception:
            pass
            
    # 2. Fallback to hardcoded mapping rules
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
    
    # Makeup Mapping Rules
    if "cushion" in cat:
        return "Cushion"
    if "blush" in cat:
        return "Blush"
    if "powder" in cat:
        return "Powder"
    if "eye" in cat or "eyeliner" in cat or "mascara" in cat or "eyebrow" in cat:
        return "Eye Product"
    if "lip" in cat or "lipstick" in cat or "lip tint" in cat or "lip balm" in cat:
        return "LIP Product"
        
    return "Lainnya"


def run_migration():
    print("\n" + "=" * 50)
    print("[START] RE-IMPORTING SOCIOLLA DATA (ROBUST MODE)")
    print("=" * 50)

    Base.metadata.create_all(bind=engine)
    
    if not os.path.exists(JSON_FILE):
        print(f"[ERROR] File {JSON_FILE} tidak ditemukan!")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Handle both list and dict with "products" key
        if isinstance(data, list):
            products = data
        else:
            products = data.get("products", [])

    if not products:
        print("[WARNING] File JSON kosong.")
        return

    print(f"[INFO] Total produk di JSON: {len(products)}")
    
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

            # Mapping dengan proteksi nilai None
            brand_val = p.get("brand", "Unknown Brand")
            name_val = p.get("product_name", "Unknown Product")

            # Cek duplikat berdasarkan slug ATAU (brand, product_name)
            exists = session.query(SociollaReferensi).filter(
                (SociollaReferensi.slug == slug) |
                ((SociollaReferensi.brand == brand_val) & (SociollaReferensi.product_name == name_val))
            ).first()
            if exists:
                # UPDATE existing product with new enriched data
                exists.product_name = name_val
                exists.brand = brand_val
                exists.brand_country = p.get("brand_country") or exists.brand_country
                exists.brand_region = p.get("brand_region") or exists.brand_region
                exists.keyword_digunakan = f"{brand_val} {name_val}".strip()
                exists.category = normalize_category(p.get("category_source") or p.get("category")) or exists.category
                exists.all_categories = p.get("all_categories", []) or exists.all_categories
                
                exists.min_price = float(p.get("min_price") or 0)
                exists.max_price = float(p.get("max_price") or 0)
                exists.min_price_after_discount = float(p.get("min_price_after_discount") or 0)
                exists.max_price_after_discount = float(p.get("max_price_after_discount") or 0)
                
                exists.rating_sociolla = float(p.get("average_rating") or 0)
                exists.total_reviews = int(p.get("total_reviews") or 0)
                exists.total_recommended = int(p.get("total_recommended") or 0)
                exists.repurchase_yes = int(p.get("repurchase_yes") or 0)
                exists.repurchase_no = int(p.get("repurchase_no") or 0)
                exists.repurchase_maybe = int(p.get("repurchase_maybe") or 0)
                exists.total_wishlist = int(p.get("total_wishlist") or 0)
                
                exists.bpom_reg_no = p.get("bpom_reg_no") or exists.bpom_reg_no
                exists.url_sociolla = p.get("url") or exists.url_sociolla
                exists.image_url = p.get("image_url") or exists.image_url
                exists.is_in_stock = bool(p.get("is_in_stock", True))
                exists.is_flashsale = bool(p.get("is_flashsale", False))
                
                exists.description_raw = p.get("description_raw", "") or exists.description_raw
                exists.how_to_use_raw = p.get("how_to_use_raw", "") or exists.how_to_use_raw
                exists.ingredients = p.get("ingredients", "") or exists.ingredients
                
                exists.variants = p.get("variants", [])
                exists.reviews = p.get("reviews", [])
                
                berhasil += 1
                if berhasil % 50 == 0:
                    session.commit()
                    print(f"   * Progress: {berhasil} produk diupdate...")
                continue

            db_product = SociollaReferensi(
                slug=slug,
                product_name=name_val,
                brand=brand_val,
                brand_country=p.get("brand_country"),
                brand_region=p.get("brand_region"),
                keyword_digunakan=f"{brand_val} {name_val}".strip(),
                category=normalize_category(p.get("category_source") or p.get("category")),
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
            session.flush()
            
            berhasil += 1
            if berhasil % 50 == 0:
                session.commit()
                print(f"   * Progress: {berhasil} produk disimpan...")

        except Exception as e:
            session.rollback()
            print(f"[ERROR] Gagal import [Index {i}] {p.get('product_name')}: {e}")
            gagal += 1

    session.commit()
    session.close()

    print("\n" + "=" * 50)
    print(f"[SUCCESS] HASIL IMPORT & UPDATE:")
    print(f"   Berhasil : {berhasil}")
    print(f"   Dilewati : {lewati} (Tanpa Slug)")
    print(f"   Gagal    : {gagal}")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    run_migration()