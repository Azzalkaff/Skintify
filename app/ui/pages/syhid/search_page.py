from nicegui import ui
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import Produk, Toko, SociollaReferensi
from sqlalchemy import or_

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
                    'shop_name': best_prod.toko.nama if best_prod.toko else None
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
                'shop_name': best_prod.toko.nama if best_prod.toko else None
            }
    return None

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

    # 2. Refreshable Status Bar (Optional, jika ada)
    @ui.refreshable
    def taskbar_status() -> None:
        analysis = data_mgr.analyze_routine(state.routine, kota=state.kota)
        UIComponents.routine_status_badge(analysis)

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
                search_input = ui.input(placeholder='Cari nama produk...').classes('w-full mb-3')
                
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
                sort_options = ['Rating (Tertinggi)', 'Harga (Terendah)', 'Harga (Tertinggi)']
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
                
                # 1. Detail Dialog
                detail_data = {'p': {}, 'g': '', 'a': '', 'ic': ''}
                with ui.dialog() as detail_modal, ui.card().classes('p-0 w-[500px] overflow-hidden rounded-2xl') as detail_card:
                    @ui.refreshable
                    def detail_content():
                        p, g, a, ic = detail_data['p'], detail_data['g'], detail_data['a'], detail_data['ic']
                        if not p: return
                        with ui.element('div').classes('w-full h-52 bg-gray-50 flex items-center justify-center overflow-hidden'):
                            if p.get('image_url') and str(p.get('image_url')).startswith('http'):
                                ui.image(p['image_url']).classes('w-full h-full object-contain').style('mix-blend-mode:multiply')
                            else:
                                ui.label(ic).classes('text-6xl')
                        
                        with ui.column().classes('p-6 gap-2 w-full'):
                            # Brand & Country
                            with ui.row().classes('w-full justify-between items-start'):
                                with ui.column().classes('gap-0'):
                                    brand_label = p.get('brand', '-')
                                    if p.get('brand_country'):
                                        brand_label += f" ({p['brand_country']})"
                                    ui.label(brand_label).classes('text-xs font-black text-pink-400 uppercase tracking-widest')
                                    ui.label(p.get('product_name', '-')).classes('text-xl font-black text-gray-800 leading-tight')
                            
                            # Price & Rating
                            with ui.row().classes('items-center gap-4 mt-1'):
                                ui.label(f"Rp{p.get('min_price', 0):,.0f}".replace(',', '.')).classes('text-pink-500 font-black text-lg')
                                rating_v = p.get('average_rating') or p.get('rating') or 0
                                with ui.row().classes('items-center gap-1 bg-yellow-50 px-2 py-0.5 rounded-lg'):
                                    ui.icon('star', color='yellow-500', size='16px')
                                    ui.label(f'{rating_v}').classes('text-yellow-700 text-xs font-bold')
                                ui.label(p.get('category', '-')).classes('text-[10px] font-bold bg-pink-50 text-pink-500 px-2 py-0.5 rounded-full')

                            # BPOM
                            if p.get('bpom_reg_no'):
                                with ui.row().classes('items-center gap-1 mt-1'):
                                    ui.icon('verified', color='blue-400', size='14px')
                                    ui.label(f"BPOM: {p['bpom_reg_no']}").classes('text-[10px] font-bold text-gray-400')

                            # Repurchase Stats
                            if p.get('repurchase_yes') or p.get('repurchase_no'):
                                total = p.get('repurchase_yes', 0) + p.get('repurchase_no', 0) + p.get('repurchase_maybe', 0)
                                if total > 0:
                                    yes_pct = (p['repurchase_yes'] / total) * 100
                                    with ui.column().classes('w-full gap-1 mt-3 p-3 bg-gray-50 rounded-xl border border-gray-100'):
                                        with ui.row().classes('w-full justify-between items-center'):
                                            with ui.column().classes('gap-0'):
                                                ui.label('Repurchase Rate').classes('text-[10px] font-black text-gray-500 uppercase tracking-wider')
                                                ui.label(f"{p.get('total_recommended', 0)} User Merekomendasikan").classes('text-[8px] text-gray-400')
                                            ui.label(f"{yes_pct:.0f}%").classes('text-xs font-black text-green-600')
                                        with ui.element('div').classes('w-full h-2 bg-gray-200 rounded-full overflow-hidden'):
                                            ui.element('div').style(f'width: {yes_pct}%').classes('h-full bg-gradient-to-r from-green-400 to-emerald-500')

                            # Scrollable Text Area
                            with ui.scroll_area().classes('w-full h-64 mt-4 pr-3'):
                                with ui.column().classes('gap-4'):
                                    if p.get('description_raw'):
                                        with ui.column().classes('gap-1'):
                                            ui.label('Tentang Produk').classes('font-black text-xs text-gray-700 uppercase tracking-wider')
                                            ui.html(p['description_raw']).classes('text-xs text-gray-500 leading-relaxed')
                                    
                                    if p.get('how_to_use_raw'):
                                        with ui.column().classes('gap-1'):
                                            ui.label('Cara Penggunaan').classes('font-black text-xs text-gray-700 uppercase tracking-wider')
                                            ui.html(p['how_to_use_raw']).classes('text-xs text-gray-500 leading-relaxed')

                                    with ui.column().classes('gap-1'):
                                        ui.label('Kandungan Lengkap').classes('font-black text-xs text-gray-700 uppercase tracking-wider')
                                        raw_ing = p.get('ingredients') or '-'
                                        ui.label(raw_ing).classes('text-xs text-gray-500 leading-relaxed')

                            # ── MARKETPLACE PRICE COMPARISON ──
                            ui.separator().classes('my-2')
                            with ui.column().classes('w-full gap-2 mt-1'):
                                ui.label('Perbandingan Harga Marketplace').classes('text-[10px] font-black text-gray-400 uppercase tracking-widest')
                                
                                with ui.row().classes('w-full gap-2 items-center justify-between'):
                                    # 1. Sociolla Price
                                    s_price = p.get('min_price')
                                    s_price_str = f"Rp{s_price:,.0f}".replace(',', '.') if s_price else '-'
                                    with ui.card().classes('flex-1 p-3 items-center gap-1 border border-pink-100 bg-pink-50/20 hover:bg-pink-50/50 cursor-pointer shadow-none rounded-xl transition-all') \
                                        .on('click', lambda: ui.open(p.get('url_sociolla') or 'https://www.sociolla.com', new_tab=True)):
                                        ui.icon('spa', color='pink-500', size='20px')
                                        ui.label('Sociolla').classes('text-[9px] font-black text-pink-500 uppercase tracking-wider')
                                        ui.label(s_price_str).classes('text-xs font-black text-gray-800')
                                    
                                    # 2. Tokopedia Price
                                    topo = get_best_marketplace_product(p, 'tokopedia')
                                    t_price_str = f"Rp{topo['price']:,.0f}".replace(',', '.') if topo else 'Tidak Ada'
                                    with ui.card().classes('flex-1 p-3 items-center gap-1 border border-green-100 bg-green-50/20 hover:bg-green-50/50 cursor-pointer shadow-none rounded-xl transition-all') \
                                        .on('click', lambda: ui.open(topo['url'] if topo else 'https://www.tokopedia.com', new_tab=True) if topo else None):
                                        ui.icon('shopping_bag', color='green-500', size='20px')
                                        ui.label('Tokopedia').classes('text-[9px] font-black text-green-600 uppercase tracking-wider')
                                        ui.label(t_price_str).classes('text-xs font-black text-gray-800' if topo else 'text-[10px] text-gray-400 font-bold')
                                    
                                    # 3. Lazada Price
                                    laza = get_best_marketplace_product(p, 'lazada')
                                    l_price_str = f"Rp{laza['price']:,.0f}".replace(',', '.') if laza else 'Tidak Ada'
                                    with ui.card().classes('flex-1 p-3 items-center gap-1 border border-blue-100 bg-blue-50/20 hover:bg-blue-50/50 cursor-pointer shadow-none rounded-xl transition-all') \
                                        .on('click', lambda: ui.open(laza['url'] if laza else 'https://www.lazada.co.id', new_tab=True) if laza else None):
                                        ui.icon('shopping_cart', color='blue-500', size='20px')
                                        ui.label('Lazada').classes('text-[9px] font-black text-blue-600 uppercase tracking-wider')
                                        ui.label(l_price_str).classes('text-xs font-black text-gray-800' if laza else 'text-[10px] text-gray-400 font-bold')
 
                            # Footer
                            with ui.row().classes('w-full gap-2 mt-4'):
                                if p.get('url_sociolla'):
                                    ui.button('Lihat di Sociolla ↗', on_click=lambda: ui.open(p['url_sociolla'], new_tab=True)).props('flat').classes('flex-1 text-blue-500 text-xs font-bold bg-blue-50 rounded-xl')
                                ui.button('Tutup', on_click=detail_modal.close).props('flat').classes('flex-1 text-gray-500 text-xs font-bold bg-gray-100 rounded-xl')
                    detail_content()

                def open_detail(p, g, a, ic):
                    # Save to recent
                    recent = state.__dict__.get('recent_products', [])
                    if not any(x.get('slug') == p.get('slug') for x in recent):
                        recent.insert(0, p)
                        state.__dict__['recent_products'] = recent[:5]
                    # Update & Open
                    detail_data.update({'p': p, 'g': g, 'a': a, 'ic': ic})
                    detail_modal.open()

                # --- 1.5. Dialog Perbandingan Harga Marketplace ---
                compare_data = {'p': {}}
                with ui.dialog() as compare_modal, ui.card().classes('p-0 w-[1100px] max-w-[95vw] overflow-hidden rounded-2xl bg-white shadow-2xl') as compare_card:
                    @ui.refreshable
                    def compare_content():
                        p = compare_data['p']
                        if not p: return
                        
                        # Fetch all marketplace products for this reference ID
                        pid = p.get('id')
                        tokopedia_products = []
                        lazada_products = []
                        
                        if pid:
                            with SessionLocal() as session:
                                db_prods = session.query(Produk).filter(Produk.referensi_id == pid).all()
                                for dp in db_prods:
                                    dp_data = {
                                        'nama': dp.nama,
                                        'harga': dp.harga,
                                        'harga_asli': dp.harga_asli,
                                        'diskon_persen': dp.diskon_persen,
                                        'url': dp.url,
                                        'gambar': dp.gambar,
                                        'rating': dp.rating,
                                        'jumlah_review': dp.jumlah_review,
                                        'terjual': dp.terjual,
                                        'badge': dp.label_badge,
                                        'shop_name': dp.toko.nama if dp.toko else 'Toko Skincare',
                                        'shop_kota': dp.toko.kota if dp.toko else 'Indonesia',
                                        'shop_official': dp.toko.is_official if dp.toko else False,
                                        'free_ongkir': dp.free_ongkir
                                    }
                                    if dp.platform.lower() == 'tokopedia':
                                        tokopedia_products.append(dp_data)
                                    elif dp.platform.lower() == 'lazada':
                                        lazada_products.append(dp_data)
                                        
                        # Fallback: jika relasi direct kosong, cari dengan get_best_marketplace_product
                        if not tokopedia_products:
                            topo = get_best_marketplace_product(p, 'tokopedia')
                            if topo:
                                with SessionLocal() as session:
                                    dp = session.query(Produk).filter(Produk.url == topo['url']).first()
                                    if dp:
                                        tokopedia_products.append({
                                            'nama': dp.nama,
                                            'harga': dp.harga,
                                            'harga_asli': dp.harga_asli,
                                            'diskon_persen': dp.diskon_persen,
                                            'url': dp.url,
                                            'gambar': dp.gambar,
                                            'rating': dp.rating,
                                            'jumlah_review': dp.jumlah_review,
                                            'terjual': dp.terjual,
                                            'badge': dp.label_badge,
                                            'shop_name': dp.toko.nama if dp.toko else topo['shop_name'],
                                            'shop_kota': dp.toko.kota if dp.toko else 'Indonesia',
                                            'shop_official': dp.toko.is_official if dp.toko else False,
                                            'free_ongkir': dp.free_ongkir
                                        })
                        if not lazada_products:
                            laza = get_best_marketplace_product(p, 'lazada')
                            if laza:
                                with SessionLocal() as session:
                                    dp = session.query(Produk).filter(Produk.url == laza['url']).first()
                                    if dp:
                                        lazada_products.append({
                                            'nama': dp.nama,
                                            'harga': dp.harga,
                                            'harga_asli': dp.harga_asli,
                                            'diskon_persen': dp.diskon_persen,
                                            'url': dp.url,
                                            'gambar': dp.gambar,
                                            'rating': dp.rating,
                                            'jumlah_review': dp.jumlah_review,
                                            'terjual': dp.terjual,
                                            'badge': dp.label_badge,
                                            'shop_name': dp.toko.nama if dp.toko else laza['shop_name'],
                                            'shop_kota': dp.toko.kota if dp.toko else 'Indonesia',
                                            'shop_official': dp.toko.is_official if dp.toko else False,
                                            'free_ongkir': dp.free_ongkir
                                        })

                        # Urutkan dari harga terendah ke tertinggi
                        tokopedia_products.sort(key=lambda x: x['harga'] or float('inf'))
                        lazada_products.sort(key=lambda x: x['harga'] or float('inf'))

                        # Header Modal Cantik (Spesial Gradien Pink/Rose Premium & Lebih Luas)
                        with ui.element('div').classes('w-full p-6 bg-gradient-to-r from-pink-500 to-rose-600 text-white flex justify-between items-center'):
                            with ui.row().classes('items-center gap-4'):
                                ui.icon('compare', size='32px')
                                with ui.column().classes('gap-0.5'):
                                    ui.label('Perbandingan Harga Pasar').classes('font-black text-lg uppercase tracking-wider')
                                    ui.label(p.get('product_name', 'Produk')).classes('text-xs text-pink-100 font-medium line-clamp-1 max-w-[700px]')
                            ui.button(icon='close', on_click=compare_modal.close).props('flat round color=white').classes('hover:bg-white/10')
                        
                        # Body Modal (Scroll Area Luas)
                        with ui.scroll_area().classes('w-full max-h-[75vh] p-6'):
                            # 🟢 SEKSI TOKOPEDIA (Hijau Premium)
                            ui.label('TOKOPEDIA').classes('text-sm font-black text-green-600 tracking-widest mb-4 flex items-center gap-2')
                            if not tokopedia_products:
                                with ui.row().classes('w-full p-6 bg-gray-50 border border-dashed border-gray-200 rounded-xl items-center justify-center mb-6'):
                                    ui.label('🏜️ Belum ada produk dari Tokopedia yang tersinkronisasi.').classes('text-xs text-gray-400 font-bold')
                            else:
                                with ui.column().classes('w-full gap-4 mb-8'):
                                    for tp in tokopedia_products:
                                        with ui.row().classes('w-full p-5 md:p-6 border border-gray-100 hover:border-green-400 bg-white hover:bg-green-50/10 rounded-2xl gap-6 items-center justify-between transition-all cursor-pointer shadow-md hover:shadow-lg') \
                                            .on('click', lambda url=tp['url']: ui.open(url or 'https://www.tokopedia.com', new_tab=True)):
                                            
                                            with ui.row().classes('items-center gap-6 flex-1 min-w-0'):
                                                # Format URL Gambar (Sistem Deteksi Double Slash)
                                                tp_img = str(tp.get('gambar') or '')
                                                if tp_img.startswith('//'):
                                                    tp_img = 'https:' + tp_img
                                                
                                                if tp_img.startswith('http'):
                                                    ui.image(tp_img).classes('w-28 h-28 rounded-2xl object-cover flex-shrink-0 border border-gray-200')
                                                else:
                                                    with ui.element('div').classes('w-28 h-28 bg-green-50 flex items-center justify-center rounded-2xl flex-shrink-0 border border-green-100'):
                                                        ui.icon('shopping_bag', color='green-500', size='48px')
                                                
                                                with ui.column().classes('gap-2 flex-1 min-w-0'):
                                                    # Baris Info Toko
                                                    with ui.row().classes('items-center gap-2'):
                                                        if tp['shop_official']:
                                                            ui.label('Mall').classes('text-[10px] font-black bg-blue-600 text-white px-2 py-0.5 rounded-md')
                                                        elif tp['badge']:
                                                            ui.label(tp['badge']).classes('text-[10px] font-black bg-green-100 text-green-700 px-2 py-0.5 rounded-md')
                                                        ui.label(tp['shop_name']).classes('text-sm font-bold text-gray-700 truncate')
                                                        ui.label(f"• {tp['shop_kota']}").classes('text-xs text-gray-500 font-semibold')
                                                    
                                                    # Nama Produk Lebih Besar & Lengkap
                                                    ui.label(tp['nama']).classes('text-base font-bold text-gray-900 line-clamp-2 leading-relaxed w-full')
                                                    
                                                    # Rating & Bebas Ongkir
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.label('★').classes('text-yellow-500 text-base')
                                                        ui.label(f"{tp['rating'] or 0.0:.1f}").classes('text-sm font-bold text-gray-800')
                                                        ui.label(f"({tp['jumlah_review'] or 0} ulasan)").classes('text-xs text-gray-500 font-semibold')
                                                        if tp['free_ongkir'] == 1:
                                                            ui.label('Bebas Ongkir').classes('text-[10px] font-black bg-green-50 text-green-600 border border-green-200 px-2 py-0.5 rounded-md ml-2')
                                            
                                            # Harga & Diskon (Sisi Kanan)
                                            with ui.column().classes('items-end gap-1.5 flex-shrink-0'):
                                                if tp['diskon_persen'] and tp['diskon_persen'] > 0:
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.label(f"{tp['diskon_persen']}%").classes('text-xs font-black bg-red-100 text-red-600 px-2 py-0.5 rounded-md')
                                                        ui.label(f"Rp{tp['harga_asli']:,.0f}".replace(',', '.')).classes('text-xs text-gray-400 line-through font-semibold')
                                                
                                                ui.label(f"Rp{tp['harga']:,.0f}".replace(',', '.')).classes('text-xl font-black text-green-600')
                                                ui.label(f"{tp['terjual'] or 0}+ terjual").classes('text-xs text-gray-500 font-semibold')

                            # 🔵 SEKSI LAZADA (Biru Premium)
                            ui.label('LAZADA').classes('text-sm font-black text-blue-600 tracking-widest mb-4 flex items-center gap-2')
                            if not lazada_products:
                                with ui.row().classes('w-full p-6 bg-gray-50 border border-dashed border-gray-200 rounded-xl items-center justify-center'):
                                    ui.label('🏜️ Belum ada produk dari Lazada yang tersinkronisasi.').classes('text-xs text-gray-400 font-bold')
                            else:
                                with ui.column().classes('w-full gap-4'):
                                    for lp in lazada_products:
                                        with ui.row().classes('w-full p-5 md:p-6 border border-gray-100 hover:border-blue-400 bg-white hover:bg-blue-50/10 rounded-2xl gap-6 items-center justify-between transition-all cursor-pointer shadow-md hover:shadow-lg') \
                                            .on('click', lambda url=lp['url']: ui.open(url or 'https://www.lazada.co.id', new_tab=True)):
                                            
                                            with ui.row().classes('items-center gap-6 flex-1 min-w-0'):
                                                # Format URL Gambar (Sistem Deteksi Double Slash)
                                                lp_img = str(lp.get('gambar') or '')
                                                if lp_img.startswith('//'):
                                                    lp_img = 'https:' + lp_img
                                                
                                                if lp_img.startswith('http'):
                                                    ui.image(lp_img).classes('w-28 h-28 rounded-2xl object-cover flex-shrink-0 border border-gray-200')
                                                else:
                                                    with ui.element('div').classes('w-28 h-28 bg-blue-50 flex items-center justify-center rounded-2xl flex-shrink-0 border border-blue-100'):
                                                        ui.icon('shopping_cart', color='blue-500', size='48px')
                                                
                                                with ui.column().classes('gap-2 flex-1 min-w-0'):
                                                    # Baris Info Toko
                                                    with ui.row().classes('items-center gap-2'):
                                                        if lp['shop_official']:
                                                            ui.label('LazMall').classes('text-[10px] font-black bg-red-600 text-white px-2 py-0.5 rounded-md')
                                                        ui.label(lp['shop_name']).classes('text-sm font-bold text-gray-700 truncate')
                                                        ui.label(f"• {lp['shop_kota']}").classes('text-xs text-gray-500 font-semibold')
                                                    
                                                    # Nama Produk Lazada Lebih Besar & Lengkap
                                                    ui.label(lp['nama']).classes('text-base font-bold text-gray-900 line-clamp-2 leading-relaxed w-full')
                                                    
                                                    # Rating & Review
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.label('★').classes('text-yellow-500 text-base')
                                                        ui.label(f"{lp['rating'] or 0.0:.1f}").classes('text-sm font-bold text-gray-800')
                                                        ui.label(f"({lp['jumlah_review'] or 0} ulasan)").classes('text-xs text-gray-500 font-semibold')
                                            
                                            # Harga & Diskon (Sisi Kanan)
                                            with ui.column().classes('items-end gap-1.5 flex-shrink-0'):
                                                if lp['diskon_persen'] and lp['diskon_persen'] > 0:
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.label(f"{lp['diskon_persen']}%").classes('text-xs font-black bg-red-100 text-red-600 px-2 py-0.5 rounded-md')
                                                        ui.label(f"Rp{lp['harga_asli']:,.0f}".replace(',', '.')).classes('text-xs text-gray-400 line-through font-semibold')
                                                
                                                ui.label(f"Rp{lp['harga']:,.0f}".replace(',', '.')).classes('text-xl font-black text-blue-600')
                                                ui.label(f"{lp['terjual'] or 0}+ terjual").classes('text-xs text-gray-500 font-semibold')
                    compare_content()

                def open_compare(p):
                    compare_data.update({'p': p})
                    compare_content.refresh()
                    compare_modal.open()

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
<<<<<<< HEAD
                    print("=== CATALOG VIEW JALAN ===")

                    # --- ASYNC LOADING LOGIC ---
