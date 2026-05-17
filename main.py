import importlib
import logging
from nicegui import ui, app
from app.database.database_manager import BasisData
from app.database.engine import init_db
from app.ui.components import UIComponents
from app.auth.auth import AuthManager

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Inisialisasi Database
BasisData.inisialisasi()  # data_skintify.db (pengguna)
init_db()                 # tokopedia.db (SQLAlchemy) — termasuk migrasi kolom 'role'

# 2. Konfigurasi Static Files & Head
import os
base_dir  = os.path.dirname(os.path.abspath(__file__))
style_dir = os.path.join(base_dir, 'app', 'ui', 'style')
ui.add_head_html('<link href="/static/style.css" rel="stylesheet">', shared=True)
app.add_static_files('/static', style_dir)

# 3. Daftar Halaman (Kontrak Kerja Tim)
# Syaqila: home, wishlist
# Najla: compare, stats
# Falisha: profile, onboarding
PAGES = {
    '/': 'syaqila.home_page',
    '/search': 'syhid.search_page',
    '/compare': 'najla.compare_page',
    '/wishlist': 'syaqila.wishlist_page',
    '/stats': 'najla.stats_page',
    '/profile': 'falisha.profile_page',
    '/onboarding': 'falisha.onboarding_page',
    '/login': 'login_page',
    '/routine': 'syhid.routine_page',
    '/admin': 'syhid.admin_page',
}

# Halaman yang hanya boleh diakses oleh Admin
ADMIN_ONLY_PAGES = {'/admin'}

# ─────────────────────────────────────────────────────────────────────────────
#  HELPER RIWAYAT AKTIVITAS
#  Dipanggil oleh halaman lain (compare, search, wishlist) untuk mencatat log.
#  Contoh pemakaian di compare_page.py:
#    from main import tambah_riwayat
#    tambah_riwayat('compare_arrows', 'blue', 'Membandingkan 2 produk', 'Wardah vs The Ordinary')
# ─────────────────────────────────────────────────────────────────────────────
def tambah_riwayat(icon: str, color: str, judul: str, subjudul: str = ''):
    """Tambah satu entri ke riwayat aktivitas user di app.storage."""
    import datetime
    riwayat = app.storage.user.get('activity_log', [])
    riwayat.insert(0, {
        'icon':     icon,
        'color':    color,
        'judul':    judul,
        'subjudul': subjudul,
        'waktu':    datetime.datetime.now().strftime('%d %b %Y, %H:%M'),
    })
    app.storage.user['activity_log'] = riwayat[:20]   # max 20 entri


# 4. Route Khusus: Halaman Utama (/)
@ui.page('/')
def index():
    # Belum login → ke login
    if not app.storage.user.get('authenticated'):
        return ui.navigate.to('/login')
    # Sudah login tapi belum isi onboarding → ke onboarding
    if not app.storage.user.get('skin_type'):
        app.storage.user['onboarding_mode'] = None   # pastikan mode bukan 'edit'
        return ui.navigate.to('/onboarding')
    # Semua OK → tampilkan home
    from app.ui.pages.syaqila.home_page import show_page
    return show_page()


# 5. Fungsi Pembungkus Route yang Aman
def create_safe_route(path, module_name):
    """Membungkus setiap halaman agar error di satu file tidak merusak aplikasi."""

    @ui.page(path)
    def _page_wrapper():
        # Halaman yang boleh diakses tanpa login
        is_standalone = path in ['/login', '/onboarding']

        try:
            # A. Proteksi Login
            if path != '/login' and not app.storage.user.get('authenticated'):
                return ui.navigate.to('/login')

            # B. Proteksi Admin (Route Guard — Keamanan 3B)
            #    Jika halaman ini admin-only, cek role sebelum render
            if path in ADMIN_ONLY_PAGES and app.storage.user.get('role') != 'admin':
                ui.notify('⛔ Akses Ditolak: Halaman ini khusus Admin.', color='negative', icon='block')
                return ui.navigate.to('/')

            # C. Proteksi Onboarding
            #    Kalau belum isi skin_type dan bukan di /onboarding, suruh isi dulu.
            #    KECUALI: user sedang di mode 'edit' (datang dari tombol Edit Profil)
            #    — dalam kasus itu, skin_type sudah ada, jadi tidak akan ter-redirect.
            if (path not in ['/login', '/onboarding']
                    and not app.storage.user.get('skin_type')):
                return ui.navigate.to('/onboarding')

            # C. Gunakan modul yang sudah di-import sebelumnya (lebih cepat)
            module = PAGE_REGISTRY.get(path)
            if not module:
                # Fallback jika belum ter-import
                module = importlib.import_module(f'app.ui.pages.{module_name}')
            
            return module.show_page()

        except Exception as e:
            logger.error(f"Error pada {module_name}: {e}")
            # Tetap coba render navbar agar user tidak terjebak
            try:
                if not is_standalone:
                    UIComponents.navbar()
                    UIComponents.sidebar()
            except Exception:
                pass

            with ui.column().classes('w-full h-screen items-center justify-center p-10'):
                ui.icon('report_problem', size='100px', color='red-200')
                ui.label('Ups! Terjadi Kesalahan Teknis').classes(
                    'text-3xl font-black text-red-600'
                )
                ui.label(f'Halaman {module_name} sedang diperbaiki oleh rekan tim Anda.').classes(
                    'text-gray-500'
                )
                with ui.expansion('Detail Error untuk Developer').classes('w-full max-w-2xl mt-4'):
                    ui.code(str(e)).classes('w-full bg-red-50 p-4 rounded')


# 6. Registrasi & Pre-import Semua Halaman
PAGE_REGISTRY = {}
for path, module_name in PAGES.items():
    try:
        PAGE_REGISTRY[path] = importlib.import_module(f'app.ui.pages.{module_name}')
        logger.info(f"✅ Module {module_name} pre-imported.")
    except Exception as e:
        logger.error(f"❌ Gagal pre-import {module_name}: {e}")

for path, module_name in PAGES.items():
    create_safe_route(path, module_name)


# 7. Jalankan Aplikasi
if __name__ in {"__main__", "__mp_main__"}:
    # Ambil konfigurasi reload dari environment (diatur oleh cli.py atau .env)
    should_reload = os.getenv("SKINTIFY_RELOAD", "False").lower() == "true"
    
    ui.run(
        title='Skintify Desktop - Team Lab',
        storage_secret='skintify-secret-key-2026',
        port=8081,
        native=True,
        window_size=(1280, 800),
        reload=should_reload,
    )
