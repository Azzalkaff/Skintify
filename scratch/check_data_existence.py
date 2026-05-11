
import os
import sys

# Add root dir to sys.path
root_dir = os.path.abspath(os.path.join(os.getcwd()))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import SessionLocal, init_db
from app.database.models import SociollaReferensi, Produk, Toko

def check_data():
    with SessionLocal() as session:
        # Check products in SociollaReferensi
        products_to_check = [
            ("Cathy Doll", "Ultra Light Sun Fluid SPF50+ PA++++"),
            ("Carasun", "Duo Healthy Matte 70ml"),
            ("Erha", "Perfect Shield Active Light Sunscreen")
        ]
        
        print("=== Checking SociollaReferensi ===")
        for brand, name in products_to_check:
            res = session.query(SociollaReferensi).filter(
                SociollaReferensi.brand.ilike(f"%{brand}%"),
                SociollaReferensi.product_name.ilike(f"%{name}%")
            ).first()
            if res:
                print(f"Found: {res.brand} - {res.product_name}")
                print(f"  Price: {res.min_price}")
                print(f"  Rating: {res.rating_sociolla}")
                print(f"  Scraped: {res.sudah_di_scrape}")
                
                # Check for marketplace data
                print(f"  --- Marketplace Data ---")
                kw = res.keyword_digunakan or f"{res.brand} {res.product_name}"
                market_products = session.query(Produk).filter(Produk.keyword == kw).all()
                if market_products:
                    print(f"  Found {len(market_products)} marketplace products for keyword '{kw}'")
                    for mp in market_products:
                        print(f"    [{mp.platform}] {mp.nama} - Rp{mp.harga}")
                else:
                    print(f"  No marketplace data found for keyword '{kw}'")
            else:
                print(f"Not found: {brand} - {name}")
            print("-" * 20)

if __name__ == "__main__":
    check_data()
