from nicegui import ui
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import Produk
from sqlalchemy import or_
import re


def get_marketplace_price(p, platform):
    # 1. Cek if data sudah ada di dict (Hasil dari DataManager)
    mkt = p.get('marketplace', {})
    if isinstance(mkt, dict) and mkt.get(platform):
        return mkt[platform].get('harga')

    # 2. Cek by referensi_id jika ada id (Lebih akurat)
    pid = p.get('id')
    if pid:
        with SessionLocal() as session:
            best = session.query(Produk.harga).filter(
                Produk.referensi_id == pid,
                Produk.platform == platform
            ).order_by(Produk.harga.asc()).first()
            if best:
                return best[0]

    # 3. Fallback: Search logic (Nama/Brand)
    name = p.get("product_name", "") or ""
    brand = p.get("brand", "") or ""
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

    with SessionLocal() as session:
        rows = session.query(Produk.harga).filter(
            Produk.platform == platform,
            or_(*filters)
        ).all()

        prices = [r[0] for r in rows if r[0]]
        return min(prices) if prices else None


def get_marketplace_price_and_url(p, platform):
    # 1. Cek if data sudah ada di dict
    mkt = p.get('marketplace', {})
    if isinstance(mkt, dict) and mkt.get(platform):
        item = mkt[platform]
        return item.get('harga'), item.get('url')

    # 2. Cek by referensi_id
    pid = p.get('id')
    if pid:
        with SessionLocal() as session:
            best = session.query(Produk).filter(
                Produk.referensi_id == pid,
                Produk.platform == platform
            ).order_by(Produk.harga.asc()).first()
            if best:
                return best.harga, best.url

    # 3. Fallback search
    name = p.get("product_name", "") or ""
    brand = p.get("brand", "") or ""
    if not name and not brand:
        return None, None

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
        return None, None

    with SessionLocal() as session:
        best = session.query(Produk).filter(
            Produk.platform == platform,
            or_(*filters)
        ).order_by(Produk.harga.asc()).first()
        if best:
            return best.harga, best.url
    return None, None


def get_tokopedia_price(p):
    return get_marketplace_price(p, "tokopedia")


def get_lazada_price(p):
    return get_marketplace_price(p, "lazada")
    
def show_all_ingredients(ingredients):
    with ui.dialog() as dialog, ui.card():
        ui.label("Kandungan & Fungsinya").classes("font-bold mb-2")

        for ing in ingredients:
            label = ing.lower()

            if "niacinamide" in label:
                desc = "- Brightening"
            elif "hyaluronic" in label:
                desc = "- Hydrating"
            elif "centella" in label:
                desc = "- Soothing"
            elif "salicylic" in label:
                desc = "- Acne care"
            else:
                desc = ""

            ui.label(f"{ing} {desc}")

    dialog.open()

def get_main_ingredients(p):
    text = str(
        p.get('description_raw')
        or ''
    ).lower()

    if not text:
        return '-'

    keywords = {
        'niacinamide': 'Niacinamide',
        'hyaluronic': 'Hyaluronic Acid',
        'centella': 'Centella',
        'salicylic': 'Salicylic Acid',
        'ceramide': 'Ceramide',
        'retinol': 'Retinol',
        'tea tree': 'Tea Tree',
        'cica': 'Cica',
        'vitamin c': 'Vitamin C',
        'panthenol': 'Panthenol',
        'alpha arbutin': 'Alpha Arbutin',
        'tranexamic': 'Tranexamic Acid',
        'bha': 'BHA',
        'aha': 'AHA',
        'pha': 'PHA',
    }

    found = []

    for key, label in keywords.items():
        if key in text:
            found.append(label)

    found = list(dict.fromkeys(found))

    if not found:
        return '-'

    return ', '.join(found[:3])

    # hapus duplikat
    found = list(dict.fromkeys(found))

    if not found:
        return '-'

    return ', '.join(found[:3])

