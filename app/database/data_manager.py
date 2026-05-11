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
        sort_val: str = "Rating (Tertinggi)", marketplace_only: bool = False
    ) -> Dict[str, Any]:
        """Ambil data dengan filter cerdas yang sadar akan harga marketplace."""
        
        with SessionLocal() as session:
            # Check for empty DB (Cached)
            if self._db_is_empty is None:
                self._db_is_empty = session.query(SociollaReferensi).count() < 1
            
            if self._db_is_empty:
                return self._fallback_json_load(page, items_per_page, category_filter, keyword, min_price, max_price, sort_val)

            # 1. Base query dengan Join ke Produk untuk filter harga yang lebih akurat
            # Kita ingin tahu harga terendah dari (Sociolla, Tokopedia, Lazada)
            
            # Subquery untuk harga termurah per referensi_id dari marketplace
            mkt_min_price = session.query(
                Produk.referensi_id,
                func.min(Produk.harga).label("min_mkt_price")
            ).filter(Produk.harga > 0).group_by(Produk.referensi_id).subquery()

            query = session.query(SociollaReferensi).outerjoin(
                mkt_min_price, SociollaReferensi.id == mkt_min_price.c.referensi_id
            )
            
            # 2. Logika Harga Efektif (Sociolla vs Marketplace)
            effective_price = func.coalesce(
                case(
                    (mkt_min_price.c.min_mkt_price < SociollaReferensi.min_price, mkt_min_price.c.min_mkt_price),
                    else_=SociollaReferensi.min_price
                ),
                SociollaReferensi.min_price
            )

            # --- FILTERING ---
            
            # Filter Kategori
            if category_filter != "All":
                query = query.filter(SociollaReferensi.category == category_filter)
            
            # Filter Keyword (Lebih Luas)
            if keyword:
                st = f"%{keyword.lower()}%"
                query = query.filter(or_(
                    SociollaReferensi.product_name.ilike(st),
                    SociollaReferensi.brand.ilike(st),
                    SociollaReferensi.category.ilike(st),
                    SociollaReferensi.description_raw.ilike(st)
                ))
            
            # Filter Marketplace Only
            if marketplace_only:
                query = query.filter(mkt_min_price.c.referensi_id.isnot(None))
                
            # Filter Harga (Menggunakan Effective Price!)
            if min_price > 0:
                query = query.filter(effective_price >= min_price)
            if max_price < float('inf'):
                query = query.filter(effective_price <= max_price)
                
            # --- SORTING ---
            if sort_val == 'Rating (Tertinggi)':
                query = query.order_by(SociollaReferensi.rating_sociolla.desc())
            elif sort_val == 'Harga (Terendah)':
                query = query.order_by(effective_price.asc())
            elif sort_val == 'Harga (Tertinggi)':
                query = query.order_by(effective_price.desc())
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
                    if not marketplace_map[p.referensi_id][p.platform]:
                        marketplace_map[p.referensi_id][p.platform] = {
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

    def _fallback_json_load(self, *args, **kwargs) -> Dict[str, Any]:
        """Placeholder jika DB benar-benar kosong."""
        return {"items": [], "total_pages": 1, "current_page": 1, "total_items": 0}

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
            uv = weather_data.get("uv_index", 0)
            hum = weather_data.get("humidity", 0)
            
            if uv >= 7:
                suggestions.append("☀️ UV Index sangat tinggi! Gunakan Re-apply Sunscreen setiap 2 jam.")
            if hum < 50:
                suggestions.append("🌵 Udara kering terdeteksi. Gunakan Moisturizer yang lebih oklusif.")
            elif hum > 80:
                suggestions.append("💦 Kelembapan tinggi. Gunakan produk berbahan dasar gel agar tidak gerah.")
                
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
