
import sqlite3
import os

root_db = "tokopedia.db"
primary_db = "data/db/tokopedia.db"

if not os.path.exists(root_db):
    print("Root database not found. Skipping merge.")
    exit()

if not os.path.exists(primary_db):
    print("Primary database not found. Please run setup first.")
    exit()

print(f"Merging {root_db} into {primary_db}...")

conn_primary = sqlite3.connect(primary_db)
conn_root = sqlite3.connect(root_db)

# Attach root DB to primary connection
conn_primary.execute(f"ATTACH DATABASE '{root_db}' AS root_db")

# Move Toko (ignore duplicates)
conn_primary.execute("""
    INSERT OR IGNORE INTO toko (platform, shop_id, nama, kota, tier, is_official, url, dibuat_pada)
    SELECT platform, shop_id, nama, kota, tier, is_official, url, dibuat_pada FROM root_db.toko
""")

# Move Produk (ignore duplicates)
# Note: This won't fix missing referensi_id yet, but moves the records
conn_primary.execute("""
    INSERT OR IGNORE INTO produk (platform, product_id, keyword, nama, url, gambar, harga, harga_teks, harga_asli, diskon_persen, rating, jumlah_review, terjual, kategori, label_badge, free_ongkir, in_stock, is_sponsored, dibuat_pada, referensi_id, toko_id)
    SELECT platform, product_id, keyword, nama, url, gambar, harga, harga_teks, harga_asli, diskon_persen, rating, jumlah_review, terjual, kategori, label_badge, free_ongkir, in_stock, is_sponsored, dibuat_pada, referensi_id, toko_id FROM root_db.produk
""")

conn_primary.commit()
print("Merge complete.")

# Close and cleanup
conn_primary.close()
conn_root.close()

# Rename old db for safety
os.rename(root_db, root_db + ".bak")
print(f"Old database renamed to {root_db}.bak")
