"""
anggota1_scraper.py
SkinCompare ID — Modul Scraping Sociolla
Anggota 1

Fungsi utama:
  1. fetch_products_page()   — ambil 1 halaman produk dari API
  2. scrape_all_products()   — loop semua halaman, return list lengkap
  3. parse_ingredients()     — ekstrak ingredients dari field description
  4. validate_json()         — validasi struktur data sebelum disimpan
  5. save_to_json()          — simpan hasil ke file JSON
  6. auto_refresh()          — jalankan ulang scraping jika data lama

Cara run:
  python anggota1_scraper.py
"""

import requests
import json
import re
import os
import time
import html
import asyncio
from datetime import datetime, timedelta

try:
    from sociolla_enricher import enrich_all_products_async
    ASYNC_ENRICH_AVAILABLE = True
except ImportError:
    ASYNC_ENRICH_AVAILABLE = False
    print("[WARNING] sociolla_enricher.py tidak ditemukan — fallback ke enrichment sync")


# ─────────────────────────────────────────────
# KONFIGURASI
# ─────────────────────────────────────────────

# Endpoint ditemukan dari Network tab (tidak butuh login)
BASE_URL = "https://catalog-api.sociolla.com/v3/search"

# ID KATEGORI SKINCARE
CATEGORY_MOISTURIZER = "5e9955b673a74cf9570ce331"   # Moisturizer
CATEGORY_FACE_GEL    = "5e9955b673a74cf9570ce331"   # Face Gel
CATEGORY_TONER       = "5d3ac309a6992471b7c97f7f"   # Toner
CATEGORY_SUNSCREEN   = "5d3ac309a6992471b7c97f91"   # Sunscreen
CATEGORY_FACE_WASH   = "5e9938206d9c07e1021e1294"   # Face Wash
CATEGORY_FACE_TONER  = "5d3ac309a6992471b7c97f7d"   # Face Toner
CATEGORY_MICELLAR_WATER = "5e995498d3f996090509ba8d" # Micellar Water
CATEGORY_SERUM       = "5d3ac309a6992471b7c97f7d"   # Serum

#ID KATEGORI MAKE UP

CATEGORY_CUSHION     = "62cea8ee6e55507c2de6a13e"   # Cushion
CATEGORY_BLUSH      = "5d3ac309a6992471b7c97f6b"   # Blush
CATEGORY_POWDER     = "5d3ac309a6992471b7c97f6d"   # Powder
CATEGORY_EYE_PRODUCT = "5dbb1374ca096d5a008cefc8"   # Eye Product
CATEGORY_LIP_PRODUCT = "5eb9779ecb172d6891a43143"   # LIP Product

CATEGORIES_TO_SCRAPE = [
    #{"id": CATEGORY_MOISTURIZER, "name": "Moisturizer"},
    #{"id": CATEGORY_FACE_GEL,    "name": "Face Gel"},
    #{"id" : CATEGORY_TONER,      "name": "Toner"},
    #{"id" : CATEGORY_SUNSCREEN,   "name": "Sunscreen"},
    #{"id" : CATEGORY_FACE_WASH,   "name": "Face Wash"},
    #{"id" : CATEGORY_FACE_TONER,   "name": "Face Toner"},
    #{"id" : CATEGORY_MICELLAR_WATER,   "name": "Micellar Water"},
    #{"id" : CATEGORY_SERUM,        "name": "Serum"},
    {"id" : CATEGORY_CUSHION,      "name": "Cushion"},
    {"id" : CATEGORY_BLUSH,        "name": "Blush"},
    {"id" : CATEGORY_POWDER,       "name": "Powder"},
    {"id" : CATEGORY_EYE_PRODUCT,  "name": "Eye Product"},
    {"id" : CATEGORY_LIP_PRODUCT,  "name": "LIP Product"}


]

