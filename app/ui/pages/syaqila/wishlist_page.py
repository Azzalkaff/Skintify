import json
import asyncio
import logging

from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal, simpan_hasil
from app.database.models import Produk, Toko, SociollaReferensi
from app.services.routine_service import RoutineService

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


from app.ui.product_detail_modal import show_shared_product_detail as buka_modal_detail


"""
Halaman Wishlist (Daftar Keinginan) Skintify
Dibuat oleh: Syaqila
Halaman ini bertugas untuk menampilkan produk-produk yang disimpan oleh pengguna,
termasuk melakukan pengecekan harga langsung ke toko online.
"""
def show_page():
    
    # Memeriksa apakah pengguna sudah login, jika belum kembalikan ke halaman login
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    
    # Menampilkan menu navigasi atas dan samping (Komponen Bersama)
    UIComponents.navbar()
    UIComponents.sidebar()

    # ui.column() menyusun seluruh elemen di halaman ini dari atas ke bawah
    with ui.column().classes('w-full p-8 bg-rose-50/30 min-h-screen gap-4'):
        
        # 1. BAGIAN KEPALA HALAMAN (HEADER)
        # ui.row() menyusun teks "Wishlist" dan tipe kulit pengguna agar bersebelahan
        with ui.row().classes('w-full items-center justify-between pb-4 border-b border-pink-100/50'):
            ui.label('Wishlist').classes('text-3xl font-extrabold tracking-tight text-gray-800')
            with ui.element('div').classes('bg-gradient-to-r from-pink-100 to-rose-100 px-5 py-2 rounded-2xl shadow-sm'):
                skin_type = app.storage.user.get('skin_type', 'Belum diisi')
                ui.label(f'Tipe Kulit: {skin_type}').classes('text-pink-600 text-sm font-bold tracking-wide')
        
        # Variabel penyimpanan sementara untuk mengingat filter kategori apa yang sedang dipilih
        filter_state = {'category': 'Semua'}
        
        # @ui.refreshable adalah sebuah mantra (fungsi khusus) agar bagian dalam fungsi ini 
        # bisa diperbarui/digambar ulang secara instan tanpa perlu memuat ulang seluruh web (refresh page).
        @ui.refreshable
        def render_wishlist():
            # Mengambil daftar wishlist dari sistem utama
            raw_wishlist = state.wishlist or []
            
            # --- BAGIAN TOMBOL FILTER KATEGORI ---
            active_cat = filter_state['category']
            main_cats = ['Cleanser', 'Toner', 'Serum', 'Moisturizer', 'Sunscreen']
            
            if raw_wishlist:
                ui.label('KATEGORI IMPIAN').classes('text-[10px] font-black text-pink-400 uppercase tracking-widest mt-2')
                with ui.row().classes('w-full gap-2 flex-wrap mb-2'):
                    cats = ['Semua'] + main_cats + ['Lainnya']
                    for c in cats:
                        def set_cat(selected=c):
                            filter_state['category'] = selected
                            render_wishlist.refresh()
                        
                        is_active = filter_state['category'] == c
                        if is_active:
                            ui.button(c, on_click=set_cat).props('unelevated rounded size=sm color=pink-4 text-color=white').classes('font-bold px-4 py-1 shadow-md')
                        else:
                            ui.button(c, on_click=set_cat).props('outline rounded size=sm color=pink-2 text-color=grey-7').classes('font-bold px-4 py-1 bg-white hover:bg-pink-50')
            
            wishlist_products = []
            if active_cat == 'Semua':
                wishlist_products = raw_wishlist
            else:
                for p in raw_wishlist:
                    cat = str(p.get('category', '')).lower()
                    if active_cat == 'Lainnya':
                        if not any(mc.lower() in cat for mc in main_cats):
                            wishlist_products.append(p)
                    else:
                        if active_cat.lower() in cat:
                            wishlist_products.append(p)
            # --- END CATEGORY FILTER ---
            def hapus_produk(slug: str):
                state.wishlist = [p for p in state.wishlist if p.get('slug') != slug]
                
                # Hapus dari set if exists
                if hasattr(state, 'wishlist_slugs'):
                    state.wishlist_slugs.discard(slug)
                
                # SIMPAN PERUBAHAN KE DATABASE PERMANEN O(1)
                email = app.storage.user.get('email')
                if email:
                    from app.database.database_manager import BasisData
                    BasisData.hapus_dari_wishlist(email, slug)
                    
                ui.notify('Produk dihapus dari Wishlist', color='pink')
                render_wishlist.refresh()

            def dialog_pindah_rutin(product):
                user_email = app.storage.user.get('email')
                with SessionLocal() as session:
                    user = RoutineService.get_or_create_user(session, user_email)
                    routines = RoutineService.get_user_routines(session, user.id)
                
                if not routines:
                    ui.notify('Anda belum memiliki Rutinitas. Buat di Routine Planner dulu!', color='warning')
                    return
                
                dlg = ui.dialog()
                with dlg, ui.card().classes('w-[90vw] max-w-md p-6 rounded-2xl'):
                    ui.label('Pindahkan ke Rutinitas').classes('text-lg font-black text-gray-800 mb-4')
                    ui.label(f"{product.get('product_name') or product.get('nama')}").classes('text-sm text-pink-500 font-bold mb-4')
                    
                    routine_options = {r.id: r.name for r in routines}
                    selected_routine = ui.select(options=routine_options, value=list(routine_options.keys())[0], label='Pilih Rutinitas').classes('w-full mb-4')
                    hapus_checkbox = ui.checkbox('Hapus dari Wishlist setelah ditambahkan', value=True).classes('w-full mb-6 text-sm text-gray-600')
                    
                    def eksekusi_pindah():
                        if not selected_routine.value:
                            ui.notify('Pilih rutinitas target!', color='warning')
                            return
                        
                        prod_id = product.get('id')
                        with SessionLocal() as session:
                            matched_produk = session.query(Produk).filter_by(referensi_id=prod_id).first() if prod_id else None
                            prod_name = product.get('product_name') or product.get('nama', 'Unknown Product')
                            
                            if matched_produk:
                                RoutineService.add_item_to_routine(session, selected_routine.value, product_id=matched_produk.id)
                            else:
                                notes = f"IMAGE:{product.get('image_url') or product.get('image', '')}"
                                RoutineService.add_item_to_routine(session, selected_routine.value, custom_name=prod_name, notes=notes)
                        
                        ui.notify('Produk berhasil dipindahkan ke Rutinitas!', color='green', icon='check_circle')
                        if hapus_checkbox.value:
                            hapus_produk(product.get('slug'))
                        dlg.close()
                        
                    with ui.row().classes('w-full justify-end gap-3'):
                        ui.button('Batal', on_click=dlg.close).props('flat text-gray-500 hover:bg-gray-100').classes('rounded-xl')
                        ui.button('Simpan', on_click=eksekusi_pindah).classes('bg-gradient-to-r from-pink-500 to-rose-400 text-white font-bold rounded-xl shadow-sm px-6 hover:scale-105 transition-transform')
                dlg.open()
                
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
            # Poin 5: EMPTY STATE YANG LEBIH MENARIK DENGAN SVG
            if not wishlist_products:
                with ui.column().classes('w-full items-center justify-center py-20 gap-4'):
                    # SVG Heart Broken / Empty Box
                    ui.html('''
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-28 h-28 text-pink-200 drop-shadow-[0_10px_15px_rgba(236,72,153,0.2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                        </svg>
                    ''')
                    if not raw_wishlist:
                        ui.label("Wishlist masih kosong").classes('text-2xl font-extrabold text-gray-800 mt-2')
                        ui.label("Simpan produk incaranmu di sini agar tidak lupa!").classes('text-gray-500 text-center max-w-sm font-medium')
                        ui.button('Eksplorasi Produk', on_click=lambda: ui.navigate.to('/search')).classes(
                            'mt-6 bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-2xl px-8 py-3 shadow-[0_8px_20px_rgba(244,63,94,0.3)] hover:scale-105 transition-transform duration-300 font-bold'
                        ).props('no-caps')
                    else:
                        ui.label(f"Tidak ada produk di kategori {active_cat}").classes('text-2xl font-extrabold text-gray-800 mt-2')
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
                                    'Bandingkan Harga Marketplace',
                                    on_click=lambda p=product: buka_modal_detail(p)
                                ).props('no-caps').classes(
                                    'bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-xl px-4 py-2 shadow-sm font-bold hover:scale-105 transition-all text-xs'
                                )
                                # Check if product is currently selected for comparison
                                is_selected = any(x.get('slug') == product.get('slug') for x in state.__dict__.get('wishlist_compare_selections', []))
                                if is_selected:
                                    ui.button(
                                        'Terpilih',
                                        on_click=lambda p=product: toggle_compare_selection(p)
                                    ).props('no-caps').classes(
                                        'bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl px-4 py-2 shadow-sm font-bold hover:scale-105 transition-all text-xs'
                                    )
                                else:
                                    ui.button(
                                        'Bandingkan',
                                        on_click=lambda p=product: toggle_compare_selection(p)
                                    ).props('outline no-caps').classes(
                                        'text-blue-500 border-blue-200 hover:bg-blue-50 rounded-xl px-4 py-2 font-bold transition-all text-xs'
                                    )
                                
                                ui.button(
                                    icon='delete',
                                    on_click=lambda p=product: hapus_produk(p.get('slug'))
                                ).props('flat round size=sm').classes(
                                    'text-red-500 hover:bg-red-50 transition-colors'
                                ).tooltip('Hapus dari Wishlist')
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