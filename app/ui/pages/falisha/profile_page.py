from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager

def show_page():
    """MISI FALISHA: Halaman Profil Lengkap — Layout Opsi 7"""

    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    # --- 🚀 MULAI KERJAKAN DI SINI ---

    # ── Ambil data dari storage ───────────────────────────────────────────────
    email        = app.storage.user.get('email', 'user@skintify.com')
    username     = app.storage.user.get('username', '')
    if not username:
        try:
            from app.database.database_manager import BasisData
            data_user = BasisData.ambil_pengguna_by_identifier(email)
            if data_user:
                username = data_user.get('username', '')
                if username:
                    app.storage.user['username'] = username
        except Exception:
            pass
    if not username:
        username = email.split('@')[0].capitalize()

    skin_type    = app.storage.user.get('skin_type', 'Belum diisi')
    hindari_list = app.storage.user.get('avoid_ingredients', []) or []
    masalah_list = app.storage.user.get('skin_issues', []) or []
    city         = app.storage.user.get('city', 'Belum diisi')
    activity_log = app.storage.user.get('activity_log', [])
    wishlist_count = len(state.routine)

    skin_type    = skin_type if skin_type else 'Belum diisi'
    hindari_text = ', '.join(hindari_list) if hindari_list else 'Tidak ada'
    masalah_text = ', '.join(masalah_list) if masalah_list else 'Tidak ada'

    # ── LAYOUT UTAMA ─────────────────────────────────────────────────────────
    with ui.column().classes('w-full p-6 gap-4'):

        # ════════════════════════════════════════════════════════════════════
        #  BARIS 1 — Info user + tombol aksi
        # ════════════════════════════════════════════════════════════════════
        with ui.card().classes('w-full shadow-sm rounded-2xl p-5'):
            with ui.row().classes('w-full items-center gap-4'):

                # Avatar inisial
                with ui.element('div').classes(
                    'w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0'
                ).style('background: #FBEAF0;'):
                    ui.label(username[0].upper() if username else 'U').classes(
                        'text-xl font-bold'
                    ).style('color: #D4537E;')

                # Nama & email
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(username).classes('text-lg font-bold text-gray-800')
                    
                    user_role = app.storage.user.get('role', 'user')
                    
                    if str(user_role).lower() == 'admin':
                        ui.label('Admin Skintify').classes('text-xs text-pink-600 font-medium')
                    else:
                        ui.label('Pengguna Skintify').classes('text-xs text-gray-500')

                # Tombol Edit + Logout
                def edit_profil():
                    app.storage.user['onboarding_mode'] = 'edit'
                    ui.navigate.to('/onboarding')

                ui.button('✏️  Edit Profil', on_click=edit_profil, color='#E56486').classes(
                    'rounded-xl text-white font-bold px-5 py-2 shadow-sm'
                )
        # ════════════════════════════════════════════════════════════════════
        #  BARIS 2 — 5 stat card ringkasan
        # ══════════════════════════════════════════════
        with ui.row().classes('w-full gap-4'):

            #  Ganti 'droplet' menjadi 'water_drop'
            _stat_card('water_drop', '#D4537E', 'Tipe Kulit', 
                        skin_type if skin_type else 'Belum diisi')
            _stat_card('location_on',     '#185FA5', 'Lokasi',       city)
            _stat_card('warning_amber',   '#90021F', 'Masalah',
                       f'{len(masalah_list)} item' if masalah_list else '—')
            _stat_card('favorite',        '#EA3B52', 'Wishlist',
                       f'{wishlist_count} produk')
            _stat_card('compare_arrows',  '#4B0076', 'Bandingkan',
                       f'{len([a for a in activity_log if "andingkan" in a.get("judul","")])} kali')

        # ════════════════════════════════════════════════════════════════════
        #  BARIS 3 — Data profil (kiri) + Riwayat (tengah) + Ringkasan (kanan)
        # ════════════════════════════════════════════════════════════════════
        with ui.row().classes('w-full gap-4 items-stretch'):

            # ── KARTU KIRI: Data Profil ───────────────────────────────────
            with ui.card().classes('flex-1 p-6 shadow-sm rounded-2xl'):
                ui.label('Data Profil').classes(
                    'text-xs font-bold text-gray-400 uppercase tracking-wider mb-3'
                ).style('letter-spacing:.07em;')

                _baris('Email',           email)
                _baris('Tipe Kulit',      skin_type)
                _baris('Lokasi',          city)
                _baris('Bahan Dihindari', hindari_text)
                _baris('Masalah Kulit',   masalah_text)

            # ── KARTU TENGAH: Riwayat Aktivitas ──────────────────────────
            with ui.card().classes('flex-1 p-6 shadow-sm rounded-2xl'):
                ui.label('Riwayat Aktivitas').classes(
                    'text-xs font-bold text-gray-400 uppercase tracking-wider mb-3'
                ).style('letter-spacing:.07em;')

                if activity_log:
                    # Tampilkan maks 5 entri terbaru
                    for act in activity_log[:5]:
                        with ui.row().classes('w-full items-start gap-3 pb-3 mb-0 border-b'):
                            with ui.element('div').classes(
                                'w-2 h-2 rounded-full flex-shrink-0 mt-2'
                            ).style(f'background: {_color_hex(act.get("color","pink"))};'):
                                pass
                            with ui.column().classes('flex-1 gap-0'):
                                ui.label(act.get('judul', '')).classes(
                                    'text-sm font-bold text-gray-800'
                                )
                                ui.label(act.get('subjudul', '')).classes(
                                    'text-xs text-gray-500'
                                )
                            ui.label(act.get('waktu', '')).classes(
                                'text-xs text-gray-400 whitespace-nowrap flex-shrink-0'
                            )
                else:
                    with ui.column().classes('items-center justify-center h-full py-8 gap-2 w-full'):
                        ui.icon('history', size='2.5rem').classes('text-gray-300')
                        ui.label('Belum ada aktivitas').classes(
                            'text-sm font-bold text-gray-400'
                        )
                        ui.label(
                            'Cari, bandingkan, atau tambah wishlist\n'
                            'untuk melihat riwayatmu.'
                        ).classes('text-xs text-gray-400 text-center whitespace-pre-line')

            # ── KARTU KANAN: Ringkasan Akun ───────────────────────────────
            with ui.card().classes('flex-1 p-6 shadow-sm rounded-2xl'):
                ui.label('Ringkasan Akun').classes(
                    'text-xs font-bold text-gray-400 uppercase tracking-wider mb-3'
                ).style('letter-spacing:.07em;')

                cari_count   = len([a for a in activity_log if 'ari' in a.get('judul', '').lower()])
                bandingkan_count = len([a for a in activity_log if 'andingkan' in a.get('judul', '')])

                _ringkasan('Produk dicari',     f'{cari_count} produk')
                _ringkasan('Total wishlist',    f'{wishlist_count} produk')
                _ringkasan('Perbandingan',      f'{bandingkan_count} kali')
                _ringkasan('Member sejak',      'Mei 2026')

    # --- AKHIR AREA BELAJAR ---


