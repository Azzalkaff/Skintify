"""
admin_page.py — Admin Panel (Role-Based Access Control)
Halaman khusus Admin untuk:
  1. Manajemen Katalog Produk (CRUD)
  2. Kurasi Template Routine
  3. Data Ops & Trigger Scraping
"""
from nicegui import ui, app
import subprocess
import sys
import os
import asyncio
import logging

from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.context import data_mgr
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi, Produk

logger = logging.getLogger(__name__)


def show_page():
    """Halaman Admin Panel — Hanya bisa diakses oleh role 'admin'."""

    # === DOUBLE CHECK KEAMANAN (3B) — Jangan hanya andalkan route guard ===
    if app.storage.user.get('role') != 'admin':
        ui.navigate.to('/')
        return

    UIComponents.navbar()
    UIComponents.sidebar()

    # State untuk manajemen UI
    admin_state = {
        'active_tab': 'produk',
        'product_page': 1,
        'product_search': '',
        'scraping_log': [],
        'is_scraping': False,
    }

    with ui.column().classes('w-full p-8 gap-6'):
        # Header Admin
        with ui.row().classes('w-full items-center gap-4 mb-2'):
            ui.icon('admin_panel_settings', size='40px').classes('text-[#7B1FA2]')
            with ui.column().classes('gap-0'):
                ui.label('Admin Panel').classes('text-2xl font-black text-gray-800 tracking-tight')
                ui.label(f'Selamat datang, {app.storage.user.get("username", "Admin")}').classes('text-sm text-gray-500')

        # Tab Navigation
        with ui.tabs().classes('w-full').props('dense active-color=purple indicator-color=purple') as tabs:
            tab_produk = ui.tab('produk', label='📦 Manajemen Produk')
            tab_template = ui.tab('template', label='🧴 Template Routine')
            tab_dataops = ui.tab('dataops', label='⚡ Data Ops & Scraping')

        with ui.tab_panels(tabs, value='produk').classes('w-full'):

            # ═══════════════════════════════════════════════════════
            # TAB 1: MANAJEMEN PRODUK (CRUD)
            # ═══════════════════════════════════════════════════════
            with ui.tab_panel('produk'):
                _render_product_management(admin_state)

            # ═══════════════════════════════════════════════════════
            # TAB 2: TEMPLATE ROUTINE
            # ═══════════════════════════════════════════════════════
            with ui.tab_panel('template'):
                _render_template_management()

            # ═══════════════════════════════════════════════════════
            # TAB 3: DATA OPS & SCRAPING
            # ═══════════════════════════════════════════════════════
            with ui.tab_panel('dataops'):
                _render_data_ops(admin_state)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1: MANAJEMEN PRODUK
# ─────────────────────────────────────────────────────────────────────────────

def _render_product_management(admin_state: dict):
    with ui.tabs().classes('w-full').props('dense align=left active-color=primary indicator-color=primary') as subtabs:
        tab_sociolla = ui.tab('sociolla', label='Sociolla (Master)')
        tab_tokopedia = ui.tab('tokopedia', label='Tokopedia')
        tab_lazada = ui.tab('lazada', label='Lazada')

    with ui.tab_panels(subtabs, value='sociolla').classes('w-full bg-transparent p-0 mt-4'):
        with ui.tab_panel('sociolla'):
            _render_sociolla_table(admin_state)
        with ui.tab_panel('tokopedia'):
            _render_marketplace_table(admin_state, 'tokopedia')
        with ui.tab_panel('lazada'):
            _render_marketplace_table(admin_state, 'lazada')

