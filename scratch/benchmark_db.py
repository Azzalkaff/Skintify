import time
import os
import sys

# Tambahkan path project agar bisa import modul
sys.path.append(os.getcwd())

from app.database.data_manager import DataManager
from app.database.engine import init_db

def benchmark_search():
    init_db()
    dm = DataManager()
    
    print("Mulai Benchmark...")
    
    # 1. Tanpa filter
    start = time.time()
    res = dm.get_paginated_products(page=1, items_per_page=12)
    end = time.time()
    print(f"Tanpa filter: {end - start:.4f}s (Total: {res['total_items']})")
    
    # 2. Filter Keyword
    start = time.time()
    res = dm.get_paginated_products(page=1, items_per_page=12, keyword="serum")
    end = time.time()
    print(f"Filter Keyword 'serum': {end - start:.4f}s (Total: {res['total_items']})")
    
    # 3. Filter Marketplace Only
    start = time.time()
    res = dm.get_paginated_products(page=1, items_per_page=12, marketplace_only=True)
    end = time.time()
    print(f"Filter Marketplace Only: {end - start:.4f}s (Total: {res['total_items']})")

    # 4. Filter Kategori + Harga
    start = time.time()
    res = dm.get_paginated_products(page=1, items_per_page=12, category_filter="Serum", min_price=50000, max_price=150000)
    end = time.time()
    print(f"Filter Serum + Harga: {end - start:.4f}s (Total: {res['total_items']})")

if __name__ == "__main__":
    benchmark_search()