# ── Helper UI ─────────────────────────────────────────────────────────────────

def _stat_card(icon: str, color: str, label: str, value: str):
    """Satu stat card kecil di baris tengah."""
    with ui.card().classes('flex-1 p-4 shadow-sm rounded-2xl items-center text-center'):
        ui.icon(icon, size='1.4rem').style(f'color: {color};')
        ui.label(label).classes('text-xs text-gray-500 mt-1')
        ui.label(value).classes('text-sm font-bold text-gray-800')


def _baris(label: str, nilai: str):
    """Satu baris label-nilai dengan garis bawah."""
    with ui.row().classes('w-full justify-between border-b pb-2 mb-1'):
        ui.label(label).classes('text-xs text-gray-500')
        ui.label(nilai).classes('text-xs font-bold text-right text-gray-800')


def _ringkasan(label: str, nilai: str):
    """Satu baris ringkasan akun."""
    with ui.row().classes('w-full justify-between border-b pb-2 mb-1'):
        ui.label(label).classes('text-xs text-gray-500')
        ui.label(nilai).classes('text-xs font-bold text-gray-800')


def _color_hex(color_name: str) -> str:
    """Konversi nama warna ke hex untuk dot riwayat."""
    return {
        'pink':   '#D4537E',
        'blue':   '#378ADD',
        'green':  '#1D9E75',
        'orange': '#BA7517',
        'purple': '#7C3AED',
        'red':    '#EF4444',
    }.get(color_name, '#D4537E')