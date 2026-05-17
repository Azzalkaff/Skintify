from nicegui import ui, app
from app.context import data_mgr, state


def show_page():
    """MISI FALISHA: Onboarding (Selamat Datang) & Edit Profil Kulit"""

    # Cek apakah user membuka ini untuk EDIT PROFIL atau PERTAMA KALI
    # main.py set app.storage.user['onboarding_mode'] = 'edit' saat dari tombol Edit Profil
    is_edit_mode = app.storage.user.get('onboarding_mode') == 'edit'

    with ui.column().classes('w-full h-screen items-center justify-center bg-pink-50'):

        # --- Header: beda teks tergantung mode ---
        with ui.column().classes('items-center mb-4 gap-1'):
            ui.image('/static/logo-skintify-fix.png').classes('w-28 h-28 object-contain')

            if is_edit_mode:
                # Mode Edit: tidak ada kata "Selamat Datang", langsung ke pertanyaan
                ui.label('Perbarui Profil Kulitmu').classes('text-xl font-bold text-gray-800')
                ui.label('Ubah informasi kulitmu kapan saja.').classes('text-sm text-gray-500')
            else:
                # Mode Pertama Kali: sambutan hangat
                ui.label('Selamat Datang!').classes('text-xl font-bold text-gray-800')
                ui.label(
                    'Jawab beberapa pertanyaan singkat agar kami bisa merekomendasikan\n'
                    'produk skincare yang paling cocok untukmu.'
                ).classes('text-sm text-center text-gray-500 whitespace-pre-line')

        # --- Kartu Survey ---
        with ui.card().classes('w-full max-w-md p-8 shadow-lg rounded-2xl'):

            # Ambil nilai lama kalau mode edit (pre-fill)
            old_skin    = app.storage.user.get('skin_type', None)
            old_avoid   = app.storage.user.get('avoid_ingredients', [])
            old_masalah = app.storage.user.get('skin_issues', [])

            # --- PERTANYAAN 1: Tipe Kulit ---
            ui.label('Apa tipe kulitmu?').classes('font-bold text-lg')
            skin_options = ['Normal', 'Berminyak', 'Kering', 'Kombinasi', 'Sensitif']
            selected_skin = ui.select(
                skin_options,
                label='Pilih tipe kulit',
                value=old_skin
            ).classes('w-full')

            # --- PERTANYAAN 2: Bahan yang Dihindari ---
            ui.label('Bahan yang ingin kamu hindari?').classes('font-bold text-lg mt-4')
            ui.label('Pilih bahan yang membuat kulitmu sensitif.').classes('text-xs text-gray-400 -mt-2')
            avoid_options = ['Alcohol', 'Fragrance', 'Paraben', 'Sulfate', 'Essential Oil', 'Silicone']
            selected_avoid = ui.select(
                avoid_options,
                multiple=True,
                label='Pilih bahan (opsional)',
                value=old_avoid
            ).classes('w-full')

            # --- PERTANYAAN 3: Masalah Kulit ---
            ui.label('Apa masalah utama kulitmu?').classes('font-bold text-lg mt-4')
            ui.label('Boleh pilih lebih dari satu.').classes('text-xs text-gray-400 -mt-2')
            masalah_options = ['Jerawat', 'Kusam', 'Flek Hitam', 'Pori-pori Besar', 'Kerutan', 'Dehidrasi']
            selected_masalah = ui.select(
                masalah_options,
                multiple=True,
                label='Pilih masalah kulit (opsional)',
                value=old_masalah
            ).classes('w-full')

            # --- PERTANYAAN 4: Lokasi (BARU) ---
            ui.label('Di mana kamu tinggal?').classes('font-bold text-lg mt-4')
            ui.label('Lokasimu membantu kami menyesuaikan tips dengan cuaca setempat.').classes('text-xs text-gray-400 -mt-2')
            city_options = ['Jakarta', 'Bandung', 'Surabaya', 'Jogja', 'Medan', 'Makassar', 'Semarang']
            selected_city = ui.select(
                city_options,
                label='Pilih Kota',
                value=app.storage.user.get('city', 'Jakarta')
            ).classes('w-full')

            # --- Fungsi Simpan ---
            def simpan_dan_lanjut():
                tipe_kulit        = selected_skin.value
                hindari_kandungan = selected_avoid.value or []
                masalah_kulit     = selected_masalah.value or []
                kota              = selected_city.value

                if not tipe_kulit:
                    ui.notify('Tipe kulit wajib diisi ya! 🌸', color='warning')
                    return

                try:
                    # Simpan ke storage
                    app.storage.user['skin_type']         = tipe_kulit
                    app.storage.user['avoid_ingredients'] = hindari_kandungan
                    app.storage.user['skin_issues']       = masalah_kulit
                    app.storage.user['city']              = kota

                    # Bersihkan mode setelah selesai
                    app.storage.user['onboarding_mode'] = None

                    # Catat ke riwayat aktivitas
                    _tambah_riwayat(
                        icon='edit',
                        color='pink',
                        judul='Memperbarui profil kulit' if is_edit_mode else 'Mengisi profil kulit',
                        subjudul=f'Tipe kulit: {tipe_kulit}'
                    )

                    # Simpan ke database kalau fungsinya ada
                    email = app.storage.user.get('email')
                    if email:
                        try:
                            data_mgr.update_user_profile(
                                email       = email,
                                skin_type   = tipe_kulit,
                                city        = kota
                            )
                        except Exception:
                            pass

                    ui.notify('Profil berhasil disimpan!', color='positive')

                    if is_edit_mode:
                        ui.navigate.to('/profile')  # Kembali ke profil setelah edit
                    else:
                        ui.navigate.to('/')          # Ke home setelah onboarding pertama kali

                except Exception as e:
                    ui.notify(f'Gagal menyimpan: {e}', color='negative')
                    print(f"Error Detail: {e}")

            # --- Tombol Aksi ---
            label_tombol = 'Simpan Perubahan ✓' if is_edit_mode else 'Mulai Eksplorasi →'
            ui.button(label_tombol, on_click=simpan_dan_lanjut).classes(
                'w-full mt-6 bg-pink-500 text-white font-bold py-3 rounded-xl'
            )

            # Tombol batal (hanya muncul di mode edit)
            if is_edit_mode:
                ui.button('Batal', on_click=lambda: ui.navigate.to('/profile')).classes(
                    'w-full mt-2 text-gray-400 text-sm'
                ).props('flat')
            else:
                def skip_onboarding():
                    app.storage.user['skin_type'] = 'Normal' # Default untuk skip
                    ui.notify('Onboarding dilewati (Default: Normal)', color='info')
                    ui.navigate.to('/')

                ui.button('Lewati untuk sekarang', on_click=skip_onboarding).classes(
                    'w-full mt-2 text-gray-400 text-sm'
                ).props('flat')


def _tambah_riwayat(icon: str, color: str, judul: str, subjudul: str):
    """Helper: tambah satu entri ke riwayat aktivitas di app.storage.user."""
    import datetime
    riwayat = app.storage.user.get('activity_log', [])
    riwayat.insert(0, {           # insert di depan agar yang terbaru di atas
        'icon':     icon,
        'color':    color,
        'judul':    judul,
        'subjudul': subjudul,
        'waktu':    datetime.datetime.now().strftime('%d %b %Y, %H:%M'),
    })
    app.storage.user['activity_log'] = riwayat[:20]  # simpan max 20 entri
