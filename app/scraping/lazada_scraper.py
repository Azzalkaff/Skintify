"""
lazada_scraper.py
Scraper produk Lazada Indonesia
Endpoint: https://www.lazada.co.id/catalog/?ajax=true&...

Cara pakai:
    from lazada_scraper import ambil_top_toko_lazada

    produk_list, toko_list = ambil_top_toko_lazada("Benton Snail Bee High Content Lotion", top_n=5)
"""

import os
import time
import random
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# ── Endpoint ──────────────────────────────────────────────────────────────────
ENDPOINT = "https://www.lazada.co.id/catalog/"


# ── Headers ───────────────────────────────────────────────────────────────────
def _build_headers() -> dict:
    return {
        "accept":           "application/json, text/plain, */*",
        "accept-language":  "en-GB,en-US;q=0.9,en;q=0.8",
        "referer":          "https://www.lazada.co.id/",
        "sec-fetch-dest":   "empty",
        "sec-fetch-mode":   "cors",
        "sec-fetch-site":   "same-origin",
        "x-csrf-token":     os.getenv("LAZADA_CSRF_TOKEN", ""),
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
    }


def _build_cookies() -> dict:
    """Parse cookie string dari .env ke dict."""
    raw = os.getenv("LAZADA_COOKIE", "")
    cookies = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


# ── Helper ────────────────────────────────────────────────────────────────────
def _parse_terjual(teks: str) -> int:
    """
    Konversi '84.9K Terjual' → 84900
    Konversi '2.2K Terjual' → 2200
    Konversi '191 Terjual'  → 191
    """
    if not teks:
        return 0
    
    teks_bersih = teks.replace("Terjual", "").replace("sold", "").strip().upper()
    multiplier = 1
    if "K" in teks_bersih:
        multiplier = 1000
        teks_bersih = teks_bersih.replace("K", "")
    elif "M" in teks_bersih:
        multiplier = 1000000
        teks_bersih = teks_bersih.replace("M", "")
        
    try:
        return int(float(teks_bersih) * multiplier)
    except ValueError:
        return 0


def _parse_diskon(teks: str) -> int:
    """'44% Off' → 44, '' → 0"""
    if not teks:
        return 0
    try:
        return int(teks.replace("%", "").replace("Off", "").strip())
    except ValueError:
        return 0


def _parse_rating(val) -> float:
    """'' atau None → 0.0"""
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_review(val) -> int:
    """'' atau None → 0"""
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _build_url(relative_url: str) -> str:
    """'//www.lazada.co.id/products/...' → 'https://www.lazada.co.id/products/...'"""
    if relative_url.startswith("//"):
        return "https:" + relative_url
    if relative_url.startswith("/"):
        return "https://www.lazada.co.id" + relative_url
    return relative_url


# ── Fungsi pencarian utama ─────────────────────────────────────────────────────
def cari_produk_lazada(keyword: str, page: int = 1, sort: str = "popularity") -> dict:
    """
    Kirim request ke Lazada catalog API dan kembalikan response mentah (dict).
    sort options: 'popularity' (default/terlaris), 'priceasc', 'pricedesc'
    """
    params = {
        "ajax":           "true",
        "isFirstRequest": "true",
        "page":           str(page),
        "q":              keyword,
        "sort":           sort,
    }

    resp = requests.get(
        ENDPOINT,
        params=params,
        headers=_build_headers(),
        cookies=_build_cookies(),
        timeout=15,
    )
    resp.raise_for_status()
    try:
        return resp.json()
    except requests.exceptions.JSONDecodeError as e:
        raise ValueError(f"Lazada memblokir request (kemungkinan anti-bot/Captcha). Response tidak berupa JSON: {e}")


