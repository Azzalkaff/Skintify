# 🎯 System Prompt: Integrasi Shopee Scraper ke Skintify-C4
> **Panduan Salin-Tempel (Copy-Paste) untuk Claude Chatbot — Edisi Sempurna (Bebas Bug)**

Dokumen ini berisi **System Prompt** super spesifik dan kaya konteks yang dapat langsung Anda salin dan tempelkan ke **Claude Chatbot** agar Claude menghasilkan kode modul **Shopee Scraper** yang 100% kompatibel dengan arsitektur **Skintify-C4**.

---

## 📋 Petunjuk Penggunaan:
1. Salin seluruh isi teks di bawah garis batas.
2. Tempelkan ke jendela obrolan Claude.
3. Claude akan menghasilkan kode yang rapi, modular, bebas bug pembagian harga Shopee, dan siap pasang!

---

### ✂️ MULAI SALIN DARI SINI ✂️

```text
Halo Claude, saya sedang mengembangkan aplikasi desktop/web skincare bernama "Skintify-C4" berbasis Python 3.12, NiceGUI (Vue/Quasar), dan SQLite (SQLAlchemy ORM). 

Saya ingin Anda membuatkan modul "Shopee Scraper" yang tangguh, modular, dan terintegrasi penuh ke dalam sistem pengikatan data (data binding) dan ORM kami. Modul ini bertugas merayapi produk skincare di platform Shopee Indonesia dan menyelaraskannya dengan data referensi kami (anti-mismatch).

Agar Anda memiliki pemahaman 100% tentang ekosistem kode kami, berikut adalah spesifikasi teknis dan potongan kode yang ada di proyek saat ini:

---

### 1. KELAS UTAMA SCRAPER (`app/scraping/core/base.py`)
Scraper baru harus mewarisi kelas abstrak BaseScraper berikut:

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Tuple
import random
import time

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name
        self.results_dir = Path("data/raw")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def scrape(self, keyword: str, top_n: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Melakukan scraping dan mengembalikan tuple (products, shops)."""
        pass

    def save_to_json(self, data: Dict[str, Any], filename: str):
        filepath = self.results_dir / f"{filename}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def random_sleep(self, min_s: float = 2.0, max_s: float = 4.0):
        time.sleep(random.uniform(min_s, max_s))

---

### 2. STRUKTUR HASIL KELUARAN & FORMULA FORMAT SHOPEE (EXPECTED OUTPUT FORMAT)
Fungsi `scrape()` dari ShopeeScraper harus mengembalikan Tuple berisi `(filtered_products, shops[:top_n])`.

#### ⚠️ JEBAKAN UTAMA SHOPEE API (WAJIB DIPATUHI):
1. **Pecahan Harga (Price Unit Gotcha)**:
   API Shopee mengirimkan data harga yang dikalikan dengan 100.000. Contohnya, Rp29.000 dikirim sebagai `2900000000`. Anda WAJIB membaginya dengan `100000.0` (misal: `price = float(raw_price) / 100000.0`) agar tidak merusak database Skintify!
2. **Konstruksi URL Detail Produk**:
   URL detail produk shopee harus dibentuk menggunakan format:
   `url = f"https://shopee.co.id/product-i.{shop_id}.{item_id}"`
3. **Konstruksi URL Gambar**:
   Gunakan alamat CDN gambar Shopee resmi berikut untuk merender gambar secara valid di UI:
   `image_url = f"https://down-id.img.susercontent.com/file/{image_hash}"`

#### A. Rincian Kunci `filtered_products` (List[Dict[str, Any]]):
- `source`: "shopee"
- `product_id`: str (ID produk unik shopee)
- `name`: str (nama produk)
- `url`: str (URL detail produk lengkap memakai formula di atas)
- `image`: str (URL gambar produk lengkap memakai CDN di atas)
- `price`: float (harga setelah diskon/harga live riil yang sudah dibagi 100.000)
- `price_original`: float (harga coret/original yang sudah dibagi 100.000. Jika tidak ada diskon, samakan dengan harga live)
- `discount`: int (persentase diskon, contoh: 15)
- `rating`: float (skala 0.0 - 5.0)
- `sold`: int (angka riil penjualan historis produk)
- `shop_id`: str (ID toko shopee)

#### B. Rincian Kunci `shops` (List[Dict[str, Any]]):
- `shop_id`: str (ID toko shopee)
- `name`: str (nama toko)
- `city`: str (lokasi kota toko)
- `tier`: int atau None
- `is_official`: bool (True jika Star Seller, Star+, atau Shopee Mall)

---

### 3. CONTOH JSON RESPONSE API PENCARIAN SHOPEE
Gunakan endpoint pencarian API Shopee V4 berikut:
`https://shopee.co.id/api/v4/search/search_items?by=relevancy&keyword={keyword}&limit=40&newest=0&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2`

