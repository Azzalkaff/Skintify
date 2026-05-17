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
            
            # Filter Keyword (Lebih Luas)
            if keyword:
                st = f"%{keyword.lower()}%"
                query = query.filter(or_(
                    SociollaReferensi.product_name.ilike(st),
                    SociollaReferensi.brand.ilike(st),
                    SociollaReferensi.category.ilike(st),
                    SociollaReferensi.description_raw.ilike(st)
                ))
            
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
                
            # --- SORTING ---
            if sort_val == 'Rating (Tertinggi)':
                query = query.order_by(SociollaReferensi.rating_sociolla.desc())
            elif sort_val == 'Harga (Terendah)':
                query = query.order_by(SociollaReferensi.min_price.asc())
            elif sort_val == 'Harga (Tertinggi)':
                query = query.order_by(SociollaReferensi.min_price.desc())
            elif sort_val == 'Paling Populer':
                query = query.order_by(SociollaReferensi.total_reviews.desc())
                
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
                        marketplace_map[p.referensi_id] = {"tokopedia": None, "lazada": None}
                    platform_lower = str(p.platform).lower()
                    if platform_lower in marketplace_map[p.referensi_id] and not marketplace_map[p.referensi_id][platform_lower]:
                        marketplace_map[p.referensi_id][platform_lower] = {
                            "harga": p.harga, "url": p.url, "nama": p.nama, "terjual": p.terjual
                        }
            
            items = []
            for r in results:
                mkt = marketplace_map.get(r.id, {"tokopedia": None, "lazada": None})
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
                    "image_url": r.image_url or "",   
                    "url_sociolla": r.url_sociolla or "",
                    "is_in_stock": r.is_in_stock,
                    "is_manual": getattr(r, 'is_manual', False),
                    "marketplace": mkt
                })
                
            return {
                "items": items,
                "total_pages": total_pages,
                "current_page": safe_page,
                "total_items": total_items
            }

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

        def _norm_cat(raw_cat: str) -> str:
            if not raw_cat:
                return "Lainnya"
            cat = str(raw_cat).lower()
            
            # Dynamic check from JSON configuration
            json_config = self.data_dir / "categories_to_scrape.json"
            if json_config.exists():
                try:
                    with open(json_config, "r", encoding="utf-8") as f:
                        custom_cats = json.load(f)
                        for cc in custom_cats:
                            cc_name = cc["name"]
                            if cc_name.lower() in cat or cat in cc_name.lower():
                                return cc_name
                except Exception:
                    pass
                    
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

            # 2. Keyword Filter
            p_name = p.get("product_name", "").lower()
            p_brand = p.get("brand", "").lower()
            p_desc = p.get("description_raw", "").lower()
            if keyword:
                kw_low = keyword.lower()
                if kw_low not in p_name and kw_low not in p_brand and kw_low not in cat.lower() and kw_low not in p_desc:
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

            # 4. Harga Filter
            price = float(p.get("min_price") or 0.0)
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
                "image_url": p.get("image_url") or "",   
                "url_sociolla": p.get("url") or "",
                "is_in_stock": bool(p.get("is_in_stock", True)),
                "is_manual": False,
                "marketplace": {"tokopedia": None, "lazada": None}
            })

        # --- SORTING ---
        if sort_val == 'Rating (Tertinggi)':
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
        Melakukan analisis mendalam terhadap daftar bahan dari seluruh produk dalam rutin.
        Menggabungkan data cuaca untuk memberikan saran personal.
        """
        all_ingredients_str = ""
        for r in routine_list:
            all_ingredients_str += r.get("ingredients", "") + ", "
        
        # Bersihkan & Unikkan bahan
        ingredient_set = {i.strip().lower() for i in all_ingredients_str.split(',') if i.strip()}
        
        # 1. Cek Keamanan Aktif (Conflict Detection)
        warnings = SkincareAnalyzer.check_routine_safety(ingredient_set)
        
        # 2. Cek Komedogenik & Iritasi
        aggregate = self.ingredient_db.get_aggregate(ingredient_set)
        warnings.extend(SkincareAnalyzer.check_comedogenicity(aggregate))
        warnings.extend(SkincareAnalyzer.check_irritancy_load(aggregate))
        
        # 3. Data Cuaca & Saran
        weather_data = WeatherService.fetch_weather(kota)
        suggestions = []
        
        if weather_data.get("status") == "success":
            # Advice for Today
            uv = weather_data.get("uv_index", 0)
            hum = weather_data.get("humidity", 0)
            
            if uv >= 7:
                suggestions.append("☀️ Hari ini: UV Index sangat tinggi! Gunakan Re-apply Sunscreen setiap 2 jam.")
            elif uv >= 5:
                suggestions.append("☀️ Hari ini: UV Index cukup kuat. Pastikan pakai Sunscreen sebelum keluar rumah.")
                
            if hum < 50:
                suggestions.append("🌵 Hari ini: Udara kering terdeteksi. Gunakan pelembap oklusif.")
            elif hum > 80:
                suggestions.append("💦 Hari ini: Kelembapan tinggi. Direkomendasikan produk berbahan dasar gel.")
                
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
