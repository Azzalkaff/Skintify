
import os
import sys
from pathlib import Path

# Add project root to path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import SessionLocal
from app.database.models import Produk, SociollaReferensi

def fix_links():
    print("Checking database links...")
    with SessionLocal() as session:
        # Find all products with missing referensi_id
        unlinked = session.query(Produk).filter(Produk.referensi_id == None).all()
        print(f"Found {len(unlinked)} unlinked marketplace products.")
        
        if not unlinked:
            return

        linked_count = 0
        for p in unlinked:
            # Try to find a matching reference by keyword
            # Keyword in Produk table should match SociollaReferensi.keyword_digunakan
            ref = session.query(SociollaReferensi).filter_by(keyword_digunakan=p.keyword).first()
            
            if not ref:
                # Try partial match or brand + product name
                # (Optional logic here)
                pass
                
            if ref:
                p.referensi_id = ref.id
                ref.sudah_di_scrape = True
                linked_count += 1
        
        session.commit()
        print(f"Successfully linked {linked_count} products to their references.")

if __name__ == "__main__":
    fix_links()