# ── Parser response ────────────────────────────────────────────────────────────
def parse_produk_lazada(raw: dict, keyword: str) -> tuple[list, list, int]:
    """
    Parsing response Lazada → (list_produk, list_toko_unik, total_data)

    Setiap produk berisi field yang sejajar dengan scraper Tokopedia
    agar bisa disimpan ke struktur database yang sama.
    """
    # Validasi struktur dasar
    mods = raw.get("mods", {})
    main_info = raw.get("mainInfo", {})

    if main_info.get("bizCode", -1) != 0:
        err = main_info.get("errorMsg", "Unknown error")
        raise ValueError(f"Lazada API error: {err}")

    total_data = int(main_info.get("totalResults", 0))
    raw_items = mods.get("listItems", [])

    # Filter hanya item bertipe produk (bukan banner/iklan khusus)
    raw_products = [i for i in raw_items if i.get("tItemType") == "nt_product"]

    toko_map = {}     # sellerId → dict toko
    produk_list = []

    for p in raw_products:
        seller_id = str(p.get("sellerId", ""))
        seller_name = p.get("sellerName", "")
        location = p.get("location", "")

        # Kumpulkan toko unik
        if seller_id and seller_id not in toko_map:
            toko_map[seller_id] = {
                "seller_id":   seller_id,
                "nama":        seller_name,
                "kota":        location,
                "is_lazmall":  any(
                    ic.get("bizType") == "lazMall"
                    for ic in (p.get("icons") or [])
                ),
            }

        item_url = _build_url(p.get("itemUrl", ""))

        produk_list.append({
            "item_id":       str(p.get("itemId", "")),
            "keyword":       keyword,
            "nama":          p.get("name", ""),
            "url":           item_url,
            "gambar":        p.get("image", ""),
            "harga":         float(p.get("price") or 0),
            "harga_teks":    p.get("priceShow", ""),
            "harga_asli":    float(p.get("originalPrice") or 0),
            "diskon_persen": _parse_diskon(p.get("discount", "")),
            "rating":        _parse_rating(p.get("ratingScore")),
            "jumlah_review": _parse_review(p.get("review")),
            "terjual":       _parse_terjual(p.get("itemSoldCntShow", "")),
            "lokasi":        location,
            "in_stock":      bool(p.get("inStock", False)),
            "seller_id":     seller_id,
            "seller_name":   seller_name,
            "is_sponsored":  bool(p.get("isSponsored", False)),
        })

    return produk_list, list(toko_map.values()), total_data


# ── Ambil top-N toko terbaik ───────────────────────────────────────────────────
def ambil_top_toko_lazada(keyword: str, top_n: int = 5) -> tuple[list, list]:
    """
    Cari produk di Lazada untuk keyword, kembalikan produk dari top_n toko
    pertama (urutan = relevansi + penjualan dari API, sort=popularity).

    Return: (produk_dari_top_toko, top_toko_list)
    """
    print(f"\n[Lazada] Mencari: '{keyword}'")

    raw = cari_produk_lazada(keyword, page=1, sort="popularity")
    produk_list, semua_toko, total_data = parse_produk_lazada(raw, keyword)

    print(f"   Total data Lazada    : {total_data:,}")
    print(f"   Produk diambil       : {len(produk_list)}")
    print(f"   Toko unik ditemukan  : {len(semua_toko)}")

    # Ambil top_n toko pertama (posisi = urutan kemunculan = relevansi)
    top_toko      = semua_toko[:top_n]
    top_seller_ids = {t["seller_id"] for t in top_toko}

    # Filter produk hanya dari top toko, exclude produk sponsored
    produk_top = [
        p for p in produk_list
        if p["seller_id"] in top_seller_ids and not p["is_sponsored"]
    ]

    print(f"   Top {top_n} toko terpilih  : {[t['nama'] for t in top_toko]}")
    print(f"   Produk dari top toko : {len(produk_top)}")

    # Detil Data untuk Transparansi (Anti-Blackbox)
    if produk_top:
        print("   --- Data yang Diambil (Sample) ---")
        for p in produk_top[:5]: # Tampilkan 5 produk teratas
            print(f"   🔸 [Lazada] {p['nama'][:60]}...")
            print(f"      Harga: Rp{p['harga']:,} | Rating: {p['rating']} | Seller: {p['seller_id']}")
    else:
        print("   ! Tidak ada produk yang sesuai kriteria (Sponsored dibuang).")

    # Rate limit — jaga sopan santun
    delay = random.uniform(2.5, 4.5)
    print(f"   . Tunggu {delay:.1f}s sebelum request berikutnya...")
    time.sleep(delay)

    return produk_top, top_toko


# ── Test mandiri ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    keyword_test = "wardah Crystal Secret α-Arbutin 5% Niacinamide Hyperpigmentation Expert SPF 35 PA+++ Day Moisturizer"
    produk, toko = ambil_top_toko_lazada(keyword_test, top_n=5)

    print("\n=== HASIL PARSING ===")
    print(f"Produk  : {len(produk)}")
    print(f"Toko    : {len(toko)}")
    if produk:
        print("\nContoh produk pertama:")
        print(json.dumps(produk[0], indent=2, ensure_ascii=False))
    if toko:
        print("\nDaftar top toko:")
        for t in toko:
            print(f"  - {t['nama']} ({t['kota']}) | LazMall: {t['is_lazmall']}")