from nicegui import ui
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager

def show_page():
    """Halaman Template - Silakan ubah isi kontennya!"""
    
    # 1. Proteksi Login
    auth_redirect = AuthManager.require_auth()
    if auth_redirect:
        return auth_redirect

    # 2. Refreshable Status Bar (Optional)
    @ui.refreshable
    def taskbar_status() -> None:
        analysis = data_mgr.analyze_routine(state.routine, kota=state.kota)
        UIComponents.routine_status_badge(analysis)

    # 3. Layout Komponen Standar
    UIComponents.navbar(status_widget=taskbar_status)
    UIComponents.sidebar()

    # 4. Area Konten (Ganti bagian ini)
    with ui.column().classes('w-full p-8 items-center justify-center'):
        with ui.card().classes('glass-card p-20 items-center gap-6'):
            ui.icon('construction', size='64px', color='blue-300')
            ui.label('Halaman Dalam Pengembangan').classes('text-3xl font-black text-gray-700')
            ui.label('Bagian ini sedang dikerjakan oleh rekan tim lainnya.').classes('text-gray-400')
            
            ui.button('Kembali ke Beranda', on_click=lambda: ui.navigate.to('/')).classes('btn-primary')
