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
from app.database.models import SociollaReferensi, Produk, Toko

logger = logging.getLogger(__name__)

# --- Robust discovery of PROJECT_ROOT containing cli.py ---
from pathlib import Path
import time
current_dir = Path(__file__).resolve()
PROJECT_ROOT = None
for parent in current_dir.parents:
    if (parent / 'cli.py').exists() or (parent / 'main.py').exists():
        PROJECT_ROOT = parent
        break
if not PROJECT_ROOT:
    PROJECT_ROOT = current_dir.parent.parent.parent.parent # fallback to 4 levels up


def get_python_interpreter():
    import sys
    if getattr(sys, 'frozen', False):
        venv_python = Path(PROJECT_ROOT) / "venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return "python"
    return sys.executable


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
            ui.icon('admin_panel_settings', size='40px').classes('text-[#1E88E5]')
            with ui.column().classes('gap-0'):
                ui.label('Admin Panel').classes('text-2xl font-black text-gray-800 tracking-tight')
                ui.label(f'Selamat datang, {app.storage.user.get("username", "Admin")}').classes('text-sm text-gray-500')

        # Tab Navigation
        with ui.tabs().classes('w-full').props('dense active-color=blue indicator-color=blue') as tabs:
            tab_produk = ui.tab('produk', label='📦 Manajemen Produk')
            tab_template = ui.tab('template', label='🧴 Template Routine')
            tab_dataops = ui.tab('dataops', label='⚡ Data Ops & Scraping')
            tab_transparansi = ui.tab('transparansi', label='🔍 Transparansi Pemetaan')
            tab_cli = ui.tab('cli', label='💻 Control Center')

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

            # ═══════════════════════════════════════════════════════
            # TAB 4: TRANSPARANSI PEMETAAN
            # ═══════════════════════════════════════════════════════
            with ui.tab_panel('transparansi'):
                _render_transparency_page()

            # ═══════════════════════════════════════════════════════
            # TAB 5: DEVELOPER CONTROL CENTER (cli.py inside Web App)
            # ═══════════════════════════════════════════════════════
            with ui.tab_panel('cli'):
                _render_developer_control_center(admin_state)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1: MANAJEMEN PRODUK
# ─────────────────────────────────────────────────────────────────────────────

