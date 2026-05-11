"""
Debug script — jalankan ini untuk melihat response mentah dari Tokopedia.
Jalankan: python debug.py
"""
import json
from scraper import cari_produk

print("Mengirim request ke Tokopedia...")
print("-" * 50)

try:
    raw = cari_produk("g2g moisturizer", rows=8)

    print("✅ Request berhasil dikirim")
    print(f"Tipe response  : {type(raw)}")
    print(f"Panjang array  : {len(raw) if isinstance(raw, list) else 'bukan list'}")
    print()
    print("=== ISI RESPONSE (pretty print) ===")
    print(json.dumps(raw, indent=2, ensure_ascii=False)[:3000])
    print()
    print("(output dipotong di 3000 karakter pertama)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()