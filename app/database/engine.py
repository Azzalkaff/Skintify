"""
database.py — Engine, Session, dan fungsi simpan ke DB
Mendukung multi-platform: Tokopedia & Lazada
"""

import sys
import codecs

# Fix UnicodeEncodeError on Windows / PyInstaller executables when printing emojis
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach(), errors="backslashreplace")
        except Exception:
            pass

if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach(), errors="backslashreplace")
        except Exception:
            pass

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

from app.database.models import Base, Toko, Produk, HasilPencarian, SociollaReferensi, User, Routine, RoutineItem

load_dotenv()

# ── Algoritma Similarity Matching (Pencegahan Duplikasi & Mismatch) ──

def hitung_kemiripan(scraped_name: str, brand: str, ref_name: str):
    """
    Menghitung kecocokan produk dari Tokopedia/Lazada dengan referensi Sociolla.
    Mengembalikan (overlap_score, is_match).
    """
    def clean_str(s: str) -> str:
        if not s: return ""
        s = s.lower()
        # Hapus tanda kutip & strip tanda baca untuk penanganan A'pieu -> apieu
        s = s.replace("'", "").replace("-", "")
        import re
        s = re.sub(r'[^a-z0-9\s]', ' ', s)
        return " ".join(s.split())

    cleaned_scraped = clean_str(scraped_name)
    cleaned_brand = clean_str(brand)
    cleaned_ref = clean_str(ref_name)

    if not cleaned_scraped or not cleaned_brand:
        return 0.0, False

    # 1. Cek Brand (Substring check)
    # Hapus semua spasi untuk perbandingan brand rapat, contoh: 'rose all day' -> 'roseallday'
    brand_flat = cleaned_brand.replace(" ", "")
    scraped_flat = cleaned_scraped.replace(" ", "")
    
    brand_match = brand_flat in scraped_flat
    
    if not brand_match:
        # Cek kata brand penting (panjang > 2, bukan kata generik)
        brand_words = [w for w in cleaned_brand.split() if len(w) > 2]
        generic_words = {"cosmetics", "beauty", "official", "store", "indonesia"}
        important_brand_words = [w for w in brand_words if w not in generic_words]
        if not important_brand_words:
            important_brand_words = brand_words
            
        for bw in important_brand_words:
            if bw in cleaned_scraped.split():
                brand_match = True
                break

    # 2. Cek Kesamaan Kata Kunci Produk (Word Overlap)
    ref_words = [w for w in cleaned_ref.split() if len(w) > 2]
    if not ref_words:
        ref_words = cleaned_ref.split()

    # Kata generik skincare yang diabaikan dalam pembobotan produk
    generic_ref_words = {"skin", "skincare", "care", "original", "bpom", "promo", "murah", "gel", "cream", "ml", "pcs"}
    important_ref_words = [w for w in ref_words if w not in generic_ref_words]
    if not important_ref_words:
        important_ref_words = ref_words

    scraped_words_set = set(cleaned_scraped.split())
    matches = sum(1 for w in important_ref_words if w in scraped_words_set)
    
    overlap_score = (matches / len(important_ref_words)) * 100 if important_ref_words else 0.0

    # Kriteria Match: brand harus cocok, dan minimal 40% kata penting cocok ATAU minimal ada 2 kata penting yang sama
    is_match = brand_match and (overlap_score >= 40.0 or matches >= 2)
    
    # Jika nama produk asli sangat pendek (hanya 1 kata penting), toleransi penuh asal brand cocok & ada kata tersebut
    if len(important_ref_words) == 1 and matches == 1:
        is_match = brand_match

    return overlap_score, is_match


# ── Engine & Session ──────────────────────────────────────────────────────────

