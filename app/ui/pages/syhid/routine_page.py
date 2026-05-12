from nicegui import ui, app
from app.database.engine import SessionLocal
from app.services.routine_service import RoutineService
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.context import data_mgr, state
import logging

logger = logging.getLogger(__name__)

def show_page():
    """SYHID'S MISSION: Premium Routine Planner with Low Cognitive Load."""
    
    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    user_email = app.storage.user.get('email')
    
    # Ensure user exists in SQLAlchemy DB
    with SessionLocal() as session:
        user = RoutineService.get_or_create_user(session, user_email)
        user_id = user.id

    @ui.refreshable
    def render_routines():
        with SessionLocal() as session:
            routines = RoutineService.get_user_routines(session, user_id)
            
            if not routines:
                with ui.column().classes('w-full items-center justify-center py-20 text-gray-400 gap-4'):
                    UIComponents.empty_state_svg()
                    ui.label('Belum ada rutin skincare aktif.').classes('text-xl font-black text-gray-800')
                    ui.label('Mulailah membangun kebiasaan sehat dengan membuat rutin pertama Anda.').classes('text-sm text-center max-w-md mb-4')
                    ui.button('Buat Rutin Baru', on_click=lambda: add_routine_modal.open(), icon='add').classes('btn-primary px-8 py-3 rounded-2xl')
            else:
                with ui.grid(columns='1 md:2 lg:2').classes('w-full gap-8 p-0'):
                    for r in routines:
                        # Perform Analysis for this routine
                        routine_ingredients = []
                        for item in r.items:
                            # Try to find sociolla ref to get ingredients
                            from app.database.models import SociollaReferensi
                            if item.product and item.product.keyword:
                                ref = session.query(SociollaReferensi).filter(SociollaReferensi.keyword_digunakan == item.product.keyword).first()
                                if ref and ref.ingredients:
                                    routine_ingredients.append({"ingredients": ref.ingredients})
                        
                        analysis = data_mgr.analyze_routine(routine_ingredients)
                        
                        with ui.card().classes('glass-card border-none overflow-hidden p-0 flex flex-col h-full'):
                            # Header
                            is_morning = 'morning' in r.name.lower() or 'pagi' in r.name.lower()
                            header_color = 'from-blue-400 to-indigo-600' if is_morning else 'from-indigo-800 to-purple-900'
                            
                            with ui.row().classes(f'w-full p-6 bg-gradient-to-br {header_color} text-white items-center justify-between'):
                                with ui.row().classes('items-center gap-4'):
                                    with ui.element('div').classes('p-2 bg-white/20 rounded-xl backdrop-blur-md'):
                                        ui.icon('wb_sunny' if is_morning else 'dark_mode', size='24px')
                                    with ui.column().classes('gap-0'):
                                        ui.label(r.name).classes('text-xl font-black')
                                        ui.label(f'{len(r.items)} Produk Terdaftar').classes('text-[10px] font-bold opacity-70 uppercase tracking-widest')
                                
                                with ui.row().classes('gap-1'):
                                    ui.button(icon='edit', on_click=lambda r=r: edit_routine(r)).props('flat round color=white size=sm').tooltip('Edit Nama/Deskripsi')
                                    ui.button(icon='delete', on_click=lambda r=r: confirm_delete(r)).props('flat round color=white size=sm').tooltip('Hapus Rutin')
                            
                            # Analysis Summary (Poka-yoke)
                            with ui.row().classes('w-full px-6 py-3 bg-white/10 border-b border-white/10 items-center justify-between'):
                                UIComponents.routine_status_badge(analysis)
                                if r.description:
                                    ui.label(r.description).classes('text-[10px] text-gray-400 italic truncate max-w-[200px]')
                            
                            # Product List
                            with ui.column().classes('p-6 w-full gap-4 flex-grow bg-white/5'):
                                if not r.items:
                                    with ui.column().classes('w-full items-center py-10 opacity-30'):
                                        ui.icon('inventory_2', size='48px')
                                        ui.label('Klik tombol di bawah untuk tambah produk').classes('text-xs font-bold mt-2')
                                else:
                                    # Sort items by step_order manually to be safe
                                    sorted_items = sorted(r.items, key=lambda x: x.step_order)
                                    for idx, item in enumerate(sorted_items):
                                        with ui.row().classes('w-full items-center gap-4 p-3 glass-card bg-white/30 border-white/40 hover:bg-white/50 transition-all group'):
                                            # Step Number
                                            ui.label(str(item.step_order)).classes('w-8 h-8 bg-pink-500 text-white text-xs font-black rounded-full flex items-center justify-center shadow-lg shrink-0')
                                            
                                            # Image & Notes Logic
                                            img_url = 'https://via.placeholder.com/150?text=Skin'
                                            display_notes = item.notes
                                            
                                            if item.product and item.product.gambar:
                                                img_url = item.product.gambar
                                            elif item.notes and item.notes.startswith('IMAGE:'):
                                                img_url = item.notes.split('IMAGE:')[1]
                                                display_notes = '' # Don't show the raw image URL
                                            
                                            with ui.element('div').classes('w-16 h-16 bg-white rounded-xl p-1 shadow-sm overflow-hidden shrink-0 border border-pink-50'):
                                                ui.image(img_url).classes('w-full h-full object-contain')
                                            
                                            # Info
                                            with ui.column().classes('flex-1 min-w-0 gap-0'):
                                                prod_name = item.product.nama if item.product else item.custom_name
                                                ui.label(prod_name).classes('text-sm font-black leading-tight line-clamp-1 text-gray-800')
                                                if display_notes:
                                                    ui.label(display_notes).classes('text-[10px] text-gray-400 italic truncate')
                                            
                                            # Actions (Reordering & Delete)
                                            with ui.row().classes('gap-0 opacity-0 group-hover:opacity-100 transition-opacity'):
                                                if idx > 0:
                                                    ui.button(icon='arrow_upward', on_click=lambda i=item, r_items=sorted_items: move_item(i, -1, r_items)).props('flat round size=xs color=gray').tooltip('Naikkan')
                                                if idx < len(sorted_items) - 1:
                                                    ui.button(icon='arrow_downward', on_click=lambda i=item, r_items=sorted_items: move_item(i, 1, r_items)).props('flat round size=xs color=gray').tooltip('Turunkan')
                                                ui.button(icon='delete_outline', on_click=lambda item_id=item.id: remove_item(item_id)) \
                                                    .props('flat round size=xs color=red').tooltip('Hapus dari Rutin')
                            
                            # Add Product Button
                            ui.button('TAMBAH PRODUK', icon='add', on_click=lambda r_id=r.id: open_add_item(r_id)).props('flat size=sm').classes('w-full py-4 text-pink-500 font-black tracking-widest hover:bg-pink-50 transition-colors')

    def move_item(item, direction, all_items):
        with SessionLocal() as session:
            current_idx = next(i for i, x in enumerate(all_items) if x.id == item.id)
            target_idx = current_idx + direction
            
            if 0 <= target_idx < len(all_items):
                target_item = all_items[target_idx]
                
                # Swap orders
                RoutineService.update_item_order(session, item.id, target_item.step_order)
                RoutineService.update_item_order(session, target_item.id, item.step_order)
                
                ui.notify('Urutan diperbarui')
                render_routines.refresh()

    # State untuk pembuatan kit
    new_routine_state = {
        'name': '',
        'desc': '',
        'selected_kit': None,
        'filter_category': 'Semua',
        'filter_price': 'Semua'
    }

    async def save_routine():
        try:
            name = new_routine_state['name']
            desc = new_routine_state['desc']
            if not name:
                ui.notify('Nama rutin wajib diisi!', type='warning')
                return
            
            with SessionLocal() as session:
                # 1. Buat Routine Header
                routine = RoutineService.create_routine(session, user_id, name, desc)
                
                # 2. Jika ada Kit yang dipilih, masukkan semua produknya
                kit = new_routine_state['selected_kit']
                if kit and 'products' in kit:
                    from app.database.models import Produk
                    for idx, prod in enumerate(kit['products']):
                        prod_name = f"{prod.get('brand', '')} {prod.get('name', '')}".strip()
                        if not prod_name:
                            prod_name = prod.get('nama', 'Unknown Product')
                            
                        # Coba temukan produk fisik (marketplace) yang cocok dengan referensi kit ini
                        # agar user bisa melihat gambar dan harga aslinya
                        ref_id = prod.get('id')
                        matched_produk = session.query(Produk).filter_by(referensi_id=ref_id).first() if ref_id else None
                        
                        if matched_produk:
                            RoutineService.add_item_to_routine(
                                session=session, 
                                routine_id=routine.id, 
                                product_id=matched_produk.id
                            )
                        else:
                            # Fallback jika belum di-scrape: gunakan nama custom dan simpan gambar di notes
                            notes = f"IMAGE:{prod.get('image', '')}" if prod.get('image') else ""
                            RoutineService.add_item_to_routine(
                                session=session, 
                                routine_id=routine.id, 
                                custom_name=prod_name,
                                notes=notes
                            )
            
            ui.notify(f'✨ Rutin "{name}" berhasil dibuat!', type='positive')
            add_routine_modal.close()
            
            # Reset state
            new_routine_state['name'] = ''
            new_routine_state['desc'] = ''
            new_routine_state['selected_kit'] = None
            
            render_routines.refresh()
        except Exception as e:
            logger.error(f"Error saving routine: {e}")
            ui.notify(f"Gagal menyimpan rutin: {str(e)}", color='negative', timeout=5000)

    def confirm_delete(routine):
        with ui.dialog() as d, ui.card().classes('p-8 rounded-[2rem] glass-card border-none items-center text-center'):
            ui.icon('warning', color='red-500', size='48px')
            ui.label(f'Hapus rutin "{routine.name}"?').classes('text-xl font-black text-gray-800 mt-4')
            ui.label('Seluruh produk dalam daftar rutin ini akan ikut terhapus.').classes('text-sm text-gray-500')
            with ui.row().classes('w-full gap-4 mt-8'):
                ui.button('Batal', on_click=d.close).props('flat').classes('flex-1 text-gray-400 font-bold')
                ui.button('Hapus', on_click=lambda: delete_routine(routine.id, d)).props('unelevated').classes('flex-1 bg-red-500 text-white rounded-xl font-bold')
        d.open()

    def delete_routine(id, dialog):
        with SessionLocal() as session:
            RoutineService.delete_routine(session, id)
        ui.notify('Rutin telah dihapus')
        dialog.close()
        render_routines.refresh()

    def remove_item(item_id):
        with SessionLocal() as session:
            RoutineService.remove_item_from_routine(session, item_id)
        ui.notify('Produk dilepas dari rutin')
        render_routines.refresh()

    current_routine_id = None
    def open_add_item(routine_id):
        nonlocal current_routine_id
        current_routine_id = routine_id
        add_item_modal.open()

    async def search_product_for_routine(e):
        if len(e.value) < 3:
            search_results_container.clear()
            return
        
        with SessionLocal() as session:
            # Menggunakan referensi untuk mengurangi cognitive load (tidak ada duplikat seller)
            results = RoutineService.search_referensi_products(session, e.value)
            search_results_container.clear()
            with search_results_container:
                if not results:
                    ui.label('Produk tidak ditemukan').classes('text-gray-400 text-sm p-4 italic')
                    ui.button(f'Tambahkan "{e.value}" secara manual', on_click=lambda: add_custom_item(e.value)).classes('btn-primary w-full py-3 rounded-xl')
                else:
                    for p in results:
                        with ui.row().classes('w-full hover:bg-pink-50 p-4 cursor-pointer items-center rounded-2xl border border-transparent hover:border-pink-100 transition-all group'):
                            with ui.element('div').classes('w-12 h-12 bg-white rounded-lg p-1 border border-gray-100 flex items-center justify-center shrink-0'):
                                img = p.image_url if p.image_url else 'https://via.placeholder.com/50'
                                ui.image(img).classes('w-full h-full object-contain')
                            with ui.column().classes('flex-1 min-w-0 gap-0'):
                                ui.label(p.product_name).classes('text-xs font-black text-gray-800 line-clamp-1')
                                ui.label(p.brand).classes('text-[8px] font-black text-pink-400 uppercase tracking-widest')
                            ui.button(icon='add', on_click=lambda ref=p: add_product_to_routine(ref)).props('flat round size=sm').classes('bg-pink-50 text-pink-500 shrink-0')

    def add_product_to_routine(ref_obj):
        try:
            with SessionLocal() as session:
                from app.database.models import Produk
                
                # Coba temukan representasi fisiknya
                matched_produk = session.query(Produk).filter_by(referensi_id=ref_obj.id).first()
                
                if matched_produk:
                    RoutineService.add_item_to_routine(session, current_routine_id, product_id=matched_produk.id)
                else:
                    prod_name = f"{ref_obj.brand} {ref_obj.product_name}".strip()
                    notes = f"IMAGE:{ref_obj.image_url}" if ref_obj.image_url else ""
                    RoutineService.add_item_to_routine(session, current_routine_id, custom_name=prod_name, notes=notes)
                    
            ui.notify('✨ Produk ditambahkan ke rutin')
            add_item_modal.close()
            render_routines.refresh()
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            ui.notify(f"Gagal menambahkan produk: {str(e)}", color='negative', timeout=5000)

    def add_custom_item(name):
        with SessionLocal() as session:
            RoutineService.add_item_to_routine(session, current_routine_id, custom_name=name)
        ui.notify('Produk manual ditambahkan')
        add_item_modal.close()
        render_routines.refresh()

    # --- UI Layout ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 lg:p-10 gap-10'):
        # Header Section
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-1'):
                ui.label('Routine Planner').classes('text-5xl font-black text-gray-800 tracking-tight')
                ui.label('Kelola urutan perawatan kulit harian Anda dengan cerdas.').classes('text-gray-500 text-lg font-medium')
            
            ui.button('Rutin Baru', icon='add', on_click=lambda: add_routine_modal.open()).classes('btn-primary px-8 py-4 rounded-[1.5rem]')

        # Main Content
        render_routines()

    # --- Modals ---
    with ui.dialog() as add_routine_modal, ui.card().classes('w-[900px] max-w-full rounded-[2.5rem] p-10 glass-card border-none'):
        ui.label('Pilih Skintify Curated Kit').classes('text-3xl font-black text-gray-800 mb-2')
        ui.label('Mulai dengan paket yang telah dirancang khusus oleh ahlinya, atau buat dari nol.').classes('text-sm text-gray-500 mb-6')
        
        with ui.row().classes('w-full gap-8 items-start'):
            # KIRI: Daftar Kit
            with ui.column().classes('flex-[2] gap-4'):
                # Filters
                with ui.row().classes('w-full gap-2 mb-2'):
                    ui.select(['Semua', 'Skincare', 'Makeup'], label='Kategori').bind_value(new_routine_state, 'filter_category') \
                        .props('outlined dense').classes('w-32')
                    ui.select(['Semua', '< Rp 150rb', 'Rp 150rb - Rp 300rb', '> Rp 300rb'], label='Harga').bind_value(new_routine_state, 'filter_price') \
                        .props('outlined dense').classes('w-48')

                @ui.refreshable
                def kit_gallery():
                    templates = app.storage.general.get('admin_templates', [])
                    
                    # Filtering Logic
                    cat_f = new_routine_state['filter_category']
                    prc_f = new_routine_state['filter_price']
                    
                    filtered_templates = []
                    for t in templates:
                        # Abaikan template format lama (tanpa products)
                        if not t.get('products'):
                            continue
                            
                        if cat_f != 'Semua' and t.get('category') != cat_f:
                            continue
                            
                        price = t.get('total_price', 0)
                        if prc_f == '< Rp 150rb' and price >= 150000: continue
                        if prc_f == 'Rp 150rb - Rp 300rb' and (price < 150000 or price > 300000): continue
                        if prc_f == '> Rp 300rb' and price <= 300000: continue
                        
                        filtered_templates.append(t)

                    if not filtered_templates:
                        ui.label('Tidak ada kit yang sesuai dengan filter.').classes('text-sm text-gray-400 italic p-8 text-center border-2 border-dashed border-gray-200 rounded-2xl w-full')
                        return

                    with ui.grid(columns=2).classes('w-full gap-4'):
                        for t in filtered_templates:
                            is_selected = new_routine_state['selected_kit'] == t
                            border_class = 'border-pink-500 bg-pink-50' if is_selected else 'border-transparent bg-white hover:border-pink-200'
                            
                            with ui.card().classes(f'p-4 cursor-pointer transition-all border-2 {border_class} shadow-sm').on('click', lambda tmpl=t: select_kit(tmpl)):
                                ui.label(t['name']).classes('text-sm font-black text-gray-800 line-clamp-1')
                                ui.label(f"{len(t.get('products', []))} Produk").classes('text-[10px] font-bold text-gray-400')
                                ui.label(f"Rp {int(t.get('total_price', 0)):,}").classes('text-xs font-black text-green-600 mt-2')

                def select_kit(t):
                    # Jika klik kit yang sama, batalkan pilihan
                    if new_routine_state['selected_kit'] == t:
                        new_routine_state['selected_kit'] = None
                        new_routine_state['name'] = ''
                        new_routine_state['desc'] = ''
                    else:
                        new_routine_state['selected_kit'] = t
                        new_routine_state['name'] = t['name']
                        new_routine_state['desc'] = f"Dari Skintify Kit: {t['name']}"
                    kit_gallery.refresh()

                # Watcher untuk filter
                ui.timer(0.1, kit_gallery.refresh, once=True) # First render
                ui.timer(0.5, kit_gallery.refresh) # Simple polling for filter changes

                with ui.scroll_area().classes('w-full h-[350px]'):
                    kit_gallery()

            # KANAN: Form Finalisasi
            with ui.column().classes('flex-1 gap-4 p-6 bg-gray-50 rounded-2xl border border-gray-100 h-full'):
                ui.label('Rincian Rutin').classes('text-lg font-black text-gray-800 mb-2')
                
                ui.input('Nama Rutin').bind_value(new_routine_state, 'name').props('outlined').classes('w-full')
                ui.textarea('Deskripsi').bind_value(new_routine_state, 'desc').props('outlined').classes('w-full mt-2')
                
                with ui.row().classes('w-full gap-2 mt-auto pt-8'):
                    ui.button('Batal', on_click=add_routine_modal.close).props('flat').classes('flex-1 text-gray-400 font-bold')
                    ui.button('Simpan', on_click=save_routine).classes('flex-[2] btn-primary py-3 rounded-2xl')

    with ui.dialog() as add_item_modal, ui.card().classes('w-[650px] max-w-full rounded-[2.5rem] p-0 overflow-hidden glass-card border-none'):
        with ui.column().classes('w-full'):
            # Header Modal
            with ui.column().classes('p-10 bg-gradient-to-br from-pink-50 to-white w-full border-b border-pink-100'):
                ui.label('Tambah ke Rutin').classes('text-3xl font-black text-gray-800')
                ui.label('Sempurnakan urutan perawatan Anda dengan produk terbaik.').classes('text-sm text-gray-400 font-medium')

            with ui.column().classes('p-10 w-full gap-6'):
                # Low Cognitive Options: Category Chips
                ui.label('TELUSURI KATEGORI').classes('text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]')
                with ui.row().classes('w-full gap-3 flex-wrap'):
                    categories = ['Cleanser', 'Toner', 'Serum', 'Moisturizer', 'Sunscreen', 'Mask']
                    for cat in categories:
                        ui.button(cat, on_click=lambda c=cat: search_input.set_value(c)).props('outline rounded size=sm').classes('text-pink-400 border-pink-100 px-4 py-1')

                # Search Input
                search_input = ui.input('Cari Produk...', on_change=search_product_for_routine).props('outlined rounded icon=search').classes('w-full')
                
                # Results Area
                ui.label('HASIL PENCARIAN').classes('text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mt-4')
                search_results_container = ui.column().classes('w-full max-h-[350px] overflow-y-auto gap-3')
                
                # Initial show: Wishlist
                wishlist = app.storage.user.get('wishlist', [])
                if wishlist:
                    with search_results_container:
                        ui.label('✨ Dari Wishlist Anda').classes('text-[10px] font-black text-blue-400 uppercase tracking-widest mt-2')
                        for p in wishlist[:5]:
                            with ui.row().classes('w-full hover:bg-blue-50 p-4 cursor-pointer items-center rounded-[1.5rem] border border-gray-100 transition-all'):
                                with ui.element('div').classes('w-12 h-12 bg-white rounded-xl p-1 border border-gray-100 flex items-center justify-center'):
                                    ui.image(p.get('image_url') or p.get('image')).classes('w-full h-full object-contain')
                                with ui.column().classes('flex-1 gap-0'):
                                    ui.label(p.get('product_name') or p.get('nama')).classes('text-xs font-black text-gray-800 line-clamp-1')
                                    ui.label(p.get('brand', 'Unknown Brand')).classes('text-[8px] font-black text-gray-400 uppercase')
                                ui.button(icon='add', on_click=lambda p_name=(p.get('product_name') or p.get('nama')): add_custom_item(p_name)).props('flat round size=sm').classes('bg-blue-50 text-blue-500')

            with ui.row().classes('w-full justify-center p-6 bg-gray-50 border-t'):
                ui.button('Selesai', on_click=add_item_modal.close).props('flat').classes('text-gray-400 font-bold uppercase tracking-widest text-xs')

    UIComponents.sidebar()
