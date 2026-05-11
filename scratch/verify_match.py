import sqlite3
import os

db_path = r"c:\Pemrograman\Kuliah\PPLD\Pra ETS\Proyek Punya Kelompok\main program\Skintify-C4\Skintify-C4\data\db\tokopedia.db"

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("SELECT brand, product_name, keyword_digunakan FROM sociolla_referensi WHERE keyword_digunakan LIKE ?", ('%Emina Ms Pimple%',))
ref = c.fetchone()
print(f"Ref: {ref}")

if ref:
    kw = ref[2]
    c.execute("SELECT platform, COUNT(*) FROM produk WHERE keyword = ? GROUP BY platform", (kw,))
    prods = c.fetchall()
    print(f"Products for '{kw}': {prods}")

conn.close()
