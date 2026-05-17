import os
import sys

# Fix Pathing
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.data_manager import DataManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi, Produk

dm = DataManager()
res = dm.get_paginated_products(page=1, items_per_page=12)
print("Total Items Found:", res.get("total_items"))
print("Items count returned:", len(res.get("items")))
if res.get("items"):
    print("First Item Sample:", res.get("items")[0])
else:
    print("No items returned!")

with SessionLocal() as session:
    total_db = session.query(SociollaReferensi).count()
    print("Total in DB (SociollaReferensi):", total_db)
    
    total_mkt = session.query(Produk).count()
    print("Total in DB (Produk - Marketplace):", total_mkt)
