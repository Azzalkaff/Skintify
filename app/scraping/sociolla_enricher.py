"""
sociolla_enricher.py
Async enrichment layer — ambil ingredients & reviews secara paralel.

Cara pakai (dari sociolla_scraper.py):
    import asyncio
    from sociolla_enricher import enrich_all_products_async

    raw_products = scrape_all_products(...)          # sync, cepat
    enriched     = asyncio.run(
        enrich_all_products_async(raw_products)
    )
"""

import asyncio
import json
import re
import html
import aiohttp
from typing import Optional


# ─── Konfigurasi ──────────────────────────────────────────
CATALOG_API   = "https://catalog-api.sociolla.com/v3/products"
REVIEW_API    = "https://soco-api.sociolla.com/reviews"
MAX_WORKERS   = 5       # concurrent requests (sedang, aman dari rate-limit)
REQUEST_DELAY = 0.3     # detik antar request per worker
REVIEW_LIMIT  = 10
HEADERS = {
    "Accept":       "application/json, text/plain, */*",
    "Origin":       "https://www.sociolla.com",
    "Referer":      "https://www.sociolla.com/",
    "Soc-Platform": "sociolla-web-mobile",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


# ─── Fetch data mentah dari endpoint detail produk ────────

async def _fetch_details(
    session: aiohttp.ClientSession,
    slug: str,
) -> dict:
    """Mengambil data mentah ingredients, description, dan how_to_use"""
    if not slug:
        return {}
    try:
        url = f"{CATALOG_API}/{slug}"
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return {}
            data       = await resp.json()
            data_obj   = data.get("data") or {}
            
            return {
                "ingredients_raw": data_obj.get("ingredients", ""),
                "description_raw": data_obj.get("description", ""),
                "how_to_use_raw":  data_obj.get("how_to_use", "")
            }
    except Exception:
        return {}


# ─── Fetch reviews ────────────────────────────────────────

async def _fetch_reviews(
    session: aiohttp.ClientSession,
    mysql_id: str,
) -> list:
    # [FIX] Fail-Safe O(1): Pastikan ID ada dan murni angka. Mencegah network request salah target.
    if not mysql_id or not mysql_id.isdigit():
        return []
    
    params = {
        "filter":   json.dumps({"product_id": mysql_id, "is_published": True}),
        "limit":    REVIEW_LIMIT,
        "sort":     "-created_at",
        "populate": "user",
    }
    for attempt in range(3):
        try:
            async with session.get(
                REVIEW_API,
                headers=HEADERS,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 429:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                if resp.status != 200:
                    return []
                body = await resp.json()
                return [
                    {
                        "username":       item.get("name", "Anonim"),
                        "rating":         item.get("average_rating", 0),
                        "is_recommended": item.get("is_recommended", ""),
                        "is_repurchase":  item.get("is_repurchase", ""),
                        "is_verified":    item.get("is_verified_purchase", False),
                        "sub_ratings": {
                            k: v for k, v in {
                                "effectiveness":   item.get("star_effectiveness"),
                                "texture":         item.get("star_texture"),
                                "packaging":       item.get("star_packaging"),
                                "value_for_money": item.get("star_value_for_money"),
                            }.items() if v is not None
                        },
                        "comment": item.get("detail", ""),
                    }
                    for item in body.get("data", [])
                ]
        except asyncio.TimeoutError:
            await asyncio.sleep(2 ** attempt)
        except Exception:
            return []
    return []


# ─── Enrich satu produk (ingredients + reviews, paralel) ──

async def _enrich_one(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    product: dict,
    index: int,
    total: int,
) -> dict:
    async with semaphore:
        slug     = product.get("slug", "")
        # [FIX] Gunakan ID asli. Buang tebakan via slug.split() yang memicu data corruption.
        mysql_id = str(product.get("my_sociolla_sql_id", "")).strip()

        # Jalankan detail mentah & reviews secara paralel
        details, reviews = await asyncio.gather(
            _fetch_details(session, slug),
            _fetch_reviews(session, mysql_id),
        )

        # Update teks mentah ke dalam produk (menyimpan versi HTML tanpa mengganggu versi clean)
        raw_ing = details.get("ingredients_raw", "")
        product["ingredients_raw"] = raw_ing
        if raw_ing:
            clean_ing = re.sub(r"<[^>]+>", " ", raw_ing)
            clean_ing = html.unescape(clean_ing).strip()
            clean_ing = re.sub(r"\s+", " ", clean_ing)
            product["ingredients"] = clean_ing
            
        product["description_raw"] = details.get("description_raw") or product.get("description_raw", "")
        product["how_to_use_raw"]  = details.get("how_to_use_raw")  or product.get("how_to_use_raw", "")
        
        product["reviews"]         = reviews

        if (index + 1) % 10 == 0 or index == 0:
            print(f"  [Enrich] {index + 1}/{total} selesai — {product.get('product_name', '')[:40]}")

        await asyncio.sleep(REQUEST_DELAY)
        return product


# ─── Entry point utama ─────────────────────────────────────

async def enrich_all_products_async(
    products: list,
    max_concurrent: int = MAX_WORKERS,
) -> list:
    """
    Tambahkan ingredients & reviews ke semua produk secara async paralel.

    Args:
        products       : list produk dari scrape_all_products() (belum di-enrich)
        max_concurrent : jumlah worker paralel (default 5)

    Returns:
        list produk yang sudah dilengkapi ingredients & reviews
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    total     = len(products)
    print(f"\n[Enrich] Mulai async enrichment: {total} produk, {max_concurrent} worker paralel")

    connector = aiohttp.TCPConnector(limit=max_concurrent * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _enrich_one(session, semaphore, p, i, total)
            for i, p in enumerate(products)
        ]
        enriched = await asyncio.gather(*tasks)

    print(f"[Enrich] Selesai: {len(enriched)} produk di-enrich")
    return list(enriched)