=======
                    # --- LOADING LOGIC ---
>>>>>>> 9b7123ff6ba998aab091ec6c6d8ba299e5375ba1
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

<<<<<<< HEAD
                        # Move blocking DB call to a separate thread
                        from nicegui import run
=======
                        # Pemanggilan database secara langsung (sinkron) dengan filter tipe kulit
>>>>>>> 9b7123ff6ba998aab091ec6c6d8ba299e5375ba1
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

                                        # Rating dengan bintang visual
                                        with ui.row().classes('items-center gap-1 mb-1'):
                                            ui.label('★').classes('text-yellow-400 text-sm')
                                            ui.label(f'{rating:.1f}' if isinstance(rating, (int, float)) else str(rating)).classes('text-xs font-bold text-gray-700')
                                        
                                        # ── Marketplace Button ──
                                        mkt = prod.get('marketplace', {})
                                        has_mkt = mkt.get('tokopedia') or mkt.get('lazada')
                                        mkt_btn_label = 'Lazada & Tokped' if has_mkt else 'Cek Marketplace'
                                        with ui.button(on_click=lambda p=prod: open_compare(p)).props('flat no-caps dense').classes('w-full py-2 text-xs font-semibold rounded-lg hover:bg-gray-100 border border-dashed border-gray-200 mt-1'):
                                            with ui.row().classes('items-center gap-1.5 justify-center'):
                                                ui.icon('shopping_bag', color='pink' if has_mkt else 'grey').classes('text-sm')
                                                ui.label(mkt_btn_label).classes('text-[10px] text-gray-600 font-bold')
                                        
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