# Headers minimal yang dibutuhkan
HEADERS = {
    "Accept":       "application/json, text/plain, */*",
    "Origin":       "https://www.sociolla.com",
    "Referer":      "https://www.sociolla.com/",
    "Soc-Platform": "sociolla-web-mobile",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Path output
OUTPUT_DIR  = "data"
# Menghapus OUTPUT_FILE global karena akan dibuat dinamis

# Batas scraping
LIMIT_PER_PAGE     = 50
MAX_PRODUCTS       = 99999   # hilangkan cap; out-of-stock ada di halaman belakang
DELAY_SECONDS      = 1.5

# Konfigurasi review & checkpoint
MAX_REVIEW_RETRIES = 3
DEBUG_REVIEWS      = False
CHECKPOINT_FILE    = "data/checkpoint.json"
REVIEWS_PER_PRODUCT = 10   # dinaikkan dari 5


# ─────────────────────────────────────────────
# FUNGSI 1: fetch_products_page
# ─────────────────────────────────────────────

def fetch_products_page(category_id: str, skip: int = 0, limit: int = LIMIT_PER_PAGE) -> dict:
    """
    Ambil satu halaman produk dari Sociolla API.

    Args:
        category_id : ID kategori (string MongoDB ObjectId)
        skip        : offset produk (0 = halaman 1, 50 = halaman 2, dst)
        limit       : jumlah produk per halaman

    Returns:
        dict dengan key:
          "success" : bool
          "data"    : list produk
          "total"   : total produk di kategori (jika tersedia di response)
          "error"   : pesan error (jika gagal)
    """
    params = {
        "filter": json.dumps({"categories.id": category_id}),
        "skip":   skip,
        "limit":  limit,
        "sort":   "-review_stats.total_reviews",
        "fields": (
            "id _id my_sociolla_sql_id name brand slug default_category categories "
            "review_stats min_price max_price min_price_after_discount "
            "max_price_after_discount is_in_stock is_flashsale "
            "total_wishlist url_sociolla description how_to_use images "
            "combinations default_combination bpom_reg_no"
        ),
    }

    try:
        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        # Cek apakah response punya key "data" (struktur yang ditemukan)
        if "data" not in data:
            return {
                "success": False,
                "data": [],
                "total": 0,
                "error": f"Struktur response tidak terduga: {list(data.keys())}"
            }

        # Coba ambil total — field namanya belum pasti, cek beberapa kemungkinan
        total = (
            data.get("total") or
            data.get("count") or
            data.get("x-items-count") or
            len(data["data"])   # fallback: anggap ini adalah semua data
        )

        return {
            "success": True,
            "data":    data["data"],
            "total":   total,
            "error":   None
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        # 401 = butuh login, 403 = blocked, 429 = rate limit
        return {
            "success": False,
            "data":    [],
            "total":   0,
            "error":   f"HTTP {status}: {str(e)}"
        }
    except requests.exceptions.Timeout:
        return {"success": False, "data": [], "total": 0, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "data": [], "total": 0, "error": str(e)}
    except json.JSONDecodeError:
        return {"success": False, "data": [], "total": 0, "error": "Response bukan JSON valid"}


# ─────────────────────────────────────────────
# FUNGSI 2: scrape_all_products
# ─────────────────────────────────────────────

def scrape_all_products(category_id: str = CATEGORY_MOISTURIZER) -> list:
    """
    Loop semua halaman dan kumpulkan semua produk dalam satu list.

    Strategi paginasi: skip/limit (MongoDB style)
    Berhenti jika:
      - Halaman kosong (data = [])
      - Sudah melebihi MAX_PRODUCTS
      - 3 kali error berturut-turut

    Returns:
        list of dict — produk yang sudah dibersihkan dan siap disimpan
    """
    resume_skip, all_products = load_checkpoint(category_id)
    skip        = resume_skip
    error_count = 0
    total_known = None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mulai scraping Sociolla...")
    print(f"Kategori ID : {category_id}")
    print(f"Limit/page  : {LIMIT_PER_PAGE}")
    print("-" * 50)

    while True:
        # Safety cap
        if len(all_products) >= MAX_PRODUCTS:
            print(f"[STOP] Sudah mencapai batas MAX_PRODUCTS ({MAX_PRODUCTS})")
            break

        print(f"  Fetching skip={skip} ... ", end="", flush=True)
        result = fetch_products_page(category_id, skip=skip, limit=LIMIT_PER_PAGE)

        if not result["success"]:
            error_count += 1
            print(f"GAGAL — {result['error']} (error ke-{error_count})")
            if error_count >= 3:
                print("[STOP] 3 error berturut-turut, scraping dihentikan")
                break
            time.sleep(3)
            continue

        # Reset error counter kalau berhasil
        error_count = 0

        page_data = result["data"]

        # Simpan total produk dari response pertama
        if total_known is None and result["total"]:
            total_known = result["total"]
            print(f"\n  Total produk di kategori: {total_known}")

        # Halaman kosong = sudah habis
        if not page_data:
            print(f"KOSONG — scraping selesai")
            break

        # Bersihkan dan tambahkan ke list
        for raw in page_data:
            clean = _clean_product(raw)
            if clean:
                all_products.append(clean)

        print(f"OK — dapat {len(page_data)} produk (total: {len(all_products)})")

        # Simpan checkpoint setiap 100 produk
        if len(all_products) % 100 == 0 and len(all_products) > 0:
            save_checkpoint(category_id, skip, all_products)

        if len(page_data) < LIMIT_PER_PAGE:
            print("  [INFO] Halaman terakhir tercapai")
            break

        skip += LIMIT_PER_PAGE
        time.sleep(DELAY_SECONDS)

    clear_checkpoint()

    print("-" * 50)
    print(f"Scraping selesai: {len(all_products)} produk berhasil dikumpulkan")
    return all_products


# ─────────────────────────────────────────────
# FUNGSI 3: parse_ingredients
# ─────────────────────────────────────────────

def parse_ingredients(description_raw: str) -> str:
    """
    Ekstrak daftar ingredients dari field description Sociolla.

    Field description mengandung HTML entities dan HTML tags:
    "...Bahan Ingredients: Niacinamide, Panthenol...\u003C/p\u003E"

    Args:
        description_raw: string mentah dari API

    Returns:
        string bersih, contoh: "Niacinamide, Panthenol, Glycerin"
        atau "" jika tidak ditemukan
    """
    if not description_raw:
        return ""

    # Step 1: Decode HTML entities (\u003C → <, dll)
    decoded = html.unescape(description_raw)

    # Step 2: Hapus semua HTML tags
    no_tags = re.sub(r"<[^>]+>", " ", decoded)

    # Step 3: Cari section ingredients
    # Sociolla pakai berbagai label: "Ingredients:", "Bahan Ingredients:", "Komposisi:"
    patterns = [
        r"(?:Bahan\s+)?Ingredients?\s*:\s*(.+?)(?:\n|$|Cara\s+Penggunaan|How\s+to\s+Use)",
        r"Komposisi\s*:\s*(.+?)(?:\n|$)",
        r"INGREDIENTS?\s*:\s*(.+?)(?:\n|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, no_tags, re.IGNORECASE | re.DOTALL)
        if match:
            ingredients = match.group(1).strip()
            # Bersihkan spasi berlebih
            ingredients = re.sub(r"\s+", " ", ingredients)
            return ingredients

    return ""


# ─────────────────────────────────────────────
# FUNGSI TAMBAHAN: fetch_product_reviews
# ─────────────────────────────────────────────

def fetch_product_reviews(mysql_id: str, limit: int = 5) -> list:
    """
    Ekstrak ulasan produk dari endpoint review API Sociolla.
    Retry otomatis dengan exponential backoff untuk kasus rate-limit / timeout.
    Graceful degradation: jika semua retry habis, return list kosong.

    Args:
        mysql_id : ID numerik produk dari prefix slug ("25320-nama-produk" → "25320")
        limit    : jumlah ulasan yang diambil
    """
    if not mysql_id:
        return []

    url    = "https://soco-api.sociolla.com/reviews"
    params = {
        "filter":   json.dumps({"product_id": mysql_id, "is_published": True}),
        "limit":    limit,
        "sort":     "-created_at",
        "populate": "user",  # minta server embed full user object
    }

    if DEBUG_REVIEWS:
        import urllib.parse
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        print(f"\n    [DEBUG] GET {full_url}")

    for attempt in range(MAX_REVIEW_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)

            if DEBUG_REVIEWS:
                print(f"    [DEBUG] Status: {response.status_code}")
                print(f"    [DEBUG] Body  : {response.text[:300]}")

            # 429 = rate-limit: tunggu lebih lama lalu retry
            if response.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"    [RATE-LIMIT] Tunggu {wait}s sebelum retry ({attempt + 1}/{MAX_REVIEW_RETRIES})...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"    [-] Review HTTP {response.status_code} untuk mysql_id={mysql_id}")
                return []

            reviews = []
            for item in response.json().get("data", []):
                # Ambil sub-rating yang tersedia di response (beauty_profile tidak ada di endpoint ini)
                sub_ratings = {
                    "effectiveness":   item.get("star_effectiveness"),
                    "texture":         item.get("star_texture"),
                    "packaging":       item.get("star_packaging"),
                    "value_for_money": item.get("star_value_for_money"),
                }
                # Hanya sertakan sub-rating yang tidak null
                filled_sub_ratings = {k: v for k, v in sub_ratings.items() if v is not None}

                reviews.append({
                    "username":          item.get("name", "Anonim"),
                    "rating":            item.get("average_rating", 0),
                    "is_recommended":    item.get("is_recommended", ""),
                    "is_repurchase":     item.get("is_repurchase", ""),
                    "is_verified":       item.get("is_verified_purchase", False),
                    "sub_ratings":       filled_sub_ratings,
                    "comment":           item.get("detail", ""),
                })
            return reviews

        except requests.exceptions.Timeout:
            wait = 2 ** attempt
            print(f"    [TIMEOUT] mysql_id={mysql_id}, retry {attempt + 1}/{MAX_REVIEW_RETRIES} dalam {wait}s...")
            time.sleep(wait)

        except Exception as e:
            print(f"    [-] Gagal scrape ulasan mysql_id={mysql_id}: {e}")
            return []

    print(f"    [-] Semua {MAX_REVIEW_RETRIES} retry habis untuk mysql_id={mysql_id}")
    return []
# ─────────────────────────────────────────────
# FUNGSI 4: validate_json
# ─────────────────────────────────────────────

def validate_json(products: list) -> dict:
    """
    Validasi struktur data sebelum disimpan.

    Cek:
      - Minimal 50 produk (requirement modul)
      - Setiap produk punya minimal 4 kolom wajib
      - Tidak ada produk duplikat (by slug)
      - Tidak ada nilai None pada kolom wajib

    Args:
        products: list of dict hasil scraping

    Returns:
        dict {
          "valid": bool,
          "errors": list of string,
          "warnings": list of string,
          "stats": dict
        }
    """
    errors   = []
    warnings = []
    REQUIRED_COLUMNS = ["product_name", "brand", "category", "min_price"]

    # Cek jumlah minimum
    if len(products) < 50:
        errors.append(f"Jumlah produk {len(products)} < 50 (requirement minimum modul)")
    
    # Cek kolom wajib
    missing_col_count = 0
    for i, p in enumerate(products):
        for col in REQUIRED_COLUMNS:
            if col not in p or p[col] is None or p[col] == "":
                missing_col_count += 1
                if missing_col_count <= 5:  # hanya tampilkan 5 pertama
                    errors.append(f"Produk index {i} ({p.get('product_name','?')}): kolom '{col}' kosong")

    if missing_col_count > 5:
        errors.append(f"...dan {missing_col_count - 5} error kolom kosong lainnya")

    # Cek duplikat
    slugs = [p.get("slug") for p in products if p.get("slug")]
    unique_slugs = set(slugs)
    if len(slugs) != len(unique_slugs):
        dup_count = len(slugs) - len(unique_slugs)
        warnings.append(f"{dup_count} produk duplikat ditemukan (by slug)")

    # Cek produk tanpa harga
    no_price = [p["product_name"] for p in products if not p.get("min_price")]
    if no_price:
        warnings.append(f"{len(no_price)} produk tanpa harga: {no_price[:3]}...")

    # Cek keberadaan my_sociolla_sql_id (Akar masalah gagal ambil review)
    missing_sql_id = sum(1 for p in products if not p.get("my_sociolla_sql_id"))
    if missing_sql_id > 0:
        warnings.append(f"CRITICAL: {missing_sql_id} produk kehilangan 'my_sociolla_sql_id'. Enrichment review berpotensi salah target.")

    # Deteksi kegagalan total review scraping
    total_with_reviews = sum(1 for p in products if p.get("reviews"))
    if total_with_reviews == 0 and len(products) > 0:
        errors.append("CRITICAL: 0 dari semua produk memiliki data review — periksa fetch_product_reviews()")
    elif total_with_reviews < len(products) * 0.5:
        warnings.append(
            f"Hanya {total_with_reviews}/{len(products)} produk berhasil diambil reviewnya (<50%)"
        )

    # Validasi struktur field review baru (sub_ratings menggantikan skin_profile lama)
    malformed_reviews = 0
    for p in products:
        for r in p.get("reviews", []):
            if "skin_profile" in r:
                malformed_reviews += 1
                break
    if malformed_reviews > 0:
        warnings.append(
            f"{malformed_reviews} produk masih pakai struktur review lama (skin_profile) — jalankan ulang scraping"
        )

    # Statistik
    stats = {
        "total_products":    len(products),
        "unique_products":   len(unique_slugs),
        "with_ingredients":  sum(1 for p in products if p.get("ingredients")),
        "with_discount":     sum(1 for p in products if p.get("discount_range")),
        "with_reviews":      sum(1 for p in products if len(p.get("reviews", [])) > 0),
        "avg_rating":        round(
            sum(p.get("average_rating", 0) for p in products) / len(products), 2
        ) if products else 0,
    }

    return {
        "valid":    len(errors) == 0,
        "errors":   errors,
        "warnings": warnings,
        "stats":    stats
    }


# ─────────────────────────────────────────────
# FUNGSI 5: save_to_json
# ─────────────────────────────────────────────

def save_to_json(products: list, filepath: str, category_name: str) -> bool:
    """
    Simpan list produk ke file JSON.

    Args:
        products : list of dict
        filepath : path file output

    Returns:
        True jika berhasil, False jika gagal
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        output = {
            "metadata": {
                "source":       "Sociolla",
                "scraped_at":   datetime.now().isoformat(),
                "total":        len(products),
                "category":     category_name,
                "endpoint":     BASE_URL,
            },
            "products": products
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        size_kb = os.path.getsize(filepath) / 1024
        print(f"[SAVED] {filepath} ({len(products)} produk, {size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"[ERROR] Gagal menyimpan JSON: {e}")
        return False


# ─────────────────────────────────────────────
# FUNGSI 6: auto_refresh
# ─────────────────────────────────────────────

def auto_refresh(max_age_hours: int = 24, filepath: str = None, category_id: str = CATEGORY_MOISTURIZER) -> list:
    
    """
    Jalankan ulang scraping hanya jika data sudah lebih lama dari max_age_hours.
    Jika data masih baru, langsung load dari file lokal.

    Args:
        max_age_hours : batas usia data dalam jam
        filepath      : path file JSON lokal

    Returns:
        list of dict — produk (dari file atau hasil scraping baru)
    """
    # Cek apakah file sudah ada
    if os.path.exists(filepath):
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        age       = datetime.now() - file_time

        if age < timedelta(hours=max_age_hours):
            print(f"[CACHE] Data masih baru ({age.seconds // 3600}j {(age.seconds % 3600) // 60}m), load dari file lokal")
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("products", [])
        else:
            print(f"[REFRESH] Data sudah {age.days}h {age.seconds // 3600}j, scraping ulang...")

    # Scrape baru
    products = scrape_all_products(category_id=category_id)
    if products:
        validation = validate_json(products)
        if not validation["valid"]:
            print("[WARNING] Validasi gagal:")
            for err in validation["errors"]:
                print(f"  - {err}")
        save_to_json(products)

    return products


# ─────────────────────────────────────────────
# HELPER INTERNAL
# ─────────────────────────────────────────────

def _clean_product(raw: dict):
    """
    Transformasi satu objek produk mentah dari API ke format yang dibutuhkan.
    Return None jika data tidak valid (skip produk ini).
    """
    try:
        # Ambil nama brand dan asal negara (nested object)
        brand_obj = raw.get("brand") or {}
        brand_name = brand_obj.get("name", "") if isinstance(brand_obj, dict) else ""
        brand_country = brand_obj.get("country", "") if isinstance(brand_obj, dict) else ""
        brand_region = brand_obj.get("region", "") if isinstance(brand_obj, dict) else ""

        # Ambil kategori utama & jamak
        cat_obj   = raw.get("default_category") or {}
        cat_name  = cat_obj.get("name", "") if isinstance(cat_obj, dict) else ""
        cats_raw  = raw.get("categories") or []
        all_categories = [c.get("name") for c in cats_raw if isinstance(c, dict) and c.get("name")]

        # Ambil review stats dan metrik loyalitas
        review    = raw.get("review_stats") or {}

        # Ambil data teks mentah (raw text) untuk NLP
        desc_raw       = raw.get("description", "")
        how_to_use_raw = raw.get("how_to_use", "")
        ingredients    = parse_ingredients(desc_raw)

        # Skip produk tanpa nama
        product_name = raw.get("name", "").strip()
        if not product_name:
            return None
            
        slug = raw.get("slug", "")

        # Ingredients di-enrich async oleh sociolla_enricher.py
        # Di sini hanya ambil dari description; patch async dijalankan setelah scraping selesai

        # Ambil URL gambar pertama dari array 'images'
        images_data = raw.get("images") or []
        image_url = images_data[0].get("url", "") if len(images_data) > 0 else ""
# [FIX] Smart ID Extractor: Prioritaskan SQL ID, fallback ke prefix slug dengan validasi ketat
        raw_sql_id = str(raw.get("my_sociolla_sql_id") or "").strip()
        slug_prefix = str(raw.get("slug", "")).split("-")[0]
        
        if raw_sql_id.isdigit():
            mysql_id = raw_sql_id
        elif slug_prefix.isdigit():
            mysql_id = slug_prefix
        else:
            mysql_id = ""

        reviews_data = []
        # [FIX] Performa & Anti-Stuck: Matikan I/O Blocking Synchronous. 
        # Delegasikan tugas berat ini sepenuhnya ke sociolla_enricher.py (Async Paralel).
        if mysql_id and not ASYNC_ENRICH_AVAILABLE:
            reviews_data = fetch_product_reviews(mysql_id, limit=REVIEWS_PER_PRODUCT)
            time.sleep(0.5)

        variants = _extract_variants(raw.get("combinations") or [])
        bpom_reg_no = (
            raw.get("bpom_reg_no")
            or (raw.get("default_combination") or {}).get("bpom_reg_no", "")
            or ""
        )

        return {
            # 4 kolom wajib
            "product_name":              product_name,
            "my_sociolla_sql_id":        mysql_id, # [FIX] Preserve original DB ID sebagai Source of Truth untuk enricher
            "brand":                     brand_name,
            "category":                  cat_name,
            "min_price":                 raw.get("min_price"),

            # Brand Detail & Kategori Jamak
            "brand_country":             brand_country,
            "brand_region":              brand_region,
            "all_categories":            all_categories,

            # Harga (String dihilangkan)
            "max_price":                 raw.get("max_price"),
            "min_price_after_discount":  raw.get("min_price_after_discount"),
            "max_price_after_discount":  raw.get("max_price_after_discount"),

            # Rating, Review & Loyalty Metrics
            "average_rating":            round(review.get("average_rating", 0), 2),
            "total_reviews":             review.get("total_reviews", 0),
            "total_recommended":         review.get("total_recommended_count", 0),
            "repurchase_yes":            review.get("total_repurchase_yes_count", 0),
            "repurchase_no":             review.get("total_repurchase_no_count", 0),
            "repurchase_maybe":          review.get("total_repurchase_maybe_count", 0),

            # Metadata produk
            "slug":                      raw.get("slug", ""),
            "url":                       raw.get("url_sociolla", ""),
            "is_in_stock":               raw.get("is_in_stock", False),
            "is_flashsale":              raw.get("is_flashsale", False),
            "total_wishlist":            raw.get("total_wishlist", 0),
            "bpom_reg_no":               bpom_reg_no,
            "variants":                  variants,
            
            # Teks Mentah (Raw)
            "description_raw":           desc_raw,
            "how_to_use_raw":            how_to_use_raw,
            "ingredients":               ingredients, # Tetap simpan versi bersihnya
            
            "image_url":                 image_url,
            "reviews":                   reviews_data,
        }

    except Exception as e:
        print(f"  [SKIP] Error saat clean produk: {e}")
        return None


# ─────────────────────────────────────────────
# DEBUG HELPER
# ─────────────────────────────────────────────

def test_single_product_reviews(slug: str, limit: int = 3) -> None:
    """
    Tes fetch review untuk satu produk secara isolated.
    Gunakan sebelum scraping massal untuk verifikasi endpoint.

    Contoh pakai:
        test_single_product_reviews("25320-facial-sun-shield-spf-50")
    """
    mysql_id = slug.split("-")[0] if slug else None
    if not mysql_id:
        print("[TEST] Slug tidak valid, tidak ada prefix numerik.")
        return

    print(f"\n{'=' * 50}")
    print(f"[TEST] Slug    : {slug}")
    print(f"[TEST] mysql_id: {mysql_id}")
    print(f"{'=' * 50}")

    # Aktifkan debug sementara tanpa ubah konstanta global
    global DEBUG_REVIEWS
    _prev = DEBUG_REVIEWS
    DEBUG_REVIEWS = True

    reviews = fetch_product_reviews(mysql_id, limit=limit)

    DEBUG_REVIEWS = _prev

    print(f"\n[TEST] Hasil: {len(reviews)} review ditemukan")
    for i, r in enumerate(reviews, 1):
        print(f"  [{i}] {r.get('username')} | ★{r.get('rating')} | {r.get('comment', '')[:80]}")

    if not reviews:
        print("[TEST] ⚠ Review kosong — cek output [DEBUG] di atas untuk diagnosa")
    print(f"{'=' * 50}\n")

# ─────────────────────────────────────────────
# HELPER: ekstrak varian dari combinations[]
# ─────────────────────────────────────────────

def _extract_variants(combinations: list) -> list:
    """
    Ekstrak info varian (ukuran, harga, stok, BPOM) dari array combinations.
    Mendukung atribut 'size' maupun 'variant' (shade, dll).
    """
    variants = []
    for combo in combinations:
        attrs    = combo.get("attributes") or {}
        size_obj = attrs.get("size") or attrs.get("variant") or {}
        size_name = size_obj.get("name", "") if isinstance(size_obj, dict) else ""

        stock = combo.get("stock", 0)
        variants.append({
            "variant_name":            size_name,
            "bpom_reg_no":             combo.get("bpom_reg_no", ""),
            "price":                   combo.get("price"),
            "price_after_discount":    combo.get("price_after_discount"),
            "discount_percentage":     combo.get("deduction_percentage"),
            "stock":                   stock,
            "is_in_stock":             stock > 0 and not combo.get("is_out_of_stock_sociolla", True),
            "sold_quota":              combo.get("sold_quota"),
            "total_quota":             combo.get("total_quota"),
            "is_default":              combo.get("is_default", False),
        })
    return variants


# ─────────────────────────────────────────────
# CHECKPOINT: resume scraping jika terputus
# ─────────────────────────────────────────────

def save_checkpoint(category_id: str, skip: int, products: list) -> None:
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "category_id": category_id,
            "skip":        skip,
            "timestamp":   datetime.now().isoformat(),
            "count":       len(products),
            "products":    products,
        }, f, ensure_ascii=False)


def load_checkpoint(category_id: str) -> tuple:
    """Return (resume_skip, products_so_far) atau (0, []) jika tidak ada."""
    if not os.path.exists(CHECKPOINT_FILE):
        return 0, []
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("category_id") != category_id:
            return 0, []
        skip     = data.get("skip", 0)
        products = data.get("products", [])
        print(f"[RESUME] Checkpoint ditemukan: skip={skip}, {len(products)} produk sudah tersimpan")
        return skip, products
    except Exception:
        return 0, []


def clear_checkpoint() -> None:
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("[CHECKPOINT] Dihapus setelah scraping selesai")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("SkinCompare ID — Sociolla Scraper")
    print("=" * 50)

    # ── Quick test sebelum scraping massal ──────────────────
    # Uncomment salah satu baris di bawah, jalankan, lalu comment kembali.
    # Ambil slug dari field "slug" di JSON output sebelumnya.
    #
    # test_single_product_reviews("56216-acne-clarifying-2in1-cleanser")
    # ────────────────────────────────────────────────────────

    all_combined = []
    seen_global  = set()

    for cat in CATEGORIES_TO_SCRAPE:
        print(f"\n{'=' * 50}")
        print(f"Kategori: {cat['name']}")
        print(f"{'=' * 50}")

        cat_products = scrape_all_products(category_id=cat["id"])

        seen_local     = set()
        clean_products = []
        for p in cat_products:
            p["category_source"] = cat["name"]
            if p["slug"] not in seen_local:
                seen_local.add(p["slug"])
                clean_products.append(p)

        if not clean_products:
            print(f"[ERROR] Tidak ada data untuk {cat['name']}.")
            continue

        # Simpan per kategori
        safe_name  = cat["name"].replace(" ", "_").lower()
        file_path  = os.path.join(OUTPUT_DIR, f"products_sociolla_{safe_name}.json")
        save_to_json(clean_products, file_path, cat["name"])

        # Validasi
        validation = validate_json(clean_products)
        print(f"Status   : {'✅ VALID' if validation['valid'] else '❌ TIDAK VALID'}")
        for k, v in validation["stats"].items():
            print(f"  {k:<25}: {v}")

        # Kumpulkan ke combined (dedup global by slug)
        for p in clean_products:
            if p["slug"] not in seen_global:
                seen_global.add(p["slug"])
                all_combined.append(p)

    # Async enrichment (ingredients + reviews paralel)
    if all_combined and ASYNC_ENRICH_AVAILABLE:
        print(f"\n[Enrich] Mulai async enrichment untuk {len(all_combined)} produk...")
        all_combined = asyncio.run(enrich_all_products_async(all_combined))
    elif not ASYNC_ENRICH_AVAILABLE:
        print("[WARNING] Enrichment sync sudah berjalan per produk (mode fallback)")

    # Simpan combined
    if all_combined:
        combined_path = os.path.join(OUTPUT_DIR, "products_sociolla_ALL.json")
        save_to_json(all_combined, combined_path, "ALL")
        print(f"\n✅ Combined saved: {len(all_combined)} produk unik → {combined_path}")