Struktur JSON response yang akan Anda parse berbentuk seperti ini:
{
  "items": [
    {
      "item_basic": {
        "itemid": 12345678,
        "shopid": 9876543,
        "name": "Emina Bright Stuff Moisturizing Cream",
        "image": "id-11134210-7rasa-m1n3",
        "price": 2350000000, 
        "price_before_discount": 2700000000,
        "raw_discount": 13,
        "historical_sold": 4500,
        "item_rating": {
          "rating_star": 4.85
        },
        "is_official_shop": true,
        "shopee_verified": true
      }
    }
  ]
}

*Catatan: Gunakan kunci `is_official_shop` atau `shopee_verified` untuk menentukan nilai `is_official` toko.*

---

### 4. STRUKTUR INTEGRASI BASIS DATA (`app/database/engine.py`)
Data hasil scraping akan divalidasi kemiripannya dengan fungsi `hitung_kemiripan()` dan disimpan via `simpan_hasil()`. Berikut adalah kode riil dari dua fungsi normalisasi internal di `app/database/engine.py` saat ini yang melayani Tokopedia & Lazada. Saya butuh Anda menuliskan kode pembaruan/modifikasi persis untuk menyisipkan cabang `"shopee"` ke dalamnya:

```python
def _normalize_toko(platform: str, raw: dict) -> dict:
    """
    Konversi dict toko dari scraper (Tokopedia/Lazada) ke format unified.

    Tokopedia keys : shop_id, nama, kota, tier, url
    Lazada keys    : seller_id, nama, kota, is_lazmall
    """
    if platform == "tokopedia":
        return {
            "platform":    "tokopedia",
            "shop_id":     raw.get("shop_id", ""),
            "nama":        raw.get("nama") if raw.get("nama") else raw.get("name", ""),
            "kota":        raw.get("kota", ""),
            "tier":        raw.get("tier", 0),
            "is_official": raw.get("tier", 0) >= 1,   # 1=official, 2=power merchant
            "url":         raw.get("url", ""),
        }
    elif platform == "lazada":
        return {
            "platform":    "lazada",
            "shop_id":     raw.get("shop_id") if raw.get("shop_id") else raw.get("seller_id", ""),
            "nama":        raw.get("nama") if raw.get("nama") else raw.get("name", ""),
            "kota":        raw.get("kota", ""),
            "tier":        None,
            "is_official": raw.get("is_lazmall") if raw.get("is_lazmall") is not None else raw.get("is_official", False),
            "url":         raw.get("url", ""),
        }
    else:
        raise ValueError(f"Platform tidak dikenal: {platform}")


def _normalize_produk(platform: str, raw: dict) -> dict:
    """
    Konversi dict produk dari scraper (Tokopedia/Lazada) ke format unified.

    Tokopedia keys : product_id, shop_id, nama, url, gambar, harga, harga_teks,
                     harga_asli, diskon_persen, rating, kategori, label_badge, free_ongkir
    Lazada keys    : item_id, seller_id, nama, url, gambar, harga, harga_teks,
                     harga_asli, diskon_persen, rating, jumlah_review, terjual,
                     in_stock, is_sponsored
    """
    # Common field aliases for robustness
    p_id = raw.get("product_id") or raw.get("item_id")
    s_id = raw.get("shop_id") or raw.get("seller_id")
    name = raw.get("nama") or raw.get("name", "")
    img  = raw.get("gambar") or raw.get("image", "")
    kw   = raw.get("keyword", "")

    if platform == "tokopedia":
        return {
            "platform":      "tokopedia",
            "product_id":    p_id,
            "shop_id":       s_id,
            "keyword":       kw,
            "nama":          name,
            "url":           raw.get("url", ""),
            "gambar":        img,
            "harga":         raw.get("harga") if raw.get("harga") else raw.get("price", 0.0),
            "harga_teks":    raw.get("harga_teks", ""),
            "harga_asli":    raw.get("harga_asli") if raw.get("harga_asli") else raw.get("price_original", 0.0),
            "diskon_persen": raw.get("diskon_persen") if raw.get("diskon_persen") else raw.get("discount", 0),
            "rating":        raw.get("rating", 0.0),
            "jumlah_review": raw.get("jumlah_review") if raw.get("jumlah_review") else raw.get("reviews", 0),
            "terjual":       raw.get("terjual") if raw.get("terjual") else raw.get("sold", 0),
            "kategori":      raw.get("kategori", ""),
            "label_badge":   raw.get("label_badge", ""),
            "free_ongkir":   raw.get("free_ongkir", 0),
            "in_stock":      None,
            "is_sponsored":  None,
        }
    elif platform == "lazada":
        return {
            "platform":      "lazada",
            "product_id":    p_id,
            "shop_id":       s_id,
            "keyword":       kw,
            "nama":          name,
            "url":           raw.get("url", ""),
            "gambar":        img,
            "harga":         raw.get("harga") if raw.get("harga") else raw.get("price", 0.0),
            "harga_teks":    raw.get("harga_teks", ""),
            "harga_asli":    raw.get("harga_asli") if raw.get("harga_asli") else raw.get("price_original", 0.0),
            "diskon_persen": raw.get("diskon_persen") if raw.get("diskon_persen") else raw.get("discount", 0),
            "rating":        raw.get("rating", 0.0),
            "jumlah_review": raw.get("jumlah_review") if raw.get("jumlah_review") else raw.get("reviews", 0),
            "terjual":       raw.get("terjual") if raw.get("terjual") else raw.get("sold", 0),
            "kategori":      None,
            "label_badge":   None,
            "free_ongkir":   None,
            "in_stock":      raw.get("in_stock", True),
            "is_sponsored":  raw.get("is_sponsored", False),
        }
    else:
        raise ValueError(f"Platform tidak dikenal: {platform}")
```

