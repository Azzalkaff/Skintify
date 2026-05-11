import time
import os
import sys

# Tambahkan path project agar bisa import modul
sys.path.append(os.getcwd())

from app.database.data_manager import DataManager
from app.database.engine import init_db

def benchmark_analysis():
    init_db()
    dm = DataManager()
    
    # Mock routine dengan 5 produk
    mock_routine = [
        {"ingredients": "Water, Glycerin, Niacinamide, Retinol"},
        {"ingredients": "Water, Salicylic Acid, Glycolic Acid"},
        {"ingredients": "Water, Ascorbic Acid, Tocopherol"},
        {"ingredients": "Water, Ceramide NP, Squalane"},
        {"ingredients": "Water, Zinc Oxide, Ethylhexyl Methoxycinnamate"}
    ]
    
    print("Mulai Benchmark Analisis...")
    
    start = time.time()
    for _ in range(10): # simulasi beberapa kali call
        res = dm.analyze_routine(mock_routine, kota="Jakarta")
    end = time.time()
    
    print(f"Rata-rata Analisis Rutin: {(end - start)/10:.4f}s")

if __name__ == "__main__":
    benchmark_analysis()