def _render_sociolla_table(admin_state: dict):
    """CRUD interface untuk katalog produk Sociolla."""

    # State untuk form tambah produk
    form_data = {
        'product_name': '',
        'brand': '',
        'category': 'Serum',
        'price': '',
        'ingredients': '',
        'image_url': '',
    }

    # State untuk form edit produk
    edit_data = {
        'id': None,
        'product_name': '',
        'brand': '',
        'category': 'Serum',
        'price': '',
        'ingredients': '',
        'image_url': '',
        'visible': False,
    }

    @ui.refreshable
    def product_table():
        """Tabel produk dengan pagination dan pencarian."""
        with SessionLocal() as session:
            query = session.query(SociollaReferensi)

            # Pencarian
            keyword = admin_state.get('product_search', '')
            if keyword:
                st = f"%{keyword}%"
                query = query.filter(
                    SociollaReferensi.product_name.ilike(st) |
                    SociollaReferensi.brand.ilike(st)
                )

            total = query.count()
            page = admin_state.get('product_page', 1)
            per_page = 15
            total_pages = max(1, (total + per_page - 1) // per_page)
            page = max(1, min(page, total_pages))

            results = query.order_by(SociollaReferensi.id.desc()) \
                .offset((page - 1) * per_page).limit(per_page).all()

        # Statistik
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(f'Total: {total} produk').classes('text-sm font-bold text-gray-600')
            ui.label(f'Halaman {page}/{total_pages}').classes('text-xs text-gray-400')

        if not results:
            with ui.column().classes('w-full items-center py-10'):
                ui.icon('inventory_2', size='64px').classes('text-gray-200')
                ui.label('Belum ada produk di database').classes('text-gray-400 mt-2')
            return

        # Tabel
        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
            {'name': 'brand', 'label': 'Brand', 'field': 'brand', 'align': 'left', 'sortable': True},
            {'name': 'product_name', 'label': 'Nama Produk', 'field': 'product_name', 'align': 'left', 'sortable': True},
            {'name': 'category', 'label': 'Kategori', 'field': 'category', 'align': 'left'},
            {'name': 'price', 'label': 'Harga', 'field': 'price', 'align': 'right'},
            {'name': 'manual', 'label': 'Manual', 'field': 'manual', 'align': 'center'},
            {'name': 'actions', 'label': 'Aksi', 'field': 'actions', 'align': 'center'},
        ]

        rows = []
        for r in results:
            rows.append({
                'id': r.id,
                'brand': r.brand or '-',
                'product_name': (r.product_name or '-')[:50],
                'category': r.category or '-',
                'price': f"Rp {int(r.min_price or 0):,}".replace(',', '.'),
                'manual': '✅' if getattr(r, 'is_manual', False) else '',
                'actions': r.id,
            })

        table = ui.table(
            columns=columns, rows=rows, row_key='id',
            pagination={'rowsPerPage': per_page}
        ).classes('w-full').props('flat bordered dense')

        # Slot aksi untuk setiap baris
        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round dense icon="edit" color="blue" size="sm"
                    @click="$parent.$emit('edit', props.row)" />
                <q-btn flat round dense icon="delete" color="red" size="sm"
                    @click="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')

        def handle_edit(e):
            row = e.args
            edit_data['id'] = row['id']
            edit_data['product_name'] = row['product_name']
            edit_data['brand'] = row['brand']
            edit_data['category'] = row['category']
            edit_data['price'] = row['price'].replace('Rp ', '').replace('.', '')
            edit_data['visible'] = True
            edit_dialog.open()

        def handle_delete(e):
            row = e.args
            pid = row['id']
            success = data_mgr.delete_custom_product(pid)
            if success:
                ui.notify(f'✅ Produk ID {pid} berhasil dihapus!', color='positive')
                product_table.refresh()
            else:
                ui.notify(f'❌ Gagal menghapus produk ID {pid}', color='negative')

        table.on('edit', handle_edit)
        table.on('delete', handle_delete)

        # Pagination controls
        with ui.row().classes('w-full justify-center gap-4 mt-4'):
            prev_btn = ui.button(icon='chevron_left', on_click=lambda: _change_page(-1)).props('outline round size=sm')
            if page <= 1:
                prev_btn.disable()
            ui.label(f'{page} / {total_pages}').classes('text-sm font-bold text-gray-600 self-center')
            next_btn = ui.button(icon='chevron_right', on_click=lambda: _change_page(1)).props('outline round size=sm')
            if page >= total_pages:
                next_btn.disable()

    def _change_page(delta):
        admin_state['product_page'] = admin_state.get('product_page', 1) + delta
        product_table.refresh()

    # === SEARCH BAR ===
    with ui.row().classes('w-full items-center gap-4 mb-4'):
        search_input = ui.input('Cari produk (nama/brand)...', on_change=lambda e: _search(e.value)) \
            .props('outlined rounded dense clearable').classes('flex-1')

    def _search(val):
        admin_state['product_search'] = val or ''
        admin_state['product_page'] = 1
        product_table.refresh()

    # === FORM TAMBAH PRODUK (Expansion Panel) ===
    with ui.expansion('➕ Tambah Produk Baru', icon='add_circle').classes('w-full glass-card mb-4').props('header-class="text-purple-700 font-bold"'):
        with ui.column().classes('w-full gap-3 p-4'):
            with ui.row().classes('w-full gap-4'):
                ui.input('Nama Produk').bind_value(form_data, 'product_name').props('outlined dense').classes('flex-1')
                ui.input('Brand').bind_value(form_data, 'brand').props('outlined dense').classes('w-48')
            with ui.row().classes('w-full gap-4'):
                ui.select(data_mgr.categories, label='Kategori').bind_value(form_data, 'category').props('outlined dense').classes('w-48')
                ui.input('Harga (Rp)').bind_value(form_data, 'price').props('outlined dense type=number').classes('w-48')
            ui.input('URL Gambar').bind_value(form_data, 'image_url').props('outlined dense').classes('w-full')
            ui.textarea('Ingredients (pisahkan dengan koma)').bind_value(form_data, 'ingredients').props('outlined dense').classes('w-full')

            def tambah_produk():
                if not form_data['product_name'] or not form_data['brand']:
                    ui.notify('Nama produk dan brand wajib diisi!', color='warning')
                    return
                success = data_mgr.add_custom_product(form_data)
                if success:
                    ui.notify('✅ Produk berhasil ditambahkan!', color='positive')
                    # Reset form
                    for key in form_data:
                        form_data[key] = '' if key != 'category' else 'Serum'
                    product_table.refresh()
                else:
                    ui.notify('❌ Gagal menambahkan produk. Cek log.', color='negative')

            ui.button('Simpan Produk', icon='save', on_click=tambah_produk) \
                .classes('bg-[#7B1FA2] text-white').props('unelevated no-caps')

    # === DIALOG EDIT PRODUK ===
    with ui.dialog() as edit_dialog:
        with ui.card().classes('w-[500px] p-6'):
            ui.label('Edit Produk').classes('text-lg font-bold text-gray-800 mb-4')
            ui.input('Nama Produk').bind_value(edit_data, 'product_name').props('outlined dense').classes('w-full mb-2')
            ui.input('Brand').bind_value(edit_data, 'brand').props('outlined dense').classes('w-full mb-2')
            ui.select(data_mgr.categories, label='Kategori').bind_value(edit_data, 'category').props('outlined dense').classes('w-full mb-2')
            ui.input('Harga (Rp)').bind_value(edit_data, 'price').props('outlined dense type=number').classes('w-full mb-2')
            ui.input('URL Gambar').bind_value(edit_data, 'image_url').props('outlined dense').classes('w-full mb-2')
            ui.textarea('Ingredients').bind_value(edit_data, 'ingredients').props('outlined dense').classes('w-full mb-4')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Batal', on_click=edit_dialog.close).props('flat no-caps')

                def simpan_edit():
                    success = data_mgr.update_custom_product(edit_data['id'], {
                        'product_name': edit_data['product_name'],
                        'brand': edit_data['brand'],
                        'category': edit_data['category'],
                        'price': edit_data['price'],
                        'ingredients': edit_data['ingredients'],
                        'image_url': edit_data['image_url'],
                    })
                    if success:
                        ui.notify('✅ Produk berhasil diperbarui!', color='positive')
                        edit_dialog.close()
                        product_table.refresh()
                    else:
                        ui.notify('❌ Gagal update produk.', color='negative')

                ui.button('Simpan', icon='save', on_click=simpan_edit) \
                    .classes('bg-[#7B1FA2] text-white').props('unelevated no-caps')

    # Render tabel
    product_table()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1B: MARKETPLACE TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _render_marketplace_table(admin_state: dict, platform: str):
    """View interface untuk data produk Tokopedia/Lazada."""
    page_key = f"{platform}_page"
    search_key = f"{platform}_search"

    @ui.refreshable
    def marketplace_table():
        with SessionLocal() as session:
            query = session.query(Produk).filter(Produk.platform == platform)

            keyword = admin_state.get(search_key, '')
            if keyword:
                st = f"%{keyword}%"
                query = query.filter(
                    Produk.nama.ilike(st) |
                    Produk.keyword.ilike(st)
                )

            total = query.count()
            page = admin_state.get(page_key, 1)
            per_page = 15
            total_pages = max(1, (total + per_page - 1) // per_page)
            page = max(1, min(page, total_pages))

            results = query.order_by(Produk.id.desc()) \
                .offset((page - 1) * per_page).limit(per_page).all()

        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(f'Total: {total} produk').classes('text-sm font-bold text-gray-600')
            ui.label(f'Halaman {page}/{total_pages}').classes('text-xs text-gray-400')

        if not results:
            with ui.column().classes('w-full items-center py-10'):
                ui.icon('inventory_2', size='64px').classes('text-gray-200')
                ui.label(f'Belum ada produk {platform.capitalize()} di database').classes('text-gray-400 mt-2')
            return

        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
            {'name': 'keyword', 'label': 'Keyword Scrape', 'field': 'keyword', 'align': 'left', 'sortable': True},
            {'name': 'nama', 'label': 'Nama Produk', 'field': 'nama', 'align': 'left'},
            {'name': 'harga', 'label': 'Harga', 'field': 'harga', 'align': 'right', 'sortable': True},
            {'name': 'terjual', 'label': 'Terjual', 'field': 'terjual', 'align': 'right', 'sortable': True},
            {'name': 'rating', 'label': 'Rating', 'field': 'rating', 'align': 'right', 'sortable': True},
            {'name': 'mapped', 'label': 'Mapped to Master', 'field': 'mapped', 'align': 'center'},
        ]

        rows = []
        for r in results:
            rows.append({
                'id': r.id,
                'keyword': (r.keyword or '-')[:30],
                'nama': (r.nama or '-')[:60],
                'harga': f"Rp {int(r.harga or 0):,}".replace(',', '.'),
                'terjual': r.terjual or 0,
                'rating': r.rating or '-',
                'mapped': '✅' if r.referensi_id else '❌'
            })

        ui.table(
            columns=columns, rows=rows, row_key='id',
            pagination={'rowsPerPage': per_page}
        ).classes('w-full').props('flat bordered dense')

        with ui.row().classes('w-full justify-center gap-4 mt-4'):
            prev_btn = ui.button(icon='chevron_left', on_click=lambda: _change_page(-1)).props('outline round size=sm')
            if page <= 1: prev_btn.disable()
            ui.label(f'{page} / {total_pages}').classes('text-sm font-bold text-gray-600 self-center')
            next_btn = ui.button(icon='chevron_right', on_click=lambda: _change_page(1)).props('outline round size=sm')
            if page >= total_pages: next_btn.disable()

    def _change_page(delta):
        admin_state[page_key] = admin_state.get(page_key, 1) + delta
        marketplace_table.refresh()

    with ui.row().classes('w-full items-center gap-4 mb-4'):
        ui.input(f'Cari produk {platform.capitalize()}...', on_change=lambda e: _search(e.value)) \
            .props('outlined rounded dense clearable').classes('flex-1')

    def _search(val):
        admin_state[search_key] = val or ''
        admin_state[page_key] = 1
        marketplace_table.refresh()

    marketplace_table()

# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2: TEMPLATE ROUTINE
# ─────────────────────────────────────────────────────────────────────────────

def _render_template_management():
    """Kurasi template skincare/makeup routine resmi dari Skintify (Kits/Bundles)."""

    template_form = {
        'name': '',
        'description': '',
        'category': 'Skincare',
        'skin_type': 'Semua Jenis Kulit',
        'products': []  # List of product dicts
    }

    search_input = {'value': ''}

    with ui.column().classes('w-full gap-4'):
        # Header
        with ui.row().classes('items-center gap-3 mb-2'):
            ui.icon('inventory_2', size='32px').classes('text-[#7B1FA2]')
            ui.label('Buat Skintify Curated Kit').classes('text-xl font-bold text-gray-800')

        ui.label('Kombinasikan produk-produk dari database menjadi satu paket (Kit) yang bisa langsung dipilih oleh user.') \
            .classes('text-sm text-gray-500 mb-4')

        # Form Pembuatan Kit
        with ui.card().classes('w-full glass-card p-6'):
            with ui.row().classes('w-full gap-4'):
                ui.input('Nama Kit (misal: Acne Rescue Starter Pack)') \
                    .bind_value(template_form, 'name').props('outlined dense').classes('flex-1')
                ui.select(
                    ['Skincare', 'Makeup', 'Bodycare', 'Haircare'],
                    label='Kategori Kit'
                ).bind_value(template_form, 'category').props('outlined dense').classes('w-40')
                ui.select(
                    ['Normal', 'Kering', 'Berminyak', 'Kombinasi', 'Sensitif', 'Semua Jenis Kulit'],
                    label='Target Kulit'
                ).bind_value(template_form, 'skin_type').props('outlined dense').classes('w-48')

            ui.textarea('Deskripsi Singkat (Jelaskan manfaat kit ini)') \
                .bind_value(template_form, 'description').props('outlined dense').classes('w-full mt-3')

            ui.separator().classes('my-4')

            # --- BUILDER AREA ---
            with ui.row().classes('w-full gap-6 items-start'):
                # Kiri: Search & Add Products
                with ui.column().classes('flex-1 gap-2'):
                    ui.label('1. Cari & Tambah Produk').classes('text-sm font-bold text-gray-700 uppercase tracking-wider')
                    
                    search_field = ui.input('Ketik nama/brand produk...', on_change=lambda e: _search_product(e.value)) \
                        .props('outlined dense icon=search clearable').classes('w-full')

                    # Quick Shortcuts (Low Cognitive)
                    with ui.row().classes('w-full gap-2 mt-1 mb-2 flex-wrap'):
                        shortcuts = ['Cleanser', 'Toner', 'Serum', 'Moisturizer', 'Sunscreen', 'Mask']
                        for cat in shortcuts:
                            ui.button(cat, on_click=lambda c=cat: search_field.set_value(c)).props('outline rounded size=xs').classes('text-purple-500 border-purple-100 bg-purple-50/50 hover:bg-purple-100 px-3 py-0 font-bold')

                    search_results_container = ui.column().classes('w-full max-h-[300px] overflow-y-auto gap-2 p-2 border border-gray-100 rounded-xl bg-gray-50')
                    
                    def _search_product(keyword):
                        search_results_container.clear()
                        if not keyword or len(keyword) < 3:
                            with search_results_container:
                                ui.label('Ketik minimal 3 huruf...').classes('text-xs text-gray-400 italic p-2')
                            return
                            
                        with SessionLocal() as session:
                            st = f"%{keyword.lower()}%"
                            results = session.query(SociollaReferensi).filter(
                                SociollaReferensi.product_name.ilike(st) | SociollaReferensi.brand.ilike(st)
                            ).limit(10).all()
                            
                            with search_results_container:
                                if not results:
                                    ui.label('Tidak ditemukan.').classes('text-xs text-gray-400 italic p-2')
                                else:
                                    for p in results:
                                        with ui.row().classes('w-full items-center justify-between p-2 bg-white rounded-lg border border-gray-200 hover:border-purple-300 transition-all'):
                                            with ui.row().classes('items-center gap-2 flex-1 min-w-0'):
                                                img = p.image_url if p.image_url else 'https://via.placeholder.com/50'
                                                ui.image(img).classes('w-8 h-8 object-contain rounded')
                                                with ui.column().classes('gap-0 flex-1'):
                                                    ui.label(p.product_name).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                                    ui.label(f"{p.brand} • Rp {int(p.min_price or 0):,}").classes('text-[10px] text-gray-500')
                                            
                                            ui.button(icon='add', on_click=lambda prod=p: _add_to_kit(prod)) \
                                                .props('flat round dense size=sm color=purple').tooltip('Tambahkan')

                    def _add_to_kit(prod):
                        # Cek duplikat
                        if any(item['id'] == prod.id for item in template_form['products']):
                            ui.notify('Produk sudah ada di Kit!', color='warning')
                            return
                            
                        template_form['products'].append({
                            'id': prod.id,
                            'name': prod.product_name,
                            'brand': prod.brand,
                            'price': prod.min_price or 0,
                            'image': prod.image_url
                        })
                        kit_list.refresh()
                        ui.notify(f"Ditambahkan: {prod.product_name}", color='positive')

                # Kanan: Current Kit Items
                with ui.column().classes('flex-1 gap-2'):
                    ui.label('2. Isi Kit Anda').classes('text-sm font-bold text-gray-700 uppercase tracking-wider')
                    
                    @ui.refreshable
                    def kit_list():
                        if not template_form['products']:
                            ui.label('Belum ada produk. Tambahkan dari panel kiri.').classes('text-xs text-gray-400 italic p-4 text-center border-2 border-dashed border-gray-200 rounded-xl w-full')
                            return
                            
                        total_price = 0
                        with ui.column().classes('w-full gap-2'):
                            for i, item in enumerate(template_form['products']):
                                total_price += item['price']
                                with ui.row().classes('w-full items-center justify-between p-2 bg-purple-50 rounded-lg border border-purple-100'):
                                    with ui.row().classes('items-center gap-2 flex-1 min-w-0'):
                                        ui.label(str(i+1)).classes('w-5 h-5 bg-purple-200 text-purple-800 rounded-full flex items-center justify-center text-[10px] font-black shrink-0')
                                        img = item['image'] if item['image'] else 'https://via.placeholder.com/50'
                                        ui.image(img).classes('w-8 h-8 object-contain rounded bg-white')
                                        with ui.column().classes('gap-0 flex-1'):
                                            ui.label(item['name']).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                            ui.label(f"Rp {int(item['price']):,}").classes('text-[10px] text-purple-600 font-bold')
                                    
                                    ui.button(icon='close', on_click=lambda idx=i: _remove_from_kit(idx)) \
                                        .props('flat round dense size=sm color=red')
                                        
                        # Estimasi Harga
                        with ui.row().classes('w-full justify-between items-center mt-2 p-3 bg-gray-800 rounded-xl text-white'):
                            ui.label('Estimasi Total Harga:').classes('text-xs font-bold')
                            ui.label(f"Rp {int(total_price):,}").classes('text-lg font-black text-green-400')
                            
                    def _remove_from_kit(idx):
                        template_form['products'].pop(idx)
                        kit_list.refresh()

                    kit_list()

            ui.separator().classes('my-6')

            def save_template():
                if not template_form['name']:
                    ui.notify('Nama Kit wajib diisi!', color='warning')
                    return
                if not template_form['products']:
                    ui.notify('Tambahkan minimal 1 produk ke dalam Kit!', color='warning')
                    return

                # Simpan ke app.storage
                templates = app.storage.general.get('admin_templates', [])
                
                # Hitung total harga
                total = sum(p['price'] for p in template_form['products'])
                
                templates.append({
                    'name': template_form['name'],
                    'description': template_form['description'],
                    'category': template_form['category'],
                    'skin_type': template_form['skin_type'],
                    'products': list(template_form['products']),
                    'total_price': total,
                    'created_by': app.storage.user.get('username', 'Admin'),
                })
                app.storage.general['admin_templates'] = templates

                ui.notify(f'✅ Kit "{template_form["name"]}" berhasil disimpan!', color='positive')
                
                # Reset Form
                template_form['name'] = ''
                template_form['description'] = ''
                template_form['products'] = []
                kit_list.refresh()
                saved_templates.refresh()

            ui.button('💾 Simpan Kit Publik', on_click=save_template) \
                .classes('bg-[#7B1FA2] text-white w-full py-4 text-base font-black tracking-widest') \
                .props('unelevated no-caps rounded-xl shadow-lg')

        # === DAFTAR KIT YANG SUDAH ADA ===
        ui.label('Daftar Curated Kit Skintify').classes('text-lg font-bold text-gray-800 mt-8 mb-2')

        @ui.refreshable
        def saved_templates():
            templates = app.storage.general.get('admin_templates', [])
            if not templates:
                ui.label('Belum ada kit yang dibuat.').classes('text-sm text-gray-400 italic p-6 bg-white rounded-xl w-full text-center')
                return

            with ui.grid(columns=2).classes('w-full gap-4'):
                for i, t in enumerate(templates):
                    # Migrasi struktur lama ke baru (fallback)
                    prods = t.get('products', [])
                    is_legacy = len(prods) == 0 and t.get('steps')
                    
                    with ui.card().classes('glass-card p-4 border-none'):
                        with ui.row().classes('w-full justify-between items-start mb-2'):
                            with ui.column().classes('gap-1'):
                                ui.label(t['name']).classes('text-base font-black text-gray-800')
                                with ui.row().classes('gap-1'):
                                    ui.badge(t.get('category', 'Skincare'), color='purple').props('outline')
                                    ui.badge(t['skin_type'], color='blue').props('outline')
                            
                            ui.button(icon='delete', on_click=lambda idx=i: hapus_template(idx)) \
                                .props('flat round dense size=sm color=red bg-red-50').tooltip('Hapus Kit')
                                
                        if t.get('description'):
                            ui.label(t['description']).classes('text-xs text-gray-500 mb-3 line-clamp-2')
                            
                        if is_legacy:
                            ui.label('⚠️ Format Lama (Teks Saja)').classes('text-[10px] text-orange-500 font-bold')
                        else:
                            ui.label(f"Total Produk: {len(prods)}").classes('text-[10px] font-bold text-gray-400 uppercase tracking-wider')
                            with ui.row().classes('w-full overflow-x-auto gap-2 py-2 no-wrap hide-scrollbar'):
                                for p in prods:
                                    img = p.get('image') if p.get('image') else 'https://via.placeholder.com/50'
                                    ui.image(img).classes('w-10 h-10 rounded object-contain bg-white border border-gray-100 shrink-0').tooltip(p.get('name', ''))
                            
                            ui.label(f"Rp {int(t.get('total_price', 0)):,}").classes('text-sm font-black text-green-600 mt-2')

            def hapus_template(idx):
                templates = app.storage.general.get('admin_templates', [])
                templates.pop(idx)
                app.storage.general['admin_templates'] = templates
                ui.notify('Kit dihapus.', color='info')
                saved_templates.refresh()

        saved_templates()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3: DATA OPS & SCRAPING