def buat_engine():
    url = os.getenv("DATABASE_URL", "")
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    if not url:
        db_path = os.path.join(base_dir, "data", "db", "tokopedia.db")
        url = f"sqlite:///{db_path}"
    elif url.startswith("sqlite:///"):
        db_path_raw = url.replace("sqlite:///", "")
        if not os.path.isabs(db_path_raw):
            db_path = os.path.join(base_dir, db_path_raw)
            url = f"sqlite:///{db_path}"

    # Buat folder jika belum ada
    if url.startswith("sqlite:///"):
        db_path_to_create = url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(os.path.abspath(db_path_to_create)), exist_ok=True)

    if url.startswith("sqlite"):
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            """
            Konfigurasi SQLite per-connection untuk performa maksimal:

            WAL mode    — Write-Ahead Logging: reader & writer tidak saling blokir.
                          Menghilangkan 'database is locked' saat scraping berjalan.
            cache_size  — 64MB page cache in-memory. Query yang sama berulang tidak
                          baca disk lagi.
            synchronous — NORMAL: fsync hanya saat checkpoint WAL, bukan tiap commit.
                          Masih aman dari korupsi, tapi jauh lebih cepat dari FULL.
            temp_store  — Tabel temporary (ORDER BY, GROUP BY) disimpan di RAM,
                          bukan file disk sementara.
            mmap_size   — Memory-mapped I/O 256MB: OS langsung baca file via virtual
                          memory tanpa syscall read() per blok.
            """
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA cache_size=-65536")    # 64MB page cache
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
            cursor.execute("PRAGMA busy_timeout=15000")   # 15s timeout (mengganti timeout connect_args)
            cursor.close()

        from sqlalchemy import event
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False}
        )
        event.listen(engine, "connect", _set_sqlite_pragma)
        return engine

    return create_engine(url)


engine       = buat_engine()
SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,   # Cegah lazy-load query setelah commit
    autoflush=False,          # Flush manual, bukan otomatis setiap query
)


def init_db():
    """Buat semua tabel jika belum ada + jalankan migrasi kolom baru + buat indexes."""
    Base.metadata.create_all(bind=engine)

    # ── Migrasi: Tambah kolom 'role' ke tabel 'users' jika belum ada ──────────
    import sqlite3
    db_path = str(engine.url).replace("sqlite:///", "")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Migrasi kolom 'role'
            cursor.execute("PRAGMA table_info(users)")
            kolom = [info[1] for info in cursor.fetchall()]
            if 'role' not in kolom:
                cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
                conn.commit()
                print("✅ Migrasi: Kolom 'role' ditambahkan ke tabel 'users'.")

            # ── Indexes untuk query yang sering dipanggil ───────────────────────────
            # SociollaReferensi — tabel utama pencarian produk
            indexes = [
                # Filter & sort pada pencarian produk
                "CREATE INDEX IF NOT EXISTS idx_sociolla_category     ON sociolla_referensi (category)",
                "CREATE INDEX IF NOT EXISTS idx_sociolla_brand         ON sociolla_referensi (brand)",
                "CREATE INDEX IF NOT EXISTS idx_sociolla_rating        ON sociolla_referensi (rating_sociolla DESC)",
                "CREATE INDEX IF NOT EXISTS idx_sociolla_price         ON sociolla_referensi (min_price)",
                # Composite index: category + rating (pola filter paling umum)
                "CREATE INDEX IF NOT EXISTS idx_sociolla_cat_rating    ON sociolla_referensi (category, rating_sociolla DESC)",
                # Search by product name & brand (LIKE %keyword% tidak pakai index,
                # tapi prefix search bisa memanfaatkan ini untuk ORDER BY)
                "CREATE INDEX IF NOT EXISTS idx_sociolla_name          ON sociolla_referensi (product_name)",
                # Produk marketplace — lookup by referensi_id (JOIN paling sering)
                "CREATE INDEX IF NOT EXISTS idx_produk_ref_id          ON produk (referensi_id)",
                "CREATE INDEX IF NOT EXISTS idx_produk_ref_platform    ON produk (referensi_id, platform)",
                "CREATE INDEX IF NOT EXISTS idx_produk_platform_harga  ON produk (platform, harga ASC)",
                # User lookup
                "CREATE INDEX IF NOT EXISTS idx_users_email            ON users (email)",
                # Routine lookup by user
                "CREATE INDEX IF NOT EXISTS idx_routine_user           ON routines (user_id)",
                "CREATE INDEX IF NOT EXISTS idx_routine_item_routine   ON routine_items (routine_id)",
            ]
            for idx_sql in indexes:
                try:
                    cursor.execute(idx_sql)
                except Exception as _ie:
                    pass  # Index mungkin sudah ada atau tabel belum ada
            conn.commit()
            print("✅ Database indexes siap.")

    except Exception as e:
        print(f"⚠️ Migrasi/Index gagal (mungkin bukan SQLite): {e}")

    print("Database siap.")


