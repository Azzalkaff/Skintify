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
        res = ambil_tokopedia(keyword, top_n=15)
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
        lazada_products, lazada_shops = ambil_lazada(keyword, top_n=15)
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

from app.ui.product_detail_modal import show_shared_product_detail as buka_modal_detail

def show_page():
    """Halaman Pencarian Produk (100% Selesai) - Dipegang oleh Syahid"""
    if not hasattr(state, 'page'):
        state.page = 1

    # Fetch distinct brands dynamically from DB using cached property
    unique_brands = data_mgr.brands if hasattr(data_mgr, 'brands') else ["Skintific", "Cosrx", "Wardah", "Somethinc", "The Originote", "Anessa", "Azarine", "Avoskin"]

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
                sort_select = ui.select(sort_options, value='Terlaris', label='Urutkan').classes('w-full mb-4')
                
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
                    ui.timer(0.2, lambda: ui.run_javascript('document.querySelectorAll(".scroll, .q-scrollarea__container, .q-table__middle").forEach(el => el.scrollTop = 0); window.scrollTo(0, 0);'), once=True)

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
                    # Save to recent (O(1) array shifting via Deque)
                    from collections import deque
                    recent_dq = state.__dict__.get('recent_products_dq')
                    if not recent_dq:
                        recent_dq = deque(state.__dict__.get('recent_products', []), maxlen=5)
                        state.__dict__['recent_products_dq'] = recent_dq
                        
                    if not any(x.get('slug') == p.get('slug') for x in recent_dq):
                        recent_dq.appendleft(p)
                        state.__dict__['recent_products'] = list(recent_dq)
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

                    # Container statis yang mereservasi DOM Slot agar tidak hilang
                    result_container = ui.column().classes('w-full')

                    async def fetch_and_render():

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

                            import asyncio
                            
                            # Gunakan await asyncio.to_thread untuk melempar blocking DB ke thread pool (Best Practice)
                            paginated_data = await asyncio.to_thread(
                                data_mgr.get_paginated_products,
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
                        
                        with result_container:
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
                                            # Inisialisasi set O(1) lookup jika belum ada
                                            if not hasattr(state, 'wishlist_slugs'):
                                                state.wishlist_slugs = {item.get('slug') for item in getattr(state, 'wishlist', []) if item.get('slug')}

                                            slug = p.get('slug', '')
                                            if slug and slug not in state.wishlist_slugs:
                                                current = getattr(state, 'wishlist', [])
                                                state.wishlist = current + [p]
                                                state.wishlist_slugs.add(slug)
                                                
                                                # SIMPAN KE DATABASE PERMANEN O(1) (Menggunakan tabel relasional)
                                                email = app.storage.user.get('email')
                                                if email:
                                                    from app.database.database_manager import BasisData
                                                    import json
                                                    BasisData.tambah_ke_wishlist(email, slug, json.dumps(p))
                                                    
                                                ui.notify(f'{p.get("product_name", "Produk")} ditambahkan ke Wishlist!',
                                                        color='pink', position='bottom-right')
                                            elif not slug:
                                                ui.notify('Error: Produk tidak memiliki identifier valid.', color='negative', position='bottom-right')
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
                                                    ui.button('Bandingkan Harga Marketplace', on_click=lambda p=prod, g=grad, a=accent, ic=cat_icon: open_detail(p, g, a, ic)).props('flat no-caps').classes('flex-grow font-bold border border-pink-200 text-pink-600 text-xs py-1.5 rounded-lg bg-pink-50 hover:bg-pink-100')
                                                    ui.button('+ Wishlist', on_click=handle_add_item).props('flat no-caps').classes('flex-grow border border-gray-200 text-xs text-gray-700 py-1.5 rounded-lg hover:bg-gray-50')
                                                    
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
                                ui.timer(0.2, lambda: ui.run_javascript('document.querySelectorAll(".scroll, .q-scrollarea__container, .q-table__middle").forEach(el => el.scrollTop = 0); window.scrollTo(0, 0);'), once=True)

                            if paginated_data["total_pages"] > 1:
                                ui.separator().classes('mt-10 mb-6 opacity-20')
                                UIComponents.pagination_controls(
                                    current_page=paginated_data["current_page"],
                                    total_pages=paginated_data["total_pages"],
                                    on_change=handle_page_change
                                )
                        
                    # Eksekusi fetch and render di background timer agar tidak memblokir render sinkron UI NiceGUI
                    ui.timer(0, fetch_and_render, once=True)
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
