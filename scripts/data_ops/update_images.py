"""
update_images.py — Populate kolom image_url, slug, dan ingredients
dari file JSON ke database yang sudah ada.

Strategi: match berdasarkan (brand + product_name) atau slug.
Jalankan: python scripts/update_images.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv
load_dotenv(override=True)

from app.database.engine import engine, SessionLocal
from app.database.models import SociollaReferensi
from sqlalchemy import text

print("=" * 60)
print(" [UPDATE] Sinkronisasi image_url dari JSON ke Database")
print("=" * 60)

# 1. Load JSON
json_file = os.path.join(os.path.dirname(__file__), "..", "..", "data", "products_sociolla.json")
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

products_json = data.get("products", [])
print(f"\n[JSON] {len(products_json)} produk ditemukan di JSON")

# 2. Buat lookup map dari JSON: brand+name -> product dict
lookup_by_slug = {}
lookup_by_brand_name = {}

for p in products_json:
    slug = p.get("slug", "")
    brand = (p.get("brand", "") or "").strip().lower()
    name = (p.get("product_name", "") or "").strip().lower()
    
    if slug:
        lookup_by_slug[slug] = p
    if brand and name:
        lookup_by_brand_name[f"{brand}||{name}"] = p

print(f"[INDEX] Slug lookup: {len(lookup_by_slug)} | Brand+Name lookup: {len(lookup_by_brand_name)}")

# 3. Update DB
updated = 0
skipped = 0
not_found = 0

with SessionLocal() as session:
    all_db = session.query(SociollaReferensi).all()
    print(f"[DB] {len(all_db)} produk di database akan diproses...\n")
    
    for db_product in all_db:
        # Cari match di JSON
        json_match = None
        
        # Coba match by slug dulu
        if db_product.slug and db_product.slug in lookup_by_slug:
            json_match = lookup_by_slug[db_product.slug]
        
        # Kalau tidak ketemu, coba by brand+name
        if not json_match:
            brand_key = (db_product.brand or "").strip().lower()
            name_key = (db_product.product_name or "").strip().lower()
            key = f"{brand_key}||{name_key}"
            if key in lookup_by_brand_name:
                json_match = lookup_by_brand_name[key]
        
        if not json_match:
            not_found += 1
            continue
        
        # Update field-field yang kosong
        changed = False
        
        new_image = json_match.get("image_url", "")
        new_slug   = json_match.get("slug", "")
        new_url    = json_match.get("url", "")
        new_ingr   = json_match.get("ingredients", "")
        new_desc   = json_match.get("description_raw", "")
        new_how    = json_match.get("how_to_use_raw", "")
        new_brand_country = json_match.get("brand_country", "")
        new_brand_region  = json_match.get("brand_region", "")
        new_bpom   = json_match.get("bpom_reg_no", "")
        new_min_after = json_match.get("min_price_after_discount")
        new_max_after = json_match.get("max_price_after_discount")
        new_total_rec = json_match.get("total_recommended", 0)
        new_rep_yes   = json_match.get("repurchase_yes", 0)
        new_rep_no    = json_match.get("repurchase_no", 0)
        new_rep_maybe = json_match.get("repurchase_maybe", 0)
        new_wishlist  = json_match.get("total_wishlist", 0)
        new_variants  = json_match.get("variants", [])
        
        if new_image and not db_product.image_url:
            db_product.image_url = new_image
            changed = True
        if new_slug and not db_product.slug:
            db_product.slug = new_slug
            changed = True
        if new_url and not db_product.url_sociolla:
            db_product.url_sociolla = new_url
            changed = True
        if new_ingr and not db_product.ingredients:
            db_product.ingredients = new_ingr
            changed = True
        if new_desc and not db_product.description_raw:
            db_product.description_raw = new_desc
            changed = True
        if new_how and not db_product.how_to_use_raw:
            db_product.how_to_use_raw = new_how
            changed = True
        if new_brand_country and not db_product.brand_country:
            db_product.brand_country = new_brand_country
            changed = True
        if new_brand_region and not db_product.brand_region:
            db_product.brand_region = new_brand_region
            changed = True
        if new_bpom and not db_product.bpom_reg_no:
            db_product.bpom_reg_no = new_bpom
            changed = True
        if new_min_after is not None and not db_product.min_price_after_discount:
            db_product.min_price_after_discount = new_min_after
            changed = True
        if new_max_after is not None and not db_product.max_price_after_discount:
            db_product.max_price_after_discount = new_max_after
            changed = True
        if new_total_rec and not db_product.total_recommended:
            db_product.total_recommended = new_total_rec
            changed = True
        if new_rep_yes and not db_product.repurchase_yes:
            db_product.repurchase_yes = new_rep_yes
            changed = True
        if new_rep_no and not db_product.repurchase_no:
            db_product.repurchase_no = new_rep_no
            changed = True
        if new_rep_maybe and not db_product.repurchase_maybe:
            db_product.repurchase_maybe = new_rep_maybe
            changed = True
        if new_wishlist and not db_product.total_wishlist:
            db_product.total_wishlist = new_wishlist
            changed = True
        if new_variants and not db_product.variants:
            db_product.variants = new_variants
            changed = True
        
        if changed:
            updated += 1
        else:
            skipped += 1
    
    session.commit()
    print(f"[DONE] Diupdate: {updated} produk")
    print(f"[SKIP] Sudah lengkap: {skipped} produk")
    print(f"[MISS] Tidak cocok di JSON: {not_found} produk")

# Verifikasi
with SessionLocal() as session:
    has_img = session.query(SociollaReferensi).filter(
        SociollaReferensi.image_url.isnot(None),
        SociollaReferensi.image_url != ""
    ).count()
    total = session.query(SociollaReferensi).count()
    print(f"\n[RESULT] Produk dengan image_url: {has_img}/{total}")

print("=" * 60)
