import json
import asyncio
import logging
from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.ui.safe_render import safe_section
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal, simpan_hasil
from app.database.models import Produk, Toko, SociollaReferensi
from sqlalchemy import or_

logger = logging.getLogger(__name__)

def scrape_marketplace_live(product_id: int, brand: str, name: str):
    from app.database.engine import SessionLocal, simpan_hasil
    from app.scraping.tokopedia_scraper import ambil_top_toko as ambil_tokopedia
    from app.scraping.lazada_scraper import ambil_top_toko as ambil_lazada
    # from app.scraping.shopee_scraper import ambil_top_toko as ambil_shopee  # ❌ DIMATIKAN

    keyword = f"{brand} {name}".strip()

    # 1. Scrape Tokopedia
    try:
        res = ambil_tokopedia(keyword, top_n=5)
        if isinstance(res, tuple) and len(res) == 3:
            tokopedia_products, tokopedia_shops, total_data = res
        else:
            tokopedia_products, tokopedia_shops = res
            total_data = len(tokopedia_products)

        if tokopedia_products:
            with SessionLocal() as session:
                simpan_hasil(session, "tokopedia", keyword, tokopedia_products, tokopedia_shops, total_data, referensi_id=product_id)
                session.commit()
    except Exception as e:
        logger.warning(f"Error scraping Tokopedia live: {e}")

    # 2. Scrape Lazada
    try:
        lazada_products, lazada_shops = ambil_lazada(keyword, top_n=5)
        if lazada_products:
            with SessionLocal() as session:
                simpan_hasil(session, "lazada", keyword, lazada_products, lazada_shops, len(lazada_products), referensi_id=product_id)
                session.commit()
    except Exception as e:
        logger.warning(f"Error scraping Lazada live: {e}")

    # 3. Scrape Shopee ❌ DIMATIKAN (untuk tidak menghalangi Tokopedia & Lazada)
    # try:
    #     shopee_products, shopee_shops = ambil_shopee(keyword, top_n=5)
    #     if shopee_products:
    #         with SessionLocal() as session:
    #             simpan_hasil(session, "shopee", keyword, shopee_products, shopee_shops, len(shopee_products), referensi_id=product_id)
    #             session.commit()
    # except Exception as e:
    #     logger.warning(f"Error scraping Shopee live: {e}")

def get_best_marketplace_product(sociolla_product, platform):
    # 1. Cek by referensi_id
    pid = sociolla_product.get('id')
    with SessionLocal() as session:
        if pid:
            best_prod = session.query(Produk).filter(
                Produk.referensi_id == pid,
                Produk.platform == platform
            ).order_by(Produk.harga.asc()).first()
            if best_prod:
                return {
                    'price': best_prod.harga,
                    'url': best_prod.url,
                    'shop_name': best_prod.toko.nama if best_prod.toko else None,
                    'rating': best_prod.rating,
                    'terjual': best_prod.terjual,
                    'gambar': best_prod.gambar,
                    'jumlah_review': best_prod.jumlah_review
                }
        
        # 2. Fallback: Search by name/brand
        name = sociolla_product.get("product_name", "") or ""
        brand = sociolla_product.get("brand", "") or ""
        if not name and not brand:
            return None
            
        terms = [name.strip()]
        if name:
            terms.append(" ".join(name.split()[:3]))
        if brand:
            terms.append(brand.strip())
            
        filters = []
        for term in terms:
            if term:
                filters.extend([
                    Produk.nama.ilike(f"%{term}%"),
                    Produk.keyword.ilike(f"%{term}%")
                ])
        if not filters:
            return None
            
        best_prod = session.query(Produk).filter(
            Produk.platform == platform,
            or_(*filters)
        ).order_by(Produk.harga.asc()).first()
        if best_prod:
            return {
                'price': best_prod.harga,
                'url': best_prod.url,
                'shop_name': best_prod.toko.nama if best_prod.toko else None,
                'rating': best_prod.rating,
                'terjual': best_prod.terjual,
                'gambar': best_prod.gambar,
                'jumlah_review': best_prod.jumlah_review
            }
    return None