---

### 5. INTEGRASI DENGAN `app/scraping/scraper_manager.py`
Berikut adalah struktur `ScraperManager` saat ini. Tunjukkan dengan presisi bagaimana meregistrasikan `ShopeeScraper` di sini:

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from .core.tokopedia import TokopediaScraper
from .core.lazada import LazadaScraper
from .core.config import OUTPUT_DIR, SLEEP_RANGE

class ScraperManager:
    def __init__(self):
        self.scrapers = [TokopediaScraper(), LazadaScraper()]
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_batch(self, keywords: List[str], top_n: int = 5):
        # Alur batch run...

---

### TUGAS ANDA:
Berdasarkan konteks di atas, tolong buatkan:

1. **`app/scraping/core/shopee.py`**:
   - Tulis kode lengkap untuk kelas `ShopeeScraper` yang mewarisi `BaseScraper`.
   - Implementasikan fungsi `_fetch` menggunakan pustaka `requests` Python, lengkap dengan header penyamaran mobile browser terbaru.
   - Gunakan fungsi `get_shopee_headers()` dan `get_shopee_cookies()` yang diimpor dari `.config`.
   - Implementasikan fungsi `_parse` untuk mengekstrak data JSON response dari Shopee. Pastikan pembagian harga riil dan original dibagi `100000.0`. Tangani ekstraksi rating dan angka penjualan secara kokoh menggunakan `try-except` fallback.

2. **Pembaruan Konfigurasi `app/scraping/core/config.py`**:
   - Tambahkan konstanta `SHOPEE_ENDPOINT` dan helper fungsi pembuat header/cookie penyamaran Shopee agar terpusat.

3. **Modifikasi `app/database/engine.py`**:
   - Berikan kode perubahan persis (diff format atau penjelasan yang jelas) untuk menyisipkan cabang `elif platform == "shopee":` ke dalam fungsi `_normalize_toko` dan `_normalize_produk` agar ORM database dapat menyimpan hasil scrape Shopee tanpa melanggar batasan unik.

4. **Modifikasi `app/scraping/scraper_manager.py`**:
   - Tunjukkan cara mengimpor dan menambahkan `ShopeeScraper` ke dalam list `self.scrapers`.

Tulis kode Python yang elegan, bersih, penuh komentar (in Indonesian), dan aman dari kebocoran Exception. Terima kasih!
```

---

### ✂️ BATAS AKHIR SALIN ✂️
