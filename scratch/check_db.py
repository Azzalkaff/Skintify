import sqlite3
import os

db_path = r"c:\Pemrograman\Kuliah\PPLD\Pra ETS\Proyek Punya Kelompok\main program\Skintify-C4\Skintify-C4\data\db\tokopedia.db"

if not os.path.exists(db_path):
    print(f"File not found: {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Table Counts ---")
    for table in ["toko", "produk", "hasil_pencarian", "sociolla_referensi"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{table}: {count}")
        except Exception as e:
            print(f"{table}: Error {e}")
            
    print("\n--- Platform Counts (Produk) ---")
    try:
        cursor.execute("SELECT platform, COUNT(*) FROM produk GROUP BY platform")
        for row in cursor.fetchall():
            print(f"{row[0]}: {row[1]}")
    except Exception as e:
        print(f"Error platform counts: {e}")
        
    conn.close()
