from nicegui import ui
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager

def show_page():
    """Halaman Pencarian Produk (100% Selesai) - Dipegang oleh Syahid"""
    if not hasattr(state, 'page'):
        state.page = 1

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

    with ui.row().classes('w-full max-w-[2000px] mx-auto items-stretch no-wrap mt-8 px-8 gap-8').style('min-height: calc(100vh - 120px);'):
        
        # Panel Kiri: Form Pencarian & Filter
        with ui.column().classes('w-64 flex-shrink-0 pt-4'):
            ui.label('Cari Produk').classes('text-2xl font-black text-gray-800 mb-6')
            
            with ui.card().classes('w-full p-4 shadow-sm bg-white'):
                # Kotak Pencarian
                search_input = ui.input(placeholder='Cari nama produk...').classes('w-full mb-4')
                
                # Dropdown Kategori
                # Asumsi data_mgr.categories berisi list kategori
                cats = ['Semua'] + list(set(
                    ['Serum', 'Moisturizer', 'Toner', 'Sunscreen', 'Cleanser'] +
                    (data_mgr.categories if hasattr(data_mgr, 'categories') else [])
                ))
                default_category = (
                    state.category
                    if hasattr(state, 'category') and state.category in cats
                    else 'Semua'
                )

                cat_select = ui.select(
                    cats,
                    value=default_category,
                    label='Kategori'
                ).classes('w-full mb-4')
                
                # Dropdown Tipe Kulit
                skin_types = ['Semua', 'Dry', 'Oily', 'Normal', 'Combination', 'Sensitive']
                skin_select = ui.select(skin_types, value='Semua', label='Tipe Kulit').classes('w-full mb-4')
                
                # Dropdown Harga
                price_ranges = ['Semua', '< Rp 50k', 'Rp 50k - Rp 150k', 'Rp 150k - Rp 300k', '> Rp 300k']
                price_select = ui.select(price_ranges, value='Semua', label='Range Harga').classes('w-full mb-4')
                
                # Dropdown Urutkan
                sort_options = ['Rating (Tertinggi)', 'Harga (Terendah)', 'Harga (Tertinggi)']
                sort_select = ui.select(sort_options, value='Rating (Tertinggi)', label='Urutkan').classes('w-full mb-6')
                
                # Filter Marketplace
                mkt_filter = ui.checkbox(
                    'Hanya dengan Marketplace', 
                    value=getattr(state, 'mkt_filter', False)
                ).classes('mb-4 text-xs font-bold text-gray-600')
                
                def trigger_search(e=None):
                    state.page = 1
                    state.mkt_filter = mkt_filter.value
                    if hasattr(state, 'category'):
                        state.category = cat_select.value if cat_select.value != 'Semua' else None
                    catalog_view.refresh()

                # Event listeners
                search_input.on('keydown.enter', trigger_search)
                cat_select.on_value_change(trigger_search)
                skin_select.on_value_change(trigger_search)
                price_select.on_value_change(trigger_search)
                sort_select.on_value_change(trigger_search)
                mkt_filter.on_value_change(trigger_search)
                
                ui.button('Terapkan Filter', on_click=trigger_search, color='pink-500').classes('w-full font-bold text-white mb-2')

                ui.separator().classes('my-2')
                
                def open_add_dialog():
                    product_form_dialog()

                ui.button('Tambah Produk Baru', icon='add', on_click=open_add_dialog, color='green-500').classes('w-full font-bold text-white')

        # Panel Kanan: Katalog Produk
        with ui.column().classes('flex-1 glass-card p-8 relative h-[calc(100vh-120px)]'):
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
                        with ui.element('div').classes(f'w-full h-52 bg-gradient-to-br {g} flex items-center justify-center overflow-hidden'):
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
                    detail_content.refresh()
                    detail_modal.open()

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
                async def catalog_view() -> None:
                    # --- ASYNC LOADING LOGIC ---
                    loading_spinner.set_visibility(True)
                    try:
                        keyword = search_input.value.lower() if search_input.value else ""
                        sort_val = sort_select.value
                        category_filter = cat_select.value

                        ui_to_backend = {
                            'Semua': 'All',
                            'Serum': 'Serum',
                            'Moisturizer': 'Moisturizer',
                            'Toner': 'Toner',
                            'Sunscreen': 'Sunscreen',
                            'Cleanser': 'Cleanser',
                        }
                        backend_category = ui_to_backend.get(category_filter, 'All')

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
                        paginated_data = await run.io_bound(
                            data_mgr.get_paginated_products,
                            page=state.page,
                            items_per_page=12,
                            category_filter=backend_category,
                            keyword=keyword,
                            min_price=min_price,
                            max_price=max_price,
                            sort_val=sort_val,
                            marketplace_only=getattr(state, 'mkt_filter', False)
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
                                        object.__setattr__(state, 'wishlist', current + [p])
                                        ui.notify(f'✨ {p.get("product_name", "Produk")} ditambahkan ke Wishlist!',
                                                color='pink', position='bottom-right')
                                    else:
                                        ui.notify('Produk ini sudah ada di Wishlist.', color='info', position='bottom-right')

                                # ── Palet warna & ikon fallback per kategori ──
                                cat_palette = {
                                    'Serum':       ('from-blue-50 to-indigo-100',  '#6366F1', '💧'),
                                    'Moisturizer': ('from-green-50 to-emerald-100','#10B981', '🧴'),
                                    'Sunscreen':   ('from-yellow-50 to-amber-100', '#F59E0B', '☀️'),
                                    'Toner':       ('from-cyan-50 to-sky-100',     '#0EA5E9', '🌊'),
                                    'Cleanser':    ('from-purple-50 to-violet-100','#8B5CF6', '🫧'),
                                    'Face Gel':    ('from-teal-50 to-cyan-100',    '#14B8A6', '💦'),
                                    'Face Wash':   ('from-purple-50 to-violet-100','#8B5CF6', '🫧'),
                                }
                                prod_cat = prod.get('category', '')
                                grad, accent, cat_icon = cat_palette.get(prod_cat, ('from-pink-50 to-rose-100', '#EC4899', '✨'))

                                # Kartu Produk
                                with ui.card().classes('p-0 shadow-sm hover:shadow-lg transition-all duration-200 flex flex-col justify-between overflow-hidden rounded-xl'):
                                    # ── Area Gambar ──
                                    with ui.element('div').classes(f'w-full h-36 bg-gradient-to-br {grad} relative overflow-hidden flex items-center justify-center'):
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
                                    with ui.column().classes('w-full p-4 gap-1'):
                                        ui.label(name).classes('font-bold text-sm leading-tight line-clamp-2 min-h-[40px] text-gray-800')
                                        ui.label(brand).classes('text-xs text-gray-400 truncate w-full')
                                        ui.label(format_price).classes('text-pink-500 font-bold text-base mt-1')

                                        # Rating dengan bintang visual
                                        with ui.row().classes('items-center gap-1 mb-1'):
                                            ui.label('★').classes('text-yellow-400 text-sm')
                                            ui.label(f'{rating:.1f}' if isinstance(rating, (int, float)) else str(rating)).classes('text-xs font-bold text-gray-700')
                                        
                                        # ── Marketplace Section ──
                                        mkt = prod.get('marketplace', {})
                                        has_mkt = mkt.get('tokopedia') or mkt.get('lazada')
                                        
                                        with ui.column().classes('w-full -mt-2 gap-1'):
                                            # Container Marketplace: Muncul otomatis jika ada data
                                            mkt_container = ui.column().classes(f'w-full p-2 gap-1 bg-gray-50 rounded-lg border border-gray-100 {"hidden" if not has_mkt else ""}')
                                            
                                            with mkt_container:
                                                if has_mkt:
                                                    if mkt.get('tokopedia'):
                                                        with ui.row().classes('w-full justify-between items-center'):
                                                            with ui.row().classes('items-center gap-1'):
                                                                ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-green-500')
                                                                ui.label('Tokopedia').classes('text-[9px] font-bold text-gray-500')
                                                            with ui.column().classes('items-end gap-0'):
                                                                ui.label(f"Rp{mkt['tokopedia']['harga']:,.0f}".replace(',', '.')).classes('text-[9px] font-black text-green-600')
                                                                ui.label(f"{mkt['tokopedia'].get('terjual', 0)}+ terjual").classes('text-[7px] text-gray-400')
                                                    
                                                    if mkt.get('lazada'):
                                                        with ui.row().classes('w-full justify-between items-center'):
                                                            with ui.row().classes('items-center gap-1'):
                                                                ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-orange-500')
                                                                ui.label('Lazada').classes('text-[9px] font-bold text-gray-500')
                                                            with ui.column().classes('items-end gap-0'):
                                                                ui.label(f"Rp{mkt['lazada']['harga']:,.0f}".replace(',', '.')).classes('text-[9px] font-black text-orange-600')
                                                                ui.label(f"{mkt['lazada'].get('terjual', 0)}+ terjual").classes('text-[7px] text-gray-400')
                                                else:
                                                    with ui.row().classes('w-full justify-center py-1 items-center gap-1'):
                                                        ui.label('Data belum di-sync').classes('text-[8px] text-gray-400 uppercase font-bold')

                                            def toggle_mkt(container=mkt_container):
                                                if 'hidden' in container.classes:
                                                    container.classes(remove='hidden')
                                                else:
                                                    container.classes(add='hidden')

                                            mkt_btn_label = 'Bandingkan Harga' if has_mkt else 'Cek Marketplace'
                                            ui.button(mkt_btn_label, on_click=toggle_mkt).props(f'flat icon="shopping_bag" {"color=pink" if has_mkt else "color=gray"}').classes('w-full text-[9px] font-black h-8 rounded-lg border-dashed border-gray-200 hover:bg-gray-50')
                                    
                                        # ── Tombol Bawah ──
                                        with ui.row().classes('w-full gap-2 px-4 pb-4 mt-1'):
                                            ui.button('Detail', on_click=lambda p=prod, g=grad, a=accent, ic=cat_icon: open_detail(p, g, a, ic)).props('flat').classes('flex-1 border border-gray-200 text-xs text-gray-700 rounded-lg')
                                            ui.button('+ Wishlist', on_click=handle_add_item).props('flat').classes('flex-1 font-bold border border-pink-200 text-pink-600 text-xs rounded-lg bg-pink-50 hover:bg-pink-100')
                                            
                                            # Tombol Edit/Hapus
                                            with ui.row().classes('gap-1'):
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
                        ui.label('✨ Tambah Produk Baru' if not product else '📝 Edit Produk').classes('text-2xl font-black text-gray-800 mb-6')
                        
                        with ui.column().classes('w-full gap-4'):
                            name = ui.input('Nama Produk', placeholder='Contoh: Hydrating Serum', value=product['product_name'] if product else '').classes('w-full')
                            brand = ui.input('Brand', placeholder='Contoh: Skintific', value=product['brand'] if product else '').classes('w-full')
                            
                            with ui.row().classes('w-full gap-4'):
                                price = ui.number('Harga (Rp)', value=product['min_price'] if product else 0, format='%.0f').classes('flex-1')
                                cats_list = ['Serum', 'Moisturizer', 'Toner', 'Sunscreen', 'Cleanser']
                                category = ui.select(cats_list, label='Kategori', value=product['category'] if product else 'Serum').classes('flex-1')
                            
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
                                ui.notify('Produk berhasil disimpan! ✨', color='positive')
                                dialog.close()
                                catalog_view.refresh()
                            else:
                                ui.notify('Gagal menyimpan produk. Coba lagi.', color='negative')
                        
                        with ui.row().classes('w-full justify-end gap-3 mt-4'):
                            ui.button('Batal', on_click=dialog.close).props('flat').classes('text-gray-500')
                            ui.button('Simpan Produk', on_click=save_data, color='pink-500').classes('text-white px-6 font-bold')
                    
                    dialog.open()
                
                if hasattr(state, 'category') and state.category:
                    cat_select.value = state.category
                    state.page = 1
                    catalog_view.refresh()
