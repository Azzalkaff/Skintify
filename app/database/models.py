"""
models.py — SQLAlchemy ORM Models
Mendukung multi-platform: Tokopedia & Lazada
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    email       = Column(String(255), unique=True, nullable=False)
    username    = Column(String(100), unique=True, nullable=False)
    password    = Column(String(255), nullable=False)
    city        = Column(String(100), nullable=True)  # Lokasi untuk API cuaca
    created_at  = Column(DateTime, default=datetime.utcnow)

    routines = relationship("Routine", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} ({self.email})>"


class Routine(Base):
    __tablename__ = "routines"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(100), nullable=False)  # e.g., "Morning Routine"
    description = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user  = relationship("User", back_populates="routines")
    items = relationship("RoutineItem", back_populates="routine", cascade="all, delete-orphan", order_by="RoutineItem.step_order")

    def __repr__(self):
        return f"<Routine {self.name} by User {self.user_id}>"


class RoutineItem(Base):
    __tablename__ = "routine_items"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    routine_id  = Column(Integer, ForeignKey("routines.id"), nullable=False)
    product_id  = Column(Integer, ForeignKey("produk.id"), nullable=True)
    custom_name = Column(String(255), nullable=True)  # if product not in DB
    step_order  = Column(Integer, default=0)
    notes       = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True)

    routine = relationship("Routine", back_populates="items")
    product = relationship("Produk")

    def __repr__(self):
        return f"<RoutineItem step {self.step_order} in Routine {self.routine_id}>"



class Toko(Base):
    __tablename__ = "toko"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    platform    = Column(String(20), nullable=False, index=True)          # 'tokopedia' | 'lazada'
    shop_id     = Column(String(100), nullable=False)         # seller_id / shop_id
    nama        = Column(String(255))
    kota        = Column(String(100))
    tier        = Column(Integer, nullable=True)               # Tokopedia: 0/1/2, Lazada: None
    is_official = Column(Boolean, default=False)              # official store / LazMall
    url         = Column(String(500), nullable=True)
    dibuat_pada = Column(DateTime, default=datetime.utcnow)

    produk = relationship("Produk", back_populates="toko", cascade="all, delete-orphan")

    # Unique per platform — shop_id bisa sama nilainya antar platform (collision)
    __table_args__ = (
        UniqueConstraint("platform", "shop_id", name="uq_toko_platform_shopid"),
    )

    def __repr__(self):
        return f"<Toko [{self.platform}] {self.nama} ({self.shop_id})>"


class Produk(Base):
    __tablename__ = "produk"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    platform            = Column(String(20), nullable=False, index=True)  # 'tokopedia' | 'lazada'
    product_id          = Column(String(100), nullable=False) # item_id / product_id
    keyword             = Column(String(500), nullable=False, index=True)
    nama                = Column(String(500))
    url                 = Column(String(500))
    gambar              = Column(String(500))

    # ── Harga ────────────────────────────────────────────────────────────────
    harga               = Column(Float, index=True)
    harga_teks          = Column(String(100))
    harga_asli          = Column(Float)          # harga sebelum diskon
    diskon_persen       = Column(Integer)

    # ── Performa ─────────────────────────────────────────────────────────────
    rating              = Column(Float)
    jumlah_review       = Column(Integer, default=0)
    terjual             = Column(Integer, default=0)  # Lazada: sold count

    # ── Metadata Tokopedia ───────────────────────────────────────────────────
    kategori            = Column(String(255), nullable=True)
    label_badge         = Column(String(255), nullable=True)  # "Mall", "Power Merchant"
    free_ongkir         = Column(Integer, nullable=True)      # 1=ada, 0=tidak (Tokopedia)

    # ── Metadata Lazada ──────────────────────────────────────────────────────
    in_stock            = Column(Boolean, nullable=True)
    is_sponsored        = Column(Boolean, nullable=True)

    dibuat_pada         = Column(DateTime, default=datetime.utcnow)
 
    referensi_id = Column(Integer, ForeignKey("sociolla_referensi.id"), nullable=True, index=True)
    referensi    = relationship("SociollaReferensi", back_populates="marketplace_products")

    toko_id = Column(Integer, ForeignKey("toko.id"))
    toko    = relationship("Toko", back_populates="produk")

    # Unique per platform + product_id + keyword
    __table_args__ = (
        UniqueConstraint("platform", "product_id", "keyword", name="uq_produk_platform_keyword"),
    )

    def __repr__(self):
        return f"<Produk [{self.platform}] {self.nama[:40]}... Rp{self.harga:,.0f}>"


class SociollaReferensi(Base):
    """Menyimpan produk Sociolla sebagai referensi sumber keyword."""
    __tablename__ = "sociolla_referensi"

    id                      = Column(Integer, primary_key=True, autoincrement=True)
    slug                    = Column(String(255), unique=True)
    product_name            = Column(String(500), nullable=False, index=True)
    brand                   = Column(String(255), nullable=False, index=True)
    brand_country           = Column(String(100))
    brand_region            = Column(String(100))
    keyword_digunakan       = Column(String(500), index=True)   # keyword yang dikirim ke scraper
    category                = Column(String(255), index=True)
    all_categories          = Column(JSON)          # List kategori nested
    
    # Harga
    min_price               = Column(Float, index=True)
    max_price               = Column(Float)
    min_price_after_discount = Column(Float)
    max_price_after_discount = Column(Float)
    harga_setelah_diskon    = Column(Float, nullable=True)
    diskon                  = Column(String(50), nullable=True)
    
    # Performa & Metrik
    rating_sociolla         = Column(Float, default=0, index=True)
    total_reviews           = Column(Integer, default=0)
    total_recommended       = Column(Integer, default=0)
    repurchase_yes          = Column(Integer, default=0)
    repurchase_no           = Column(Integer, default=0)
    repurchase_maybe        = Column(Integer, default=0)
    total_wishlist          = Column(Integer, default=0)
    
    # Metadata & Stock
    bpom_reg_no             = Column(String(100))
    url_sociolla            = Column(String(500))
    image_url               = Column(String(500))
    is_in_stock             = Column(Boolean, default=True)
    is_flashsale            = Column(Boolean, default=False)
    sudah_di_scrape         = Column(Boolean, default=False)
    is_manual               = Column(Boolean, default=False)  # Penanda produk input manual UI
    
    # Raw Texts (Full Description)
    description_raw         = Column(Text)
    how_to_use_raw          = Column(Text)
    ingredients             = Column(Text)
    
    # JSON Nested
    variants                = Column(JSON)
    reviews                 = Column(JSON)
    
    dibuat_pada             = Column(DateTime, default=datetime.utcnow)
 
    marketplace_products = relationship("Produk", back_populates="referensi", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("brand", "product_name", name="uq_sociolla_brand_product"),
    )

    def __repr__(self):
        return f"<SociollaReferensi {self.brand} — {self.product_name[:40]}>"


class HasilPencarian(Base):
    """Menyimpan metadata tiap sesi pencarian per platform."""
    __tablename__ = "hasil_pencarian"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    platform        = Column(String(20), nullable=False)  # 'tokopedia' | 'lazada'
    keyword         = Column(String(500), nullable=False)
    total_data      = Column(Integer)      # total produk di marketplace untuk keyword ini
    jumlah_produk   = Column(Integer)      # produk yang berhasil diambil
    jumlah_toko     = Column(Integer)      # toko unik yang ditemukan
    dicari_pada     = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Pencarian [{self.platform}] '{self.keyword}' — {self.jumlah_produk} produk>"