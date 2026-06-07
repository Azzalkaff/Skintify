from nicegui import ui, app
import asyncio
from datetime import datetime
import re
from typing import Callable, Optional

from app.database.engine import SessionLocal
from app.database.models import Produk, Toko, SociollaReferensi
from app.context import data_mgr, state
from app.auth.auth import AuthManager

def get_best_products(db_rows, limit=5):
    valid = [r for r in db_rows if r.get('harga', 0) > 0 and r.get('terjual', 0) > 0]
    valid.sort(key=lambda x: x.get('terjual', 0), reverse=True)
    return valid[:limit]

def extract_size(product_name: str) -> float:
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(ml|gr|g)', product_name, re.IGNORECASE)
    if match:
        val = match.group(1).replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return 0.0
    return 0.0

def render_platform_card(platform_name, card_border_class, hover_bg_class, icon_color_style, text_color_class, title, subtitle, price, url, image=None, rating=None, terjual=0, reviews_count=0, harga_asli=0, diskon_persen=0, in_stock=True, label_badge=None, free_ongkir=0, nama=''): 
    from app.ui.pages.syhid.search_page import render_platform_card as rpc
    return rpc(platform_name, card_border_class, hover_bg_class, icon_color_style, text_color_class, title, subtitle, price, url, image, rating, terjual, reviews_count, harga_asli, diskon_persen, in_stock, label_badge, free_ongkir, nama)

def get_best_marketplace_product(product, platform):
    from app.ui.pages.syhid.search_page import get_best_marketplace_product as gbmp
    return gbmp(product, platform)