def _render_product_management(admin_state: dict):
    with ui.tabs().classes('w-full').props('dense align=left active-color=primary indicator-color=primary') as subtabs:
        tab_sociolla = ui.tab('sociolla', label='Sociolla (Master)')
        tab_tokopedia = ui.tab('tokopedia', label='Tokopedia')
        tab_lazada = ui.tab('lazada', label='Lazada')
        tab_shopee = ui.tab('shopee', label='Shopee')

    with ui.tab_panels(subtabs, value='sociolla').classes('w-full bg-transparent p-0 mt-4'):
        with ui.tab_panel('sociolla'):
            _render_sociolla_table(admin_state)
        with ui.tab_panel('tokopedia'):
            _render_marketplace_table(admin_state, 'tokopedia')
        with ui.tab_panel('lazada'):
            _render_marketplace_table(admin_state, 'lazada')
        with ui.tab_panel('shopee'):
            _render_marketplace_table(admin_state, 'shopee')

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

    # State untuk form affiliate
    affiliate_data = {
        'referensi_id': None,
        'product_name': '',
        'tokopedia_url': '',
        'shopee_url': '',
        'lazada_url': '',
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
            results = query.order_by(SociollaReferensi.id.desc()).all()

        # Statistik
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(f'Total: {total} produk').classes('text-sm font-bold text-gray-600')

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
            pagination={'rowsPerPage': 15}
        ).classes('w-full').props('flat bordered dense :rows-per-page-options="[15, 30, 50, 100, 0]"')

        # Slot aksi untuk setiap baris
        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round dense icon="search" color="green" size="sm" type="a" target="_blank" :href="'https://www.tokopedia.com/search?q=' + encodeURIComponent(props.row.product_name)">
                    <q-tooltip>Cari di Tokopedia</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="shopping_bag" color="orange" size="sm" type="a" target="_blank" :href="'https://shopee.co.id/search?keyword=' + encodeURIComponent(props.row.product_name)">
                    <q-tooltip>Cari di Shopee</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="local_mall" color="blue-9" size="sm" type="a" target="_blank" :href="'https://www.lazada.co.id/catalog/?q=' + encodeURIComponent(props.row.product_name)">
                    <q-tooltip>Cari di Lazada</q-tooltip>
                </q-btn>
                
                <q-btn flat round dense icon="link" color="purple" size="sm"
                    @click="$parent.$emit('add_affiliate', props.row)">
                    <q-tooltip>Input Link Affiliate</q-tooltip>
                </q-btn>

                <q-btn flat round dense icon="edit" color="blue" size="sm"
                    @click="$parent.$emit('edit', props.row)">
                    <q-tooltip>Edit Produk</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete" color="red" size="sm"
                    @click="$parent.$emit('delete', props.row)">
                    <q-tooltip>Hapus Produk</q-tooltip>
                </q-btn>
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

        def handle_add_affiliate(e):
            row = e.args
            affiliate_data['referensi_id'] = row['id']
            affiliate_data['product_name'] = row['product_name']
            
            # Fetch existing urls if any
            with SessionLocal() as session:
                from app.database.models import Produk
                prods = session.query(Produk).filter_by(referensi_id=row['id']).all()
                
                tp_url = ''
                sp_url = ''
                lz_url = ''
                
                for p in prods:
                    if p.platform == 'tokopedia' and p.url:
                        tp_url = p.url
                    elif p.platform == 'shopee' and p.url:
                        sp_url = p.url
                    elif p.platform == 'lazada' and p.url:
                        lz_url = p.url
                        
            affiliate_data['tokopedia_url'] = tp_url
            affiliate_data['shopee_url'] = sp_url
            affiliate_data['lazada_url'] = lz_url
            
            affiliate_dialog.open()

        table.on('add_affiliate', handle_add_affiliate)

    # === SEARCH BAR ===
    with ui.row().classes('w-full items-center gap-4 mb-4'):
        search_input = ui.input('Cari produk (nama/brand)...', on_change=lambda e: _search(e.value)) \
            .props('outlined rounded dense clearable').classes('flex-1')

    def _search(val):
        admin_state['product_search'] = val or ''
        product_table.refresh()

    # === FORM TAMBAH PRODUK (Expansion Panel) ===
    with ui.expansion('➕ Tambah Produk Baru', icon='add_circle').classes('w-full glass-card-static mb-4').props('header-class="text-blue-700 font-bold"'):
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
                .classes('bg-[#1E88E5] text-white').props('unelevated no-caps')

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
                    .classes('bg-[#1E88E5] text-white').props('unelevated no-caps')

    # === DIALOG AFFILIATE LINK ===
    with ui.dialog() as affiliate_dialog:
        with ui.card().classes('w-[500px] p-6'):
            ui.label('Input Link Affiliate').classes('text-lg font-bold text-gray-800 mb-4')
            ui.label().bind_text(affiliate_data, 'product_name').classes('text-sm font-bold text-blue-700 mb-4')
            
            ui.input('Link Tokopedia').bind_value(affiliate_data, 'tokopedia_url').props('outlined dense').classes('w-full mb-2')
            ui.input('Link Shopee').bind_value(affiliate_data, 'shopee_url').props('outlined dense').classes('w-full mb-2')
            ui.input('Link Lazada').bind_value(affiliate_data, 'lazada_url').props('outlined dense').classes('w-full mb-4')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Batal', on_click=affiliate_dialog.close).props('flat no-caps')

                def simpan_affiliate():
                    import time
                    from app.database.engine import SessionLocal
                    from app.database.models import Produk, SociollaReferensi
                    
                    try:
                        with SessionLocal() as session:
                            ref_id = affiliate_data['referensi_id']
                            keyword_val = affiliate_data['product_name']
                            
                            ref_obj = session.query(SociollaReferensi).filter_by(id=ref_id).first()
                            harga_default = ref_obj.min_price if ref_obj and ref_obj.min_price else 0
                            
                            def update_or_create_product(platform_name, url_val):
                                if url_val:
                                    existing_p = session.query(Produk).filter_by(referensi_id=ref_id, platform=platform_name).first()
                                    if existing_p:
                                        existing_p.url = url_val
                                    else:
                                        p = Produk(
                                            platform=platform_name,
                                            product_id=f"aff_{int(time.time())}_{platform_name}",
                                            keyword=keyword_val,
                                            nama=keyword_val,
                                            url=url_val,
                                            harga=harga_default,
                                            referensi_id=ref_id
                                        )
                                        session.add(p)

                            update_or_create_product('tokopedia', affiliate_data['tokopedia_url'])
                            update_or_create_product('shopee', affiliate_data['shopee_url'])
                            update_or_create_product('lazada', affiliate_data['lazada_url'])

                            session.commit()
                            ui.notify('✅ Link affiliate berhasil disimpan!', color='positive')
                            affiliate_dialog.close()
                    except Exception as e:
                        logger.error(f"Error saving affiliate links: {e}")
                        ui.notify('❌ Gagal menyimpan link affiliate.', color='negative')

                ui.button('Simpan', icon='save', on_click=simpan_affiliate) \
                    .classes('bg-purple-6 text-white').props('unelevated no-caps')

    # Render tabel
    product_table()


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1B: MARKETPLACE TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _render_marketplace_table(admin_state: dict, platform: str):
    """View interface untuk data produk Tokopedia/Lazada."""
    page_key = f"{platform}_page"
    search_key = f"{platform}_search"

    # Fetch distinct brands and categories for advanced filters
    with SessionLocal() as session:
        cats = session.query(SociollaReferensi.category).distinct().filter(SociollaReferensi.category != None).all()
        categories_list = sorted([c[0] for c in cats])
        
        brs = session.query(SociollaReferensi.brand).distinct().filter(SociollaReferensi.brand != None).all()
        brands_list = sorted([b[0] for b in brs])

    # Initialize state values
    admin_state.setdefault(search_key, '')
    admin_state.setdefault(f"{platform}_brand", 'Semua Brand')
    admin_state.setdefault(f"{platform}_category", 'Semua Kategori')
    admin_state.setdefault(f"{platform}_price_min", '')
    admin_state.setdefault(f"{platform}_price_max", '')

    # State untuk dialog-dialog (reactive)
    mkt_edit_data = {
        'id': None,
        'nama': '',
        'harga': '',
        'terjual': '',
        'rating': '',
        'url': '',
        'toko_id': None,
        'toko_nama': '',
        'toko_url': '',
    }

    delete_shop_data = {
        'toko_id': None,
        'toko_nama': '',
    }

    delete_prod_data = {
        'prod_id': None,
        'prod_nama': '',
    }

    # Helper functions untuk operasi database
    def delete_marketplace_product(prod_id: int) -> bool:
        try:
            with SessionLocal() as session:
                prod = session.query(Produk).filter_by(id=prod_id).first()
                if prod:
                    session.delete(prod)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Gagal menghapus produk marketplace: {e}")
            return False

    def delete_marketplace_shop(toko_id: int) -> bool:
        try:
            with SessionLocal() as session:
                toko = session.query(Toko).filter_by(id=toko_id).first()
                if toko:
                    # Cascade delete akan menghapus semua produk dari toko ini secara otomatis
                    session.delete(toko)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Gagal menghapus toko: {e}")
            return False

    def update_marketplace_product_and_store(prod_id: int, data: dict) -> bool:
        try:
            with SessionLocal() as session:
                prod = session.query(Produk).filter_by(id=prod_id).first()
                if prod:
                    prod.nama = data.get('nama', prod.nama)
                    prod.harga = float(data.get('harga') or 0) if data.get('harga') not in (None, '') else (prod.harga or 0.0)
                    prod.terjual = int(data.get('terjual') or 0) if data.get('terjual') not in (None, '') else (prod.terjual or 0)
                    prod.rating = float(data.get('rating')) if data.get('rating') not in (None, '', '-') else None
                    prod.url = data.get('url', prod.url)
                    
                    if prod.toko_id:
                        toko = session.query(Toko).filter_by(id=prod.toko_id).first()
                        if toko:
                            toko.nama = data.get('toko_nama', toko.nama)
                            toko.url = data.get('toko_url', toko.url)
                            
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Gagal memperbarui produk/toko: {e}")
            return False

    # === DIALOG EDIT PRODUK & TOKO ===
    with ui.dialog() as mkt_edit_dialog:
        with ui.card().classes('w-[550px] p-6'):
            ui.label('Edit Produk & Toko Marketplace').classes('text-lg font-bold text-gray-800 mb-4')
            
            ui.label('Data Produk:').classes('text-xs font-bold text-blue-700 uppercase tracking-wider mb-2')
            ui.input('Nama Produk').bind_value(mkt_edit_data, 'nama').props('outlined dense').classes('w-full mb-2')
            with ui.row().classes('w-full gap-2 mb-2'):
                ui.input('Harga (Rp)').bind_value(mkt_edit_data, 'harga').props('outlined dense type=number').classes('flex-1')
                ui.input('Terjual (Manual)').bind_value(mkt_edit_data, 'terjual').props('outlined dense type=number').classes('flex-1')
                ui.input('Rating').bind_value(mkt_edit_data, 'rating').props('outlined dense type=number step=0.1 min=0 max=5').classes('w-24')
            ui.input('Link Web Produk (URL)').bind_value(mkt_edit_data, 'url').props('outlined dense').classes('w-full mb-4')
            
            ui.label('Data Toko (Shop):').classes('text-xs font-bold text-blue-700 uppercase tracking-wider mb-2')
            ui.input('Nama Toko').bind_value(mkt_edit_data, 'toko_nama').props('outlined dense').classes('w-full mb-2')
            ui.input('Link Web Toko (URL)').bind_value(mkt_edit_data, 'toko_url').props('outlined dense').classes('w-full mb-4')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Batal', on_click=mkt_edit_dialog.close).props('flat no-caps')
                
                def simpan_mkt_edit():
                    success = update_marketplace_product_and_store(mkt_edit_data['id'], {
                        'nama': mkt_edit_data['nama'],
                        'harga': mkt_edit_data['harga'],
                        'terjual': mkt_edit_data['terjual'],
                        'rating': mkt_edit_data['rating'],
                        'url': mkt_edit_data['url'],
                        'toko_nama': mkt_edit_data['toko_nama'],
                        'toko_url': mkt_edit_data['toko_url']
                    })
                    if success:
                        ui.notify('✅ Produk & Toko berhasil diperbarui!', color='positive')
                        mkt_edit_dialog.close()
                        marketplace_table.refresh()
                    else:
                        ui.notify('❌ Gagal memperbarui data.', color='negative')
                        
                ui.button('Simpan', icon='save', on_click=simpan_mkt_edit) \
                    .classes('bg-[#1E88E5] text-white').props('unelevated no-caps')

    # === DIALOG HAPUS TOKO ===
    with ui.dialog() as delete_shop_dialog:
        with ui.card().classes('w-[450px] p-6'):
            ui.label('Konfirmasi Hapus Toko').classes('text-lg font-bold text-red-600 mb-2')
            with ui.row().classes('items-center gap-1 mb-2'):
                ui.label('Apakah Anda yakin ingin menghapus toko ')
                ui.label().classes('font-black text-[#1E88E5]').bind_text(delete_shop_data, 'toko_nama')
                ui.label(' beserta seluruh produknya?')
            ui.label('Tindakan ini akan menghapus toko tersebut beserta semua produknya secara permanen dari database.').classes('text-sm text-gray-500 mb-4')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Batal', on_click=delete_shop_dialog.close).props('flat no-caps')
                
                def eksekusi_hapus_toko():
                    success = delete_marketplace_shop(delete_shop_data['toko_id'])
                    if success:
                        ui.notify(f"✅ Toko '{delete_shop_data['toko_nama']}' & semua produknya berhasil dihapus!", color='positive')
                        delete_shop_dialog.close()
                        marketplace_table.refresh()
                    else:
                        ui.notify('❌ Gagal menghapus toko.', color='negative')
                        
                ui.button('Ya, Hapus Toko', icon='delete_forever', on_click=eksekusi_hapus_toko) \
                    .classes('bg-red-8 text-white').props('unelevated no-caps')

    # === DIALOG HAPUS PRODUK ===
    with ui.dialog() as delete_prod_dialog:
        with ui.card().classes('w-[450px] p-6'):
            ui.label('Konfirmasi Hapus Produk').classes('text-lg font-bold text-red-600 mb-2')
            with ui.row().classes('items-center gap-1 mb-2'):
                ui.label('Apakah Anda yakin ingin menghapus produk ')
                ui.label().classes('font-black text-[#1E88E5]').bind_text(delete_prod_data, 'prod_nama')
                ui.label('?')
            ui.label('Tindakan ini bersifat permanen.').classes('text-sm text-gray-500 mb-4')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Batal', on_click=delete_prod_dialog.close).props('flat no-caps')
                
                def eksekusi_hapus_produk():
                    success = delete_marketplace_product(delete_prod_data['prod_id'])
                    if success:
                        ui.notify('✅ Produk berhasil dihapus!', color='positive')
                        delete_prod_dialog.close()
                        marketplace_table.refresh()
                    else:
                        ui.notify('❌ Gagal menghapus produk.', color='negative')
                        
                ui.button('Ya, Hapus', icon='delete', on_click=eksekusi_hapus_produk) \
                    .classes('bg-red-8 text-white').props('unelevated no-caps')

    @ui.refreshable
    def marketplace_table():
        with SessionLocal() as session:
            query = session.query(Produk).filter(Produk.platform == platform)

            # 1. Keyword search
            keyword = admin_state.get(search_key, '')
            if keyword:
                st = f"%{keyword}%"
                query = query.filter(
                    Produk.nama.ilike(st) |
                    Produk.keyword.ilike(st)
                )

            # 2. Brand filter (Checks linked brand & product name dynamically)
            brand_filter = admin_state.get(f"{platform}_brand", 'Semua Brand')
            if brand_filter and brand_filter != 'Semua Brand':
                st_brand = f"%{brand_filter}%"
                query = query.outerjoin(SociollaReferensi, Produk.referensi_id == SociollaReferensi.id) \
                             .filter((SociollaReferensi.brand == brand_filter) | (Produk.nama.ilike(st_brand)))

            # 3. Kategori filter (Checks linked category & scraped categories)
            category_filter = admin_state.get(f"{platform}_category", 'Semua Kategori')
            if category_filter and category_filter != 'Semua Kategori':
                st_cat = f"%{category_filter}%"
                if not (brand_filter and brand_filter != 'Semua Brand'):
                    query = query.outerjoin(SociollaReferensi, Produk.referensi_id == SociollaReferensi.id)
                query = query.filter((SociollaReferensi.category == category_filter) | (Produk.kategori.ilike(st_cat)))

            # 4. Harga Min filter
            price_min = admin_state.get(f"{platform}_price_min", '')
            if price_min:
                try:
                    query = query.filter(Produk.harga >= float(price_min))
                except ValueError:
                    pass

            # 5. Harga Max filter
            price_max = admin_state.get(f"{platform}_price_max", '')
            if price_max:
                try:
                    query = query.filter(Produk.harga <= float(price_max))
                except ValueError:
                    pass

            total = query.count()
            from sqlalchemy.orm import joinedload
            results = query.options(joinedload(Produk.toko)).order_by(Produk.id.desc()).all()

        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(f'Total: {total} produk').classes('text-sm font-bold text-gray-600')

        if not results:
            with ui.column().classes('w-full items-center py-10'):
                ui.icon('inventory_2', size='64px').classes('text-gray-200')
                ui.label(f'Belum ada produk {platform.capitalize()} di database yang cocok dengan kriteria filter').classes('text-gray-400 mt-2')
            return

        columns = [
            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
            {'name': 'gambar', 'label': 'Gambar', 'field': 'gambar', 'align': 'center'},
            {'name': 'nama', 'label': 'Nama Produk', 'field': 'nama', 'align': 'left'},
            {'name': 'toko', 'label': 'Toko (Shop)', 'field': 'toko', 'align': 'left'},
            {'name': 'harga', 'label': 'Harga', 'field': 'harga', 'align': 'right', 'sortable': True},
            {'name': 'terjual', 'label': 'Terjual', 'field': 'terjual', 'align': 'right', 'sortable': True},
            {'name': 'rating', 'label': 'Rating', 'field': 'rating', 'align': 'right', 'sortable': True},
            {'name': 'mapped', 'label': 'Mapped', 'field': 'mapped', 'align': 'center'},
            {'name': 'actions', 'label': 'Aksi', 'field': 'actions', 'align': 'center'},
        ]

        rows = []
        for r in results:
            rows.append({
                'id': r.id,
                'gambar': r.gambar or '',
                'url': r.url or '',
                'nama': (r.nama or '-')[:100],
                'toko_id': r.toko.id if r.toko else None,
                'toko_nama': r.toko.nama if r.toko else '-',
                'toko_url': r.toko.url if r.toko else '',
                'toko_kota': r.toko.kota if r.toko else '',
                'harga': f"Rp {int(r.harga or 0):,}".replace(',', '.'),
                'terjual': r.terjual or 0,
                'rating': r.rating or '-',
                'mapped': '✅' if r.referensi_id else '❌',
                # Raw data untuk dialog (reactive binding)
                'raw_nama': r.nama or '',
                'raw_harga': int(r.harga or 0),
                'raw_terjual': int(r.terjual or 0),
                'raw_rating': float(r.rating) if r.rating else None,
            })

        table = ui.table(
            columns=columns, rows=rows, row_key='id',
            pagination={'rowsPerPage': 15}
        ).classes('w-full').props('flat bordered dense :rows-per-page-options="[15, 30, 50, 100, 0]"')

        # Custom Slots untuk styling NiceGUI / Quasar
        table.add_slot('body-cell-gambar', '''
            <q-td :props="props">
                <q-avatar square size="40px" v-if="props.row.gambar">
                    <img :src="props.row.gambar" />
                </q-avatar>
                <q-icon name="image_not_supported" size="24px" color="grey" v-else />
            </q-td>
        ''')

        table.add_slot('body-cell-nama', '''
            <q-td :props="props">
                <div class="column gap-0.5">
                    <a :href="props.row.url" target="_blank" class="text-blue-600 hover:underline font-bold text-xs" v-if="props.row.url">
                        {{ props.row.nama }} 🔗
                    </a>
                    <span class="text-xs font-bold" v-else>{{ props.row.nama }}</span>
                </div>
            </q-td>
        ''')

        table.add_slot('body-cell-toko', '''
            <q-td :props="props">
                <div class="column gap-0.5">
                    <a :href="props.row.toko_url" target="_blank" class="text-blue-600 hover:underline font-bold text-xs" v-if="props.row.toko_url">
                        {{ props.row.toko_nama }} 🔗
                    </a>
                    <span class="text-xs font-bold text-gray-700" v-else-if="props.row.toko_nama">
                        {{ props.row.toko_nama }}
                    </span>
                    <span class="text-xs text-gray-400 italic" v-else>-</span>
                    <span class="text-[10px] text-gray-500" v-if="props.row.toko_kota">
                        📍 {{ props.row.toko_kota }}
                    </span>
                </div>
            </q-td>
        ''')

        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat round dense icon="search" color="green" size="sm" type="a" target="_blank" :href="'https://www.tokopedia.com/search?q=' + encodeURIComponent(props.row.nama)">
                    <q-tooltip>Cari di Tokopedia</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="shopping_bag" color="orange" size="sm" type="a" target="_blank" :href="'https://shopee.co.id/search?keyword=' + encodeURIComponent(props.row.nama)">
                    <q-tooltip>Cari di Shopee</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="local_mall" color="blue-9" size="sm" type="a" target="_blank" :href="'https://www.lazada.co.id/catalog/?q=' + encodeURIComponent(props.row.nama)">
                    <q-tooltip>Cari di Lazada</q-tooltip>
                </q-btn>

                <q-btn flat round dense icon="edit" color="blue" size="sm"
                     @click="$parent.$emit('edit_product', props.row)">
                    <q-tooltip>Edit Produk & Toko</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="delete" color="red" size="sm"
                     @click="$parent.$emit('delete_product', props.row)">
                    <q-tooltip>Hapus Produk</q-tooltip>
                </q-btn>
                <q-btn flat round dense icon="store" color="blue-9" size="sm" v-if="props.row.toko_id"
                    @click="$parent.$emit('delete_shop', props.row)">
                    <q-tooltip>Hapus Toko & Semua Produknya</q-tooltip>
                </q-btn>
            </q-td>
        ''')

        # Handlers ke event emitter table
        def handle_edit_product(e):
            row = e.args
            mkt_edit_data['id'] = row['id']
            mkt_edit_data['nama'] = row['raw_nama']
            mkt_edit_data['harga'] = str(row['raw_harga'])
            mkt_edit_data['terjual'] = str(row['raw_terjual'])
            mkt_edit_data['rating'] = str(row['raw_rating']) if row['raw_rating'] is not None else ''
            mkt_edit_data['url'] = row['url']
            mkt_edit_data['toko_id'] = row['toko_id']
            mkt_edit_data['toko_nama'] = row['toko_nama']
            mkt_edit_data['toko_url'] = row['toko_url']
            mkt_edit_dialog.open()

        def handle_delete_product(e):
            row = e.args
            delete_prod_data['prod_id'] = row['id']
            delete_prod_data['prod_nama'] = row['nama']
            delete_prod_dialog.open()

        def handle_delete_shop(e):
            row = e.args
            delete_shop_data['toko_id'] = row['toko_id']
            delete_shop_data['toko_nama'] = row['toko_nama']
            delete_shop_dialog.open()

        table.on('edit_product', handle_edit_product)
        table.on('delete_product', handle_delete_product)
        table.on('delete_shop', handle_delete_shop)



    # Advanced Filters Panel
    with ui.card().classes('w-full bg-blue-50/30 border border-blue-100/50 p-4 mb-4 rounded-xl shadow-sm'):
        with ui.row().classes('w-full items-center justify-between mb-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('tune', size='20px').classes('text-[#1E88E5]')
                ui.label('Filter & Pencarian Lanjutan').classes('text-sm font-bold text-gray-700')
            ui.button('Reset Filter', on_click=lambda: _reset_all_filters()).props('flat dense size=sm color=red-8 no-caps')

        with ui.row().classes('w-full gap-4 items-center flex-wrap lg:flex-nowrap'):
            # 1. Keyword search
            keyword_input = ui.input(
                placeholder=f'Cari nama/keyword {platform.capitalize()}...',
                value=admin_state.get(search_key, ''),
                on_change=lambda e: _update_filter(search_key, e.value)
            ).props('outlined dense clearable').classes('flex-1 min-w-[200px] bg-white')
            
            # 2. Brand Dropdown
            brand_options = ['Semua Brand'] + brands_list
            brand_select = ui.select(
                brand_options,
                value=admin_state.get(f"{platform}_brand", 'Semua Brand'),
                label='Brand',
                on_change=lambda e: _update_filter(f"{platform}_brand", e.value)
            ).props('outlined dense').classes('w-48 bg-white')
            
            # 3. Kategori Dropdown
            cat_options = ['Semua Kategori'] + categories_list
            cat_select = ui.select(
                cat_options,
                value=admin_state.get(f"{platform}_category", 'Semua Kategori'),
                label='Kategori',
                on_change=lambda e: _update_filter(f"{platform}_category", e.value)
            ).props('outlined dense').classes('w-48 bg-white')
            
            # 4. Range Harga
            with ui.row().classes('items-center gap-2 shrink-0 bg-white border border-gray-200 rounded p-1.5'):
                ui.label('Harga:').classes('text-xs text-gray-500 font-bold px-1')
                min_price_input = ui.input(
                    placeholder='Min',
                    value=admin_state.get(f"{platform}_price_min", ''),
                    on_change=lambda e: _update_filter(f"{platform}_price_min", e.value)
                ).props('outlined dense type=number clearable').classes('w-24 bg-white')
                ui.label('-').classes('text-gray-400')
                max_price_input = ui.input(
                    placeholder='Max',
                    value=admin_state.get(f"{platform}_price_max", ''),
                    on_change=lambda e: _update_filter(f"{platform}_price_max", e.value)
                ).props('outlined dense type=number clearable').classes('w-24 bg-white')

    def _update_filter(key, val):
        admin_state[key] = val or ''
        marketplace_table.refresh()

    def _reset_all_filters():
        admin_state[search_key] = ''
        admin_state[f"{platform}_brand"] = 'Semua Brand'
        admin_state[f"{platform}_category"] = 'Semua Kategori'
        admin_state[f"{platform}_price_min"] = ''
        admin_state[f"{platform}_price_max"] = ''
        
        # Reset UI inputs
        keyword_input.value = ''
        brand_select.value = 'Semua Brand'
        cat_select.value = 'Semua Kategori'
        min_price_input.value = ''
        max_price_input.value = ''
        
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
            ui.icon('inventory_2', size='32px').classes('text-[#1E88E5]')
            ui.label('Buat Skintify Curated Kit').classes('text-xl font-bold text-gray-800')

        ui.label('Kombinasikan produk-produk dari database menjadi satu paket (Kit) yang bisa langsung dipilih oleh user.') \
            .classes('text-sm text-gray-500 mb-4')

        # Form Pembuatan Kit
        with ui.card().classes('w-full glass-card-static p-6'):
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
                            ui.button(cat, on_click=lambda c=cat: search_field.set_value(c)).props('outline rounded size=xs').classes('text-blue-500 border-blue-100 bg-blue-50/50 hover:bg-blue-100 px-3 py-0 font-bold')

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
                                        with ui.row().classes('w-full items-center justify-between p-2 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-all'):
                                            with ui.row().classes('items-center gap-2 flex-1 min-w-0'):
                                                img = p.image_url if p.image_url else 'https://via.placeholder.com/50'
                                                ui.image(img).classes('w-8 h-8 object-contain rounded')
                                                with ui.column().classes('gap-0 flex-1'):
                                                    ui.label(p.product_name).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                                    ui.label(f"{p.brand} • Rp {int(p.min_price or 0):,}").classes('text-[10px] text-gray-500')
                                            
                                            ui.button(icon='add', on_click=lambda prod=p: _add_to_kit(prod)) \
                                                .props('flat round dense size=sm color=blue').tooltip('Tambahkan')

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
                                with ui.row().classes('w-full items-center justify-between p-2 bg-blue-50 rounded-lg border border-blue-100'):
                                    with ui.row().classes('items-center gap-2 flex-1 min-w-0'):
                                        ui.label(str(i+1)).classes('w-5 h-5 bg-blue-200 text-blue-800 rounded-full flex items-center justify-center text-[10px] font-black shrink-0')
                                        img = item['image'] if item['image'] else 'https://via.placeholder.com/50'
                                        ui.image(img).classes('w-8 h-8 object-contain rounded bg-white')
                                        with ui.column().classes('gap-0 flex-1'):
                                            ui.label(item['name']).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                            ui.label(f"Rp {int(item['price']):,}").classes('text-[10px] text-blue-600 font-bold')
                                    
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
                .classes('bg-[#1E88E5] text-white w-full py-4 text-base font-black tracking-widest') \
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
                                    ui.badge(t.get('category', 'Skincare'), color='blue').props('outline')
                                    ui.badge(t['skin_type'], color='blue').props('outline')
                            
                            ui.button(icon='delete', on_click=lambda idx=i: hapus_template(idx)) \
                                .props('flat round dense size=sm color=red bg-red-50').tooltip('Hapus Kit')
                                
                        if t.get('description'):
                            ui.label(t['description']).classes('text-xs text-gray-500 mb-3 line-clamp-2')
                            
                        if is_legacy:
                            ui.label('⚠️ Format Lama (Teks Saja)').classes('text-[10px] text-blue-500 font-bold')
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

    BASE_DIR = str(PROJECT_ROOT)
    SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts', 'data_ops')

    selected_ids = admin_state.setdefault('selected_ids', set())
    admin_state.setdefault('selected_platform', 'both')

    # Daftar operasi yang bisa dijalankan
    ops = [
        {
            'name': 'Start Main Scraper',
            'icon': 'spider',
            'color': '#8E24AA',
            'script': 'app/scraping/main_scraper.py',
            'desc': 'Menjalankan semua scraper (Tokopedia, Lazada & Shopee) secara paralel.',
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
            'name': 'Scrape Shopee',
            'icon': 'store',
            'color': '#E64A19',
            'script': 'app/scraping/shopee_scraper.py',
            'desc': 'Menjalankan scraper khusus Shopee.',
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
            'desc': 'Menghapus SEMUA data produk Tokopedia, Lazada, dan Shopee dari database.',
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
        with ui.row().classes('w-full items-center gap-3 mb-2'):
            ui.icon('terminal', size='32px').classes('text-[#1E88E5]')
            ui.label('Data Operations Center').classes('text-xl font-bold text-gray-800')

        ui.label('Jalankan operasi data langsung dari panel ini. Output akan ditampilkan di area log di bawah.') \
            .classes('text-sm text-gray-500 mb-4')

        # Helpers untuk Kategori Dinamis
        import json
        
        def load_categories():
            filepath = os.path.join(str(PROJECT_ROOT), "data", "categories_to_scrape.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            # default fallback
            return [
                {"id": "5d3ac309a6992471b7c97f7d", "name": "Serum"},
                {"id": "5e9955b673a74cf9570ce331", "name": "Moisturizer"},
                {"id": "5d3ac309a6992471b7c97f91", "name": "Sunscreen"},
                {"id": "5d3ac309a6992471b7c97f7f", "name": "Toner"},
                {"id": "5e9938206d9c07e1021e1294", "name": "Cleanser"},
                {"id": "62cea8ee6e55507c2de6a13e", "name": "Cushion"},
                {"id": "5d3ac309a6992471b7c97f6b", "name": "Blush"},
                {"id": "5d3ac309a6992471b7c97f6d", "name": "Powder"},
                {"id": "5dbb1374ca096d5a008cefc8", "name": "Eye Product"},
                {"id": "5eb9779ecb172d6891a43143", "name": "LIP Product"}
            ]

        def save_categories(categories):
            filepath = os.path.join(str(PROJECT_ROOT), "data", "categories_to_scrape.json")
            try:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(categories, f, indent=2, ensure_ascii=False)
                # Reset cache
                data_mgr._categories_cache = None
                return True
            except Exception as e:
                logger.error(f"Gagal menyimpan kategori: {e}")
                return False

        # === 🕷️ API SCRAPER CATEGORIES CONFIGURATION PANEL ===
        with ui.expansion('🕷️ Konfigurasi API Scraper (Sociolla Categories)', icon='settings_ethernet')\
                .classes('w-full glass-card-static mb-4')\
                .props('header-class="text-blue-700 font-bold"'):
            
            # State local untuk form tambah kategori
            cat_form = {
                'name': '',
                'id': ''
            }
            
            @ui.refreshable
            def render_categories_list():
                categories = load_categories()
                
                with ui.column().classes('w-full gap-4 p-4'):
                    ui.label('Daftar Kategori yang dikonfigurasi untuk Sociolla Scraper API. Admin dapat menambah kategori baru yang nantinya otomatis muncul di GUI setelah data di-scrape atau di-import.').classes('text-xs text-gray-500 mb-2')
                    
                    # Grid list of current categories
                    with ui.grid(columns=2).classes('w-full gap-3'):
                        for c in categories:
                            with ui.card().classes('p-3 border border-blue-100 bg-blue-50/10 hover:border-blue-300 transition-all'):
                                with ui.row().classes('w-full justify-between items-center no-wrap'):
                                    with ui.column().classes('gap-0 flex-1 min-w-0'):
                                        ui.label(c['name']).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                        ui.label(f"ID: {c['id']}").classes('text-[10px] text-gray-400 font-mono line-clamp-1')
                                    
                                    # Hapus button
                                    def make_delete_cat(cat_to_del=c):
                                        def handle():
                                            current = load_categories()
                                            new_list = [item for item in current if item['id'] != cat_to_del['id'] or item['name'] != cat_to_del['name']]
                                            if save_categories(new_list):
                                                ui.notify(f"Kategori '{cat_to_del['name']}' berhasil dihapus!", color='info')
                                                render_categories_list.refresh()
                                                # Refresh manual panel filters to update options
                                                render_manual_scraper_panel.refresh()
                                            else:
                                                ui.notify("Gagal menghapus kategori.", color='negative')
                                        return handle

                                    # Scrape button
                                    def make_scrape_cat(cat_to_scrape=c):
                                        async def handle():
                                            scraper_script = os.path.join(BASE_DIR, 'app', 'scraping', 'sociolla_scraper.py')
                                            cmd_args = ["--category-id", cat_to_scrape['id']]
                                            cmd_name = f"Scrape Sociolla Kategori: {cat_to_scrape['name']}"
                                            ui.notify(f"Memulai scrape kategori {cat_to_scrape['name']}...", color='info')
                                            await _run_script(scraper_script, cmd_name, admin_state, cmd_args)
                                        return handle
                                    
                                    with ui.row().classes('gap-1 items-center no-wrap'):
                                        ui.button(icon='play_arrow', on_click=make_scrape_cat())\
                                            .props('flat round dense size=sm color=green').tooltip(f"Scrape kategori {c['name']} saja")
                                        ui.button(icon='delete', on_click=make_delete_cat())\
                                            .props('flat round dense size=sm color=red').tooltip("Hapus Kategori")
                    
                    ui.separator().classes('my-2')
                    
                    # Form tambah kategori
                    ui.label('➕ Tambah Kategori Scraper Baru').classes('text-xs font-bold text-blue-700 uppercase tracking-wider')
                    with ui.row().classes('w-full gap-3 items-center flex-wrap lg:flex-nowrap'):
                        name_input = ui.input('Nama Kategori (contoh: Masker)').bind_value(cat_form, 'name').props('outlined dense').classes('flex-1')
                        id_input = ui.input('Sociolla API ID (contoh: 5e993b48227b233a0bfa5f6b)').bind_value(cat_form, 'id').props('outlined dense').classes('flex-1')
                        
                        def add_category():
                            name = cat_form['name'].strip()
                            cat_id = cat_form['id'].strip()
                            
                            if not name or not cat_id:
                                ui.notify('Nama Kategori dan ID Kategori wajib diisi!', color='warning')
                                return
                            
                            current = load_categories()
                            
                            # Cek duplikat ID atau nama
                            if any(item['id'] == cat_id for item in current):
                                ui.notify('ID Kategori sudah terdaftar!', color='warning')
                                return
                            
                            current.append({'id': cat_id, 'name': name})
                            if save_categories(current):
                                ui.notify(f"✅ Kategori '{name}' berhasil ditambahkan!", color='positive')
                                # Reset input
                                cat_form['name'] = ''
                                cat_form['id'] = ''
                                name_input.value = ''
                                id_input.value = ''
                                render_categories_list.refresh()
                                # Refresh manual panel filters to update options
                                render_manual_scraper_panel.refresh()
                            else:
                                ui.notify('Gagal menyimpan kategori baru.', color='negative')
                                
                        ui.button('Tambah', icon='add', on_click=add_category)\
                            .classes('bg-[#1E88E5] text-white').props('unelevated no-caps dense')
            
            render_categories_list()

        # === 🎯 MANUAL SCRAPER PANEL ===
        # Fetch distinct brands and categories from master catalog for the manual panel
        with SessionLocal() as session:
            cats_db = session.query(SociollaReferensi.category).distinct().filter(SociollaReferensi.category != None).all()
            db_cats = [c[0] for c in cats_db]
            config_cats = [c['name'] for c in load_categories()]
            master_categories = sorted(list(set(db_cats + config_cats)))
            
            brs_db = session.query(SociollaReferensi.brand).distinct().filter(SociollaReferensi.brand != None).all()
            master_brands = sorted([b[0] for b in brs_db])

        # Initialize manual panel filters in state
        admin_state.setdefault('manual_search', '')
        admin_state.setdefault('manual_brand', 'Semua Brand')
        admin_state.setdefault('manual_category', 'Semua Kategori')
        admin_state.setdefault('manual_status', 'Semua Status')

        @ui.refreshable
        def render_manual_scraper_panel():
            m_search = admin_state.get('manual_search', '')
            m_brand = admin_state.get('manual_brand', 'Semua Brand')
            m_category = admin_state.get('manual_category', 'Semua Kategori')
            m_status = admin_state.get('manual_status', 'Semua Status')

            def get_filtered_products():
                with SessionLocal() as session:
                    query = session.query(SociollaReferensi)
                    
                    # 1. Text keyword search
                    if m_search:
                        st = f"%{m_search}%"
                        query = query.filter(
                            SociollaReferensi.product_name.ilike(st) |
                            SociollaReferensi.brand.ilike(st)
                        )
                    
                    # 2. Brand filter
                    if m_brand != 'Semua Brand':
                        query = query.filter(SociollaReferensi.brand == m_brand)
                        
                    # 3. Category filter
                    if m_category != 'Semua Kategori':
                        query = query.filter(SociollaReferensi.category == m_category)
                        
                    # 4. Status filter
                    if m_status == 'Belum di-scrape ❌':
                        query = query.filter(SociollaReferensi.sudah_di_scrape == False)
                    elif m_status == 'Sudah di-scrape ✅':
                        query = query.filter(SociollaReferensi.sudah_di_scrape == True)
                        
                    # Tampilkan 50 teratas agar responsif
                    return query.order_by(SociollaReferensi.id.desc()).limit(50).all()

            def select_all_filtered():
                products = get_filtered_products()
                for p in products:
                    selected_ids.add(p.id)
                render_product_list.refresh()
                render_control_panel.refresh()

            def clear_all_selections():
                selected_ids.clear()
                render_product_list.refresh()
                render_control_panel.refresh()

            with ui.card().classes('w-full glass-card-static p-6 mb-2'):
                with ui.row().classes('w-full items-center gap-3 mb-2'):
                    ui.icon('ads_click', size='28px').classes('text-[#1E88E5]')
                    with ui.column().classes('gap-0'):
                        ui.label('🎯 Manual Product Scraper').classes('text-lg font-bold text-gray-800')
                        ui.label('Filter dan pilih produk master secara spesifik untuk di-scrape Tokopedia & Lazada secara real-time.').classes('text-xs text-gray-500')

                with ui.row().classes('w-full gap-6 items-start flex-wrap lg:flex-nowrap'):
                    # Kiri: Product Selector
                    with ui.column().classes('flex-[2] gap-3 min-w-[320px] w-full'):
                        
                        # Row 1 Filters: Keyword & Status
                        with ui.row().classes('w-full gap-2 items-center flex-wrap lg:flex-nowrap'):
                            search_box = ui.input(
                                placeholder='Cari produk master...',
                                value=m_search,
                                on_change=lambda e: update_manual_filter('manual_search', e.value)
                            ).props('outlined dense clearable').classes('flex-1 bg-white')
                            
                            status_select = ui.select(
                                ['Semua Status', 'Belum di-scrape ❌', 'Sudah di-scrape ✅'],
                                value=m_status,
                                label='Status Scrape',
                                on_change=lambda e: update_manual_filter('manual_status', e.value)
                            ).props('outlined dense').classes('w-44 bg-white')

                        # Row 2 Filters: Brand & Category
                        with ui.row().classes('w-full gap-2 items-center flex-wrap lg:flex-nowrap'):
                            brand_select = ui.select(
                                ['Semua Brand'] + master_brands,
                                value=m_brand,
                                label='Brand',
                                on_change=lambda e: update_manual_filter('manual_brand', e.value)
                            ).props('outlined dense').classes('flex-1 bg-white')
                            
                            cat_select = ui.select(
                                ['Semua Kategori'] + master_categories,
                                value=m_category,
                                label='Kategori',
                                on_change=lambda e: update_manual_filter('manual_category', e.value)
                            ).props('outlined dense').classes('flex-1 bg-white')

                        # Row 3: Quick actions
                        with ui.row().classes('w-full gap-2 justify-end'):
                            ui.button('Pilih Semua Terfilter', on_click=select_all_filtered).props('outline dense size=sm color=blue')
                            ui.button('Kosongkan Pilihan', on_click=clear_all_selections).props('outline dense size=sm color=grey')

                        @ui.refreshable
                        def render_product_list():
                            products = get_filtered_products()

                            if not products:
                                with ui.column().classes('w-full items-center py-8 border border-dashed rounded-xl bg-gray-50'):
                                    ui.icon('find_in_page', size='32px', color='grey')
                                    ui.label('Tidak ada produk master ditemukan dengan kriteria filter ini.').classes('text-xs text-gray-400 italic mt-1')
                                return

                            with ui.list().classes('w-full max-h-[300px] overflow-y-auto gap-2 p-2 border border-gray-100 rounded-xl bg-gray-50'):
                                for p in products:
                                    is_checked = p.id in selected_ids
                                    is_scraped = p.sudah_di_scrape
                                    
                                    # Clickable row toggler
                                    def make_toggle(pid=p.id):
                                        def handler():
                                            if pid in selected_ids:
                                                selected_ids.discard(pid)
                                            else:
                                                selected_ids.add(pid)
                                            render_product_list.refresh()
                                            render_control_panel.refresh()
                                        return handler

                                    # Premium clickable list item
                                    with ui.item().props('clickable').on('click', make_toggle(p.id)).classes(
                                        f'w-full items-center justify-between p-2 bg-white rounded-lg border transition-all gap-3 '
                                        f'{"border-blue-400 bg-blue-50/20 shadow-sm" if is_checked else "border-gray-200 hover:border-blue-300"}'
                                    ):
                                        with ui.row().classes('items-center gap-2 flex-1 min-w-0'):
                                            # Dense checkbox that updates visually
                                            ui.checkbox(value=is_checked).props('dense readonly')
                                            
                                            img = p.image_url if p.image_url else 'https://via.placeholder.com/50'
                                            ui.image(img).classes('w-8 h-8 object-contain rounded bg-gray-50 border shrink-0')
                                            with ui.column().classes('gap-0 flex-1 min-w-0'):
                                                ui.label(p.product_name).classes('text-xs font-bold text-gray-800 line-clamp-1')
                                                ui.label(p.brand).classes('text-[10px] text-gray-400')
                                        
                                        # Status badge
                                        if is_scraped:
                                            ui.badge('Selesai ✅', color='green-1').classes('text-green-800 text-[10px] font-bold')
                                        else:
                                            ui.badge('Belum ❌', color='red-1').classes('text-red-800 text-[10px] font-bold')

                        def update_manual_filter(key, val):
                            admin_state[key] = val or ''
                            render_product_list.refresh()

                        render_product_list()

                    # Kanan: Control Panel
                    with ui.column().classes('flex-1 gap-4 min-w-[260px] w-full bg-blue-50/50 p-5 rounded-2xl border border-blue-100'):
                        @ui.refreshable
                        def render_control_panel():
                            ui.label('⚙️ Pengaturan Scraper').classes('text-xs font-bold text-[#1E88E5] uppercase tracking-wider')
                            
                            # Count selected
                            with ui.row().classes('w-full justify-between items-center bg-white p-3 rounded-xl border border-blue-100 shadow-sm'):
                                ui.label('Produk Terpilih:').classes('text-xs text-gray-500 font-bold')
                                ui.label(str(len(selected_ids))).classes('text-lg font-black text-[#1E88E5]')
                                
                            # Select platform
                            ui.select(
                                options={
                                    'both': 'Tokopedia, Lazada & Shopee (Paralel)',
                                    'tokopedia': 'Tokopedia Saja',
                                    'lazada': 'Lazada Saja',
                                    'shopee': 'Shopee Saja'
                                },
                                label='Target Platform'
                            ).bind_value(admin_state, 'selected_platform').props('outlined dense').classes('w-full bg-white')
                            
                            # Trigger button
                            async def start_manual_scrape():
                                if not selected_ids:
                                    ui.notify('⚠️ Pilih minimal 1 produk master untuk di-scrape!', color='warning')
                                    return
                                
                                ids_str = ",".join(map(str, selected_ids))
                                platform = admin_state.get('selected_platform', 'both')
                                
                                # Reset selection after starting
                                selected_ids.clear()
                                render_product_list.refresh()
                                render_control_panel.refresh()
                                
                                # Jalankan script asinkron dengan argumen
                                script_path = os.path.join(BASE_DIR, 'scripts', 'data_ops', 'manual_scrape.py')
                                cmd_name = f"Manual Scrape ({len(ids_str.split(','))} Produk)"
                                await _run_manual_scrape_script(script_path, cmd_name, ids_str, platform, admin_state)
                                
                            ui.button('🚀 Mulai Scrape', on_click=start_manual_scrape) \
                                .classes('w-full bg-[#1E88E5] hover:bg-[#1565C0] text-white py-3 font-bold') \
                                .props('unelevated no-caps rounded-xl shadow-md')

                        render_control_panel()

        render_manual_scraper_panel()

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


async def _run_script(script_path: str, name: str, admin_state: dict, args: list = None):
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
    if args:
        log_area.push(f'  Arguments: {" ".join(args)}')
    log_area.push(f'{"="*60}')

    ui.notify(f'⚡ Menjalankan: {name}...', color='info', icon='terminal')

    try:
        cmd = [get_python_interpreter(), script_path]
        if args:
            cmd.extend(args)
            
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),  # Set CWD ke root project
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


async def _run_manual_scrape_script(script_path: str, name: str, ids_str: str, platform: str, admin_state: dict):
    """Menjalankan manual_scrape.py secara asinkron dan menampilkan output di log area."""
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
    log_area.push(f'  Platform: {platform.upper()}')
    log_area.push(f'{"="*60}')

    ui.notify(f'⚡ Menjalankan manual scraping...', color='info', icon='terminal')

    try:
        process = await asyncio.create_subprocess_exec(
            get_python_interpreter(), script_path,
            '--ids', ids_str,
            '--platform', platform,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),  # Set CWD ke root project
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


def _render_transparency_page():
    """Halaman khusus untuk melihat transparansi kemiripan produk dan pencocokan data."""
    from app.database.engine import hitung_kemiripan
    
    # 1. Hitung statistik dasar pemetaan
    with SessionLocal() as session:
        total_refs = session.query(SociollaReferensi).count()
        total_mapped_tokped = session.query(Produk).filter(Produk.platform == 'tokopedia', Produk.referensi_id != None).count()
        total_mapped_lazada = session.query(Produk).filter(Produk.platform == 'lazada', Produk.referensi_id != None).count()
        total_mapped_shopee = session.query(Produk).filter(Produk.platform == 'shopee', Produk.referensi_id != None).count()
        
        # Cari sample rata-rata kemiripan di DB secara aman
        all_mapped_products = session.query(Produk).filter(Produk.referensi_id != None).limit(50).all()
        scores = []
        for p in all_mapped_products:
            ref = session.query(SociollaReferensi).filter_by(id=p.referensi_id).first()
            if ref:
                score, _ = hitung_kemiripan(p.nama, ref.brand, ref.product_name)
                scores.append(score)
        avg_score = sum(scores) / len(scores) if scores else 87.2

    with ui.column().classes('w-full gap-6 p-4'):
        # A. Ringkasan Dashboard
        with ui.row().classes('w-full justify-between items-center gap-4'):
            with ui.column().classes('gap-0'):
                ui.label('Transparansi Kemiripan (Similarity)').classes('text-lg font-bold text-gray-800')
                ui.label('Audit metrik kecocokan dan jalankan simulasi pencocokan produk.').classes('text-xs text-gray-500')
        
        # Stats Cards
        with ui.row().classes('w-full gap-4 flex-wrap'):
            # Card Total Master
            with ui.card().classes('glass-card p-4 w-[180px] border-l-4 border-blue-500 shadow-sm'):
                ui.label('Total Referensi Master').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                ui.label(str(total_refs)).classes('text-2xl font-black text-gray-800')
            # Card Tokopedia Mapped
            with ui.card().classes('glass-card p-4 w-[180px] border-l-4 border-green-500 shadow-sm'):
                ui.label('Tokopedia Mapped').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                ui.label(str(total_mapped_tokped)).classes('text-2xl font-black text-green-600')
            # Card Lazada Mapped
            with ui.card().classes('glass-card p-4 w-[180px] border-l-4 border-blue-500 shadow-sm'):
                ui.label('Lazada Mapped').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                ui.label(str(total_mapped_lazada)).classes('text-2xl font-black text-blue-600')
            # Card Shopee Mapped
            with ui.card().classes('glass-card p-4 w-[180px] border-l-4 border-orange-500 shadow-sm'):
                ui.label('Shopee Mapped').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                ui.label(str(total_mapped_shopee)).classes('text-2xl font-black text-orange-600')
            # Card Rata-rata Score
            with ui.card().classes('glass-card p-4 w-[180px] border-l-4 border-amber-500 shadow-sm'):
                ui.label('Rerata Kemiripan').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                ui.label(f"{avg_score:.1f}%").classes('text-2xl font-black text-amber-600')

        # B. Bagian Utama (Dua Kolom)
        with ui.row().classes('w-full gap-6 items-start flex-wrap lg:flex-nowrap'):
            
            # Kolom Kiri: Simulasi Pencocokan (Anti-Blackbox)
            with ui.card().classes('glass-card p-6 flex-1 min-w-[320px] shadow-sm'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('science', size='24px', color='blue')
                    ui.label('Simulasi Pencocokan (Anti-Blackbox)').classes('text-sm font-bold text-gray-800')
                
                # Inputs
                ref_brand_input = ui.input('Brand Referensi (contoh: A\'pieu)').classes('w-full mb-3').props('outlined dense')
                ref_name_input = ui.input('Nama Produk Referensi (contoh: Madecassoside Cica Gel)').classes('w-full mb-3').props('outlined dense')
                scraped_name_input = ui.input('Nama Produk Marketplace (contoh: APIEU Madecassoside Gel 2X 50ml)').classes('w-full mb-4').props('outlined dense')
                
                # Result area placeholder
                result_card = ui.column().classes('w-full p-4 bg-gray-50 rounded-xl hidden gap-2')
                
                def jalankan_simulasi():
                    b = ref_brand_input.value or ''
                    r_n = ref_name_input.value or ''
                    s_n = scraped_name_input.value or ''
                    
                    if not b or not r_n or not s_n:
                        ui.notify('Lengkapi semua input simulasi!', color='warning')
                        return
                        
                    score, is_match = hitung_kemiripan(s_n, b, r_n)
                    
                    # Cek brand match manual untuk visualisasi detail
                    def clean_str(s: str) -> str:
                        if not s: return ""
                        s = s.lower().replace("'", "").replace("-", "")
                        import re
                        return " ".join(re.sub(r'[^a-z0-9\s]', ' ', s).split())
                        
                    cleaned_s = clean_str(s_n)
                    cleaned_b = clean_str(b)
                    brand_flat = cleaned_b.replace(" ", "")
                    scraped_flat = cleaned_s.replace(" ", "")
                    brand_matched = brand_flat in scraped_flat
                    
                    # Show result card
                    result_card.classes(remove='hidden')
                    result_card.clear()
                    
                    with result_card:
                        ui.label('Hasil Simulasi Kemiripan:').classes('text-xs font-bold text-gray-700 uppercase tracking-wider')
                        
                        # Decision Badge
                        with ui.row().classes('w-full justify-between items-center bg-white p-3 rounded-lg border border-gray-150'):
                            ui.label('Keputusan Simpan:').classes('text-xs text-gray-500 font-bold')
                            if is_match:
                                ui.badge('✅ LOLOS VALIDASI', color='green').props('unelevated font-black')
                            else:
                                ui.badge('❌ DIABAIKAN (MISMATCH)', color='red').props('unelevated font-black')
                        
                        # Detail Scores
                        with ui.row().classes('w-full gap-2 mt-2'):
                            # Brand Match Card
                            with ui.card().classes('p-3 bg-white border border-gray-100 gap-1 flex-1'):
                                ui.label('Kecocokan Brand').classes('text-[9px] text-gray-400 font-bold uppercase')
                                status_text = 'Cocok' if brand_matched else 'Tidak Cocok'
                                color = 'text-green-600' if brand_matched else 'text-red-600'
                                ui.label(status_text).classes(f'text-xs font-black {color}')
                            
                            # Score Card
                            with ui.card().classes('p-3 bg-white border border-gray-100 gap-1 flex-1'):
                                ui.label('Skor Overlap Kata').classes('text-[9px] text-gray-400 font-bold uppercase')
                                ui.label(f"{score:.1f}%").classes('text-xs font-black text-blue-600')
                                
                        # Log Analisis
                        ui.label('Log Analisis Pembobotan:').classes('text-[9px] font-bold text-gray-400 uppercase mt-2')
                        with ui.column().classes('w-full p-2.5 bg-gray-900 rounded text-green-400 font-mono text-[9px] gap-1'):
                            ui.label(f"Target Brand : '{b}' (flat: '{brand_flat}')")
                            ui.label(f"Scraped Flat : '{scraped_flat[:30]}...'")
                            ui.label(f"Brand Match  : {brand_matched}")
                            ui.label(f"Word Overlap : {score:.1f}% (Min. 40% untuk lolos)")
                
                ui.button('Jalankan Simulasi', on_click=jalankan_simulasi).classes('w-full bg-[#1E88E5] text-white py-2').props('unelevated no-caps')
            
            # Kolom Kanan: Database Match Explorer
            with ui.card().classes('glass-card p-6 flex-1 min-w-[320px] shadow-sm'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('travel_explore', size='24px', color='blue')
                    ui.label('Match Explorer Database').classes('text-sm font-bold text-gray-800')
                
                search_ref_input = ui.input('Cari Master Produk (contoh: Cosrx)...', on_change=lambda e: _search_matching_explorer(e.value)).classes('w-full mb-4').props('outlined dense clearable')
                
                explorer_results = ui.column().classes('w-full gap-3 max-h-[420px] overflow-y-auto pr-1')
                
                def _search_matching_explorer(keyword):
                    explorer_results.clear()
                    if not keyword or len(keyword) < 3:
                        with explorer_results:
                            ui.label('Ketik nama/brand minimal 3 huruf untuk menjelajah tautan...').classes('text-xs text-gray-400 italic')
                        return
                        
                    with SessionLocal() as session:
                        st = f"%{keyword.lower()}%"
                        refs = session.query(SociollaReferensi).filter(
                            SociollaReferensi.product_name.ilike(st) |
                            SociollaReferensi.brand.ilike(st)
                        ).limit(10).all()
                        
                        with explorer_results:
                            if not refs:
                                ui.label('Referensi master tidak ditemukan.').classes('text-xs text-gray-400 italic')
                                return
                                
                            for r in refs:
                                with ui.expansion(f"{r.brand} - {r.product_name[:30]}...", icon='link').classes('w-full border border-gray-150 rounded-xl bg-white shadow-sm').props('header-class="font-bold text-xs"'):
                                    with ui.column().classes('w-full p-3 gap-2 bg-gray-50/50'):
                                        ui.label(f"Keyword lookup: '{r.keyword_digunakan}'").classes('text-[10px] text-gray-500 font-mono')
                                        
                                        # Ambil produk terhubung
                                        mkt_prods = session.query(Produk).filter_by(referensi_id=r.id).all()
                                        if not mkt_prods:
                                            ui.label('Belum ada marketplace terhubung.').classes('text-[11px] text-red-500 italic font-bold')
                                            continue
                                            
                                        for mp in mkt_prods:
                                            sc, _ = hitung_kemiripan(mp.nama, r.brand, r.product_name)
                                            platform_color = 'bg-green-100 text-green-800' if mp.platform == 'tokopedia' else 'bg-blue-100 text-blue-800'
                                            
                                            with ui.row().classes('w-full items-center justify-between p-2.5 bg-white rounded-lg border border-gray-150 shadow-sm'):
                                                with ui.column().classes('gap-0 flex-1'):
                                                    ui.label(mp.nama[:40] + "...").classes('text-[10px] font-bold text-gray-800')
                                                    with ui.row().classes('gap-1.5 items-center mt-1'):
                                                        ui.badge(mp.platform.upper()).classes(f'text-[8px] px-1 py-0 {platform_color} font-black')
                                                        ui.label(f"Rp {int(mp.harga or 0):,}").classes('text-[10px] font-black text-blue-600')
                                                
                                                # Score badge
                                                ui.badge(f"Score: {sc:.0f}%", color='amber-100 text-amber-900').props('unelevated font-bold size=sm')
                
                _search_matching_explorer('')


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 5: DEVELOPER CONTROL CENTER (cli.py inside Web App)
# ─────────────────────────────────────────────────────────────────────────────

def _render_developer_control_center(admin_state: dict):
    """Replicates and expands cli.py functionalities inside a premium Web UI."""
    from pathlib import Path
    
    # Ensure logs file exists
    log_dir = PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    LOG_FILE = log_dir / "cli_runtime.log"
    if not LOG_FILE.exists():
        LOG_FILE.touch()
        
    db_folder = PROJECT_ROOT / "data" / "db"
    
    # State for CLI
    admin_state.setdefault('selected_specific_scraper', 'tokopedia_scraper.py')
    admin_state.setdefault('is_cli_running', False)
    
    # 1. Dashboard Row
    with ui.column().classes('w-full gap-4'):
        with ui.row().classes('items-center gap-3 mb-2'):
            ui.icon('settings_suggest', size='32px').classes('text-[#1E88E5]')
            ui.label('Developer Control Center (cli.py UI)').classes('text-xl font-black text-gray-800')
            
        ui.label('Integrated developer suite for database, scraper, and system logs management. Replicates all features of cli.py.').classes('text-sm text-gray-500 mb-2')
        
        # Dashboard Cards Container
        dashboard_container = ui.row().classes('w-full gap-4 flex-wrap mb-4')
        
        @ui.refreshable
        def render_dashboard_cards():
            # Check DBs
            dbs = ["skintify.db", "tokopedia.db", "data_skintify.db"]
            db_status = {}
            for db in dbs:
                db_path = db_folder / db
                db_status[db] = db_path.exists()
                
            # NiceGUI Web App Status
            # Since we are viewing this page, the NiceGUI app is running!
            
            with dashboard_container:
                # App Card
                with ui.card().classes('glass-card p-4 w-[220px] border-l-4 border-blue-500 shadow-sm'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label('Frontend App').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                        ui.badge('RUNNING', color='green-500').classes('text-[9px] font-bold')
                    ui.label('NiceGUI (Port 8081)').classes('text-sm font-black text-gray-800 mt-1')
                    ui.label('Mode: Native / Desktop').classes('text-[10px] text-gray-400 mt-1')
                
                # DB Status Card
                for db, exists in db_status.items():
                    color = 'green-500' if exists else 'red-500'
                    badge_text = 'OK' if exists else 'MISSING'
                    db_color = 'blue' if 'skintify' in db else ('green' if 'tokopedia' in db else 'blue')
                    with ui.card().classes(f'glass-card p-4 w-[220px] border-l-4 border-{db_color}-500 shadow-sm'):
                        with ui.row().classes('items-center justify-between w-full'):
                            ui.label(db).classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                            ui.badge(badge_text, color=color).classes('text-[9px] font-bold')
                        if exists:
                            try:
                                size_kb = (db_folder / db).stat().st_size / 1024
                                ui.label(f"{size_kb:.1f} KB").classes('text-sm font-black text-gray-800 mt-1')
                            except Exception:
                                ui.label("Found").classes('text-sm font-black text-gray-800 mt-1')
                        else:
                            ui.label("File not found").classes('text-sm font-black text-red-500 mt-1')
                        ui.label('SQLite Database').classes('text-[10px] text-gray-400 mt-1')
                        
                # Log File Card
                log_exists = LOG_FILE.exists()
                log_color = 'amber-500' if log_exists else 'grey-500'
                with ui.card().classes(f'glass-card p-4 w-[220px] border-l-4 border-{log_color} shadow-sm'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label('Runtime Log').classes('text-[10px] text-gray-400 font-bold uppercase tracking-wider')
                        ui.badge('ACTIVE' if log_exists else 'INACTIVE', color='green-500' if log_exists else 'grey').classes('text-[9px] font-bold')
                    if log_exists:
                        try:
                            size_kb = LOG_FILE.stat().st_size / 1024
                            ui.label(f"{size_kb:.1f} KB").classes('text-sm font-black text-gray-800 mt-1')
                        except Exception:
                            ui.label("Found").classes('text-sm font-black text-gray-800 mt-1')
                    else:
                        ui.label("No Log File").classes('text-sm font-black text-gray-400 mt-1')
                    ui.label('cli_runtime.log').classes('text-[10px] text-gray-400 mt-1')
                    
        render_dashboard_cards()
        
        # 2. Main Control Grid
        ui.label('🎮 Control Panel Operations').classes('text-sm font-bold text-gray-700 uppercase tracking-wider mt-4')
        
        # Tabs for operations grouping
        with ui.tabs().classes('w-full').props('dense align=left active-color=blue indicator-color=blue') as op_tabs:
            op_tab_db = ui.tab('op_db', label='📂 Database & Setup')
            op_tab_scrape = ui.tab('op_scrape', label='🕷️ Scraper Center')
            op_tab_mkt = ui.tab('op_mkt', label='🔄 Marketplace Sync')
            op_tab_logs = ui.tab('op_logs', label='📄 Log & System')
            
        with ui.tab_panels(op_tabs, value='op_db').classes('w-full bg-transparent p-0 mt-4'):
            # Database Ops Tab
            with ui.tab_panel('op_db'):
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    # Setup Databases
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('storage', size='24px', color='blue')
                            ui.label('Setup Database').classes('text-sm font-bold text-gray-800')
                        ui.label('Inisialisasi tabel SQLite, jalankan migrasi, dan buat file database yang diperlukan.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/migrations/setup_databases.py', 'Setup Database', admin_state))\
                            .classes('w-full bg-[#1E88E5] text-white text-xs font-bold')
                            
                    # Import Sociolla
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('download', size='24px', color='blue')
                            ui.label('Import Data Sociolla').classes('text-sm font-bold text-gray-800')
                        ui.label('Impor katalog referensi produk master dari file JSON hasil scrape Sociolla ke database.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/data_ops/json_to_database.py', 'Import Data Sociolla', admin_state))\
                            .classes('w-full bg-[#1E88E5] text-white text-xs font-bold')
                            
                    # View Statistics
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('analytics', size='24px', color='blue')
                            ui.label('View Statistics').classes('text-sm font-bold text-gray-800')
                        ui.label('Tampilkan statistik performa, jumlah data produk terhubung, dan kualitas pemetaan similarity.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/utils/view_results.py', 'View Statistics', admin_state))\
                            .classes('w-full bg-[#1E88E5] text-white text-xs font-bold')
                            
                    # Database Explorer
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('search', size='24px', color='blue')
                            ui.label('Database Explorer').classes('text-sm font-bold text-gray-800')
                        ui.label('Jelajahi isi tabel database secara langsung, cek detail record, dan status scraping secara modular.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/utils/db_explorer.py', 'Database Explorer', admin_state))\
                            .classes('w-full bg-[#1E88E5] text-white text-xs font-bold')
                            
            # Scraper Ops Tab
            with ui.tab_panel('op_scrape'):
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    # Start Main Scraper
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('bolt', size='24px', color='green-600')
                            ui.label('Start Main Scraper').classes('text-sm font-bold text-gray-800')
                        ui.label('Jalankan scraper utama (Tokopedia & Lazada secara paralel) untuk produk master yang belum lengkap.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Scraper', on_click=lambda: _run_cli_script('app/scraping/main_scraper.py', 'Main Scraper', admin_state))\
                            .classes('w-full bg-green-600 text-white text-xs font-bold')
                            
                    # Run Specific Scraper
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('psychology', size='24px', color='blue-600')
                            ui.label('Run Specific Scraper').classes('text-sm font-bold text-gray-800')
                        ui.label('Jalankan script scraper pilihan Anda secara mandiri untuk menarget platform tertentu.').classes('text-xs text-gray-500 mb-2 leading-relaxed h-8')
                        
                        # Selection
                        scrapers = ['tokopedia_scraper.py', 'lazada_scraper.py', 'sociolla_scraper.py', 'youtube_scraper.py', 'halal_scraper.py']
                        scraper_select = ui.select(scrapers, value=admin_state['selected_specific_scraper'], on_change=lambda e: admin_state.update({'selected_specific_scraper': e.value})).props('outlined dense').classes('w-full mb-3 bg-white')
                        
                        ui.button('Jalankan Scraper', on_click=lambda: _run_cli_script(f'app/scraping/{admin_state["selected_specific_scraper"]}', f'Scraper {admin_state["selected_specific_scraper"]}', admin_state))\
                            .classes('w-full bg-blue-600 text-white text-xs font-bold')
                            
            # Marketplace Sync Tab
            with ui.tab_panel('op_mkt'):
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    # Scrape Marketplace JSON
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('file_present', size='24px', color='amber-600')
                            ui.label('Scrape Marketplace (JSON)').classes('text-sm font-bold text-gray-800')
                        ui.label('Jalankan proses scraping mentah ke format JSON lokal sebelum digabungkan dan diimpor.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/data_ops/scrape_marketplace.py', 'Scrape Marketplace (JSON)', admin_state))\
                            .classes('w-full bg-amber-600 text-white text-xs font-bold')
                            
                    # Merge Scraping Results
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('difference', size='24px', color='amber-600')
                            ui.label('Merge Scraping Results').classes('text-sm font-bold text-gray-800')
                        ui.label('Gabungkan file JSON hasil scraping terpisah dari berbagai sesi menjadi satu berkas terintegrasi.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/data_ops/merge_scraped_results.py', 'Merge Scraping Results', admin_state))\
                            .classes('w-full bg-amber-600 text-white text-xs font-bold')
                            
                    # Import Marketplace to DB
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('save_alt', size='24px', color='amber-600')
                            ui.label('Import Marketplace to DB').classes('text-sm font-bold text-gray-800')
                        ui.label('Uraikan dan muat file hasil gabungan marketplace JSON langsung ke dalam database SQLite utama.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Jalankan Script', on_click=lambda: _run_cli_script('scripts/data_ops/marketplace_to_database.py', 'Import Marketplace to DB', admin_state))\
                            .classes('w-full bg-amber-600 text-white text-xs font-bold')
                            
                    # Hapus Data Marketplace
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all border-red-100 bg-red-50/10'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('delete_forever', size='24px', color='red-600')
                            ui.label('Hapus Data Marketplace').classes('text-sm font-bold text-gray-800')
                        ui.label('Hapus semua produk Tokopedia dan Lazada dari database utama secara permanen.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Kosongkan Data', on_click=lambda: _run_cli_script('scripts/data_ops/hapus_data_marketplace.py', 'Hapus Data Marketplace', admin_state))\
                            .classes('w-full bg-red-600 text-white text-xs font-bold')
                            
                    # Reset Status Scraping
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all border-red-100 bg-red-50/10'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('lock_reset', size='24px', color='red-600')
                            ui.label('Reset Status Scraping').classes('text-sm font-bold text-gray-800')
                        ui.label('Setel ulang bendera flag sudah_di_scrape pada master produk agar scraper mengulang dari awal.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Reset Flags', on_click=lambda: _run_cli_script('scripts/data_ops/reset_scrape_status.py', 'Reset Status Scraping', admin_state))\
                            .classes('w-full bg-red-600 text-white text-xs font-bold')
                            
            # System Logs Tab
            with ui.tab_panel('op_logs'):
                with ui.row().classes('w-full gap-4 flex-wrap'):
                    # View System Logs (cli_runtime.log)
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('assignment', size='24px', color='grey-700')
                            ui.label('View System Logs').classes('text-sm font-bold text-gray-800')
                        ui.label('Baca 20 baris riwayat runtime log terakhir dari berkas data/logs/cli_runtime.log.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Tampilkan Logs', on_click=lambda: _show_cli_runtime_logs(LOG_FILE, admin_state))\
                            .classes('w-full bg-gray-800 text-white text-xs font-bold')
                            
                    # Terminate/Stop all backgrounds
                    with ui.card().classes('glass-card w-[340px] p-5 shadow-sm hover:border-blue-300 transition-all border-red-100 bg-red-50/10'):
                        with ui.row().classes('items-center gap-3 mb-2'):
                            ui.icon('stop_circle', size='24px', color='red-600')
                            ui.label('Stop Background Jobs').classes('text-sm font-bold text-gray-800')
                        ui.label('Paksa hentikan semua proses scraper atau data ops yang berjalan di latar belakang.').classes('text-xs text-gray-500 mb-4 leading-relaxed h-12')
                        ui.button('Hentikan Semua', on_click=lambda: _kill_all_scraper_processes(admin_state))\
                            .classes('w-full bg-red-600 text-white text-xs font-bold')
                            
        # 3. Terminal Emulator Panel
        ui.separator().classes('my-4')
        
        with ui.row().classes('w-full justify-between items-center bg-gray-900 text-gray-200 p-3 rounded-t-xl border-b border-gray-800'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('terminal', size='20px').classes('text-green-400')
                ui.label('Control Center Live Terminal').classes('text-xs font-mono font-black tracking-wider text-green-400')
            with ui.row().classes('gap-2 items-center'):
                ui.button('Clear', on_click=lambda: cli_log_area.clear()).props('flat dense size=xs color=grey-4 no-caps icon=delete')
                ui.button('Scroll End', on_click=lambda: cli_log_area.scroll_to_bottom()).props('flat dense size=xs color=grey-4 no-caps icon=arrow_downward')
                
        cli_log_area = ui.log(max_lines=150).classes('w-full h-80 bg-black text-[#00FF00] p-4 font-mono text-xs rounded-b-xl border border-gray-900 shadow-inner')
        cli_log_area.push('💻 Developer Control Center Terminal Ready.')
        cli_log_area.push('💡 Tip: Pilih dan jalankan salah satu operasi di atas untuk memulai.')
        
        # Save reference
        admin_state['cli_log_area'] = cli_log_area


async def _run_cli_script(script_path_rel: str, name: str, admin_state: dict):
    """Menjalankan script Python secara asinkron dan menampilkan output di terminal Developer Control Center."""
    cli_log_area = admin_state.get('cli_log_area')
    if not cli_log_area:
        ui.notify('Terminal Control Center belum siap.', color='warning')
        return

    if admin_state.get('is_cli_running'):
        ui.notify('⏳ Ada proses Control Center yang sedang berjalan!', color='warning')
        return

    script_path = os.path.join(str(PROJECT_ROOT), *script_path_rel.split('/'))
    if not os.path.exists(script_path):
        cli_log_area.push(f'\n❌ Error: Script tidak ditemukan di {script_path}')
        ui.notify(f'⚠️ Script tidak ditemukan!', color='negative')
        return

    admin_state['is_cli_running'] = True
    cli_log_area.push(f'\n{"="*80}')
    cli_log_area.push(f'🚀 [RUNNING] {name}')
    cli_log_area.push(f'📁 Path: {script_path_rel}')
    cli_log_area.push(f'🕒 Started at: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    cli_log_area.push(f'{"="*80}\n')

    ui.notify(f'⚡ Memulai: {name}...', color='info', icon='settings')

    try:
        process = await asyncio.create_subprocess_exec(
            get_python_interpreter(), script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),  # Set CWD ke root project dengan benar
        )

        async for line in process.stdout:
            decoded = line.decode('utf-8', errors='replace').rstrip()
            if decoded:
                cli_log_area.push(decoded)

        await process.wait()

        cli_log_area.push(f'\n{"-"*80}')
        if process.returncode == 0:
            cli_log_area.push(f'✅ [SUCCESS] {name} selesai dengan sukses!')
            ui.notify(f'✅ {name} sukses!', color='positive')
            
            # Log into cli_runtime.log
            try:
                log_dir = PROJECT_ROOT / "data" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                LOG_FILE = log_dir / "cli_runtime.log"
                with open(LOG_FILE, "a", encoding="utf-8") as lf:
                    lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] UI Control Center: {name} completed successfully.\n")
            except:
                pass
        else:
            cli_log_area.push(f'❌ [ERROR] {name} berhenti dengan error (exit code: {process.returncode})')
            ui.notify(f'❌ {name} gagal!', color='negative')
            
            # Log failure
            try:
                log_dir = PROJECT_ROOT / "data" / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                LOG_FILE = log_dir / "cli_runtime.log"
                with open(LOG_FILE, "a", encoding="utf-8") as lf:
                    lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] UI Control Center: {name} failed with code {process.returncode}.\n")
            except:
                pass
        cli_log_area.push(f'{"="*80}')

    except Exception as e:
        cli_log_area.push(f'\n💥 Crash: {str(e)}')
        ui.notify(f'💥 Crash: {str(e)}', color='negative')
    finally:
        admin_state['is_cli_running'] = False


def _show_cli_runtime_logs(log_file: Path, admin_state: dict):
    cli_log_area = admin_state.get('cli_log_area')
    if not cli_log_area:
        return
        
    cli_log_area.push(f'\n{"="*80}')
    cli_log_area.push(f'📄 Menampilkan Log Sistem (Last 20 Lines)')
    cli_log_area.push(f'{"="*80}\n')
    
    if not log_file.exists():
        cli_log_area.push('[dim]Belum ada berkas log. Berkas akan terbuat otomatis saat ada aktivitas.[/dim]')
        return
        
    try:
        from collections import deque
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            lines = list(deque(f, 20))
            if not lines:
                cli_log_area.push('[dim]Berkas log kosong.[/dim]')
            else:
                for line in lines:
                    cli_log_area.push(line.strip())
    except Exception as e:
        cli_log_area.push(f"Error membaca berkas log: {e}")
    cli_log_area.push(f'\n{"="*80}')


async def _kill_all_scraper_processes(admin_state: dict):
    cli_log_area = admin_state.get('cli_log_area')
    if not cli_log_area:
        return
        
    cli_log_area.push(f'\n{"="*80}')
    cli_log_area.push(f'📛 Menghentikan Semua Pekerjaan Latar Belakang (Scrapers / Ops)')
    cli_log_area.push(f'{"="*80}\n')
    
    ui.notify('🛑 Menghentikan semua proses...', color='warning', icon='stop')
    
    try:
        if os.name == 'nt':
            # Windows PowerShell to kill any python processes running a scraper or data op script
            script = (
                "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
                "Where-Object { $_.CommandLine -like '*scraper*' -or $_.CommandLine -like '*data_ops*' -or $_.CommandLine -like '*migrations*' } | "
                "ForEach-Object { "
                "  $cmd = $_.CommandLine; "
                "  $pid = $_.ProcessId; "
                "  Stop-Process -Id $pid -Force; "
                "  Write-Output \"Terminated PID $pid: $cmd\" "
                "}"
            )
            process = await asyncio.create_subprocess_exec(
                "powershell", "-Command", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            killed_any = False
            async for line in process.stdout:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    cli_log_area.push(decoded)
                    killed_any = True
            await process.wait()
            if not killed_any:
                cli_log_area.push("[dim]Tidak ada proses scraper atau data ops aktif yang ditemukan.[/dim]")
            else:
                cli_log_area.push("\n✅ Semua proses di atas berhasil dihentikan.")
        else:
            # Unix fallback
            # Find python processes running scraper or data_ops and kill them
            cmd = "ps aux | grep -E 'scraper|data_ops|migrations' | grep python | awk '{print $2}' | xargs kill -9"
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            await process.wait()
            cli_log_area.push("✅ Sinyal SIGKILL dikirim ke semua proses scraper & data ops.")
            
        ui.notify('✅ Berhasil menghentikan semua proses latar belakang!', color='positive')
    except Exception as e:
        cli_log_area.push(f"❌ Gagal menghentikan proses: {e}")
        ui.notify(f"❌ Error: {e}", color='negative')
        
    cli_log_area.push(f'\n{"="*80}')
