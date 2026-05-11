from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager


def show_page():
    """MISI FALISHA: Halaman Profil Lengkap"""

    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    # --- 🚀 MULAI KERJAKAN DI SINI ---

    # ── Ambil semua data dari app.storage.user ────────────────────────────────
    email        = app.storage.user.get('email', 'user@skintify.com')
    username     = app.storage.user.get('username', email.split('@')[0].capitalize())
    skin_type    = app.storage.user.get('skin_type', 'Belum diisi')
    hindari_list = app.storage.user.get('avoid_ingredients', [])
    masalah_list = app.storage.user.get('skin_issues', [])
    city         = app.storage.user.get('city', 'Belum diisi')

    hindari_text = ', '.join(hindari_list) if hindari_list else 'Tidak ada'
    masalah_text = ', '.join(masalah_list) if masalah_list else 'Belum diisi'

    # Riwayat aktivitas dari storage (diisi oleh halaman lain lewat _tambah_riwayat)
    activity_log = app.storage.user.get('activity_log', [])

    # ── LAYOUT UTAMA ─────────────────────────────────────────────────────────
    with ui.column().classes('w-full p-8 gap-6 min-h-screen'):

        # ════════════════════════════════════════════════════════════════════
        #  BAGIAN 1: KARTU IDENTITAS (ATAS)
        # ════════════════════════════════════════════════════════════════════
        with ui.card().classes('w-full items-center p-8 shadow-sm mb-2 rounded-2xl'):
            ui.icon('person', size='5rem').classes(
                'bg-pink-100 text-pink-600 rounded-full p-4 mb-4'
            )
            ui.label(username).classes('text-3xl font-bold text-gray-800')
            ui.label('Pengguna Skintify').classes('text-sm text-gray-500 mb-4')

            # Badge identitas kulit
            with ui.row().classes('gap-3 flex-wrap justify-center'):
                ui.badge(f'Kulit: {skin_type}', color='pink-100').classes(
                    'text-pink-600 px-4 py-2 font-bold'
                )
                ui.badge(f'Lokasi: {city}', color='blue-100').classes(
                    'text-blue-600 px-4 py-2 font-bold'
                )
                for masalah in masalah_list[:3]:   # tampilkan maks 3 badge masalah
                    ui.badge(masalah, color='pink-100').classes('text-pink-600 px-4 py-2 font-bold')
                for bahan in hindari_list[:2]:      # tampilkan maks 2 badge hindari
                    ui.badge(f'Hindari: {bahan}', color='red-100').classes(
                        'text-red-500 px-4 py-2 font-bold'
                    )

        # ════════════════════════════════════════════════════════════════════
        #  BAGIAN 2: DATA PROFIL (KIRI) + RIWAYAT AKTIVITAS (KANAN)
        # ════════════════════════════════════════════════════════════════════
        with ui.row().classes('w-full gap-6 items-stretch'):

            # ── KARTU KIRI: Data Profil ───────────────────────────────────
            with ui.card().classes('flex-1 p-8 shadow-sm rounded-2xl'):
                ui.label('Data Profil').classes('font-bold text-xl mb-6 text-pink-500')

                with ui.column().classes('w-full gap-4'):
                    _baris_data('Nama',            username)
                    _baris_data('Email',           email)
                    _baris_data('Tipe Kulit',      skin_type)
                    _baris_data('Lokasi',          city)
                    _baris_data('Bahan Dihindari', hindari_text)
                    _baris_data('Masalah Kulit',   masalah_text)

                ui.separator().classes('my-4')

                # Tombol Edit Profil → set mode edit lalu ke onboarding
                def ke_edit_profil():
                    app.storage.user['onboarding_mode'] = 'edit'
                    ui.navigate.to('/onboarding')

                ui.button('✏️  Edit Profil', on_click=ke_edit_profil).classes(
                    'w-full bg-pink-500 text-white font-bold py-3 rounded-xl mt-2'
                )

                # Tombol Logout
                def do_logout():
                    AuthManager.logout()
                    state.routine = []
                    ui.notify('Berhasil logout. Sampai jumpa! 👋', color='positive')
                    ui.navigate.to('/login')

                with ui.dialog() as confirm_dialog, ui.card().classes('p-6 gap-4'):
                    ui.label('Yakin mau logout?').classes('text-lg font-bold')
                    ui.label('Kamu akan keluar dari akun Skintify-mu.').classes(
                        'text-sm text-gray-500'
                    )
                    with ui.row().classes('gap-3 mt-2'):
                        ui.button('Batal', on_click=confirm_dialog.close).props('flat')
                        ui.button('Ya, Logout', on_click=do_logout).classes(
                            'text-white px-4 bg-red-500 rounded-lg'
                        )

                ui.button('🚪  Logout', on_click=confirm_dialog.open).classes(
                    'w-full border border-red-200 text-red-500 font-bold py-3 rounded-xl mt-2'
                ).props('flat')

            # ── KARTU KANAN: Riwayat Aktivitas ───────────────────────────
            with ui.card().classes('flex-1 p-8 shadow-sm rounded-2xl'):
                ui.label('Riwayat Aktivitas').classes('font-bold text-xl mb-6 text-gray-800')

                if activity_log:
                    for act in activity_log:
                        _baris_riwayat(
                            icon    = act.get('icon', 'circle'),
                            color   = act.get('color', 'pink'),
                            judul   = act.get('judul', ''),
                            subjudul= act.get('subjudul', ''),
                            waktu   = act.get('waktu', ''),
                        )
                else:
                    # Placeholder kalau belum ada aktivitas sama sekali
                    with ui.column().classes('items-center justify-center w-full py-10 gap-2'):
                        ui.icon('history', size='3rem').classes('text-gray-300')
                        ui.label('Belum ada aktivitas').classes('text-gray-400 font-bold')
                        ui.label('Cari produk, bandingkan, atau tambah wishlist\nuntuk melihat riwayatmu di sini!').classes(
                            'text-xs text-gray-400 text-center whitespace-pre-line'
                        )

    # --- AKHIR AREA BELAJAR ---


# ── Helper UI ─────────────────────────────────────────────────────────────────

def _baris_data(label: str, nilai: str):
    """Satu baris tabel data profil: label kiri, nilai kanan."""
    with ui.row().classes('w-full justify-between border-b pb-2'):
        ui.label(label).classes('text-gray-500')
        ui.label(nilai).classes('font-bold text-right')


def _baris_riwayat(icon: str, color: str, judul: str, subjudul: str, waktu: str):
    """Satu entri riwayat aktivitas."""
    with ui.row().classes('w-full items-start gap-3 mb-4 border-b pb-4'):
        ui.icon(icon, color=color).classes('mt-1 text-xl')
        with ui.column().classes('gap-0 flex-1'):
            ui.label(judul).classes('font-bold text-sm text-gray-800')
            ui.label(subjudul).classes('text-xs text-gray-500')
        ui.label(waktu).classes('text-xs text-gray-400 whitespace-nowrap')