# ─────────────────────────────────────────────────────────────────────────────

def _render_data_ops(admin_state: dict):
    """Interface untuk menjalankan scraping dan operasi data."""

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts', 'data_ops')

    # Daftar operasi yang bisa dijalankan
    ops = [
        {
            'name': 'Start Main Scraper',
            'icon': 'spider',
            'color': '#8E24AA',
            'script': 'app/scraping/main_scraper.py',
            'desc': 'Menjalankan semua scraper (Tokopedia & Lazada) secara paralel.',
        },
        {
            'name': 'Scrape Tokopedia',
            'icon': 'storefront',
            'color': '#42B549',
            'script': 'app/scraping/tokopedia_scraper.py',
            'desc': 'Menjalankan scraper khusus Tokopedia.',
        },
        {
            'name': 'Scrape Lazada',
            'icon': 'shopping_bag',
            'color': '#1E88E5',
            'script': 'app/scraping/lazada_scraper.py',
            'desc': 'Menjalankan scraper khusus Lazada.',
        },
        {
            'name': 'Import JSON → Database',
            'icon': 'upload_file',
            'color': '#1E88E5',
            'script': 'scripts/data_ops/json_to_database.py',
            'desc': 'Mengimpor data produk dari file JSON Sociolla ke database SQLite.',
        },
        {
            'name': 'Import Marketplace to DB',
            'icon': 'save',
            'color': '#F57C00',
            'script': 'scripts/data_ops/marketplace_to_database.py',
            'desc': 'Mengimpor data hasil scrape marketplace JSON ke SQLite.',
        },
        {
            'name': 'Hapus Data Marketplace',
            'icon': 'delete_sweep',
            'color': '#E53935',
            'script': 'scripts/data_ops/hapus_data_marketplace.py',
            'desc': 'Menghapus SEMUA data produk Tokopedia dan Lazada dari database.',
        },
        {
            'name': 'Reset Status Scrape',
            'icon': 'restart_alt',
            'color': '#E53935',
            'script': 'scripts/data_ops/reset_scrape_status.py',
            'desc': 'Me-reset flag sudah_di_scrape agar produk bisa di-scrape ulang.',
        },
    ]

    with ui.column().classes('w-full gap-4'):
        # Header
        with ui.row().classes('items-center gap-3 mb-2'):
            ui.icon('terminal', size='32px').classes('text-[#7B1FA2]')
            ui.label('Data Operations Center').classes('text-xl font-bold text-gray-800')

        ui.label('Jalankan operasi data langsung dari panel ini. Output akan ditampilkan di area log di bawah.') \
            .classes('text-sm text-gray-500 mb-4')

        # Kartu Operasi
        with ui.row().classes('w-full gap-4 flex-wrap'):
            for op in ops:
                script_path = os.path.join(BASE_DIR, *op['script'].split('/'))
                script_exists = os.path.exists(script_path)

                with ui.card().classes('glass-card w-[280px] p-5 flex-shrink-0'):
                    with ui.row().classes('items-center gap-3 mb-3'):
                        ui.icon(op['icon'], size='28px').style(f'color: {op["color"]}')
                        ui.label(op['name']).classes('text-sm font-bold text-gray-800')

                    ui.label(op['desc']).classes('text-xs text-gray-500 mb-4 leading-relaxed')

                    if script_exists:
                        ui.button(
                            '▶ Jalankan',
                            on_click=lambda s=script_path, n=op['name']: _run_script(s, n, admin_state)
                        ).classes('w-full bg-gray-800 text-white text-xs font-bold') \
                            .props('unelevated no-caps rounded')
                    else:
                        ui.label(f'⚠️ Script tidak ditemukan').classes('text-xs text-red-400 italic')

        # Area Log Output
        ui.separator().classes('my-4')
        ui.label('📋 Log Output').classes('text-sm font-bold text-gray-700 uppercase tracking-wider')

        log_area = ui.log(max_lines=50).classes('w-full h-64 bg-gray-900 text-green-400 rounded-xl p-4 font-mono text-xs')
        log_area.push('🖥️ Admin Panel Terminal — Siap menerima perintah.')

        # Store reference for _run_script
        admin_state['log_area'] = log_area