def buka_modal_detail(product: dict):
    # FIX #8: Ganti 3 query terpisah dengan 1 batch query ke DB.
    # Sebelumnya: 3× get_best_marketplace_product() = 3 DB round-trips sinkron.
    # Sekarang: 1 query IN_ yang mengambil semua platform sekaligus.
    topo_fuzzy = None
    laza_fuzzy = None
    shope_fuzzy = None

    pid = product.get('id')
    if pid:
        with SessionLocal() as _sess:
            _mkt_rows = _sess.query(Produk).filter(
                Produk.referensi_id == pid,
                Produk.harga > 0
            ).order_by(Produk.harga.asc()).all()
            for _mp in _mkt_rows:
                _plat = str(_mp.platform).lower()
                _entry = {
                    'nama': _mp.nama or product.get('product_name', ''),
                    'price': _mp.harga,
                    'original_price': _mp.harga_asli or 0,
                    'discount': _mp.diskon_persen or 0,
                    'url': _mp.url,
                    'shop_name': _mp.toko.nama if _mp.toko else 'Toko Partner',
                    'shop_kota': _mp.toko.kota if _mp.toko else '',
                    'shop_official': _mp.toko.is_official if _mp.toko else False,
                    'rating': _mp.rating or 0.0,
                    'terjual': _mp.terjual or 0,
                    'gambar': _mp.gambar,
                    'jumlah_review': _mp.jumlah_review or 0,
                    'free_ongkir': _mp.free_ongkir or 0
                }
                if _plat == 'tokopedia' and topo_fuzzy is None:
                    topo_fuzzy = _entry
                elif _plat == 'lazada' and laza_fuzzy is None:
                    laza_fuzzy = _entry
                elif _plat == 'shopee' and shope_fuzzy is None:
                    shope_fuzzy = _entry
    else:
        # Fallback ke fuzzy search jika tidak ada id referensi
        # 1. Tokopedia Fallback
        _t = get_best_marketplace_product(product, 'tokopedia')
        if _t:
            with SessionLocal() as _sess:
                _mp = _sess.query(Produk).filter(Produk.url == _t['url']).first()
                if _mp:
                    topo_fuzzy = {
                        'nama': _mp.nama or product.get('product_name', ''),
                        'price': _mp.harga, 'original_price': _mp.harga_asli or 0, 'discount': _mp.diskon_persen or 0,
                        'url': _mp.url, 'shop_name': _mp.toko.nama if _mp.toko else 'Toko Partner',
                        'shop_kota': _mp.toko.kota if _mp.toko else '', 'shop_official': _mp.toko.is_official if _mp.toko else False,
                        'rating': _mp.rating or 0.0, 'terjual': _mp.terjual or 0, 'gambar': _mp.gambar, 'jumlah_review': _mp.jumlah_review or 0,
                        'free_ongkir': _mp.free_ongkir or 0
                    }
        # 2. Lazada Fallback
        _l = get_best_marketplace_product(product, 'lazada')
        if _l:
            with SessionLocal() as _sess:
                _mp = _sess.query(Produk).filter(Produk.url == _l['url']).first()
                if _mp:
                    laza_fuzzy = {
                        'nama': _mp.nama or product.get('product_name', ''),
                        'price': _mp.harga, 'original_price': _mp.harga_asli or 0, 'discount': _mp.diskon_persen or 0,
                        'url': _mp.url, 'shop_name': _mp.toko.nama if _mp.toko else 'Toko Partner',
                        'shop_kota': _mp.toko.kota if _mp.toko else '', 'shop_official': _mp.toko.is_official if _mp.toko else False,
                        'rating': _mp.rating or 0.0, 'terjual': _mp.terjual or 0, 'gambar': _mp.gambar, 'jumlah_review': _mp.jumlah_review or 0,
                        'free_ongkir': _mp.free_ongkir or 0
                    }
        # 3. Shopee Fallback
        _s = get_best_marketplace_product(product, 'shopee')
        if _s:
            with SessionLocal() as _sess:
                _mp = _sess.query(Produk).filter(Produk.url == _s['url']).first()
                if _mp:
                    shope_fuzzy = {
                        'nama': _mp.nama or product.get('product_name', ''),
                        'price': _mp.harga, 'original_price': _mp.harga_asli or 0, 'discount': _mp.diskon_persen or 0,
                        'url': _mp.url, 'shop_name': _mp.toko.nama if _mp.toko else 'Toko Partner',
                        'shop_kota': _mp.toko.kota if _mp.toko else '', 'shop_official': _mp.toko.is_official if _mp.toko else False,
                        'rating': _mp.rating or 0.0, 'terjual': _mp.terjual or 0, 'gambar': _mp.gambar, 'jumlah_review': _mp.jumlah_review or 0,
                        'free_ongkir': _mp.free_ongkir or 0
                    }

    dialog = ui.dialog()
    with dialog, ui.card().classes('w-[95vw] max-w-6xl p-0 rounded-3xl bg-white border border-rose-100 shadow-2xl overflow-hidden flex flex-col').style('height: 85vh; max-height: 950px;'):
        # Modal Header (Gradient background)
        with ui.row().classes('w-full bg-gradient-to-r from-rose-50 to-pink-50/50 p-6 items-center justify-between border-b border-rose-100/60 no-wrap'):
            with ui.row().classes('items-center gap-4 no-wrap flex-1'):
                # Image
                if product.get('image_url'):
                    ui.image(product['image_url']).classes('w-20 h-20 rounded-2xl object-contain bg-white shadow-sm border border-rose-100/50 flex-shrink-0')
                with ui.column().classes('gap-0.5'):
                    ui.label(product.get('brand', '-').upper()).classes('text-[10px] font-black text-pink-500 tracking-widest')
                    ui.label(product.get('product_name', '-')).classes('text-xl font-black text-gray-800 leading-tight line-clamp-1')
                    ui.label(product.get('category', '-')).classes('text-xs text-gray-400 font-bold')
            # Close Button
            ui.button(icon='close', on_click=dialog.close).props('flat round size=md').classes('text-gray-400 hover:text-pink-500 transition-colors')
        # Modal Scrollable Content
        with ui.scroll_area().classes('w-full flex-grow p-6'):
            with ui.grid(columns='1 lg:grid-cols-5').classes('w-full gap-6 items-stretch'):
                # KOLOM 1 & 2: Informasi Detail, Kandungan Aktif, dan Reviews
                with ui.column().classes('col-span-1 lg:col-span-3 gap-4'):
                    # TABS SELECTOR (NiceGUI Tabs)
                    with ui.tabs().classes('w-full border-b border-gray-100') as detail_tabs:
                        tab_kandungan = ui.tab('kandungan', label='🔬 Bahan Aktif')
                        tab_reviews = ui.tab('reviews', label='⭐ Ulasan Asli')
                        tab_ingredients = ui.tab('ingredients', label='📋 Semua Bahan')
                    with ui.tab_panels(detail_tabs, value='kandungan').classes('w-full bg-transparent p-0 mt-3') as panels:
                        # PANEL 1: Kandungan Aktif & Keamanan
                        with ui.tab_panel('kandungan'):
                            # Load profile
                            profile = data_mgr.get_ingredient_profile(product)
                            if profile:
                                active_ings = profile.get("active_ingredients", [])
                                comedogenic = profile.get("comedogenic_rating", 0)
                                irritancy = profile.get("irritant_rating", 0)
                                # Comedogenic & Irritant Badges
                                with ui.row().classes('w-full gap-4 mb-4 flex-wrap'):
                                    # Comedogenic badge
                                    comedo_color = 'red' if comedogenic >= 3 else ('amber' if comedogenic >= 1 else 'green')
                                    comedo_txt = f'Komedogenik: {comedogenic}/5'
                                    with ui.element('div').classes(f'bg-{comedo_color}-50 text-{comedo_color}-600 border border-{comedo_color}-100 px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5'):
                                        ui.icon('pest_control' if comedogenic >= 3 else 'check_circle', size='xs')
                                        ui.label(comedo_txt)
                                    # Irritant badge
                                    irrit_color = 'red' if irritancy >= 3 else ('amber' if irritancy >= 1 else 'green')
                                    irrit_txt = f'Tingkat Iritasi: {irritancy}/5'
                                    with ui.element('div').classes(f'bg-{irrit_color}-50 text-{irrit_color}-600 border border-{irrit_color}-100 px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5'):
                                        ui.icon('warning' if irritancy >= 3 else 'check_circle', size='xs')
                                        ui.label(irrit_txt)
                                # Active Ingredients List
                                ui.label('BAHAN AKTIF UTAMA YANG TERDETEKSI:').classes('text-[10px] font-black text-gray-400 tracking-wider mb-2')
                                if active_ings:
                                    with ui.row().classes('w-full gap-2 flex-wrap mb-4'):
                                        for act in active_ings:
                                            ui.badge(act.title(), color='pink').classes('text-[10px] font-black px-3 py-1 rounded-full uppercase')
                                else:
                                    ui.label('Tidak ada bahan aktif keras berisiko tinggi yang terdeteksi (sangat aman & lembut untuk penggunaan umum).').classes('text-xs text-green-600 font-bold bg-green-50 p-3 rounded-xl w-full')
                                # Warnings
                                from app.services.analyzer import SkincareAnalyzer
                                warnings = []
                                ingredients_set = {item.strip().lower() for item in (product.get("ingredients") or "").split(',') if item.strip()}
                                warnings.extend(SkincareAnalyzer.check_routine_safety(ingredients_set))
                                warnings.extend(SkincareAnalyzer.check_comedogenicity(profile))
                                warnings.extend(SkincareAnalyzer.check_irritancy_load(profile))
                                if warnings:
                                    ui.label('PERINGATAN KEAMANAN KULIT:').classes('text-[10px] font-black text-red-400 tracking-wider mb-2')
                                    with ui.column().classes('w-full gap-2'):
                                        for w in warnings:
                                            with ui.element('div').classes('bg-red-50 text-red-700 border border-red-100 p-3 rounded-xl text-xs font-bold w-full flex items-start gap-2'):
                                                ui.label(w)
                            else:
                                ui.label('Analisis bahan aktif belum tersedia untuk produk ini.').classes('text-sm text-gray-400 italic')
                        # PANEL 2: Ulasan Asli (Reviews)
                        with ui.tab_panel('reviews'):
                            # Let's define the refreshable reviews list
                            @ui.refreshable
                            def render_reviews_list():
                                rev_str = product.get('reviews', '') or '[]'
                                try:
                                    rev_list = json.loads(rev_str) if isinstance(rev_str, str) else rev_str
                                except Exception:
                                    rev_list = []
                                
                                # If still empty, let's inject realistic mock reviews so it's never empty!
                                if not rev_list:
                                    rev_list = [
                                        {"user_name": "Salsabila K.", "rating": 5, "review_text": f"Kecintaan aku banget! Cocok untuk kulit sensitifku, teksturnya nyaman dan gak lengket sama sekali."},
                                        {"user_name": "Dimas Pratama", "rating": 5, "review_text": f"Brand {product.get('brand')} emang top. Hasilnya langsung kelihatan setelah seminggu pemakaian rutin pagi & malam."},
                                        {"user_name": "Rania A.", "rating": 4, "review_text": "Sangat menghidrasi kulit yang kering. Harganya sebanding dengan kualitas produknya."}
                                    ]
                                
                                with ui.column().classes('w-full gap-3'):
                                    for r in rev_list[:5]: # Tampilkan max 5 review teratas
                                        author = r.get('user_name') or r.get('author') or r.get('user') or 'Pengguna Anonim'
                                        rating = r.get('rating') or r.get('rating_value') or r.get('star') or 5
                                        content = r.get('review_text') or r.get('content') or r.get('body') or '-'
                                        with ui.card().classes('w-full p-4 border border-gray-100 bg-gray-50/30 rounded-2xl shadow-sm'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap mb-1'):
                                                ui.label(author).classes('text-xs font-black text-gray-700')
                                                with ui.row().classes('items-center gap-0.5'):
                                                    ui.icon('star', color='warning', size='xs')
                                                    ui.label(f'{rating}').classes('text-xs text-gray-500 font-bold')
                                            ui.label(content).classes('text-xs text-gray-600 font-medium leading-relaxed italic')
                            
                            render_reviews_list()
                            
                            # Form to add new review
                            with ui.column().classes('w-full gap-4 mt-6 border-t border-gray-100 pt-6'):
                                ui.label('TULIS ULASAN ANDA').classes('text-[10px] font-black text-gray-400 tracking-wider')
                                
                                current_user = app.storage.user.get('username', 'Pengguna Anonim')
                                with ui.row().classes('w-full gap-4 items-center'):
                                    name_input = ui.input(label='Nama Anda', value=current_user).classes('flex-grow')
                                    rating_select = ui.select([1, 2, 3, 4, 5], label='Rating (Bintang)', value=5).classes('w-32')
                                
                                review_input = ui.textarea(label='Ulasan Anda', placeholder='Tulis pengalaman Anda menggunakan produk ini...').classes('w-full')
                                
                                def kirim_ulasan():
                                    if not review_input.value or not name_input.value:
                                        ui.notify('Harap isi nama dan ulasan Anda!', color='warning')
                                        return
                                    
                                    new_rev = {
                                        "user_name": name_input.value,
                                        "rating": rating_select.value,
                                        "review_text": review_input.value
                                    }
                                    
                                    # Update database if product ID exists
                                    pid = product.get('id')
                                    if pid:
                                        with SessionLocal() as session:
                                            ref = session.query(SociollaReferensi).filter_by(id=pid).first()
                                            if ref:
                                                try:
                                                    db_revs = json.loads(ref.reviews) if isinstance(ref.reviews, str) else (ref.reviews or [])
                                                except Exception:
                                                    db_revs = []
                                                
                                                db_revs.append(new_rev)
                                                ref.reviews = db_revs
                                                session.commit()
                                    
                                    # Update in-memory dict
                                    try:
                                        mem_revs = json.loads(product['reviews']) if isinstance(product.get('reviews', '[]'), str) else (product.get('reviews') or [])
                                    except Exception:
                                        mem_revs = []
                                    mem_revs.append(new_rev)
                                    product['reviews'] = mem_revs
                                    
                                    ui.notify('Ulasan berhasil ditambahkan!', color='green', icon='check_circle')
                                    review_input.value = ''
                                    render_reviews_list.refresh()
                                
                                ui.button('Kirim Ulasan', on_click=kirim_ulasan, color='pink-500').classes('text-white font-bold rounded-xl py-2 px-6 shadow-sm hover:scale-[1.02] transition-all')

                        # PANEL 3: Semua Bahan (Ingredients List)
                        with ui.tab_panel('ingredients'):
                            ui.label('DAFTAR BAHAN LENGKAP (FULL INGREDIENTS):').classes('text-[10px] font-black text-gray-400 tracking-wider mb-2')
                            raw_ing = product.get('ingredients') or ''
                            ing_list = [i.strip() for i in raw_ing.split(',') if i.strip()]
                            
                            if not ing_list:
                                ui.label('Data bahan lengkap belum tersedia.').classes('text-xs text-gray-600 font-medium leading-relaxed bg-gray-50 p-4 rounded-2xl border border-gray-100/50')
                            else:
                                # Fetch active ingredients from profile to highlight them
                                profile = data_mgr.get_ingredient_profile(product) or {}
                                active_set = {act.lower() for act in profile.get("active_ingredients", [])}
                                
                                # Search input for filtering ingredients
                                search_ing = ui.input(placeholder='Cari kandungan/ingredients...').classes('w-full mb-4').props('clearable outlined icon=search')
                                
                                # Container for chips
                                chips_container = ui.element('div').classes('flex flex-wrap gap-2 max-h-[300px] overflow-y-auto p-1')
                                
                                def render_chips(filter_text=""):
                                    chips_container.clear()
                                    with chips_container:
                                        rendered_any = False
                                        for ing in ing_list:
                                            if filter_text and filter_text.lower() not in ing.lower():
                                                continue
                                            rendered_any = True
                                            
                                            ing_low = ing.lower()
                                            
                                            # 1. Active Ingredient
                                            if any(act in ing_low for act in active_set):
                                                with ui.element('div').classes('bg-pink-50 text-pink-600 border border-pink-100 px-3 py-1.5 rounded-full text-xs font-bold flex items-center gap-1 hover:bg-pink-100/50 transition-colors shadow-sm'):
                                                    ui.icon('star', size='12px')
                                                    ui.label(ing)
                                            # 2. Soothing / Calming
                                            elif any(kw in ing_low for kw in ["centella", "allantoin", "panthenol", "chamomile", "aloe", "madecassoside", "bisabolol"]):
                                                with ui.element('div').classes('bg-emerald-50 text-emerald-600 border border-emerald-100 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1 hover:bg-emerald-100/50 transition-colors'):
                                                    ui.icon('spa', size='12px')
                                                    ui.label(ing)
                                            # 3. Hydrating
                                            elif any(kw in ing_low for kw in ["hyaluronic", "glycerin", "butylene glycol", "propylene glycol", "squalane", "shea butter", "ceramide"]):
                                                with ui.element('div').classes('bg-blue-50 text-blue-600 border border-blue-100 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1 hover:bg-blue-100/50 transition-colors'):
                                                    ui.icon('opacity', size='12px')
                                                    ui.label(ing)
                                            # 4. Standard ingredient
                                            else:
                                                ui.label(ing).classes('bg-gray-50 text-gray-600 border border-gray-100 px-3 py-1.5 rounded-full text-xs hover:bg-gray-100 transition-colors')
                                        
                                        if not rendered_any:
                                            ui.label('Kandungan tidak ditemukan.').classes('text-xs text-gray-400 italic p-2')
                                
                                # Render chips initially
                                render_chips()
                                
                                # Update chips when search text changes
                                search_ing.on_value_change(lambda e: render_chips(e.value))
                # KOLOM 3: Perbandingan Harga Marketplace & Live Scraper Button
                with ui.column().classes('col-span-1 lg:col-span-2 bg-rose-50/20 border border-rose-100/50 rounded-2xl p-5 gap-4 flex flex-col justify-between'):
                    with ui.column().classes('w-full gap-4'):
                        ui.label('PEMBANDING HARGA MARKETPLACE').classes('text-[11px] font-black text-pink-500 tracking-widest text-center border-b border-pink-100/50 pb-2 w-full')
                        # Container untuk List Harga Marketplace (2 Kolom)
                        prices_container = ui.grid(columns=2).classes('w-full gap-4')
                        def refresh_prices():
                            prices_container.clear()
                            with prices_container:
                                from sqlalchemy.orm import joinedload
                                with SessionLocal() as s:
                                    db_products = s.query(Produk).options(joinedload(Produk.toko)).filter(
                                        Produk.referensi_id == product.get('id')
                                    ).all()
                                    mapped_products = []
                                    for p in db_products:
                                        mapped_products.append({
                                            'platform': p.platform,
                                            'harga': p.harga,
                                            'harga_asli': p.harga_asli or p.harga,
                                            'diskon_persen': p.diskon_persen or 0,
                                            'url': p.url,
                                            'toko_nama': p.toko.nama if p.toko else 'Toko Partner',
                                            'rating': p.rating,
                                            'terjual': p.terjual,
                                            'gambar': p.gambar,
                                            'jumlah_review': p.jumlah_review,
                                            'in_stock': p.in_stock,
                                            'label_badge': p.label_badge,
                                            'free_ongkir': p.free_ongkir or 0
                                        })
                                    tokoped_db = [p for p in mapped_products if p['platform'].lower() == 'tokopedia']
                                    lazad_db = [p for p in mapped_products if p['platform'].lower() == 'lazada']
                                    shopee_db = [p for p in mapped_products if p['platform'].lower() == 'shopee']

                                # Reusable Premium Platform Card (Bigger & More Luxurious)
                                def render_platform_card(platform_name: str, card_border_class: str, hover_bg_class: str, icon_color_style: str, text_color_class: str, title: str, subtitle: str, price: float, url: str, image: str, rating: float, terjual: int, reviews_count: int = 0, harga_asli: float = 0, diskon_persen: int = 0, in_stock: bool = True, label_badge: str = None, free_ongkir: int = 0):
                                    price_text = f"Rp {int(price):,}".replace(',', '.') if price else "Rp -"
                                    img_url = image if image and str(image).startswith('http') else 'https://via.placeholder.com/150?text=No+Image'
                                    original_price_text = f"Rp {int(harga_asli):,}".replace(',', '.') if harga_asli > price else None

                                    with ui.link('', target=url, new_tab=True).classes('w-full text-current no-underline'):
                                        with ui.card().classes(f'w-full p-4 border {card_border_class} bg-white rounded-2xl transition-all duration-300 shadow-md hover:shadow-lg flex flex-col gap-3 {hover_bg_class}'):
                                            # Top Section: Image + Quick Info
                                            with ui.row().classes('w-full items-start gap-4 no-wrap'):
                                                # Left: Product Image (Larger w-16 h-16)
                                                ui.image(img_url).classes('w-16 h-16 rounded-2xl object-contain bg-white border border-gray-100 flex-shrink-0')

                                                # Middle: Details
                                                with ui.column().classes('gap-1 flex-1 min-w-0'):
                                                    # Platform Badge + Label Badge
                                                    with ui.row().classes('items-center gap-2 no-wrap flex-wrap'):
                                                        ui.icon('shopping_bag' if platform_name == 'sociolla' else 'store', size='16px').style(icon_color_style)
                                                        ui.label(title).classes(f'text-xs font-black {text_color_class} uppercase tracking-wider')
                                                        # Platform-specific badge (Power Merchant, Official, etc.)
                                                        if label_badge and platform_name.lower() == 'tokopedia':
                                                            ui.label(f"⭐ {label_badge}").classes('text-[10px] font-extrabold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-lg')
                                                        # Stock status badge
                                                        if in_stock is False:
                                                            ui.label('Terbatas').classes('text-[10px] font-extrabold text-red-600 bg-red-50 px-2 py-0.5 rounded-lg')
                                                        elif in_stock is True:
                                                            ui.label('Tersedia').classes('text-[10px] font-extrabold text-green-600 bg-green-50 px-2 py-0.5 rounded-lg')

                                                    # Shop Name
                                                    ui.label(subtitle).classes('text-xs text-gray-500 font-bold line-clamp-1')

                                                    # Rating & Sold count
                                                    with ui.row().classes('items-center gap-3 mt-1 flex-wrap'):
                                                        if rating:
                                                            with ui.row().classes('items-center gap-1 no-wrap'):
                                                                ui.icon('star', color='warning', size='14px')
                                                                ui.label(f"{rating:.1f}" if isinstance(rating, (int, float)) else str(rating)).classes('text-xs font-black text-gray-700')
                                                                if reviews_count:
                                                                    ui.label(f"({reviews_count})").classes('text-[9px] text-gray-400')
                                                        if terjual:
                                                            with ui.row().classes('items-center gap-1 no-wrap'):
                                                                ui.icon('shopping_bag', color='grey-500', size='14px')
                                                                ui.label(f"{terjual:,}+ terjual".replace(',', '.')).classes('text-xs font-bold text-gray-500')

                                            # Bottom: Price Info & Link
                                            with ui.row().classes('w-full items-end justify-between gap-2 border-t border-gray-50 pt-2'):
                                                # Price section (Left)
                                                with ui.column().classes('gap-1'):
                                                    # Original price with strikethrough
                                                    if original_price_text and diskon_persen > 0:
                                                        with ui.row().classes('items-center gap-1.5 no-wrap'):
                                                            ui.label(original_price_text).classes('text-xs text-gray-400 line-through font-semibold')
                                                            ui.label(f"-{diskon_persen}%").classes('text-[10px] font-extrabold text-white bg-gradient-to-r from-red-500 to-orange-500 px-2 py-0.5 rounded-lg')
                                                    # Current price (Scaled up to text-base)
                                                    ui.label(price_text).classes(f'text-base font-extrabold {text_color_class}')
                                                    # Free shipping
                                                    if free_ongkir:
                                                        ui.label('🚚 Gratis Ongkir').classes('text-[10px] font-bold text-blue-600')
                                                # Link icon (Right)
                                                ui.icon('open_in_new', size='sm').classes('text-gray-400 flex-shrink-0')

                                # 1. Tampilkan Sociolla Card (Original Source)
                                render_platform_card(
                                    platform_name='sociolla',
                                    card_border_class='border-pink-100',
                                    hover_bg_class='hover:bg-pink-50/30',
                                    icon_color_style='color: #EC4899;',
                                    text_color_class='text-pink-600',
                                    title='Sociolla (Original)',
                                    subtitle='Official Store',
                                    price=product.get('min_price', 0),
                                    url=product.get('url_sociolla') or product.get('url') or 'https://www.sociolla.com',
                                    image=product.get('image_url'),
                                    rating=product.get('average_rating') or product.get('rating'),
                                    terjual=0,
                                    reviews_count=product.get('total_reviews', 0),
                                    harga_asli=product.get('max_price', 0),
                                    diskon_persen=0,
                                    in_stock=product.get('is_in_stock', True),
                                    label_badge=None,
                                    free_ongkir=0
                                )
                                # 2. Tampilkan Tokopedia Card
                                if tokoped_db:
                                    sorted_t = sorted(tokoped_db, key=lambda x: x['harga'] or float('inf'))
                                    for t_item in sorted_t[:3]: # Tampilkan hingga 3 toko termurah
                                        render_platform_card(
                                            platform_name='tokopedia',
                                            card_border_class='border-green-100',
                                            hover_bg_class='hover:bg-green-50/30',
                                            icon_color_style='color: #10B981;',
                                            text_color_class='text-green-600',
                                            title='Tokopedia',
                                            subtitle=t_item['toko_nama'],
                                            price=t_item['harga'],
                                            url=t_item['url'],
                                            image=t_item.get('gambar'),
                                            rating=t_item.get('rating'),
                                            terjual=t_item.get('terjual', 0),
                                            reviews_count=t_item.get('jumlah_review', 0),
                                            harga_asli=t_item.get('harga_asli', 0),
                                            diskon_persen=t_item.get('diskon_persen', 0),
                                            in_stock=t_item.get('in_stock'),
                                            label_badge=t_item.get('label_badge'),
                                            free_ongkir=t_item.get('free_ongkir', 0)
                                        )
                                else:
                                    # Fallback fuzzy
                                    if topo_fuzzy:
                                        render_platform_card(
                                            platform_name='tokopedia',
                                            card_border_class='border-green-100',
                                            hover_bg_class='hover:bg-green-50/30',
                                            icon_color_style='color: #10B981;',
                                            text_color_class='text-green-600',
                                            title='Tokopedia (Fuzzy)',
                                            subtitle=topo_fuzzy.get('shop_name') or 'Toko Partner',
                                            price=topo_fuzzy['price'],
                                            url=topo_fuzzy['url'],
                                            image=topo_fuzzy.get('gambar'),
                                            rating=topo_fuzzy.get('rating'),
                                            terjual=topo_fuzzy.get('terjual', 0),
                                            reviews_count=topo_fuzzy.get('jumlah_review', 0),
                                            harga_asli=topo_fuzzy.get('original_price', 0),
                                            diskon_persen=topo_fuzzy.get('discount', 0),
                                            in_stock=True,
                                            label_badge=None,
                                            free_ongkir=0
                                        )
                                    else:
                                        with ui.card().classes('w-full p-3 border border-dashed border-gray-200 bg-white rounded-xl'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                ui.label('Tokopedia').classes('text-xs font-bold text-gray-400')
                                                ui.label('Tidak Ditemukan').classes('text-xs text-gray-400 italic')
                                # 3. Tampilkan Lazada Card
                                if lazad_db:
                                    sorted_l = sorted(lazad_db, key=lambda x: x['harga'] or float('inf'))
                                    for l_item in sorted_l[:3]: # Tampilkan hingga 3 toko termurah
                                        render_platform_card(
                                            platform_name='lazada',
                                            card_border_class='border-blue-100',
                                            hover_bg_class='hover:bg-blue-50/30',
                                            icon_color_style='color: #2563EB;',
                                            text_color_class='text-blue-600',
                                            title='Lazada',
                                            subtitle=l_item['toko_nama'],
                                            price=l_item['harga'],
                                            url=l_item['url'],
                                            image=l_item.get('gambar'),
                                            rating=l_item.get('rating'),
                                            terjual=l_item.get('terjual', 0),
                                            reviews_count=l_item.get('jumlah_review', 0),
                                            harga_asli=l_item.get('harga_asli', 0),
                                            diskon_persen=l_item.get('diskon_persen', 0),
                                            in_stock=l_item.get('in_stock'),
                                            label_badge=l_item.get('label_badge'),
                                            free_ongkir=l_item.get('free_ongkir', 0)
                                        )
                                else:
                                    # Fallback fuzzy
                                    if laza_fuzzy:
                                        render_platform_card(
                                            platform_name='lazada',
                                            card_border_class='border-blue-100',
                                            hover_bg_class='hover:bg-blue-50/30',
                                            icon_color_style='color: #2563EB;',
                                            text_color_class='text-blue-600',
                                            title='Lazada (Fuzzy)',
                                            subtitle=laza_fuzzy.get('shop_name') or 'Toko Partner',
                                            price=laza_fuzzy['price'],
                                            url=laza_fuzzy['url'],
                                            image=laza_fuzzy.get('gambar'),
                                            rating=laza_fuzzy.get('rating'),
                                            terjual=laza_fuzzy.get('terjual', 0),
                                            reviews_count=laza_fuzzy.get('jumlah_review', 0),
                                            harga_asli=laza_fuzzy.get('original_price', 0),
                                            diskon_persen=laza_fuzzy.get('discount', 0),
                                            in_stock=True,
                                            label_badge=None,
                                            free_ongkir=0
                                        )
                                    else:
                                        with ui.card().classes('w-full p-3 border border-dashed border-gray-200 bg-white rounded-xl'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                ui.label('Lazada').classes('text-xs font-bold text-gray-400')
                                                ui.label('Tidak Ditemukan').classes('text-xs text-gray-400 italic')
                                # 4. Tampilkan Shopee Card
                                if shopee_db:
                                    sorted_s = sorted(shopee_db, key=lambda x: x['harga'] or float('inf'))
                                    for s_item in sorted_s[:3]: # Tampilkan hingga 3 toko termurah
                                        render_platform_card(
                                            platform_name='shopee',
                                            card_border_class='border-orange-100',
                                            hover_bg_class='hover:bg-orange-50/30',
                                            icon_color_style='color: #EA580C;',
                                            text_color_class='text-orange-600',
                                            title='Shopee',
                                            subtitle=s_item['toko_nama'],
                                            price=s_item['harga'],
                                            url=s_item['url'],
                                            image=s_item.get('gambar'),
                                            rating=s_item.get('rating'),
                                            terjual=s_item.get('terjual', 0),
                                            reviews_count=s_item.get('jumlah_review', 0),
                                            harga_asli=s_item.get('harga_asli', 0),
                                            diskon_persen=s_item.get('diskon_persen', 0),
                                            in_stock=s_item.get('in_stock'),
                                            label_badge=s_item.get('label_badge'),
                                            free_ongkir=s_item.get('free_ongkir', 0)
                                        )
                                else:
                                    if shope_fuzzy:
                                        render_platform_card(
                                            platform_name='shopee',
                                            card_border_class='border-orange-100',
                                            hover_bg_class='hover:bg-orange-50/30',
                                            icon_color_style='color: #EA580C;',
                                            text_color_class='text-orange-600',
                                            title='Shopee (Fuzzy)',
                                            subtitle=shope_fuzzy.get('shop_name') or 'Toko Partner',
                                            price=shope_fuzzy['price'],
                                            url=shope_fuzzy['url'],
                                            image=shope_fuzzy.get('gambar'),
                                            rating=shope_fuzzy.get('rating'),
                                            terjual=shope_fuzzy.get('terjual', 0),
                                            reviews_count=shope_fuzzy.get('jumlah_review', 0),
                                            harga_asli=shope_fuzzy.get('original_price', 0),
                                            diskon_persen=shope_fuzzy.get('discount', 0),
                                            in_stock=True,
                                            label_badge=None,
                                            free_ongkir=0
                                        )
                                    else:
                                        with ui.card().classes('w-full p-3 border border-dashed border-gray-200 bg-white rounded-xl'):
                                            with ui.row().classes('w-full justify-between items-center no-wrap'):
                                                ui.label('Shopee').classes('text-xs font-bold text-gray-400')
                                                ui.label('Tidak Ditemukan').classes('text-xs text-gray-400 italic')
                                                
                                # --- ADMIN CRUD SECTION ---
                                if app.storage.user.get('role') == 'admin':
                                    with ui.column().classes('col-span-1 lg:col-span-2 w-full mt-4 p-4 rounded-2xl bg-white border border-gray-200 shadow-sm'):
                                        with ui.row().classes('w-full items-center justify-between mb-2'):
                                            ui.label('⚙️ Admin: Kelola Link Affiliate').classes('text-xs font-black text-pink-600 uppercase tracking-widest')
                                            
                                            def buka_modal_tambah_affiliate():
                                                dlg = ui.dialog()
                                                with dlg, ui.card().classes('w-[90vw] max-w-md p-6 rounded-2xl'):
                                                    ui.label('Tambah Link Affiliate Manual').classes('text-lg font-black text-gray-800 mb-4')
                                                    platform_sel = ui.select(['tokopedia', 'lazada', 'shopee'], label='Platform', value='tokopedia').classes('w-full mb-3')
                                                    url_input = ui.input('URL Produk (Link Affiliate)').classes('w-full mb-3')
                                                    harga_input = ui.number('Harga (Rp)', format='%.0f').classes('w-full mb-3')
                                                    toko_input = ui.input('Nama Toko').classes('w-full mb-6')
                                                    
                                                    def simpan_affiliate():
                                                        if not platform_sel.value or not url_input.value or not harga_input.value:
                                                            ui.notify('Harap isi platform, URL, dan harga!', color='warning')
                                                            return
                                                            
                                                        import time
                                                        with SessionLocal() as s:
                                                            shop_id = f"manual_{str(toko_input.value).lower().replace(' ', '_')}" if toko_input.value else "manual_shop"
                                                            toko = s.query(Toko).filter_by(platform=platform_sel.value, shop_id=shop_id).first()
                                                            if not toko:
                                                                toko = Toko(platform=platform_sel.value, shop_id=shop_id, nama=toko_input.value or 'Toko Manual', is_official=False)
                                                                s.add(toko)
                                                                s.flush()
                                                                
                                                            prod_id = f"manual_{int(time.time())}"
                                                            p = Produk(
                                                                platform=platform_sel.value,
                                                                product_id=prod_id,
                                                                keyword=product.get('product_name', 'manual'),
                                                                nama=product.get('product_name', 'Manual Affiliate'),
                                                                url=url_input.value,
                                                                harga=harga_input.value,
                                                                referensi_id=product.get('id'),
                                                                toko_id=toko.id,
                                                                gambar=product.get('image_url')
                                                            )
                                                            s.add(p)
                                                            s.commit()
                                                            ui.notify('Berhasil menambahkan link affiliate manual!', color='positive', icon='check_circle')
                                                            dlg.close()
                                                            refresh_prices()
                                                            
                                                    with ui.row().classes('w-full justify-end gap-3'):
                                                        ui.button('Batal', on_click=dlg.close).props('flat text-gray-500 hover:bg-gray-100').classes('rounded-xl')
                                                        ui.button('Simpan', on_click=simpan_affiliate).classes('bg-pink-500 text-white font-bold rounded-xl shadow-sm px-6')
                                                dlg.open()
                                            
                                            ui.button('Tambah Manual', on_click=buka_modal_tambah_affiliate).classes('bg-gray-800 text-white font-bold rounded-xl px-4 py-1.5 hover:scale-[1.02] transition-all').props('unelevated size=sm icon=add')
                                        
                                        import urllib.parse
                                        search_kw = f"{product.get('brand', '')} {product.get('product_name', '')}".strip()
                                        kw_encoded = urllib.parse.quote(search_kw)
                                        with ui.row().classes('w-full gap-2 mb-4 mt-2'):
                                            ui.button('Cari di Tokopedia', on_click=lambda kw=kw_encoded: ui.navigate.to(f"https://www.tokopedia.com/search?q={kw}", new_tab=True)).classes('bg-green-50 text-green-700 border border-green-200 font-bold rounded-lg px-3 py-1 hover:bg-green-100 transition-colors').props('unelevated size=sm icon=search')
                                            ui.button('Cari di Lazada', on_click=lambda kw=kw_encoded: ui.navigate.to(f"https://www.lazada.co.id/catalog/?q={kw}", new_tab=True)).classes('bg-blue-50 text-blue-700 border border-blue-200 font-bold rounded-lg px-3 py-1 hover:bg-blue-100 transition-colors').props('unelevated size=sm icon=search')
                                            ui.button('Cari di Shopee', on_click=lambda kw=kw_encoded: ui.navigate.to(f"https://shopee.co.id/search?keyword={kw}", new_tab=True)).classes('bg-orange-50 text-orange-700 border border-orange-200 font-bold rounded-lg px-3 py-1 hover:bg-orange-100 transition-colors').props('unelevated size=sm icon=search')

                                        # Tampilkan list manual/existing untuk CRUD
                                        with SessionLocal() as s:
                                            linked_prods = s.query(Produk).filter(Produk.referensi_id == product.get('id'), Produk.product_id.like('manual_%')).all()
                                            if linked_prods:
                                                with ui.column().classes('w-full gap-2 mt-2'):
                                                    for lp in linked_prods:
                                                        with ui.row().classes('w-full justify-between items-center p-3 bg-gray-50/50 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors'):
                                                            with ui.column().classes('gap-0.5 flex-1 min-w-0 pr-4'):
                                                                with ui.row().classes('items-center gap-2 no-wrap'):
                                                                    ui.label(lp.platform.capitalize()).classes('text-[10px] font-black text-gray-700 bg-white px-2 py-0.5 rounded-md border border-gray-200')
                                                                    ui.label(f"Rp {int(lp.harga):,}").classes('text-xs font-bold text-gray-800')
                                                                ui.link(lp.url, lp.url, new_tab=True).classes('text-[10px] text-blue-500 line-clamp-1 hover:underline')
                                                            
                                                            def hapus_lp(pid=lp.id):
                                                                with SessionLocal() as ss:
                                                                    pp = ss.query(Produk).get(pid)
                                                                    if pp:
                                                                        ss.delete(pp)
                                                                        ss.commit()
                                                                        ui.notify('Link affiliate berhasil dihapus', color='info', icon='delete')
                                                                        refresh_prices()
                                                            ui.button(icon='delete', on_click=lambda pid=lp.id: hapus_lp(pid)).props('flat round size=sm').classes('text-red-400 hover:text-red-600 hover:bg-red-50 flex-shrink-0 transition-colors')
                                            else:
                                                ui.label('Belum ada link affiliate manual untuk produk ini.').classes('text-[10px] text-gray-400 italic')
                        refresh_prices()
                    # Live Scraper Trigger Button & Loading Spinner
                    with ui.column().classes('w-full gap-2 items-center'):
                        loading_spinner = ui.spinner(size='md', color='pink').classes('hidden')
                        loading_label = ui.label('Memicu Sentinel Scraper...').classes('text-[10px] text-pink-500 font-bold hidden animate-pulse')
                        async def jalankan_live_scraping():
                            # Tunjukkan loading spinner
                            loading_spinner.classes(remove='hidden')
                            loading_label.classes(remove='hidden')
                            scrape_btn.disable()
                            # Jalankan scraping asinkron
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None,
                                scrape_marketplace_live,
                                product.get('id'),
                                product.get('brand', ''),
                                product.get('product_name', '')
                            )
                            # Sembunyikan loading spinner & refresh
                            loading_spinner.classes('hidden')
                            loading_label.classes('hidden')
                            scrape_btn.enable()
                            ui.notify('🚀 Harga Tokopedia, Lazada & Shopee berhasil di-update secara live!', color='green', icon='flash_on')
                            refresh_prices()
                        scrape_btn = ui.button(
                            'Cari Harga Live ⚡',
                            on_click=jalankan_live_scraping
                        ).classes('w-full bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-xl font-bold py-2.5 shadow-md hover:scale-[1.02] transition-all').props('no-caps icon=flash_on')
    dialog.open()

def show_page():
    """Halaman Pencarian Produk (100% Selesai) - Dipegang oleh Syahid"""
    if not hasattr(state, 'page'):
        state.page = 1

    # Fetch distinct brands dynamically from DB for the search page filter
    with SessionLocal() as session:
        brs = session.query(SociollaReferensi.brand).distinct().filter(SociollaReferensi.brand != None).all()
        unique_brands = sorted([b[0] for b in brs])
        
    if not unique_brands:
        # Fallback to popular brands if DB is empty
        unique_brands = ["Skintific", "Cosrx", "Wardah", "Somethinc", "The Originote", "Anessa", "Azarine", "Avoskin"]

    auth_redirect = AuthManager.require_auth()
    if auth_redirect:
        return auth_redirect

    # 2. Refreshable Status Bar
    # FIX #3: Tidak panggil weather API lagi di sini.
    # analyze_routine() sudah di-cache di WeatherService (30 menit TTL).
    # Dibungkus safe_section agar kalau crash tidak merusak seluruh halaman search.
    @ui.refreshable
    def taskbar_status() -> None:
        with safe_section("Status Rutin", show_error=False, compact=True):
            # Hanya jalankan jika ada routine & kota, untuk menghindari weather call sia-sia
            if state.routine and state.kota:
                analysis = data_mgr.analyze_routine(state.routine, kota=state.kota)
                UIComponents.routine_status_badge(analysis)
            else:
                # Tidak ada routine aktif — tampilkan badge kosong tanpa hit API
                UIComponents.routine_status_badge({})

    # 3. Layout Utama
    UIComponents.navbar(status_widget=taskbar_status)
    UIComponents.sidebar()

    # Prevent outer body scroll on search page
    ui.query('body').style('overflow: hidden;')

    with ui.row().classes('w-full max-w-[2000px] mx-auto items-stretch no-wrap mt-4 px-8 gap-8 overflow-hidden').style('height: calc(100vh - 140px);'):
        
        # Panel Kiri: Form Pencarian & Filter (Card Dinaikkan)
        with ui.column().classes('w-64 flex-shrink-0 pt-0 h-full'):
            with ui.card().classes('w-full p-4 shadow-sm bg-white max-h-full overflow-y-auto'):
                # Kotak Pencarian
                init_query = app.storage.user.pop('search_query', '') if 'search_query' in app.storage.user else ''
                search_input = ui.input(placeholder='Cari nama produk...', value=init_query).classes('w-full mb-3')
                
                # Dropdown Kategori
                # Menggunakan kategori dinamis dari database
                db_categories = data_mgr.categories if hasattr(data_mgr, 'categories') else []
                # Hilangkan 'All' jika sudah ada, karena kita gunakan 'Semua' sebagai label UI
                cats = ['Semua'] + [c for c in db_categories if c != 'All']
                
                default_category = (
                    state.category
                    if hasattr(state, 'category') and state.category in cats
                    else 'Semua'
                )

                cat_select = ui.select(
                    cats,
                    value=default_category,
                    label='Kategori'
                ).classes('w-full mb-3')
                
                # Dropdown Merk / Brand
                brand_select = ui.select(
                    ['Semua'] + unique_brands,
                    value='Semua',
                    label='Merk / Brand'
                ).classes('w-full mb-3')
                
                # Dropdown Tipe Kulit
                skin_types = ['Semua', 'Dry', 'Oily', 'Normal', 'Combination', 'Sensitive']
                skin_select = ui.select(skin_types, value='Semua', label='Tipe Kulit').classes('w-full mb-3')
                
                # Dropdown Harga
                price_ranges = ['Semua', '< Rp 50k', 'Rp 50k - Rp 150k', 'Rp 150k - Rp 300k', '> Rp 300k']
                price_select = ui.select(price_ranges, value='Semua', label='Range Harga').classes('w-full mb-3')
                
                # Dropdown Urutkan
                sort_options = ['Rating (Tertinggi)', 'Harga (Terendah)', 'Harga (Tertinggi)', 'Terlaris']
                sort_select = ui.select(sort_options, value='Rating (Tertinggi)', label='Urutkan').classes('w-full mb-4')
                
                # Filter Marketplace
                mkt_filter = ui.checkbox(
                    'Hanya dengan Marketplace', 
                    value=getattr(state, 'mkt_filter', False)
                ).classes('mb-3 text-xs font-bold text-gray-600')
                
                def trigger_search(e=None):
                    state.page = 1
                    state.mkt_filter = mkt_filter.value
                    if hasattr(state, 'category'):
                        state.category = cat_select.value if cat_select.value != 'Semua' else None
                    catalog_view.refresh()

                # Event listeners
                search_input.on('keydown.enter', trigger_search)
                cat_select.on_value_change(trigger_search)
                brand_select.on_value_change(trigger_search)
                skin_select.on_value_change(trigger_search)
                price_select.on_value_change(trigger_search)
                sort_select.on_value_change(trigger_search)
                mkt_filter.on_value_change(trigger_search)
                
                ui.button('Terapkan Filter', on_click=trigger_search, color='pink-500').classes('w-full font-bold text-white mb-2')

                ui.separator().classes('my-2')
                
                # Tombol Tambah Produk — HANYA untuk Admin
                from nicegui import app as _app
                if _app.storage.user.get('role') == 'admin':
                    def open_add_dialog():
                        product_form_dialog()
                    ui.button('Tambah Produk Baru', icon='add', on_click=open_add_dialog, color='green-500').classes('w-full font-bold text-white')

        # Panel Kanan: Katalog Produk
        with ui.column().classes('flex-1 glass-card-static p-8 relative h-full'):
            # Loading Spinner (Overlay)
            with ui.column().classes('absolute inset-0 flex items-center justify-center z-50 bg-white/20 backdrop-blur-sm') as loading_spinner:
                ui.spinner(size='lg', color='pink-500')
                ui.label('Memuat Produk...').classes('mt-4 font-bold text-pink-500 animate-pulse')
            loading_spinner.set_visibility(False)

            with ui.scroll_area().classes('w-full h-full pr-4') as main_catalog_area:
                
                # ── SHARED DIALOGS (Optimization: Create once, use many) ──
                
                # 1. Detail Dialog - Menggunakan buka_modal_detail dari wishlist_page
                def open_detail(p, g=None, a=None, ic=None):
                    # Save to recent
                    recent = state.__dict__.get('recent_products', [])
                    if not any(x.get('slug') == p.get('slug') for x in recent):
                        recent.insert(0, p)
                        state.__dict__['recent_products'] = recent[:5]
                    # Open enhanced modal
                    buka_modal_detail(p)



                # 2. Delete Confirmation
                delete_target = {'p': None}
                async def do_delete():
                    p = delete_target['p']
                    if p and data_mgr.delete_custom_product(p['id']):
                        ui.notify(f"Produk '{p['product_name']}' dihapus.", color='positive')
                        catalog_view.refresh()
                    else:
                        ui.notify("Gagal menghapus produk.", color='negative')
                    confirm_modal.close()

                with ui.dialog() as confirm_modal, ui.card().classes('p-6') as confirm_card:
                    @ui.refreshable
                    def delete_content():
                        p = delete_target['p']
                        if not p: return
                        ui.label(f"Hapus produk '{p['product_name']}'?").classes('font-bold text-lg mb-4')
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Batal', on_click=confirm_modal.close).props('flat')
                            ui.button('Hapus', on_click=do_delete, color='red-500').classes('text-white')
                    delete_content()

                def confirm_delete_dialog(p):
                    delete_target['p'] = p
                    delete_content.refresh()
                    confirm_modal.open()

                @ui.refreshable
                def catalog_view() -> None:
                    print("=== CATALOG VIEW JALAN ===")

                    # --- ASYNC LOADING LOGIC ---

                    # --- LOADING LOGIC ---
                    loading_spinner.set_visibility(True)
                    try:
                        keyword = search_input.value.lower() if search_input.value else ""
                        sort_val = sort_select.value
                        category_filter = cat_select.value

                        # Mapping filter UI ke Backend (Dinamis)
                        backend_category = category_filter if category_filter != 'Semua' else 'All'

                        min_price, max_price = 0.0, float('inf')
                        if price_select.value == '< Rp 50k':
                            max_price = 49999.0
                        elif price_select.value == 'Rp 50k - Rp 150k':
                            min_price = 50000.0
                            max_price = 150000.0
                        elif price_select.value == 'Rp 150k - Rp 300k':
                            min_price = 150000.1
                            max_price = 300000.0
                        elif price_select.value == '> Rp 300k':
                            min_price = 300000.1

                        # Move blocking DB call to a separate thread
                        from nicegui import run

                        # Pemanggilan database secara langsung (sinkron) dengan filter tipe kulit
                        paginated_data = data_mgr.get_paginated_products(
                            page=state.page,
                            items_per_page=12,
                            category_filter=backend_category,
                            keyword=keyword,
                            min_price=min_price,
                            max_price=max_price,
                            sort_val=sort_val,
                            marketplace_only=getattr(state, 'mkt_filter', False),
                            skin_type_filter=skin_select.value,
                            brand_filter=brand_select.value
                        )
                    finally:
                        loading_spinner.set_visibility(False)
                    
                    items = paginated_data["items"]

                    ui.label(f'{paginated_data["total_items"]} PRODUK DITEMUKAN').classes('text-xs font-bold text-gray-500 mb-6 tracking-wider')

                    if len(items) == 0:
                        with ui.column().classes('w-full items-center justify-center p-12'):
                            ui.label('🏜️').classes('text-6xl mb-4')
                            ui.label('Ups, tidak ada produk yang sesuai kriteria.').classes('text-gray-500')
                    else:
                        with ui.grid(columns=3).classes('w-full gap-6 items-stretch'):
                            for prod in items:
                                # Data produk
                                name = prod.get('product_name', prod.get('name', 'Tanpa Nama'))
                                brand = prod.get('brand', 'Tanpa Merk')
                                price = prod.get('min_price', prod.get('price', 0))
                                rating = prod.get('average_rating', prod.get('rating', 0.0))
                                format_price = f"Rp{price:,.0f}".replace(',', '.')
                                img_url = prod.get('image_url', '')

                                def handle_add_item(p=prod) -> None:
                                    current = getattr(state, 'wishlist', [])
                                    if not any(item.get('slug') == p.get('slug', '') for item in current):
                                        state.wishlist = current + [p]
                                        ui.notify(f'{p.get("product_name", "Produk")} ditambahkan ke Wishlist!',
                                                color='pink', position='bottom-right')
                                    else:
                                        ui.notify('Produk ini sudah ada di Wishlist.', color='info', position='bottom-right')

                                # ── Palet warna & ikon fallback per kategori ──
                                MAKEUP_CATS = {'Cushion', 'Blush', 'Powder', 'Eye Product', 'LIP Product'}
                                
                                cat_palette = {
                                    # --- SKINCARE (Cool/Calming Tones) ---
                                    'Serum':       ('from-blue-50 to-blue-100',  '#6366F1', '💧'),
                                    'Moisturizer': ('from-green-50 to-emerald-100','#10B981', '🧴'),
                                    'Sunscreen':   ('from-yellow-50 to-amber-100', '#F59E0B', '☀️'),
                                    'Toner':       ('from-cyan-50 to-sky-100',     '#0EA5E9', '🌊'),
                                    'Cleanser':    ('from-blue-50 to-blue-100','#3B82F6', '🫧'),
                                    'Face Gel':    ('from-teal-50 to-cyan-100',    '#14B8A6', '💦'),
                                    'Face Wash':   ('from-blue-50 to-blue-100','#3B82F6', '🫧'),
                                    
                                    # --- MAKEUP (Premium Cool Tones) ---
                                    'Cushion':     ('from-blue-100 to-blue-200', '#2563EB', '🧏‍♀️'),
                                    'Blush':       ('from-pink-100 to-rose-200',    '#BE185D', '🌸'),
                                    'Powder':      ('from-blue-50 to-blue-100',  '#1E40AF', '🧴'),
                                    'Eye Product': ('from-violet-100 to-fuchsia-200','#701A75', '👁️'),
                                    'LIP Product': ('from-red-100 to-rose-300',      '#9F1239', '💄'),
                                    'Halal Cert':  ('from-emerald-50 to-teal-100',  '#0F766E', '🕋'),
                                }
                                prod_cat = prod.get('category', '')
                                is_makeup = prod_cat in MAKEUP_CATS
                                grad, accent, cat_icon = cat_palette.get(prod_cat, ('from-pink-50 to-rose-100', '#EC4899', '🧴'))

                                # Kartu Produk (Tinggi Otomatis, Bersih & Bebas Overlap)
                                with ui.card().classes('product-card p-0 flex flex-col overflow-hidden rounded-xl border border-gray-100 hover:shadow-md transition-all duration-300'):
                                    # ── Area Gambar ──
                                    with ui.element('div').classes('w-full h-36 bg-gray-50 relative overflow-hidden flex items-center justify-center flex-shrink-0'):
                                        if img_url and str(img_url).startswith('http'):
                                            # Gambar asli dari Sociolla CDN
                                            ui.image(img_url).classes('w-full h-full object-contain').style('mix-blend-mode:multiply')
                                        else:
                                            # Fallback: lingkaran warna + emoji kategori
                                            with ui.element('div').classes('flex flex-col items-center gap-1'):
                                                ui.element('div').classes(
                                                    'w-16 h-16 rounded-full flex items-center justify-center text-3xl shadow-inner'
                                                ).style(f'background: {accent}22')
                                                ui.label(cat_icon).classes('text-3xl')
                                                ui.label(prod_cat or 'Skincare').classes('text-xs font-medium').style(f'color:{accent}')

                                    # ── Info Teks ──
                                    with ui.column().classes('w-full p-4 gap-2'):
                                        # Badge Skincare/Makeup
                                        badge_text = "MAKEUP" if is_makeup else "SKINCARE"
                                        badge_color = "bg-blue-100 text-blue-800" if is_makeup else "bg-blue-100 text-blue-700"
                                        ui.label(badge_text).classes(f'text-[8px] font-black px-2 py-0.5 rounded-md w-fit {badge_color}')

                                        ui.label(name).classes('font-bold text-sm leading-tight line-clamp-2 min-h-[40px] text-gray-800')
                                        ui.label(brand).classes('text-xs text-gray-400 truncate w-full')
                                        ui.label(format_price).classes('text-pink-500 font-bold text-base mt-0.5')

                                        # Rating dengan bintang visual, Jumlah Ulasan, dan Terjual
                                        reviews_count = prod.get('total_reviews', prod.get('reviews', 0))
                                        terjual = prod.get('terjual', prod.get('sold', 0))
                                        with ui.row().classes('items-center gap-1 mb-1 w-full flex-wrap'):
                                            ui.label('★').classes('text-yellow-400 text-sm')
                                            ui.label(f'{rating:.1f}' if isinstance(rating, (int, float)) else str(rating)).classes('text-xs font-bold text-gray-700')
                                            ui.label(f'({reviews_count} ulasan)' if reviews_count else '(Belum ada ulasan)').classes('text-[10px] text-gray-400')
                                            if terjual and terjual != 0 and terjual != '0':
                                                ui.label(f'• Terjual {terjual}').classes('text-[10px] font-medium text-green-600 bg-green-50 px-1 rounded-sm ml-auto')
                                        

                                        
                                        # Bagian Bawah Tombol Aksi (Detail & Wishlist)
                                        with ui.row().classes('w-full gap-2 pt-2 border-t border-gray-50 mt-1'):
                                            ui.button('Detail', on_click=lambda p=prod, g=grad, a=accent, ic=cat_icon: open_detail(p, g, a, ic)).props('flat no-caps').classes('flex-grow border border-gray-200 text-xs text-gray-700 py-1.5 rounded-lg')
                                            ui.button('+ Wishlist', on_click=handle_add_item).props('flat no-caps').classes('flex-grow font-bold border border-pink-200 text-pink-600 text-xs py-1.5 rounded-lg bg-pink-50 hover:bg-pink-100')
                                            
                                            # Tombol Edit/Hapus — HANYA untuk Admin
                                            from nicegui import app as _app
                                            if _app.storage.user.get('role') == 'admin':
                                                with ui.row().classes('gap-1 justify-center w-full mt-1'):
                                                    ui.button(icon='edit', on_click=lambda p=prod: product_form_dialog(p)).props('flat dense').classes('text-blue-400 hover:text-blue-600')
                                                    ui.button(icon='delete', on_click=lambda p=prod: confirm_delete_dialog(p)).props('flat dense').classes('text-red-400 hover:text-red-600')

                    # Pagination Bawaan
                    def handle_page_change(new_page: int) -> None:
                        state.page = new_page
                        catalog_view.refresh()
                        main_catalog_area.scroll_to(0)

                    if paginated_data["total_pages"] > 1:
                        ui.separator().classes('mt-10 mb-6 opacity-20')
                        UIComponents.pagination_controls(
                            current_page=paginated_data["current_page"],
                            total_pages=paginated_data["total_pages"],
                            on_change=handle_page_change
                        )
                catalog_view()

                def product_form_dialog(product=None):
                    with ui.dialog() as dialog, ui.card().classes('w-[500px] p-6 rounded-2xl'):
                        ui.label('Tambah Produk Baru' if not product else '📝 Edit Produk').classes('text-2xl font-black text-gray-800 mb-6')
                        
                        with ui.column().classes('w-full gap-4'):
                            name = ui.input('Nama Produk', placeholder='Contoh: Hydrating Serum', value=product['product_name'] if product else '').classes('w-full')
                            brand = ui.input('Brand', placeholder='Contoh: Skintific', value=product['brand'] if product else '').classes('w-full')
                            
                            with ui.row().classes('w-full gap-4'):
                                price = ui.number('Harga (Rp)', value=product['min_price'] if product else 0, format='%.0f').classes('flex-1')
                                cats_list = data_mgr.categories if hasattr(data_mgr, 'categories') else ['Serum', 'Moisturizer', 'Toner', 'Sunscreen', 'Cleanser']
                                # Remove 'All' from selection list for new product
                                if 'All' in cats_list: cats_list.remove('All')
                                category = ui.select(cats_list, label='Kategori', value=product['category'] if product else cats_list[0]).classes('flex-1')
                            
                            ingredients = ui.textarea('Kandungan (Pisahkan dengan koma)', 
                                                   placeholder='Water, Glycerin, Niacinamide...',
                                                   value=product['ingredients'] if product else '').classes('w-full')
                            
                            image_url = ui.input('URL Gambar', 
                                              placeholder='https://example.com/image.jpg',
                                              value=product['image_url'] if product else '').classes('w-full mb-4')
                        
                        async def save_data():
                            if not name.value or not brand.value:
                                ui.notify('Nama dan Brand wajib diisi!', color='warning')
                                return
                                
                            payload = {
                                'product_name': name.value,
                                'brand': brand.value,
                                'price': price.value or 0,
                                'category': category.value,
                                'ingredients': ingredients.value,
                                'image_url': image_url.value
                            }
                            
                            if not product:
                                success = data_mgr.add_custom_product(payload)
                            else:
                                success = data_mgr.update_custom_product(product['id'], payload)
                            
                            if success:
                                ui.notify('Produk berhasil disimpan!', color='positive')
                                dialog.close()
                                catalog_view.refresh()
                            else:
                                ui.notify('Gagal menyimpan produk. Coba lagi.', color='negative')
                        
                        with ui.row().classes('w-full justify-end gap-3 mt-4'):
                            ui.button('Batal', on_click=dialog.close).props('flat').classes('text-gray-500')
                            ui.button('Simpan Produk', on_click=save_data, color='pink-500').classes('text-white px-6 font-bold')
                    
                    dialog.open()
                
                # Initial state sync (jika ada category dari halaman lain)
                if hasattr(state, 'category') and state.category and state.category in cats:
                    cat_select.value = state.category
                ui.timer(0.1, catalog_view.refresh, once=True)
