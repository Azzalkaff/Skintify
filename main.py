import sys
import codecs

# Fix UnicodeEncodeError on Windows / PyInstaller executables when printing emojis
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach(), errors="backslashreplace")
        except Exception:
            pass

if sys.stderr is not None:
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        try:
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach(), errors="backslashreplace")
        except Exception:
            pass

import importlib
import logging
import traceback
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
    '/chat': 'syhid.ai_chat_page',
}

# Halaman yang hanya boleh diakses oleh Admin
ADMIN_ONLY_PAGES = {'/admin', '/chat'}

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


# 4. Registrasi & Pre-import Semua Halaman
PAGE_REGISTRY = {}
for path, module_name in PAGES.items():
    try:
        PAGE_REGISTRY[path] = importlib.import_module(f'app.ui.pages.{module_name}')
        logger.info(f"✅ Module {module_name} pre-imported.")
    except Exception as e:
        logger.error(f"❌ Gagal pre-import {module_name}: {e}")

# 5. Router SPA Terpusat
def create_spa_router():
    """Mengubah aplikasi menjadi SPA dengan mendaftarkan semua path ke 1 fungsi utama."""
    
    def spa_page(path: str = ''):
        # Normalize path
        current_path = path if path.startswith('/') else '/' + path
        if current_path not in PAGES:
            current_path = '/' # fallback to home if unknown
            
        is_standalone = current_path in ['/login', '/onboarding']

        # A. Proteksi Login & Admin (Global SPA)
        if not is_standalone and not app.storage.user.get('authenticated'):
            return ui.navigate.to('/login')
            
        if current_path in ADMIN_ONLY_PAGES and app.storage.user.get('role') != 'admin':
            ui.notify('⛔ Akses Ditolak: Halaman ini khusus Admin.', color='negative')
            return ui.navigate.to('/')
            
        if not is_standalone and not app.storage.user.get('skin_type'):
            return ui.navigate.to('/onboarding')

        # Jika halaman mandiri, langsung render tanpa SPA wrapper
        if is_standalone:
            module = PAGE_REGISTRY.get(current_path)
            return module.show_page()

        # SPA LAYOUT INIT
        from app.context import state
        state.spa_mode = True  # Beritahu UIComponents untuk mode SPA
        
        # Render Navbar & Sidebar SEKALI per koneksi browser
        UIComponents.navbar(force=True)
        UIComponents.sidebar(force=True)
        
        # Area Konten Tengah
        content_container = ui.column().classes('w-full flex-grow no-wrap')
        
        @ui.refreshable
        def render_content(target_path):
            with content_container:
                content_container.clear()
                try:
                    module = PAGE_REGISTRY.get(target_path)
                    if module:
                        # Panggil halaman. Karena state.spa_mode = True, 
                        # UIComponents.navbar() dkk di dalam show_page() akan diabaikan!
                        module.show_page()
                except Exception as e:
                    # TAMPILAN ERROR LOKAL (Tidak menghapus Navbar & Sidebar)
                    full_tb = traceback.format_exc()
                    logger.error(f"[SPA Error] {target_path} crash:\n{full_tb}")
                    
                    try:
                        # Reset state volatil
                        _volatile_keys = ['page', 'compare_slots', 'selected_compare_category', 'wishlist_compare_selections']
                        for _k in _volatile_keys:
                            if _k in app.storage.user:
                                del app.storage.user[_k]
                    except Exception: pass
                    
                    with ui.column().classes('w-full h-[80vh] items-center justify-center p-10'):
                        ui.icon('report_problem', size='100px', color='red-200')
                        ui.label('Ups! Terjadi Kesalahan Teknis').classes('text-3xl font-black text-red-600')
                        ui.label('Halaman ini sedang bermasalah. Anda masih bisa menavigasi ke menu lain di sidebar.').classes('text-gray-500 mt-2')
                        with ui.expansion('Detail Error (Developer)').classes('w-full max-w-2xl mt-6'):
                            ui.code(full_tb).classes('w-full bg-red-50 p-4 rounded text-[10px]')
                            
        # Simpan fungsi render_content ke client storage agar safe_navigate bisa memanggilnya
        app.storage.client['spa_router_refresh'] = render_content
        
        # Render halaman pertama kali
        render_content(current_path)

    # Daftarkan semua route agar menunjuk ke fungsi SPA
    for path in PAGES.keys():
        if path == '/':
            ui.page('/')(lambda: spa_page('/'))
        else:
            ui.page(path)(lambda p=path: spa_page(p))

create_spa_router()


# 7. Jalankan Aplikasi
if __name__ in {"__main__", "__mp_main__"}:
    # Ambil konfigurasi reload dari environment (diatur oleh cli.py atau .env)
    should_reload = os.getenv("SKINTIFY_RELOAD", "False").lower() == "true"
    
    # Deteksi dinamis port dan server environment
    port = int(os.environ.get("PORT", 8081))
    is_server = "PORT" in os.environ or os.getenv("RENDER") or os.getenv("RAILWAY")
    
    # Deteksi dinamis pywebview untuk mengaktifkan mode native desktop window secara otomatis
    is_native = False
    if not is_server:
        try:
            import webview
            is_native = True
        except ImportError:
            pass
        
    ui.run(
        title='Skintify Web - Team Lab' if is_server else 'Skintify Desktop - Team Lab',
        storage_secret=os.getenv("STORAGE_SECRET", 'skintify-secret-key-2026'),
        host='0.0.0.0' if is_server else '127.0.0.1',
        port=port,
        native=is_native,
        window_size=(1280, 800),
        reload=should_reload,
        show=not is_native and not is_server,
    )