def show_shared_product_detail(product: dict, on_add_click=None, on_remove_click=None, on_data_updated=None):
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
        # Modal Header (Gradient background) - COMPACT
        with ui.row().classes('w-full bg-gradient-to-r from-rose-50 to-pink-50/50 p-3 px-5 items-center justify-between border-b border-rose-100/60 no-wrap'):
            with ui.row().classes('items-center gap-3 no-wrap flex-1'):
                # Image
                if product.get('image_url'):
                    ui.image(product['image_url']).classes('w-12 h-12 rounded-xl object-contain bg-white shadow-sm border border-rose-100/50 flex-shrink-0')
                with ui.column().classes('gap-0'):
                    ui.label(product.get('brand', '-').upper()).classes('text-[9px] font-black text-pink-500 tracking-widest')
                    ui.label(product.get('product_name', '-')).classes('text-lg font-black text-gray-800 leading-tight line-clamp-1')
                    ui.label(product.get('category', '-')).classes('text-[10px] text-gray-400 font-bold')
            # Close Button
            ui.button(icon='close', on_click=dialog.close).props('flat round size=sm').classes('text-gray-400 hover:text-pink-500 transition-colors')
        # Modal Scrollable Content
        with ui.scroll_area().classes('w-full flex-grow p-4 lg:p-6'):
            with ui.grid(columns='1 lg:grid-cols-5').classes('w-full gap-4 lg:gap-6 items-stretch'):
                # KOLOM 1: Informasi Detail (Kandungan Aktif & Semua Bahan)
                with ui.column().classes('col-span-1 lg:col-span-2 gap-3'):
                    # TABS SELECTOR (NiceGUI Tabs)
                    with ui.tabs().classes('w-full border-b border-gray-100') as detail_tabs:
                        tab_kandungan = ui.tab('kandungan', label='🔬 Bahan Aktif')
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


                        # PANEL 3: Semua Bahan (Ingredients List)
                        with ui.tab_panel('ingredients'):
                            ui.label('DAFTAR BAHAN LENGKAP (FULL INGREDIENTS):').classes('text-[10px] font-black text-gray-400 tracking-wider mb-2')
                            raw_ing = product.get('ingredients') or ''
                            if not raw_ing and product.get('id'):
                                with SessionLocal() as _sess:
                                    _ref = _sess.query(SociollaReferensi).filter_by(id=product.get('id')).first()
                                    if _ref and hasattr(_ref, 'ingredients') and _ref.ingredients:
                                        raw_ing = _ref.ingredients
                            ing_list = [i.strip() for i in raw_ing.split(',') if i.strip()]
                            
                            if not ing_list:
                                ui.label('Data bahan lengkap belum tersedia.').classes('text-xs text-gray-600 font-medium leading-relaxed bg-gray-50 p-4 rounded-2xl border border-gray-100/50')
                            else:
                                # --- PRE-COMPUTE O(I x A) SEKALI SAJA ---
                                profile = data_mgr.get_ingredient_profile(product) or {}
                                active_set = {act.lower() for act in profile.get("active_ingredients", [])}
                                soothing_set = {"centella", "allantoin", "panthenol", "chamomile", "aloe", "madecassoside", "bisabolol"}
                                hydrating_set = {"hyaluronic", "glycerin", "butylene glycol", "propylene glycol", "squalane", "shea butter", "ceramide"}
                                
                                precomputed_ingredients = []
                                for ing in ing_list:
                                    ing_low = ing.lower()
                                    cat = "standard"
                                    if any(act in ing_low for act in active_set):
                                        cat = "active"
                                    elif any(kw in ing_low for kw in soothing_set):
                                        cat = "soothing"
                                    elif any(kw in ing_low for kw in hydrating_set):
                                        cat = "hydrating"
                                    precomputed_ingredients.append({"name": ing, "cat": cat, "lower": ing_low})
                                    
                                # Search input for filtering ingredients
                                search_ing = ui.input(placeholder='Cari kandungan/ingredients...').classes('w-full mb-4').props('clearable outlined icon=search')
                                
                                # Container for chips
                                chips_container = ui.element('div').classes('flex flex-wrap gap-2 max-h-[300px] overflow-y-auto p-1')
                                
                                def render_chips(filter_text=""):
                                    chips_container.clear()
                                    ft = filter_text.lower()
                                    with chips_container:
                                        rendered_any = False
                                        for item in precomputed_ingredients:
                                            if ft and ft not in item["lower"]:
                                                continue
                                            rendered_any = True
                                            ing_name = item["name"]
                                            cat = item["cat"]
                                            
                                            # Render UI O(1) decision
                                            if cat == "active":
                                                with ui.element('div').classes('bg-pink-50 text-pink-600 border border-pink-100 px-3 py-1.5 rounded-full text-xs font-bold flex items-center gap-1 hover:bg-pink-100/50 transition-colors shadow-sm'):
                                                    ui.icon('star', size='12px')
                                                    ui.label(ing_name)
                                            elif cat == "soothing":
                                                with ui.element('div').classes('bg-emerald-50 text-emerald-600 border border-emerald-100 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1 hover:bg-emerald-100/50 transition-colors'):
                                                    ui.icon('spa', size='12px')
                                                    ui.label(ing_name)
                                            elif cat == "hydrating":
                                                with ui.element('div').classes('bg-blue-50 text-blue-600 border border-blue-100 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1 hover:bg-blue-100/50 transition-colors'):
                                                    ui.icon('opacity', size='12px')
                                                    ui.label(ing_name)
                                            else:
                                                ui.label(ing_name).classes('bg-gray-50 text-gray-600 border border-gray-100 px-3 py-1.5 rounded-full text-xs hover:bg-gray-100 transition-colors')
                                        
                                        if not rendered_any:
                                            ui.label('Kandungan tidak ditemukan.').classes('text-xs text-gray-400 italic p-2')
                                
                                # Render chips initially
                                render_chips()
                                
                                # Update chips when search text changes
                                search_ing.on_value_change(lambda e: render_chips(e.value))
                # KOLOM 2: Perbandingan Harga Marketplace & Live Scraper Button
                with ui.column().classes('col-span-1 lg:col-span-3 bg-rose-50/20 border border-rose-100/50 rounded-2xl p-4 lg:p-5 gap-4 flex flex-col justify-between'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('w-full justify-between items-center border-b border-pink-100/50 pb-2'):
                            ui.label('PEMBANDING HARGA MARKETPLACE').classes('text-[11px] font-black text-pink-500 tracking-widest')
                            
                            def do_auto_compare():
                                similar = data_mgr.get_similar_products(product, limit=2)
                                slots = [product] + similar
                                while len(slots) < 3:
                                    slots.append(None)
                                state.compare_slots = slots
                                state.selected_compare_category = product.get('category', 'All')
                                dialog.close()
                                ui.navigate.to('/compare')
                                ui.notify(f"BATTLE: {product.get('brand')} vs Kompetitor", icon='emoji_events', color='pink')
                            
                            ui.button('Bandingkan Kompetitor', icon='compare_arrows', on_click=do_auto_compare) \
                                .props('outline size=sm rounded') \
                                .classes('text-pink-600 border-pink-300 hover:bg-pink-50 hover:border-pink-500 text-[10px] font-black px-3 py-1 shadow-sm transition-all')
                        # Container untuk List Harga Marketplace (1 Kolom Vertikal)
                        prices_container = ui.column().classes('w-full gap-3')
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
                                            'free_ongkir': p.free_ongkir or 0,
                                            'nama': p.nama or '',
                                            'kota': p.toko.kota if p.toko else ''
                                        })
                                    from collections import defaultdict
                                    platform_dbs = defaultdict(list)
                                    for p in mapped_products:
                                        platform_dbs[p['platform'].lower()].append(p)
                                    tokoped_db = platform_dbs.get('tokopedia', [])
                                    lazad_db = platform_dbs.get('lazada', [])
                                    shopee_db = platform_dbs.get('shopee', [])

                                    def extract_size(nama: str):
                                        """Ekstrak ukuran dominan (terbesar) dalam ml/g dari nama produk."""
                                        import re
                                        if not nama:
                                            return None, None
                                        # Cari SEMUA angka dengan satuan (ambil yang terbesar = produk utama)
                                        ml_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:ml|ML|Ml)'
                                        g_pattern  = r'(\d+(?:[.,]\d+)?)\s*(?:gr?|GR?|Gr?)\b'
                                        
                                        ml_vals = [float(m.replace(',', '.')) for m in re.findall(ml_pattern, nama)]
                                        g_vals  = [float(m.replace(',', '.')) for m in re.findall(g_pattern, nama)]
                                        
                                        # Prioritaskan ml, ambil nilai terbesar yang masuk akal (maks 2000ml)
                                        ml_valid = [v for v in ml_vals if 1 <= v <= 2000]
                                        g_valid  = [v for v in g_vals  if 1 <= v <= 2000]
                                        
                                        if ml_valid:
                                            return max(ml_valid), 'ml'
                                        if g_valid:
                                            return max(g_valid), 'g'
                                        return None, None

                                    def get_best_products(db_list, baseline_price, baseline_size_val, baseline_size_unit, limit=5):
                                        # Step 1: Deduplikasi per toko
                                        unique_stores = {}
                                        for p in db_list:
                                            # Harus punya harga valid
                                            if not p['harga'] or p['harga'] <= 0:
                                                continue
                                                
                                            store_name = p['toko_nama'].strip().lower()
                                            if store_name not in unique_stores:
                                                unique_stores[store_name] = p
                                            else:
                                                existing = unique_stores[store_name]
                                                p_terjual = p.get('terjual') or 0
                                                ex_terjual = existing.get('terjual') or 0
                                                # Produk dengan penjualan lebih banyak menang di toko yang sama
                                                if p_terjual > ex_terjual:
                                                    unique_stores[store_name] = p
                                                elif p_terjual == ex_terjual:
                                                    if p['harga'] < existing['harga']:
                                                        unique_stores[store_name] = p
                                                        
                                        candidates = list(unique_stores.values())
                                        
                                        # Step 2: Filter toko tanpa penjualan (Terjual = 0)
                                        candidates = [x for x in candidates if (x.get('terjual') or 0) > 0]
                                        
                                        if not candidates:
                                            return []
                                        
                                        if baseline_price and baseline_price > 0:
                                            # Mencegah Share-in-Jar atau Bundle Raksasa masuk meski penjualannya tinggi
                                            # Kita buang produk yang selisih harganya terlalu ekstrim (> 60% dari harga asli)
                                            tolerable_candidates = [x for x in candidates if abs(x['harga'] - baseline_price) / baseline_price <= 0.6]
                                            
                                            if tolerable_candidates:
                                                candidates = tolerable_candidates
                                                
                                            # Step 3: Prioritaskan PENJUALAN TERBANYAK (High Sales), lalu selisih harga terkecil
                                            candidates.sort(key=lambda x: (-(x.get('terjual') or 0), abs(x['harga'] - baseline_price)))
                                            return candidates[:limit]
                                        else:
                                            # Fallback jika tidak ada harga asli
                                            candidates.sort(key=lambda x: (-(x.get('terjual') or 0), x['harga']))
                                            return candidates[:limit]

                                # Reusable Premium Platform Card (Vertical List UI)
                                def render_platform_card(platform_name: str, card_border_class: str, hover_bg_class: str, icon_color_style: str, text_color_class: str, title: str, subtitle: str, price: float, url: str, image: str, rating: float, terjual: int, reviews_count: int = 0, harga_asli: float = 0, diskon_persen: int = 0, in_stock: bool = True, label_badge: str = None, free_ongkir: int = 0, nama: str = '', kota: str = ''):
                                    price_text = f"Rp {int(price):,}".replace(',', '.') if price else "Rp -"
                                    img_url = image if image and str(image).startswith('http') else 'https://via.placeholder.com/150?text=No+Image'
                                    original_price_text = f"Rp {int(harga_asli):,}".replace(',', '.') if harga_asli > price else None
                                    
                                    # Ekstrak ukuran dan hitung price-per-unit
                                    size_val, size_unit = extract_size(nama)
                                    price_per_unit_text = None
                                    if size_val and size_val > 0 and price and price > 0:
                                        ppu = price / size_val
                                        price_per_unit_text = f"≈ Rp {int(ppu):,}/{size_unit}".replace(',', '.')
                                    
                                    # Set CTA button color explicitly
                                    btn_color = 'green' if platform_name.lower() == 'tokopedia' else ('blue' if platform_name.lower() == 'lazada' else ('orange' if platform_name.lower() == 'shopee' else 'pink'))

                                    with ui.card().classes(f'w-full p-3 border {card_border_class} bg-white rounded-2xl transition-all duration-300 shadow-sm hover:shadow-md {hover_bg_class}'):
                                        with ui.row().classes('w-full items-center gap-3 no-wrap'):
                                            # Left: Product Image
                                            ui.image(img_url).classes('w-16 h-16 rounded-xl object-contain bg-white border border-gray-100 flex-shrink-0')

                                            # Middle: Details
                                            with ui.column().classes('gap-0.5 flex-1 min-w-0 justify-center'):
                                                # Platform Badge + Stock
                                                with ui.row().classes('items-center gap-1.5 no-wrap flex-wrap'):
                                                    ui.icon('shopping_bag' if platform_name == 'sociolla' else 'store', size='14px').style(icon_color_style)
                                                    ui.label(title).classes(f'text-[11px] font-black {text_color_class} uppercase tracking-wider')
                                                    if label_badge and platform_name.lower() in ['tokopedia', 'lazada']:
                                                        color_class = "text-amber-600 bg-amber-50" if platform_name.lower() == 'tokopedia' else "text-blue-600 bg-blue-50"
                                                        ui.label(f"⭐ {label_badge}").classes(f'text-[9px] font-extrabold {color_class} px-1.5 py-0.5 rounded-md')
                                                    if in_stock is False:
                                                        ui.label('Terbatas').classes('text-[9px] font-extrabold text-red-600 bg-red-50 px-1.5 py-0.5 rounded-md')
                                                    elif in_stock is True:
                                                        ui.label('Tersedia').classes('text-[9px] font-extrabold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-md')

                                                # Shop Name + product size hint
                                                with ui.row().classes('items-baseline gap-1.5 no-wrap'):
                                                    ui.label(subtitle).classes('text-sm text-gray-800 font-bold line-clamp-1')
                                                    if size_val:
                                                        ui.label(f'{int(size_val) if size_val == int(size_val) else size_val}{size_unit}').classes('text-[9px] font-extrabold text-purple-500 bg-purple-50 px-1.5 py-0.5 rounded-md flex-shrink-0')

                                                # Rating & Sold count
                                                with ui.row().classes('items-center gap-2 mt-0.5 flex-wrap'):
                                                    if kota:
                                                        with ui.row().classes('items-center gap-0.5 no-wrap'):
                                                            ui.icon('location_on', color='grey-500', size='13px')
                                                            ui.label(kota).classes('text-[10px] font-medium text-gray-500 line-clamp-1 max-w-[80px]')
                                                    if rating:
                                                        with ui.row().classes('items-center gap-0.5 no-wrap'):
                                                            ui.icon('star', color='warning', size='13px')
                                                            ui.label(f"{rating:.1f}" if isinstance(rating, (int, float)) else str(rating)).classes('text-xs font-black text-gray-700')
                                                            if reviews_count:
                                                                ui.label(f"({reviews_count})").classes('text-[9px] text-gray-400')
                                                    if terjual:
                                                        with ui.row().classes('items-center gap-0.5 no-wrap'):
                                                            ui.icon('shopping_bag', color='grey-500', size='13px')
                                                            ui.label(f"{terjual:,}+ terjual".replace(',', '.')).classes('text-[10px] font-bold text-gray-500')

                                            # Right: Price Info & CTA
                                            with ui.column().classes('items-end justify-center gap-0.5 flex-shrink-0 min-w-[110px]'):
                                                # Original price with strikethrough
                                                if original_price_text and diskon_persen > 0:
                                                    with ui.row().classes('items-center gap-1 no-wrap'):
                                                        ui.label(f"-{diskon_persen}%").classes('text-[9px] font-extrabold text-white bg-gradient-to-r from-red-500 to-orange-500 px-1 py-0.5 rounded')
                                                        ui.label(original_price_text).classes('text-[10px] text-gray-400 line-through font-semibold')
                                                # Current price
                                                ui.label(price_text).classes(f'text-base font-extrabold {text_color_class}')
                                                # Price per unit (ml/g)
                                                if price_per_unit_text:
                                                    ui.label(price_per_unit_text).classes('text-[9px] text-gray-400 font-semibold')
                                                # CTA Button
                                                ui.button('Cek Toko', icon='open_in_new', on_click=lambda u=url: ui.run_javascript(f'window.open("{u}", "_blank")')).props(f'unelevated size=sm color={btn_color}').classes('mt-1 w-full font-bold text-[10px] py-0.5 rounded-lg text-white')

                                # 1. Tampilkan Sociolla Card (Original Source)
                                # Menandai Sociolla sebagai baseline referensi ukuran dan harga
                                ui.label('Original Baseline & Harga Referensi Filter').classes('text-xs font-bold text-pink-500 bg-pink-50 px-2 py-1 rounded w-fit mb-1')
                                
                                soc_name_for_card = product.get('name') or product.get('product_name') or ''
                                if product.get('id'):
                                    with SessionLocal() as _sess2:
                                        _ref2 = _sess2.query(SociollaReferensi).filter_by(id=product.get('id')).first()
                                        if _ref2 and hasattr(_ref2, 'variants') and _ref2.variants:
                                            try:
                                                import json
                                                v_list = _ref2.variants if isinstance(_ref2.variants, list) else json.loads(_ref2.variants)
                                                if v_list:
                                                    default_var = next((v for v in v_list if v.get('is_default')), v_list[0])
                                                    if default_var.get('variant_name'):
                                                        soc_name_for_card += " " + str(default_var.get('variant_name'))
                                            except Exception:
                                                pass

                                render_platform_card(
                                    platform_name='sociolla',
                                    card_border_class='border-pink-200 border-2 shadow-sm',
                                    hover_bg_class='hover:bg-pink-50/30',
                                    icon_color_style='color: #db2777;',
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
                                    free_ongkir=0,
                                    nama=soc_name_for_card
                                )
                                # 2. Tampilkan Tokopedia Card
                                if tokoped_db:
                                    # Ambil parameter baseline dari produk original Sociolla
                                    base_name = product.get('product_name', '') or product.get('name', '')
                                    base_size_val, base_size_unit = extract_size(base_name)
                                    base_price = product.get('min_price') or 0

                                    best_t = get_best_products(tokoped_db, base_price, base_size_val, base_size_unit, limit=5)
                                    for t_item in best_t:
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
                                            in_stock=t_item.get('in_stock', True),
                                            label_badge=t_item.get('label_badge'),
                                            free_ongkir=t_item.get('free_ongkir', 0),
                                            nama=t_item.get('nama', ''),
                                            kota=t_item.get('kota', '')
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
                                            title='Tokopedia (Rekomendasi)',
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
                                        with ui.card().classes('w-full p-4 border border-dashed border-green-200 bg-green-50/50 rounded-xl relative overflow-hidden'):
                                            # Shimmer effect
                                            ui.element('div').classes('absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/50 to-transparent animate-[shimmer_2s_infinite]')
                                            with ui.row().classes('w-full items-center justify-between no-wrap'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.icon('shopping_bag', color='green-400', size='20px')
                                                    ui.label('Cari di Tokopedia').classes('text-sm font-extrabold text-green-600')
                                                ui.label('Tekan Cek Harga 👇').classes('text-[10px] font-bold text-green-500 bg-green-100 px-2 py-1 rounded-lg animate-pulse')
                                # 3. Tampilkan Lazada Card
                                if lazad_db:
                                    best_l = get_best_products(lazad_db, base_price, base_size_val, base_size_unit, limit=5)
                                    for l_item in best_l:
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
                                            in_stock=l_item.get('in_stock', True),
                                            label_badge=l_item.get('label_badge'),
                                            free_ongkir=l_item.get('free_ongkir', 0),
                                            nama=l_item.get('nama', ''),
                                            kota=l_item.get('kota', '')
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
                                            title='Lazada (Rekomendasi)',
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
                                        with ui.card().classes('w-full p-4 border border-dashed border-blue-200 bg-blue-50/50 rounded-xl relative overflow-hidden'):
                                            # Shimmer effect
                                            ui.element('div').classes('absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/50 to-transparent animate-[shimmer_2s_infinite]')
                                            with ui.row().classes('w-full items-center justify-between no-wrap'):
                                                with ui.row().classes('items-center gap-2'):
                                                    ui.icon('shopping_bag', color='blue-400', size='20px')
                                                    ui.label('Cari di Lazada').classes('text-sm font-extrabold text-blue-600')
                                                ui.label('Tekan Cek Harga 👇').classes('text-[10px] font-bold text-blue-500 bg-blue-100 px-2 py-1 rounded-lg animate-pulse')
                                # 4. Tampilkan Shopee Card
                                if shopee_db:
                                    best_s = get_best_products(shopee_db, base_price, base_size_val, base_size_unit, limit=5)
                                    for s_item in best_s:
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
                                            free_ongkir=s_item.get('free_ongkir', 0),
                                            nama=s_item.get('nama', '')
                                        )
                                else:
                                    if shope_fuzzy:
                                        render_platform_card(
                                            platform_name='shopee',
                                            card_border_class='border-orange-100',
                                            hover_bg_class='hover:bg-orange-50/30',
                                            icon_color_style='color: #EA580C;',
                                            text_color_class='text-orange-600',
                                            title='Shopee (Rekomendasi)',
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
                                            ui.label('Belum ada link affiliate manual untuk produk ini.').classes('text-[10px] text-gray-400 italic')
                        
                        # Render prices initially saat modal pertama dibuka
                        refresh_prices()

                    # Live Scraper Trigger Button & Loading Spinner
                    with ui.column().classes('w-full gap-2 items-center'):
                        with ui.row().classes('items-center gap-3 bg-pink-50 px-4 py-2 rounded-full border border-pink-100 shadow-sm hidden') as loading_label:
                            ui.spinner('dots', size='lg', color='#ec4899')
                            ui.label('Sedang mencari harga terbaik...').classes('text-xs font-bold text-pink-600 tracking-wide')
                        
                        async def jalankan_live_scraping():
                            from app.ui.pages.syhid.search_page import scrape_marketplace_live
                            # Animasi Loading pada tombol
                            scrape_btn.props('loading=true')
                            loading_label.classes(remove='hidden')
                            
                            # Jalankan scraping asinkron
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(
                                None,
                                scrape_marketplace_live,
                                product.get('id'),
                                product.get('brand', ''),
                                product.get('product_name', '')
                            )
                            
                            # Selesai Loading
                            scrape_btn.props(remove='loading=true')
                            loading_label.classes('hidden')
                            

                            try:
                                ui.notify('🚀 Harga Tokopedia, Lazada & Shopee berhasil di-update secara live!', color='green', icon='flash_on')
                                refresh_prices()
                                if on_data_updated:
                                    on_data_updated()
                            except RuntimeError as e:
                                if "deleted" not in str(e).lower():
                                    raise
                            
                        scrape_btn = ui.button(
                            'Cari Harga Lazada & Tokopedia',
                            on_click=jalankan_live_scraping
                        ).classes('w-full bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-xl font-bold py-2.5 shadow-md hover:scale-[1.02] transition-all').props('no-caps icon=flash_on')
    dialog.open()