def infer_skin_types(p):
    # 1. Cek if explicit skin type exists
    if isinstance(p.get("skin_type"), (list, tuple)) and p.get("skin_type"):
        return list(p.get("skin_type"))
    if isinstance(p.get("skin_types"), (list, tuple)) and p.get("skin_types"):
        return list(p.get("skin_types"))
    if isinstance(p.get("skin_type"), str) and p.get("skin_type").strip():
        return [p.get("skin_type").strip()]
    if isinstance(p.get("skin_types"), str) and p.get("skin_types").strip():
        return [p.get("skin_types").strip()]

    ingredients_str = (p.get("ingredients") or "").lower()

    # 2. Scientific Active Ingredient Skin-Type Mapping
    skin_type_triggers = {
        "Oily": [
            "salicylic acid", "bha", "tea tree", "zinc pca", "niacinamide", "clay", "kaolin", 
            "bentonite", "charcoal", "witch hazel", "retinol", "retinoid"
        ],
        "Dry": [
            "hyaluronic acid", "sodium hyaluronate", "glycerin", "shea butter", "ceramide", 
            "squalane", "panthenol", "allantoin", "centella asiatica", "aloe vera", "honey",
            "urea", "butylene glycol", "propylene glycol", "vitamin e", "tocopherol"
        ],
        "Sensitive": [
            "centella asiatica", "cica", "ceramide", "allantoin", "panthenol", "chamomile", 
            "bisabolol", "oatmeal", "colloidal oatmeal", "aloe vera", "calendula", "green tea"
        ],
        "Combination": [
            "niacinamide", "hyaluronic acid", "sodium hyaluronate", "salicylic acid", "bha",
            "glycolic acid", "aha", "panthenol"
        ],
        "Normal": [
            "niacinamide", "vitamin c", "ascorbic acid", "hyaluronic acid", "glycerin", 
            "tocopherol", "ceramide", "panthenol"
        ]
    }
    
    found = []
    # If ingredients list is empty, fallback to strict title/description and review keyword scanning
    if not ingredients_str or len(ingredients_str.strip()) < 10:
        text_parts = [f"{p.get('product_name', '')} {p.get('description_raw', '')}"]
        for review in p.get("reviews", []):
            if isinstance(review, dict):
                comment = review.get("comment") or review.get("text") or ""
                text_parts.append(str(comment))
        text_to_scan = " ".join(text_parts).lower()
        
        patterns = {
            "Oily": ["berminyak", "oily", "oiliness", "minyak", "acne", "jerawat", "sebum control"],
            "Dry": ["kulit kering", "dry skin", "dry", "dehydrated", "hydrating", "moisture"],
            "Sensitive": ["kulit sensitif", "sensitive skin", "sensitif", "sensitive", "kemerahan", "redness", "iritasi", "soothing"],
            "Combination": ["kombinasi", "combination"],
            "Normal": ["normal skin", "normal", "semua jenis kulit", "all skin types"]
        }
        for label, keywords in patterns.items():
            if any(k in text_to_scan for k in keywords):
                found.append(label)
    else:
        # Perform rigorous scientific active ingredient scan
        for label, actives in skin_type_triggers.items():
            if any(active in ingredients_str for active in actives):
                found.append(label)

    # Clean default fallback
    if not found:
        return ["Normal"]
    
    return list(dict.fromkeys(found))


def get_best_price(p):
    prices = [
        p.get("min_price"),              # Sociolla
        get_tokopedia_price(p),          # Tokopedia
        get_lazada_price(p)              # Lazada
    ]

    valid = [x for x in prices if x]
    return min(valid) if valid else 0

def get_cheapest_marketplace(p):
    prices = {
        'Sociolla': p.get('min_price'),
        'Tokopedia': get_tokopedia_price(p),
        'Lazada': get_lazada_price(p)
    }

    valid_prices = {
        k: v for k, v in prices.items()
        if v and v > 0
    }

    if not valid_prices:
        return '-'

    cheapest = min(valid_prices, key=valid_prices.get)
    return f"{cheapest} ({format_rupiah(valid_prices[cheapest])})"

def get_best_marketplace_url(p):
    prices = {
        'sociolla': (
            p.get('min_price'),
            p.get('url_sociolla')
        ),

        'tokopedia': (
            get_tokopedia_price(p),
            p.get('url_tokopedia')
        ),

        'lazada': (
            get_lazada_price(p),
            p.get('url_lazada')
        )
    }

    valid = {
        k: v for k, v in prices.items()
        if v[0] and v[1]
    }

    if not valid:
        return 'https://www.sociolla.com'

    cheapest = min(valid, key=lambda x: valid[x][0])

    return valid[cheapest][1]

def format_rupiah(value):
    try:
        return f"Rp{int(value):,}".replace(',', '.')
    except:
        return '-'

