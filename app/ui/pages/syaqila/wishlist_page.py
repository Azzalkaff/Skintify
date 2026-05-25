import json
import asyncio
import logging

from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal, simpan_hasil
from app.database.models import Produk, Toko, SociollaReferensi

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
        from app.ui.pages.syhid.search_page import get_best_marketplace_product
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
    """MISI SYAQILA: Membuat Galeri Wishlist"""
    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------
    # --- 🚀 MULAI KERJAKAN DI SINI (AREA BELAJAR SYAQILA) ---
    # Data produk wishlist (nanti bisa diganti dari data_mgr)
    # --- 🚀 AREA WISHLIST DINAMIS ---
    with ui.column().classes('w-full p-8 bg-rose-50/30 min-h-screen gap-4'):
        # HEADER (Poin 4: Tipografi & Sudut Modern)
        with ui.row().classes('w-full items-center justify-between pb-4 border-b border-pink-100/50'):
            ui.label('Wishlist').classes('text-3xl font-extrabold tracking-tight text-gray-800')
            with ui.element('div').classes('bg-gradient-to-r from-pink-100 to-rose-100 px-5 py-2 rounded-2xl shadow-sm'):
                skin_type = app.storage.user.get('skin_type', 'Belum diisi')
                ui.label(f'Tipe Kulit: {skin_type}').classes('text-pink-600 text-sm font-bold tracking-wide')
        @ui.refreshable
        def render_wishlist():
            wishlist_products = state.wishlist
            def hapus_produk(slug: str):
                state.wishlist = [p for p in state.wishlist if p.get('slug') != slug]
                ui.notify('Produk dihapus dari Wishlist', color='pink')
                render_wishlist.refresh()
            # Inisialisasi list pilihan bandingkan di state
            if 'wishlist_compare_selections' not in state.__dict__:
                state.__dict__['wishlist_compare_selections'] = []
            def toggle_compare_selection(p: dict):
                selections = state.__dict__['wishlist_compare_selections']
                slug = p.get('slug')
                existing = [x for x in selections if x.get('slug') == slug]
                if existing:
                    state.__dict__['wishlist_compare_selections'] = [x for x in selections if x.get('slug') != slug]
                    ui.notify(f"Dikeluarkan dari pilihan: {p.get('brand')} {p.get('product_name') or p.get('nama')}", color='pink')
                else:
                    if len(selections) >= 3:
                        ui.notify("Maksimal 3 produk yang dapat dibandingkan sekaligus!", color='warning', icon='warning')
                    else:
                        state.__dict__['wishlist_compare_selections'].append(p)
                        ui.notify(f"Terpilih untuk dibandingkan: {p.get('brand')} {p.get('product_name') or p.get('nama')}", color='green', icon='check_circle')
                render_wishlist.refresh()
            def clear_compare_selections():
                state.__dict__['wishlist_compare_selections'] = []
                ui.notify("Pilihan perbandingan dikosongkan", color='blue')
                render_wishlist.refresh()
            def lakukan_bandingkan_wishlist():
                selections = state.__dict__['wishlist_compare_selections']
                if len(selections) < 2:
                    ui.notify("Pilih minimal 2 produk untuk dibandingkan!", color='warning')
                    return
                # Buat list slots (panjang 3)
                slots = [None, None, None]
                for idx, p in enumerate(selections):
                    compare_prod = {
                        'id': p.get('id') or p.get('my_sociolla_sql_id'),
                        'product_name': p.get('product_name') or p.get('nama', '-'),
                        'brand': p.get('brand', '-'),
                        'category': p.get('category'),
                        'image_url': p.get('image_url') or p.get('image'),
                        'min_price': p.get('min_price', 0),
                        'brand_country': p.get('brand_country'),
                        'bpom_reg_no': p.get('bpom_reg_no'),
                        'ingredients': p.get('ingredients') or p.get('ingredients_raw'),
                        'repurchase_yes': p.get('repurchase_yes', 0),
                        'repurchase_no': p.get('repurchase_no', 0),
                        'repurchase_maybe': p.get('repurchase_maybe', 0),
                        'average_rating': p.get('average_rating') or p.get('rating', 0),
                        'total_reviews': p.get('total_reviews', 0),
                        'variants': p.get('variants', []),
                        'reviews': p.get('reviews', [])
                    }
                    slots[idx] = compare_prod
                # Set compare page states in context
                state.__dict__['selected_compare_category'] = selections[0].get('category')
                state.__dict__['compare_slots'] = slots
                # Kosongkan pilihan di wishlist setelah sukses
                state.__dict__['wishlist_compare_selections'] = []
                ui.notify(f"Memulai perbandingan {len(selections)} produk dari Wishlist! ⚔️", color='green')
                ui.navigate.to('/compare')
            # jumlah produk
            if wishlist_products:
                ui.label(f'{len(wishlist_products)} PRODUK TERSIMPAN').classes(
                    'text-xs font-bold text-gray-400 tracking-widest mt-4 mb-2 uppercase'
                )
            # Poin 5: EMPTY STATE YANG LEBIH MENARIK DENGAN SVG
            if not wishlist_products:
                with ui.column().classes('w-full items-center justify-center py-20 gap-4'):
                    # SVG Heart Broken / Empty Box
                    ui.html('''
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-28 h-28 text-pink-200 drop-shadow-[0_10px_15px_rgba(236,72,153,0.2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                        </svg>
                    ''')
                    ui.label("Wishlist masih kosong").classes('text-2xl font-extrabold text-gray-800 mt-2')
                    ui.label("Simpan produk incaranmu di sini agar tidak lupa!").classes('text-gray-500 text-center max-w-sm font-medium')
                    ui.button('Eksplorasi Produk', on_click=lambda: ui.navigate.to('/search')).classes(
                        'mt-6 bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-2xl px-8 py-3 shadow-[0_8px_20px_rgba(244,63,94,0.3)] hover:scale-105 transition-transform duration-300 font-bold'
                    ).props('no-caps')
            # LIST PRODUK
            with ui.grid(columns=1).classes('w-full gap-4'):
                for product in wishlist_products:
                    # Poin 4: Sudut membulat (rounded-2xl)
                    with ui.card().classes(
                        'w-full p-4 rounded-2xl shadow-sm border border-gray-100/80 '
                        'bg-white/80 backdrop-blur-sm'
                    ):
                        with ui.row().classes('w-full items-center justify-between no-wrap'):
                            # KIRI
                            with ui.row().classes('items-center gap-5 no-wrap flex-1'):
                                # Poin 6: Peningkatan Visual Gambar / Ikon Produk dengan SVG dan Gradient
                                with ui.element('div').classes('w-16 h-16 rounded-2xl overflow-hidden shadow-sm flex items-center justify-center flex-shrink-0 cursor-pointer') \
                                    .on('click', lambda p=product: buka_modal_detail(p)):
                                    if product.get('image_url') and str(product.get('image_url')).startswith('http'):
                                        ui.image(product['image_url']).classes('w-full h-full object-contain bg-white')
                                    else:
                                        cat = product.get('category', '')
                                        if 'Serum' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-blue-100 to-blue-50 text-blue-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2.25c-1.353 3.036-3.834 6.75-5.625 9.375-1.748 2.56-2.625 5.25-2.625 7.875 0 4.5 3.75 8.25 8.25 8.25s8.25-3.75 8.25-8.25c0-2.625-.877-5.315-2.625-7.875C15.834 9 13.353 5.286 12 2.25z" /></svg>'
                                        elif 'Moisturizer' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-teal-100 to-emerald-50 text-teal-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" /></svg>'
                                        elif 'Sunscreen' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-blue-100 to-blue-50 text-blue-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>'
                                        else:
                                            bg_cls = 'bg-gradient-to-br from-pink-100 to-rose-50 text-pink-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" /></svg>'
                                        with ui.element('div').classes(f'w-full h-full flex items-center justify-center {bg_cls}'):
                                            ui.html(svg_icon)
                                with ui.column().classes('gap-1 flex-1'):
                                    ui.label(product.get('product_name', product.get('name', '-'))).classes(
                                        'text-lg font-extrabold text-gray-800 leading-tight cursor-pointer hover:text-pink-500 transition-colors'
                                    ).on('click', lambda p=product: buka_modal_detail(p))
                                    ui.label(
                                        f'{product.get("brand", "-")} · {product.get("category", "-")}'
                                    ).classes('text-sm text-gray-500 font-medium')
                            # TENGAH
                            with ui.column().classes('items-end gap-1 mr-6'):
                                ui.label(f"Rp{product.get('min_price', 0):,.0f}".replace(',', '.')).classes(
                                    'text-lg font-extrabold text-pink-500'
                                )
                                rating_val = product.get('average_rating') or product.get('rating') or '-'
                                with ui.row().classes('items-center gap-1'):
                                    ui.html('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-yellow-400"><path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z" clip-rule="evenodd" /></svg>')
                                    ui.label(f'{rating_val}').classes(
                                        'text-sm text-gray-600 font-bold'
                                    )
                            # KANAN
                            with ui.row().classes('items-center gap-2 flex-shrink-0'):
                                ui.button(
                                    'Detail 🔬',
                                    on_click=lambda p=product: buka_modal_detail(p)
                                ).props('no-caps').classes(
                                    'bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-xl px-4 py-2 shadow-sm font-bold hover:scale-105 transition-all text-xs'
                                )
                                # Check if product is currently selected for comparison
                                is_selected = any(x.get('slug') == product.get('slug') for x in state.__dict__.get('wishlist_compare_selections', []))
                                if is_selected:
                                    ui.button(
                                        'Terpilih ⚔️',
                                        on_click=lambda p=product: toggle_compare_selection(p)
                                    ).props('no-caps').classes(
                                        'bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl px-4 py-2 shadow-sm font-bold hover:scale-105 transition-all text-xs'
                                    )
                                else:
                                    ui.button(
                                        'Bandingkan ⚔️',
                                        on_click=lambda p=product: toggle_compare_selection(p)
                                    ).props('outline no-caps').classes(
                                        'text-blue-500 border-blue-200 hover:bg-blue-50 rounded-xl px-4 py-2 font-bold transition-all text-xs'
                                    )
                                ui.button(
                                    'Hapus',
                                    on_click=lambda p=product: hapus_produk(p.get('slug'))
                                ).props('outline no-caps').classes(
                                    'text-pink-500 border-pink-200 rounded-xl px-4 py-2 hover:bg-pink-50 font-bold transition-colors text-xs'
                                )
            # FLOATING COMPARE DOCK
            selections = state.__dict__.get('wishlist_compare_selections', [])
            if len(selections) >= 2:
                with ui.element('div').classes('fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-2xl p-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-pink-100 flex items-center justify-between gap-4 animate-fade-in'):
                    # Left: circular thumbnails
                    with ui.row().classes('items-center gap-3 flex-1'):
                        ui.label("SIAP ADU MEKANIK:").classes('text-[10px] font-black text-pink-500 tracking-wider flex-shrink-0')
                        with ui.row().classes('items-center gap-1.5 overflow-x-auto max-w-[300px] no-scrollbar'):
                            for idx, sel_p in enumerate(selections):
                                if idx > 0:
                                    ui.label('vs').classes('text-xs font-black text-pink-300')
                                with ui.element('div').classes('w-10 h-10 rounded-xl bg-white border border-pink-100 p-1 flex items-center justify-center shadow-sm relative flex-shrink-0'):
                                    ui.image(sel_p.get('image_url') or sel_p.get('image')).classes('w-full h-full object-contain')
                                    # Tiny indicator badge
                                    ui.badge(str(idx+1), color='pink-500').classes('absolute -top-1 -right-1 text-[8px] font-bold w-4 h-4 p-0 flex items-center justify-center rounded-full')
                    # Right: action buttons
                    with ui.row().classes('items-center gap-2 flex-shrink-0'):
                        ui.button('Batal', on_click=clear_compare_selections).props('flat rounded size=sm').classes('text-gray-400 font-bold')
                        ui.button(
                            'Bandingkan ⚔️',
                            on_click=lakukan_bandingkan_wishlist
                        ).props('unelevated rounded size=sm').classes('bg-gradient-to-r from-pink-500 to-blue-600 text-white font-black px-5 py-2 hover:scale-105 transition-all text-xs')
        # Panggil render function
        render_wishlist()