async def _run_script(script_path: str, name: str, admin_state: dict):
    """Menjalankan script Python secara asinkron dan menampilkan output di log area."""
    log_area = admin_state.get('log_area')
    if not log_area:
        ui.notify('Log area belum siap.', color='warning')
        return

    if admin_state.get('is_scraping'):
        ui.notify('⏳ Ada proses yang masih berjalan!', color='warning')
        return

    admin_state['is_scraping'] = True
    log_area.push(f'\n{"="*60}')
    log_area.push(f'▶ Memulai: {name}')
    log_area.push(f'  Script: {script_path}')
    log_area.push(f'{"="*60}')

    ui.notify(f'⚡ Menjalankan: {name}...', color='info', icon='terminal')

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(os.path.dirname(script_path)),  # Set CWD ke root project
        )

        async for line in process.stdout:
            decoded = line.decode('utf-8', errors='replace').rstrip()
            if decoded:
                log_area.push(decoded)

        await process.wait()

        if process.returncode == 0:
            log_area.push(f'\n✅ {name} selesai dengan sukses!')
            ui.notify(f'✅ {name} selesai!', color='positive')
        else:
            log_area.push(f'\n❌ {name} selesai dengan error (code: {process.returncode})')
            ui.notify(f'❌ {name} gagal!', color='negative')

    except Exception as e:
        log_area.push(f'\n💥 Error: {str(e)}')
        ui.notify(f'💥 Error: {str(e)}', color='negative')
    finally:
        admin_state['is_scraping'] = False
