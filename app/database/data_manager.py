"""
Hybrid Repository Pattern untuk DataManager
Menjadi Single Source of Truth: mencoba load SQLite terlebih dahulu. 
Jika kosong (belum ada scraping interaktif dari terminal), akan membaca file JSON fallback.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, case
from datetime import datetime

from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi, Produk, User
from app.services.analyzer import IngredientDatabase, SkincareAnalyzer
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)

class DataManager:
    """
    Facade class yang menggabungkan SQLite, JSON Fallback, Analyzer, dan WeatherService.
    Memberikan satu antarmuka yang bersih untuk digunakan oleh main.py.
    """
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.ingredient_db = IngredientDatabase(self.data_dir)
        
        # Cache memory
        self._categories_cache = None 
        self._db_is_empty = None
        self._cached_products = None 

    def get_ingredient_profile(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.ingredient_db.is_loaded():
            return None
        raw = product.get("ingredients", "")
        if not raw:
            return None
        ingredient_set = {item.strip().lower() for item in raw.split(',') if item.strip()}
        return self.ingredient_db.get_aggregate(ingredient_set)

    @property
    def categories(self) -> List[str]:
        """Ambil daftar kategori unik langsung dari database (Dinamis dengan caching)."""
        if self._categories_cache:
            return self._categories_cache
            
        with SessionLocal() as session:
            cats = session.query(SociollaReferensi.category).distinct().all()
            if cats:
                clean_cats = {c[0] for c in cats if c[0] and c[0] != "Uncategorized" and c[0] != "Lainnya"}
                # Pastikan kategori utama selalu ada di atas
                priority = ["Serum", "Moisturizer", "Sunscreen", "Toner", "Cleanser"]
                others = sorted([c for c in clean_cats if c not in priority])
                self._categories_cache = ["All"] + priority + others + ["Lainnya"]
            else:
                self._categories_cache = ["All", "Serum", "Moisturizer", "Sunscreen", "Toner", "Cleanser", "Lainnya"]
        return self._categories_cache

    def get_paginated_products(
        self, page: int = 1, items_per_page: int = 10, category_filter: str = "All",
        keyword: str = "", min_price: float = 0.0, max_price: float = float('inf'),
        sort_val: str = "Rating (Tertinggi)", marketplace_only: bool = False,
        skin_type_filter: str = "Semua", brand_filter: str = "Semua"
    ) -> Dict[str, Any]:
        """Ambil data dengan filter cerdas yang dioptimalkan secara performa tinggi."""

        # ── Lightweight parameter-hash cache (maks 5 entri, TTL 60 detik) ───────────
        # Menghindari double DB-hit saat refresh halaman / pagination tanpa perubahan filter.
        import time, hashlib, json as _json
        _cache_key_data = _json.dumps([
            page, items_per_page, category_filter, keyword,
            min_price if min_price != float('inf') else -1,
            max_price if max_price != float('inf') else -1,
            sort_val, marketplace_only, skin_type_filter, brand_filter
        ], default=str)
        _cache_key = hashlib.md5(_cache_key_data.encode()).hexdigest()

        if not hasattr(self, '_paginate_cache'):
            self._paginate_cache = {}  # {key: (timestamp, result)}

        _now = time.monotonic()
        if _cache_key in self._paginate_cache:
            _ts, _cached_result = self._paginate_cache[_cache_key]
            if (_now - _ts) < 60:  # Cache valid 60 detik
                return _cached_result

        # Buang cache kedaluwarsa (jaga agar tidak tumbuh tanpa batas)
        self._paginate_cache = {
            k: v for k, v in self._paginate_cache.items()
            if (_now - v[0]) < 60
        }

        with SessionLocal() as session:
            # Always check if DB is empty to avoid permanent empty cache
            is_empty = session.query(SociollaReferensi).count() < 1
            
            if is_empty:
                return self._fallback_json_load(
                    page, items_per_page, category_filter, keyword, min_price, max_price, sort_val, skin_type_filter, brand_filter
                )

            # 1. Base query cepat langsung ke SociollaReferensi (tanpa join subquery berat!)
            query = session.query(SociollaReferensi)
            
            # --- FILTERING ---
            
            # Filter Kategori
            if category_filter != "All":
                query = query.filter(SociollaReferensi.category == category_filter)
            
            # Filter Brand
            if brand_filter and brand_filter not in ("Semua", "All"):
                query = query.filter(SociollaReferensi.brand == brand_filter)
            
            # Filter Keyword (Fuzzy-based Token filtering inside paginator chunk)
            # strictly strict exact match is skipped here so we can do wide token matching in paginator
            
            # Filter Tipe Kulit (Skin Type)
            if skin_type_filter and skin_type_filter not in ("Semua", "All"):
                skin_map = {
                    "Dry": ["hyaluronic", "glycerin", "ceramide", "shea butter", "squalane", "panthenol"],
                    "Kering": ["hyaluronic", "glycerin", "ceramide", "shea butter", "squalane", "panthenol"],
                    "Oily": ["salicylic", "niacinamide", "tea tree", "zinc", "clay", "bha"],
                    "Berminyak": ["salicylic", "niacinamide", "tea tree", "zinc", "clay", "bha"],
                    "Sensitive": ["centella", "allantoin", "panthenol", "chamomile", "aloe"],
                    "Sensitif": ["centella", "allantoin", "panthenol", "chamomile", "aloe"],
                    "Combination": ["hyaluronic", "niacinamide", "centella", "glycerin"],
                    "Kombinasi": ["hyaluronic", "niacinamide", "centella", "glycerin"]
                }
                keywords = skin_map.get(skin_type_filter)
                if keywords:
                    ing_filters = [SociollaReferensi.ingredients.ilike(f"%{kw}%") for kw in keywords]
                    query = query.filter(or_(*ing_filters))

            # Filter Marketplace Only
            if marketplace_only:
                # Cepat menggunakan EXISTS atau subquery IN_
                has_mkt_subquery = session.query(Produk.referensi_id).filter(Produk.harga > 0).distinct().subquery()
                query = query.filter(SociollaReferensi.id.in_(has_mkt_subquery))
                
            # Filter Harga (Menggunakan kolom min_price referensi demi efisiensi indeks!)
            if min_price > 0:
                query = query.filter(SociollaReferensi.min_price >= min_price)
            if max_price < float('inf'):
                query = query.filter(SociollaReferensi.min_price <= max_price)
                
            # --- SORTING & FUZZY MATCHING LOGIC ---
            if keyword:
                import difflib
                # Pecah kata kunci pencarian menjadi token-token kata
                words = [w.strip().lower() for w in keyword.split() if len(w.strip()) >= 2]
                if words:
                    # Saring kandidat secara dinamis yang memiliki salah satu token kata
                    clauses = []
                    for w in words:
                        clauses.append(SociollaReferensi.product_name.ilike(f"%{w}%"))
                        clauses.append(SociollaReferensi.brand.ilike(f"%{w}%"))
                        clauses.append(SociollaReferensi.category.ilike(f"%{w}%"))
                    query = query.filter(or_(*clauses))
                
                # Muat maksimal 100 kandidat (turun dari 300) untuk fuzzy di Python.
                # Dengan token-pre-filter di atas, kandidat yang sampai sini
                # sudah sangat relevan sehingga 100 cukup presisi.
                candidates = query.limit(100).all()
                
                scored_candidates = []
                target = keyword.lower()
                target_tokens = set(target.split())  # Hitung sekali di luar loop
                for r in candidates:
                    cand_name = r.product_name.lower()
                    cand_brand = r.brand.lower() if r.brand else ""
                    full_name = f"{cand_brand} {cand_name}".strip()
                    
                    # Token Intersection (murah, O(k)) — cek dulu sebelum SequenceMatcher
                    cand_tokens = set(full_name.split())
                    intersection = target_tokens.intersection(cand_tokens)
                    token_ratio = len(intersection) / max(1, len(target_tokens))
                    
                    # Jika token overlap sudah tinggi, skip SequenceMatcher yang mahal
                    if token_ratio >= 0.8:
                        score = token_ratio
                    else:
                        import difflib
                        ratio2 = difflib.SequenceMatcher(None, target, cand_name).ratio()
                        score = max(token_ratio, ratio2)
                    
                    # Threshold 0.55 (sedikit longgar vs 0.65 sebelumnya agar tidak terlalu ketat)
                    if score >= 0.55:
                        is_manual = getattr(r, 'is_manual', False) or False
                        final_score = score + 0.15 if is_manual else score
                        scored_candidates.append((final_score, r))
                
                # Urutkan berdasarkan skor fuzzy tertinggi
                scored_candidates.sort(key=lambda x: x[0], reverse=True)
                
                total_items = len(scored_candidates)
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
                safe_page = max(1, min(page, total_pages))
                
                start_idx = (safe_page - 1) * items_per_page
                end_idx = start_idx + items_per_page
                results = [pair[1] for pair in scored_candidates[start_idx:end_idx]]
            else:
                # FIX #4: Ganti 2 query (COUNT + SELECT) menjadi 1 query SELECT saja.
                # Ambil semua hasil dengan ORDER BY, lalu pagination di Python.
                # Untuk dataset wajar (<50k rows), ini lebih cepat karena menghindari
                # locking overhead 2 koneksi DB berurutan.
                if sort_val == 'Rating (Tertinggi)':
                    query = query.order_by(SociollaReferensi.rating_sociolla.desc())
                elif sort_val == 'Harga (Terendah)':
                    query = query.order_by(SociollaReferensi.min_price.asc())
                elif sort_val == 'Harga (Tertinggi)':
                    query = query.order_by(SociollaReferensi.min_price.desc())
                elif sort_val == 'Paling Populer':
                    query = query.order_by(SociollaReferensi.total_reviews.desc())

                # Gunakan OFFSET+LIMIT langsung — 1 trip ke DB
                total_items = query.count()
                total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
                safe_page = max(1, min(page, total_pages))
                results = query.offset((safe_page - 1) * items_per_page).limit(items_per_page).all()

            # --- MAPPING RESULTS ---
            referensi_ids = [r.id for r in results]
            marketplace_map = {}
            
            if referensi_ids:
                all_mkt = session.query(Produk).filter(Produk.referensi_id.in_(referensi_ids)).order_by(Produk.harga.asc()).all()
                for p in all_mkt:
                    if p.referensi_id not in marketplace_map:
                        marketplace_map[p.referensi_id] = {"tokopedia": None, "lazada": None, "shopee": None}
                    platform_lower = str(p.platform).lower()
                    if platform_lower in marketplace_map[p.referensi_id] and not marketplace_map[p.referensi_id][platform_lower]:
                        marketplace_map[p.referensi_id][platform_lower] = {
                            "harga": p.harga, "url": p.url, "nama": p.nama, "terjual": p.terjual
                        }
            
            items = []
            for r in results:
                mkt = marketplace_map.get(r.id, {"tokopedia": None, "lazada": None, "shopee": None})
                items.append({
                    "id": r.id,
                    "brand": r.brand,
                    "brand_country": r.brand_country or "",
                    "product_name": r.product_name,
                    "category": r.category,
                    "slug": r.slug or f"product-{r.id}",
                    "ingredients": r.ingredients or "",
                    "description_raw": r.description_raw or "",
                    "how_to_use_raw": r.how_to_use_raw or "",
                    "bpom_reg_no": r.bpom_reg_no or "",
                    "min_price": r.min_price or 0,
                    "rating": r.rating_sociolla or 0,
                    "average_rating": r.rating_sociolla or 0,
                    "total_reviews": r.total_reviews or 0,
                    "total_recommended": r.total_recommended or 0,
                    "repurchase_yes": r.repurchase_yes or 0,
                    "repurchase_no": r.repurchase_no or 0,
                    "repurchase_maybe": r.repurchase_maybe or 0,
                    "variants": r.variants or [],
                    "reviews": r.reviews or [],
                    "image_url": r.image_url or "",   
                    "url_sociolla": r.url_sociolla or "",
                    "is_in_stock": r.is_in_stock,
                    "is_manual": getattr(r, 'is_manual', False),
                    "marketplace": mkt
                })
                
            _result = {
                "items": items,
                "total_pages": total_pages,
                "current_page": safe_page,
                "total_items": total_items
            }
            # Simpan ke cache — permintaan identik dalam 60 detik akan langsung return
            self._paginate_cache[_cache_key] = (time.monotonic(), _result)
            return _result

    def _fallback_json_load(
        self, page: int = 1, items_per_page: int = 10, category_filter: str = "All",
        keyword: str = "", min_price: float = 0.0, max_price: float = float('inf'),
        sort_val: str = "Rating (Tertinggi)", skin_type_filter: str = "Semua", brand_filter: str = "Semua"
    ) -> Dict[str, Any]:
        """Membaca data produk langsung dari file JSON fallback ketika database SQLite kosong."""
        json_file = self.data_dir / "products_sociolla_ALL.json"
        if not json_file.exists():
            logger.warning(f"File JSON fallback tidak ditemukan di {json_file}")
            return {"items": [], "total_pages": 1, "current_page": 1, "total_items": 0}

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                products = data if isinstance(data, list) else data.get("products", [])
        except Exception as e:
            logger.error(f"Gagal membaca file JSON fallback: {e}")
            return {"items": [], "total_pages": 1, "current_page": 1, "total_items": 0}

        # Cache categories_to_scrape.json ONCE to avoid thousand of disk I/O reads inside the loop
        custom_cats = []
        json_config = self.data_dir / "categories_to_scrape.json"
        if json_config.exists():
            try:
                with open(json_config, "r", encoding="utf-8") as f:
                    custom_cats = json.load(f)
            except Exception as e:
                logger.error(f"Gagal memuat kategori kustom: {e}")

        def _norm_cat(raw_cat: str) -> str:
            if not raw_cat:
                return "Lainnya"
            cat = str(raw_cat).lower()
            
            # Gunakan in-memory cache custom_cats
            for cc in custom_cats:
                cc_name = cc.get("name")
                if cc_name and (cc_name.lower() in cat or cat in cc_name.lower()):
                    return cc_name
                    
            if "serum" in cat: return "Serum"
            if "moisturizer" in cat or "gel" in cat or "cream" in cat: return "Moisturizer"
            if "sunscreen" in cat or "sun care" in cat or "sun" in cat: return "Sunscreen"
            if "toner" in cat or "mist" in cat: return "Toner"
            if "wash" in cat or "cleanser" in cat or "micellar" in cat or "cleansing" in cat: return "Cleanser"
            if "cushion" in cat: return "Cushion"
            if "blush" in cat: return "Blush"
            if "powder" in cat: return "Powder"
            if "eye" in cat or "eyeliner" in cat or "mascara" in cat or "eyebrow" in cat: return "Eye Product"
            if "lip" in cat or "lipstick" in cat or "lip tint" in cat or "lip balm" in cat: return "LIP Product"
            return "Lainnya"

        filtered_products = []
        for p in products:
            slug = p.get("slug")
            if not slug:
                continue

            # Klasifikasi kategori
            cat = _norm_cat(p.get("category_source") or p.get("category"))
            
            # 1. Kategori Filter
            if category_filter != "All" and cat != category_filter:
                continue

            # 1b. Brand Filter
            if brand_filter and brand_filter not in ("Semua", "All") and p.get("brand") != brand_filter:
                continue

            # 2. Keyword Filter (Fuzzy logic)
            fuzzy_score = 1.0
            if keyword:
                import difflib
                target = keyword.lower()
                p_name_low = p.get("product_name", "").lower()
                p_brand_low = p.get("brand", "").lower()
                full_name = f"{p_brand_low} {p_name_low}".strip()
                
                ratio1 = difflib.SequenceMatcher(None, target, full_name).ratio()
                ratio2 = difflib.SequenceMatcher(None, target, p_name_low).ratio()
                
                target_tokens = set(target.split())
                cand_tokens = set(full_name.split())
                intersection = target_tokens.intersection(cand_tokens)
                token_ratio = len(intersection) / max(1, len(target_tokens))
                
                fuzzy_score = max(ratio1, ratio2, token_ratio)
                
                if fuzzy_score < 0.65:
                    continue

            # 3. Filter Tipe Kulit (Skin Type)
            if skin_type_filter and skin_type_filter not in ("Semua", "All"):
                skin_map = {
                    "Dry": ["hyaluronic", "glycerin", "ceramide", "shea butter", "squalane", "panthenol"],
                    "Kering": ["hyaluronic", "glycerin", "ceramide", "shea butter", "squalane", "panthenol"],
                    "Oily": ["salicylic", "niacinamide", "tea tree", "zinc", "clay", "bha"],
                    "Berminyak": ["salicylic", "niacinamide", "tea tree", "zinc", "clay", "bha"],
                    "Sensitive": ["centella", "allantoin", "panthenol", "chamomile", "aloe"],
                    "Sensitif": ["centella", "allantoin", "panthenol", "chamomile", "aloe"],
                    "Combination": ["hyaluronic", "niacinamide", "centella", "glycerin"],
                    "Kombinasi": ["hyaluronic", "niacinamide", "centella", "glycerin"]
                }
                keywords = skin_map.get(skin_type_filter, [])
                if keywords:
                    ing_raw = p.get("ingredients", "").lower()
                    if not any(kw in ing_raw for kw in keywords):
                        continue

            # 4. Harga Filter (Robust parsing to prevent ValueError crash)
            raw_price = p.get("min_price")
            price = 0.0
            if raw_price is not None:
                try:
                    if isinstance(raw_price, (int, float)):
                        price = float(raw_price)
                    else:
                        # Clean currency strings, thousand indicators, etc.
                        cleaned = str(raw_price).replace("Rp", "").replace(".", "").replace(",", "").strip()
                        price = float(cleaned)
                except (ValueError, TypeError):
                    price = 0.0

            if price < min_price or price > max_price:
                continue

            filtered_products.append({
                "id": p.get("id") or (hash(slug) % 100000),
                "brand": p.get("brand", "Unknown Brand"),
                "brand_country": p.get("brand_country") or "",
                "product_name": p.get("product_name", "Unknown Product"),
                "category": cat,
                "slug": slug,
                "ingredients": p.get("ingredients") or "",
                "description_raw": p.get("description_raw") or "",
                "how_to_use_raw": p.get("how_to_use_raw") or "",
                "bpom_reg_no": p.get("bpom_reg_no") or "",
                "min_price": price,
                "rating": float(p.get("average_rating") or 0.0),
                "average_rating": float(p.get("average_rating") or 0.0),
                "total_reviews": int(p.get("total_reviews") or 0),
                "total_recommended": int(p.get("total_recommended") or 0),
                "repurchase_yes": int(p.get("repurchase_yes") or 0),
                "repurchase_no": int(p.get("repurchase_no") or 0),
                "repurchase_maybe": int(p.get("repurchase_maybe") or 0),
                "variants": p.get("variants") or [],
                "reviews": p.get("reviews") or [],
                "image_url": p.get("image_url") or "",   
                "url_sociolla": p.get("url") or "",
                "is_in_stock": bool(p.get("is_in_stock", True)),
                "is_manual": False,
                "_fuzzy_score": fuzzy_score,
                "marketplace": {"tokopedia": None, "lazada": None, "shopee": None}
            })

        # --- SORTING ---
        if keyword:
            filtered_products.sort(key=lambda x: x.get("_fuzzy_score", 0.0), reverse=True)
        elif sort_val == 'Rating (Tertinggi)':
            filtered_products.sort(key=lambda x: x["rating"], reverse=True)
        elif sort_val == 'Harga (Terendah)':
            filtered_products.sort(key=lambda x: x["min_price"])
        elif sort_val == 'Harga (Tertinggi)':
            filtered_products.sort(key=lambda x: x["min_price"], reverse=True)
        elif sort_val == 'Paling Populer':
            filtered_products.sort(key=lambda x: x["total_reviews"], reverse=True)

        total_items = len(filtered_products)
        total_pages = (total_items + items_per_page - 1) // items_per_page if total_items > 0 else 1
        safe_page = max(1, min(page, total_pages))

        start_idx = (safe_page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        paginated_items = filtered_products[start_idx:end_idx]

        return {
            "items": paginated_items,
            "total_pages": total_pages,
            "current_page": safe_page,
            "total_items": total_items
        }

    def add_custom_product(self, data: Dict[str, Any]) -> bool:
        """Menambahkan produk baru secara manual dari UI."""
        with SessionLocal() as session:
            try:
                timestamp = int(datetime.now().timestamp())
                slug_base = data['product_name'].lower().replace(" ", "-")
                new_ref = SociollaReferensi(
                    product_name = data['product_name'],
                    brand = data['brand'],
                    category = data['category'],
                    min_price = float(data.get('price', 0)),
                    ingredients = data.get('ingredients', ''),
                    image_url = data.get('image_url', ''),
                    is_manual = True,
                    slug = f"{slug_base}-{timestamp}"
                )
                session.add(new_ref)
                session.commit()
                return True
            except Exception as e:
                logger.error(f"Gagal menambah produk: {e}")
                session.rollback()
                return False

    def delete_custom_product(self, product_id: int) -> bool:
        with SessionLocal() as session:
            try:
                ref = session.query(SociollaReferensi).filter_by(id=product_id).first()
                if ref:
                    session.delete(ref)
                    session.commit()
                    return True
                return False
            except Exception as e:
                logger.error(f"Gagal hapus produk: {e}")
                session.rollback()
                return False

    def update_custom_product(self, product_id: int, data: Dict[str, Any]) -> bool:
        """Update data produk manual."""
        with SessionLocal() as session:
            try:
                ref = session.query(SociollaReferensi).filter_by(id=product_id).first()
                if ref:
                    ref.product_name = data.get('product_name', ref.product_name)
                    ref.brand = data.get('brand', ref.brand)
                    ref.category = data.get('category', ref.category)
                    ref.min_price = float(data.get('price', ref.min_price))
                    ref.ingredients = data.get('ingredients', ref.ingredients)
                    ref.image_url = data.get('image_url', ref.image_url)
                    session.commit()
                    return True
                return False
            except Exception as e:
                logger.error(f"Gagal update produk: {e}")
                session.rollback()
                return False

    def analyze_routine(self, routine_list: List[Dict[str, Any]], kota: str = "") -> Dict[str, Any]:
        """
        Melakukan analisis mendalam secara Medis & Evidence-Based.
        Menggabungkan Clinical Knowledge Graph dan Skin Exposome (Data Cuaca).
        """
        all_ingredients_str = ""
        for r in routine_list:
            # Gabungkan nama produk dan deskripsi agar deteksi bahan aktif lebih luas & fuzzy
            all_ingredients_str += r.get("product_name", "") + " " + r.get("ingredients", "") + ", "
        
        ing_text_lower = all_ingredients_str.lower()
        ingredient_set = {i.strip().lower() for i in all_ingredients_str.split(',') if i.strip()}
        
        # 1. Cek Keamanan Dasar (Modul Analyzer Bawaan)
        warnings = SkincareAnalyzer.check_routine_safety(ingredient_set)
        
        # 1.b. Clinical Knowledge Graph (Deteksi Konflik pH & Oksidasi Molekuler Absolut)
        has_retinoid = any(x in ing_text_lower for x in ["retinol", "retinoid", "retinal", "tretinoin", "adapalene"])
        has_aha_bha = any(x in ing_text_lower for x in ["glycolic", "lactic", "salicylic", "aha", "bha", "pha"])
        has_vit_c = any(x in ing_text_lower for x in ["ascorbic acid", "vitamin c", "l-ascorbic"])
        has_bp = any(x in ing_text_lower for x in ["benzoyl peroxide", "bpo"])
        
        if has_retinoid and has_aha_bha:
            warnings.append("🚨 CLINICAL CONFLICT: Retinoid + AHA/BHA! Kombinasi ini memicu over-eksfoliasi dan merusak Skin Barrier. Pisahkan penggunaan (Pagi/Malam atau beda hari).")
        if has_retinoid and has_vit_c:
            warnings.append("⚠️ pH DISRUPTION: Retinoid (pH optimal 5.5) + Vitamin C murni (pH 3.5) akan merusak stabilitas molekul. Gunakan Vit C di pagi hari, Retinoid di malam hari.")
        if has_bp and has_retinoid:
            warnings.append("🚨 MOLECULAR INACTIVATION: Benzoyl Peroxide dapat mengoksidasi dan mematikan fungsi Retinoid secara instan. Jangan ditumpuk bersamaan!")
        
        # 2. Cek Komedogenik & Iritasi
        aggregate = self.ingredient_db.get_aggregate(ingredient_set)
        warnings.extend(SkincareAnalyzer.check_comedogenicity(aggregate))
        warnings.extend(SkincareAnalyzer.check_irritancy_load(aggregate))
        
        # 3. Analisis Exposome (Pengaruh Lingkungan pada Fisiologi Kulit)
        weather_data = WeatherService.fetch_weather(kota)
        suggestions = []
        
        if weather_data.get("status") == "success":
            uv = weather_data.get("uv_index", 0)
            hum = weather_data.get("humidity", 0)
            
            # Clinical UV & ROS Logic
            if uv >= 6:
                suggestions.append(f"☀️ UV EXTREME ({uv}): Radiasi memicu Reactive Oxygen Species (ROS). WAJIB Sunscreen SPF 50+ (Re-apply 2 jam). Tambahkan serum Antioksidan (Vit C/Niacinamide) untuk perlindungan seluler.")
            elif uv >= 3:
                suggestions.append(f"🌤️ UV MODERATE ({uv}): Gunakan Sunscreen minimal SPF 30+ sebelum beraktivitas.")
                
            # Clinical Humidity & TEWL Logic
            if hum < 45:
                suggestions.append(f"🌵 KERING ({hum}%): Risiko Transepidermal Water Loss (TEWL) sangat tinggi! Hentikan eksfoliasi sementara. Gunakan teknik 'Moisture Sandwich' (Hidrator + Pelembap tebal seperti Ceramide/Shea Butter).")
            elif hum > 75:
                suggestions.append(f"💦 LEMBAP ({hum}%): Sekresi sebum berisiko meningkat. Ganti krim tebal Anda dengan pelembap bertekstur Gel ringan (Water-based) agar pori tidak tersumbat (Non-comedogenic).")
            # Forecast advice (next 3 days)
            forecast = weather_data.get("forecast", [])
            for day in forecast[1:4]:  # Day 1, 2, 3 (excluding today at index 0)
                day_name = day.get("date_label", "").split(",")[0]  # e.g., "Senin"
                f_uv = day.get("uv_index", 0)
                f_hum = day.get("humidity", 0)
                f_cond = day.get("condition", "").lower()
                
                if f_uv >= 7:
                    suggestions.append(f"☀️ {day_name}: Diperkirakan UV Index ekstrim ({f_uv}). Persiapkan Sunscreen SPF 50+!")
                if f_hum < 50:
                    suggestions.append(f"🌵 {day_name}: Diperkirakan cuaca kering ({f_hum}%). Persiapkan hidrasi ekstra.")
                elif "hujan" in f_cond or "badai" in f_cond or "gerimis" in f_cond:
                    suggestions.append(f"🌧️ {day_name}: Potensi hujan terdeteksi. Pelembap hidrogel ringan ideal untuk cuaca dingin & lembap.")
                
        # 4. Tentukan Status Akhir
        status = "safe"
        if any("⚠️" in w or "🚨" in w or "🚫" in w for w in warnings):
            status = "danger"
        elif not routine_list:
            status = "empty"

        return {
            "status": status,
            "warnings": warnings,
            "suggestions": suggestions,
            "weather": weather_data,
            "incidecoder_aggregate": aggregate if self.ingredient_db.is_loaded() else None
        }