def show_page():
    """NAJLA'S MISSION: Enhanced Comparison Page with Low Cognitive Load & Poka-yoke."""
    
    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    # --- STATE MANAGEMENT ---
    if 'compare_slots' not in state.__dict__:
        state.__dict__['compare_slots'] = [None, None, None]
    if 'selected_compare_category' not in state.__dict__:
        state.__dict__['selected_compare_category'] = None

    # --- DATA FETCHING ---
    with SessionLocal() as session:
        categories = data_mgr.categories # Get dynamic categories
        # Remove 'All' and 'Lainnya' for template-based search
        clean_categories = [c for c in categories if c not in ['All', 'Lainnya']]

    def select_category(cat):
        state.__dict__['selected_compare_category'] = cat
        state.__dict__['compare_slots'] = [None, None, None]
        main_container.refresh()
        ui.notify(f"Mode Perbandingan: {cat}", icon='category')

    def reset_comparison():
        state.__dict__['selected_compare_category'] = None
        state.__dict__['compare_slots'] = [None, None, None]
        main_container.refresh()

    def add_to_slot(slot_idx, product):
        state.__dict__['compare_slots'][slot_idx] = product
        main_container.refresh()
        ui.notify(f"Ditambahkan: {product['product_name']}", color='green')

    def remove_from_slot(slot_idx):
        state.__dict__['compare_slots'][slot_idx] = None
        main_container.refresh()

    def add_to_wishlist(product):
        if 'wishlist' not in state.__dict__:
            state.__dict__['wishlist'] = []

        wishlist = state.__dict__['wishlist']

        exists = any(
            item.get('id') == product.get('id')
            for item in wishlist
        )

        if exists:
            ui.notify('Produk sudah ada di wishlist!', color='orange')
            return
        
        wishlist.append(product)
        ui.notify('Produk ditambahkan ke wishlist', icon='check_circle', color='green')

    # --- SEARCH DIALOG ---
    def open_search_dialog(slot_idx):
        category = state.__dict__['selected_compare_category']
        if not category:
            ui.notify("Pilih kategori terlebih dahulu!", color='blue')
            return

        with ui.dialog().classes('w-full max-w-2xl') as dialog, ui.card().classes('w-full p-6 bg-white shadow-2xl rounded-2xl border-none'):
            ui.label(f"Cari {category}").classes('text-xl font-black text-gray-800 mb-4')

            search_input = ui.input('Ketik nama produk atau brand...').classes('w-full mb-4').props('outlined rounded dense')
            
            product_list_container = ui.column().classes('w-full gap-2 max-h-96 overflow-y-auto')

            def update_search():
                """FIX #5: Server-side search dengan items_per_page=24 (bukan 500 sekaligus)."""
                product_list_container.clear()
                term = search_input.value.strip()

                # Query ke server dengan keyword sehingga DB yang filter, bukan Python
                search_data = data_mgr.get_paginated_products(
                    category_filter=category,
                    keyword=term,
                    items_per_page=24   # Load max 24, cukup untuk dialog
                )
                filtered = search_data['items']
                
                if not filtered:
                    with product_list_container:
                        ui.label('Produk tidak ditemukan.').classes('text-gray-400 italic p-4')
                else:
                    for p in filtered:
                        with product_list_container:
                            with ui.row().classes('w-full items-center justify-between p-3 hover:bg-pink-50 rounded-xl cursor-pointer border border-transparent hover:border-pink-200 transition-all') \
                                .on('click', lambda p=p: (add_to_slot(slot_idx, p), dialog.close())):
                                with ui.row().classes('items-center gap-3'):
                                    if p.get('image_url') and str(p['image_url']).startswith('http'):
                                        ui.image(p['image_url']).classes('w-10 h-10 object-contain')
                                    else:
                                        ui.icon('inventory_2', size='28px', color='pink-200')
                                    with ui.column().classes('gap-0'):
                                        ui.label(p['brand']).classes('text-[10px] font-black text-pink-400 uppercase')
                                        ui.label(p['product_name']).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                ui.icon('add_circle', color='pink-300')

            search_input.on('keydown.enter', update_search)
            search_input.on('blur', update_search)
            # Load awal tanpa keyword
            update_search()
        dialog.open()

    # --- UI LAYOUT ---
    @ui.refreshable
    def main_container():
        selected_cat = state.__dict__['selected_compare_category']
        slots = state.__dict__['compare_slots']

        with ui.column().classes('w-full p-8 gap-8 bg-transparent'):
            
            # HEADER
            with ui.row().classes('w-full items-center justify-between'):
                with ui.column().classes('gap-1'):
                    ui.label('Bandingkan Produk').classes('text-4xl font-black text-gray-800 tracking-tight')
                    ui.label('Pilih kategori dan bandingkan hingga 3 produk secara akurat.').classes('text-gray-500 font-medium')
                
                if selected_cat:
                    ui.button('Ganti Kategori', icon='swap_horiz', on_click=reset_comparison).classes('btn-primary').props('unelevated rounded')

            # STEP 1: CATEGORY PICKER (Poka-yoke: Force Category First)
            if not selected_cat:
                with ui.column().classes('w-full gap-6 items-center py-12'):
                    ui.label('Langkah 1: Pilih Kategori Produk').classes('text-xs font-black text-pink-400 tracking-[0.2em] uppercase')
                    
                    with ui.row().classes('w-full justify-center gap-6 flex-wrap'):
                        # Define Icons for Categories
                        cat_icons = {
                            'Serum': 'water_drop',
                            'Moisturizer': 'spa',
                            'Sunscreen': 'light_mode',
                            'Toner': 'opacity',
                            'Cleanser': 'cleaning_services',
                            'Mask': 'face',
                            'Eye Care': 'visibility',
                            'Cushion': 'face_retouching_natural',
                            'Blush': 'flare',
                            'Powder': 'blur_on',
                            'Eye Product': 'visibility',
                            'LIP Product': 'brush',
                            'Lainnya': 'more_horiz'
                        }
                        
                        MAKEUP_CATS = {'Cushion', 'Blush', 'Powder', 'Eye Product', 'LIP Product'}
                        
                        for cat in clean_categories:
                            icon = cat_icons.get(cat, 'category')
                            icon_color = 'text-blue-400 group-hover:text-blue-600' if cat in MAKEUP_CATS else 'text-pink-300 group-hover:text-pink-500'
                            
                            with ui.card().classes('w-40 h-40 items-center justify-center gap-3 cursor-pointer glass-card border-none hover:scale-105 transition-all group') \
                                .on('click', lambda c=cat: select_category(c)):
                                ui.icon(icon, size='48px').classes(f'{icon_color} transition-colors')
                                ui.label(cat).classes('font-black text-gray-700 tracking-wide')

                    # TEMPLATES (Low Cognitive Load)
                    ui.label('— ATAU PILIH TEMPLATE —').classes('text-[10px] text-gray-300 font-black mt-8')
                    with ui.row().classes('gap-4 mt-2'):
                        templates = [
                            ("Serum Pencerah", "Serum"),
                            ("Moisturizer Viral", "Moisturizer"),
                            ("Sunscreen Terbaik", "Sunscreen")
                        ]
                        for title, cat in templates:
                            ui.button(title, on_click=lambda c=cat: select_category(c)).props('outline rounded size=sm').classes('text-pink-400 border-pink-100')

            # STEP 2: COMPARISON SLOTS & ANALYSIS (Unified for Low Cognitive Load)
            else:
                with ui.card().classes('w-full p-0 glass-card border-none overflow-hidden'):
                    # --- HEADER ROW (Product Info) ---
                    with ui.row().classes('w-full gap-0 items-stretch border-b border-pink-50/50'):
                        # Label Column Spacer
                        ui.element('div').classes('w-48 shrink-0 bg-pink-50/10')
                        
                        for i in range(3):
                            product = slots[i]
                            # Column border for separation
                            border_class = 'border-l border-pink-50/50' if i > 0 else ''
                            
                            with ui.column().classes(f'flex-1 p-6 items-center gap-4 {border_class}'):
                                if not product:
                                    # EMPTY SLOT
                                    with ui.column().classes('w-full h-full items-center justify-center py-12 gap-3 border-2 border-dashed border-pink-200/60 bg-pink-50/10 hover:bg-pink-50/50 rounded-[2rem] transition-all cursor-pointer group') \
                                        .on('click', lambda i=i: open_search_dialog(i)):
                                        with ui.element('div').classes('p-4 bg-white/80 rounded-full shadow-sm group-hover:shadow-md group-hover:scale-110 transition-all flex items-center justify-center'):
                                            ui.icon('add', size='28px').classes('text-pink-400')
                                        ui.label('Tambah Produk').classes('text-pink-400 font-bold text-sm')
                                else:
                                    # FILLED SLOT
                                    with ui.row().classes('w-full justify-between items-start mb-2'):
                                        ui.label(f'0{i+1}').classes('text-pink-300 font-black text-lg tracking-tighter')
                                        ui.button(icon='close', on_click=lambda i=i: remove_from_slot(i)).props('flat round dense size=sm').classes('text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors')
                                    
                                    with ui.element('div').classes('w-32 h-32 bg-white rounded-3xl p-3 border border-pink-100/50 flex items-center justify-center shadow-sm hover:shadow-md transition-shadow relative group'):
                                        ui.image(product['image_url']).classes('w-full h-full object-contain group-hover:scale-105 transition-transform duration-300')
                                        with ui.element('div').classes('absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity'):
                                            ui.button(icon='favorite_border', on_click=lambda p=product: add_to_wishlist(p)).props('flat round dense size=sm').classes('bg-white/90 text-pink-500 shadow-sm hover:bg-pink-50')
                                    
                                    with ui.column().classes('items-center gap-1 w-full mt-4'):
                                        ui.label(product['brand']).classes('text-[10px] font-black text-pink-400 tracking-widest uppercase')
                                        ui.label(product['product_name']).classes('text-sm font-bold text-gray-800 text-center line-clamp-2 min-h-[40px] leading-snug')
                                        
                                    ui.label(
                                        f"Rp{int(product.get('min_price', 0)):,}".replace(',', '.')
                                    ).classes('text-lg font-black text-gray-900 mt-2')

                    # --- FIX #7: BATCH MARKETPLACE QUERIES (N+1 → 1 Query) ---
                    filled_slots = [p for p in slots if p]
                    filled_slot_ids = [p['id'] for p in filled_slots if p and p.get('id')]
                    _mkt_prices_by_id = {}
                    if filled_slot_ids:
                        with SessionLocal() as _sess:
                            _mkt_rows = _sess.query(Produk).filter(
                                Produk.referensi_id.in_(filled_slot_ids),
                                Produk.harga > 0
                            ).order_by(Produk.harga.asc()).all()
                        for _p in _mkt_rows:
                            _rid = _p.referensi_id
                            _plat = str(_p.platform).lower()
                            if _rid not in _mkt_prices_by_id:
                                _mkt_prices_by_id[_rid] = {}
                            if _plat not in _mkt_prices_by_id[_rid]:
                                _mkt_prices_by_id[_rid][_plat] = {
                                    'harga': _p.harga,
                                    'url':   _p.url
                                }

                    def _cheapest_from_batch(p, mkt_map):
                        rid = p.get('id')
                        prices = {'Sociolla': p.get('min_price')}
                        if rid and rid in mkt_map:
                            for plat, data in mkt_map[rid].items():
                                prices[plat.title()] = data.get('harga')
                        valid = {k: v for k, v in prices.items() if v and v > 0}
                        if not valid:
                            return '-'
                        cheapest = min(valid, key=valid.get)
                        return f"{cheapest} (Rp{int(valid[cheapest]):,})".replace(',', '.')

                    def get_repurchase_text(p):
                        total = p.get('repurchase_yes', 0) + p.get('repurchase_no', 0) + p.get('repurchase_maybe', 0)
                        if total == 0: return "-"
                        pct = (p['repurchase_yes'] / total) * 100
                        return f"{pct:.0f}% Repurchase"

                    comparison_rows = [
                        ('Harga Sociolla', lambda p: f"Rp{int(p.get('min_price', 0)):,}".replace(',', '.') if p.get('min_price') else "-"),
                        ('Tokopedia', lambda p, _mp=_mkt_prices_by_id: f"Rp{int(_mp.get(p.get('id'), {}).get('tokopedia', {}).get('harga', 0)):,}".replace(',', '.') if _mp.get(p.get('id'), {}).get('tokopedia') else "-"),
                        ('Lazada',    lambda p, _mp=_mkt_prices_by_id: f"Rp{int(_mp.get(p.get('id'), {}).get('lazada', {}).get('harga', 0)):,}".replace(',', '.') if _mp.get(p.get('id'), {}).get('lazada') else "-"),
                        ('Harga / ml', lambda p: safe_price_per_ml(p)),
                        ('Volume', lambda p: get_volume(p)),
                        ('Bahan Utama', lambda p: get_main_ingredients(p)),
                        ('Jenis Kulit', lambda p: ', '.join(infer_skin_types(p)[:2] or ['-'])),
                        ('BPOM', lambda p: p.get('bpom_reg_no') or "-"),
                        ('Rating', lambda p: format_rating(p)),
                        ('Termurah', lambda p, _mp=_mkt_prices_by_id: _cheapest_from_batch(p, _mp)),
                    ]

                    # Platform styling — URL untuk interactive badges (gunakan data batch juga)
                    mkt_data = {
                        'Harga Sociolla': ('pink',    lambda p, _mp=_mkt_prices_by_id: (p.get('min_price'), p.get('url_sociolla') or p.get('url') or 'https://www.sociolla.com')),
                        'Tokopedia':      ('green',   lambda p, _mp=_mkt_prices_by_id: (_mp.get(p.get('id'), {}).get('tokopedia', {}).get('harga'), _mp.get(p.get('id'), {}).get('tokopedia', {}).get('url'))),
                        'Lazada':         ('blue',    lambda p, _mp=_mkt_prices_by_id: (_mp.get(p.get('id'), {}).get('lazada',    {}).get('harga'), _mp.get(p.get('id'), {}).get('lazada',    {}).get('url'))),
                    }
                    for label, extractor in comparison_rows:
                        with ui.row().classes('w-full gap-0 items-center border-b border-pink-50/50 hover:bg-white/60 transition-all'):
                            # Row Label (Lebih terbaca, warna lebih lembut)
                            with ui.element('div').classes('w-48 shrink-0 p-4 bg-pink-50/30'):
                                ui.label(label).classes('text-sm font-semibold text-gray-600')
                            for i in range(3):
                                p = slots[i]
                                border_class = 'border-l border-pink-50/20' if i > 0 else ''
                                with ui.element('div').classes(f'flex-1 p-4 text-center {border_class}'):
                                    if p:
                                        if label in mkt_data:
                                            color, getter = mkt_data[label]
                                            price, url = getter(p)
                                            if price and url:
                                                with ui.link('', target=url, new_tab=True).classes('no-underline inline-block'):
                                                    with ui.element('div').classes(f'bg-{color}-50 hover:bg-{color}-100 text-{color}-700 border border-{color}-200 px-3 py-1.5 rounded-xl text-xs font-black flex items-center gap-1.5 transition-all hover:scale-105 shadow-sm'):
                                                        ui.icon('open_in_new', size='12px').classes(f'text-{color}-500')
                                                        ui.label(f"Rp{int(price):,}".replace(',', '.'))
                                            else:
                                                ui.label('-').classes('text-gray-300')
                                        else:
                                            ui.label(extractor(p)).classes('text-xs font-bold text-gray-700')
                                    else:
                                        ui.label('-').classes('text-gray-300')

                # --- KALKULASI HARGA TOTAL ---
                if len(filled_slots) >= 1:
                    with ui.card().classes('w-full mt-10 p-8 glass-card border-none bg-pink-50/30'):
                        ui.label('KALKULASI HARGA TOTAL').classes('text-xs font-black text-pink-400 tracking-[0.2em] uppercase mb-4')
                        total_price = 0
                        for p in filled_slots:
                            best_p = get_best_price(p)
                            total_price += best_p
                            with ui.row().classes('w-full justify-between items-center py-2 border-b border-pink-100/50 last:border-0'):
                                ui.label(f"{p['brand']} {p['product_name']}").classes('text-sm font-bold text-gray-700')
                                ui.label(f"Rp {int(best_p):,}").classes('text-sm font-black text-gray-900')
                        with ui.row().classes('w-full justify-between items-center pt-4 mt-2 border-t-2 border-pink-200'):
                            ui.label('TOTAL HARGA').classes('text-lg font-black text-pink-500')
                            ui.label(f"Rp {int(total_price):,}").classes('text-2xl font-black text-pink-600')

                # --- VISUAL ANALYSIS (Separate for spacing) ---
                if len(filled_slots) >= 2:
                    with ui.column().classes('w-full mt-10 gap-6'):
                        ui.label('VISUALISASI DATA').classes('text-xs font-black text-pink-400 tracking-[0.2em] uppercase')
                        
                        with ui.row().classes('w-full gap-8'):
                            # Price Bar Chart
                            with ui.card().classes('flex-1 p-8 glass-card border-none h-80'):
                                ui.label('KOMPARASI HARGA').classes('text-[9px] font-black text-gray-400 tracking-widest mb-4')
                                names = [p['brand'] for p in filled_slots]
                                prices = [get_best_price(p) for p in filled_slots]
                                ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis'
                                    },

                                    'xAxis': {
                                        'type': 'category',
                                        'data': names,
                                        'axisLabel': {
                                            'fontSize': 10,
                                            'rotate': 10
                                        }
                                    },

                                    'yAxis': {
                                        'type': 'value'
                                    },

                                    'series': [{
                                    'data': prices,
                                    'type': 'bar',
                                    'barWidth': '45%',
                                    'itemStyle': {
                                        'borderRadius': [12, 12, 0, 0],
                                        'color': '#EC4899'
                                    },

                                    'label': {
                                        'show': True,
                                        'position': 'top',
                                        'formatter': 'Rp {c}'
                                    }
                                }]
                            }).classes('w-full h-full')

                            # Rating Bar Chart
                            with ui.card().classes('flex-1 p-8 glass-card border-none h-80'):
                                ui.label('KOMPARASI RATING').classes('text-[9px] font-black text-gray-400 tracking-widest mb-4')
                                ratings = [p.get('average_rating') or 0 for p in filled_slots]
                                ui.echart({
                                    'tooltip': {
                                        'trigger': 'axis'
                                    },

                                    'xAxis': {
                                        'type': 'category',
                                        'data': names,
                                        'axisLabel': {
                                            'fontSize': 10
                                        }
                                    },

                                    'yAxis': {
                                        'type': 'value',
                                        'max': 5
                                    },

                                    'series': [{
                                        'data': ratings,
                                        'type': 'bar',
                                        'barWidth': '45%',

                                        'itemStyle': {
                                            'borderRadius': [12, 12, 0, 0],
                                            'color': "#ECBD48"
                                        },

                                        'label': {
                                            'show': True,
                                            'position': 'top'
                                        }
                                    }]
                                }).classes('w-full h-full')

                            
                        # WINNER RECOMMENDATION
                        best_v = max(filled_slots, key=lambda x: (x.get('average_rating') or 0) / (x.get('min_price') or 1))
                        with ui.card().classes('w-full p-8 bg-gradient-to-r from-pink-500 to-blue-600 text-white border-none rounded-[2.5rem] items-center flex-row gap-8 shadow-2xl mt-4'):
                            ui.icon('emoji_events', size='56px', color='yellow-300').classes('animate-bounce')
                            with ui.column().classes('gap-1'):
                                ui.label('SKINTIFY CHOICE').classes('text-[9px] font-black text-pink-200 tracking-[0.2em]')
                                ui.label(f"{best_v['brand']} {best_v['product_name']}").classes('text-xl font-black')
                                ui.label('Rekomendasi terbaik berdasarkan analisis harga dan kepuasan pengguna.').classes('text-xs font-medium text-pink-100')
                            ui.space()
                            ui.button(
                                'Beli Termurah',
                                on_click=lambda p=best_v: ui.open(
                                    get_best_marketplace_url(p),
                                    new_tab=True
                                )
                            ).props('unelevated rounded').classes(
                                'bg-white text-pink-600 font-black px-8 py-3'
                            )

                else:
                    # Not enough products to compare
                    with ui.card().classes('w-full p-16 items-center justify-center border-none glass-card bg-white/40 mt-10'):
                        ui.icon('compare_arrows', size='48px', color='pink-100')
                        ui.label('Tambah minimal 2 produk untuk melihat grafik perbandingan.').classes('text-gray-400 font-bold mt-4')

    main_container()

# --- UTILITY FUNCTIONS (NAJLA: JANGAN DIHAPUS) ---
def get_volume(p):
    try:
        variants = p.get("variants", [])
        if not variants: return "-"
        text = variants[0].get("variant_name", "")
        match = re.search(r'\d+', text)
        return f"{match.group()} ml" if match else "-"
    except: return "-"

def safe_price_per_ml(p):
    try:
        variants = p.get("variants", [])
        if not variants: return "-"
        text = variants[0].get("variant_name", "")
        match = re.search(r'\d+', text)
        if not match: return "-"
        volume = int(match.group())
        if volume == 0: return "-"
        return f"Rp{int(p['min_price']/volume):,}"
    except: return "-"

def format_rating(p):
    rating = p.get('average_rating')

    if rating is None:
        return '-'

    rating = float(rating)

    if rating.is_integer():
        return f"{int(rating)}/5"

    return f"{rating}/5"
    # --- AKHIR AREA BELAJAR ---