# ── Normalisasi dict scraper → format unified ─────────────────────────────────

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
            "kota":        raw.get("kota") or raw.get("city") or "",
            "tier":        None,
            "is_official": raw.get("is_lazmall") if raw.get("is_lazmall") is not None else raw.get("is_official", False),
            "url":         raw.get("url", ""),
        }
    elif platform == "shopee":
        return {
            "platform":    "shopee",
            "shop_id":     str(raw.get("shop_id", "")),
            "nama":        raw.get("name") or raw.get("nama", ""),
            "kota":        raw.get("city") or raw.get("kota", ""),
            "tier":        None,
            "is_official": bool(raw.get("is_official", False)),
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
    elif platform == "shopee":
        return {
            "platform":      "shopee",
            "product_id":    str(p_id) if p_id else "",
            "shop_id":       str(s_id) if s_id else "",
            "keyword":       kw,
            "nama":          name,
            "url":           raw.get("url", ""),
            "gambar":        img,
            "harga":         float(raw.get("price", 0.0) or 0.0),
            "harga_teks":    "",
            "harga_asli":    float(raw.get("price_original", 0.0) or 0.0),
            "diskon_persen": int(raw.get("discount", 0) or 0),
            "rating":        float(raw.get("rating", 0.0) or 0.0),
            "jumlah_review": 0,
            "terjual":       int(raw.get("sold", 0) or 0),
            "kategori":      None,
            "label_badge":   None,
            "free_ongkir":   None,
            "in_stock":      None,
            "is_sponsored":  None,
        }
    else:
        raise ValueError(f"Platform tidak dikenal: {platform}")


# ── Fungsi simpan utama ───────────────────────────────────────────────────────

def simpan_hasil(
    session:      Session,
    platform:     str,
    keyword:      str,
    produk_list:  list,
    toko_list:    list,
    total_data:   int,
    referensi_id: int = None,
):
    """
    Simpan toko + produk ke database untuk platform tertentu.
    Skip duplikat (unique constraint per platform+shop_id / platform+product_id+keyword).

    platform: 'tokopedia' | 'lazada'
    """

    # 1. Normalisasi semua dict ke format unified
    # Suntikkan keyword ke setiap produk jika belum ada
    for p in produk_list:
        if "keyword" not in p:
            p["keyword"] = keyword

    toko_norm   = [_normalize_toko(platform, t)   for t in toko_list]
    produk_norm = [_normalize_produk(platform, p) for p in produk_list]

    # Ambil data referensi asli untuk validasi kemiripan
    ref = None
    if referensi_id:
        ref = session.query(SociollaReferensi).filter_by(id=referensi_id).first()

    # 2. Simpan / ambil toko dari DB
    toko_map_db = {}   # shop_id → Toko ORM object
    for t in toko_norm:
        toko_db = (
            session.query(Toko)
            .filter_by(platform=t["platform"], shop_id=t["shop_id"])
            .first()
        )
        if not toko_db:
            toko_db = Toko(
                platform    = t["platform"],
                shop_id     = t["shop_id"],
                nama        = t["nama"],
                kota        = t["kota"],
                tier        = t["tier"],
                is_official = t["is_official"],
                url         = t["url"],
            )
            session.add(toko_db)
            session.flush()   # dapat id sebelum commit
        toko_map_db[t["shop_id"]] = toko_db

    # 3. Simpan produk — skip duplikat dan skip salah sasaran (mismatch)
    baru, lewati, salah_sasaran = 0, 0, 0
    for p in produk_norm:
        # Cek duplikat di DB terlebih dahulu
        ada = (
            session.query(Produk)
            .filter_by(
                platform   = p["platform"],
                product_id = p["product_id"],
                keyword    = p["keyword"],
            )
            .first()
        )
        if ada:
            # Jika sudah ada di DB, update harga & referensi_id terupdate
            ada.harga = p["harga"]
            ada.harga_asli = p["harga_asli"]
            ada.diskon_persen = p["diskon_persen"]
            ada.terjual = p["terjual"]
            ada.rating = p["rating"]
            ada.jumlah_review = p["jumlah_review"]
            if referensi_id and ada.referensi_id is None:
                ada.referensi_id = referensi_id
            session.add(ada)
            lewati += 1
            continue

        # ── VALIDASI KEMIRIPAN (ANTI-MISMATCH & TRANSPARANSI) ──
        if ref:
            score, is_match = hitung_kemiripan(p["nama"], ref.brand, ref.product_name)
            if not is_match:
                print(f"   [Mismatch] Menyaring '{p['nama'][:45]}...' (Brand: '{ref.brand}', Score: {score:.1f}%)")
                salah_sasaran += 1
                continue

        toko_db = toko_map_db.get(p["shop_id"])
        produk_db = Produk(
            platform      = p["platform"],
            product_id    = p["product_id"],
            keyword       = p["keyword"],
            nama          = p["nama"],
            url           = p["url"],
            gambar        = p["gambar"],
            harga         = p["harga"],
            harga_teks    = p["harga_teks"],
            harga_asli    = p["harga_asli"],
            diskon_persen = p["diskon_persen"],
            rating        = p["rating"],
            jumlah_review = p["jumlah_review"],
            terjual       = p["terjual"],
            kategori      = p["kategori"],
            label_badge   = p["label_badge"],
            free_ongkir   = p["free_ongkir"],
            in_stock      = p["in_stock"],
            is_sponsored  = p["is_sponsored"],
            toko          = toko_db,
            referensi_id  = referensi_id,
        )
        session.add(produk_db)
        baru += 1

    # 4. Catat metadata sesi pencarian
    sesi = HasilPencarian(
        platform      = platform,
        keyword       = keyword,
        total_data    = total_data,
        jumlah_produk = len(produk_list) - salah_sasaran,
        jumlah_toko   = len(toko_list),
    )
    session.add(sesi)
    session.commit()

    msg = f"   [Saved] [{platform}] Disimpan: {baru} produk baru, {lewati} dilewati (duplikat)"
    if salah_sasaran > 0:
        msg += f", {salah_sasaran} disaring (mismatch)"
    print(msg)


# ── Simpan referensi Sociolla ─────────────────────────────────────────────────

def simpan_sociolla_referensi(session: Session, produk_list: list):
    """
    Simpan daftar produk Sociolla sebagai referensi keyword ke DB.
    Skip jika sudah ada (brand + product_name).
    """
    baru = 0
    for p in produk_list:
        ada = (
            session.query(SociollaReferensi)
            .filter_by(brand=p["brand"], product_name=p["product_name"])
            .first()
        )
        if ada:
            continue

        ref = SociollaReferensi(
            product_name         = p["product_name"],
            brand                = p["brand"],
            keyword_digunakan    = p.get("keyword_digunakan", ""),
            category             = p.get("category", ""),
            min_price            = p.get("min_price", 0),
            max_price            = p.get("max_price", 0),
            harga_setelah_diskon = p.get("min_price_after_discount"),
            diskon               = p.get("discount_range"),
            rating_sociolla      = p.get("average_rating", 0),
            total_reviews        = p.get("total_reviews", 0),
            url_sociolla         = p.get("url", ""),
            is_in_stock          = p.get("is_in_stock", True),
        )
        session.add(ref)
        baru += 1

    session.commit()
    print(f"   📚 Referensi Sociolla: {baru} produk baru disimpan ke DB")


def tandai_sudah_di_scrape(session: Session, brand: str, product_name: str):
    """Update flag sudah_di_scrape = True setelah scraping selesai."""
    ref = (
        session.query(SociollaReferensi)
        .filter_by(brand=brand, product_name=product_name)
        .first()
    )
    if ref:
        ref.sudah_di_scrape = True
        session.commit()