from nicegui import ui, app
from app.context import data_mgr, state


def _tambah_riwayat(icon: str, color: str, judul: str, subjudul: str = ''):
    """Tambah entri ke riwayat aktivitas user."""
    import datetime
    riwayat = app.storage.user.get('activity_log', [])
    riwayat.insert(0, {
        'icon':     icon,
        'color':    color,
        'judul':    judul,
        'subjudul': subjudul,
        'waktu':    datetime.datetime.now().strftime('%d %b %Y, %H:%M'),
    })
    app.storage.user['activity_log'] = riwayat[:20]


# Koleksi tutorial steps untuk dijelaskan dengan bahasa sederhana
TUTORIAL_STEPS = [
    {
        'title': 'Selamat Datang di Skintify! 🌸',
        'subtitle': 'Mari kita pelajari cara menggunakan aplikasi ini bersama-sama',
        'description': 'Skintify adalah asisten pribadi untuk merawat kulitmu dengan produk yang tepat.\n\nDi sini kamu bisa:\n• Mencari ribuan produk skincare terbaik\n• Mendapat rekomendasi produk dari AI\n• Membandingkan produk sebelum membeli\n• Menyimpan favorit di wishlist\n• Melihat ingredient setiap produk\n• Memantau routine dan statistik skincare\n\nSemuanya dirancang khusus untuk membantu kamu merawat kulit dengan cara yang tepat! ✨',
        'icon': 'favorite',
        'color': 'pink-500'
    },
    {
        'title': '🔍 Cari Produk Skincare',
        'subtitle': 'Temukan ribuan produk skincare yang cocok untukmu',
        'description': 
            'Gunakan kolom pencarian atau jelajahi berdasarkan kategori seperti:\n\n'
            '🧴 Cleanser - untuk membersihkan wajah\n'
            '🌊 Toner - untuk menyeimbangkan kulit\n'
            '✨ Serum - untuk perawatan intensif\n'
            '💧 Moisturizer - untuk menjaga kelembaban\n'
            '☀️ Sunscreen - untuk perlindungan UV\n\n'
            'Setiap produk menampilkan harga, review dari pengguna lain, ingredient, dan info penting lainnya. Kamu bisa lihat semua detail sebelum memutuskan membeli!',
        'icon': 'search',
        'color': 'blue-500'
    },
    {
        'title': '❤️ Simpan Favorit Produk',
        'subtitle': 'Koleksi produk yang kamu inginkan dalam wishlist',
        'description':
            'Fitur Wishlist membantu kamu:\n\n'
            '💖 Menyimpan produk favorit untuk dibeli nanti\n'
            '📋 Membuat multiple list wishlist (misal: "Harus Beli", "Coba Nanti")\n'
            '🔔 Menerima notifikasi jika harga produk turun\n'
            '👥 Membagikan wishlist dengan teman\n'
            '📝 Menambahkan catatan pada setiap produk\n\n'
            'Dengan wishlist, kamu tidak akan lupa produk bagus yang ingin dibeli!',
        'icon': 'favorite_border',
        'color': 'red-500'
    },
    {
        'title': '⚖️ Bandingkan Produk',
        'subtitle': 'Lihat perbedaan produk untuk memilih yang terbaik',
        'description':
            'Fitur Compare memudahkan kamu:\n\n'
            '👀 Membandingkan 2-5 produk secara side-by-side\n'
            '💰 Melihat perbedaan harga, ingredient, dan rating\n'
            '⚠️ Mendeteksi ingredient yang berpotensi konflik\n'
            '🛒 Langsung menambahkan produk terpilih ke keranjang\n'
            '📊 Melihat pro-con setiap produk dalam satu layar\n\n'
            'Sangat berguna saat bingung memilih antara beberapa produk!',
        'icon': 'balance',
        'color': 'purple-500'
    },
    {
        'title': '✨ Dapatkan Rekomendasi AI',
        'subtitle': 'AI kami merekomendasikan produk berdasarkan tipe kulitmu',
        'description':
            'Fitur AI Recommendation memberikan:\n\n'
            '🤖 Rekomendasi produk yang cocok untuk tipe kulitmu\n'
            '💡 Penjelasan mengapa produk direkomendasikan\n'
            '📅 Saran routine harian yang tepat\n'
            '💸 Produk alternatif dengan harga lebih terjangkau\n'
            '🎯 Saran berdasarkan masalah kulit yang kamu hadapi\n\n'
            'Makin sering kamu gunakan, makin akurat rekomendasi kami!',
        'icon': 'auto_awesome',
        'color': 'yellow-500'
    },
    {
        'title': '📊 Pantau Statistik Skincare-mu',
        'subtitle': 'Lihat perkembangan dan habit skincare kamu',
        'description':
            'Dashboard Statistik menampilkan:\n\n'
            '💳 Total pembelian dan pengeluaran skincare\n'
            '🏷️ Kategori dan brand favorit kamu\n'
            '📈 Grafik pembelian per bulan\n'
            '🧪 Analisis trend skincare kamu\n'
            '🎯 Insights tentang preferensi skincare kamu\n\n'
            'Semua ini membantu kamu memahami habit dan preference perawatan kulit!',
        'icon': 'analytics',
        'color': 'green-500'
    },
    {
        'title': '🧬 Cek Ingredient Produk',
        'subtitle': 'Pahami setiap ingredient yang masuk ke kulit kamu',
        'description':
            'Fitur Ingredient Checker membantu kamu:\n\n'
            '📋 Melihat semua ingredient dalam setiap produk\n'
            '📖 Memahami fungsi setiap ingredient\n'
            '🚨 Mendeteksi ingredient yang mungkin memicu alergi\n'
            '❌ Menghindari ingredient yang tidak cocok dengan kulitmu\n'
            '✅ Menemukan ingredient yang bagus untuk masalah kulitmu\n\n'
            'Knowledge is power - ketahui apa yang kamu gunakan di kulit! 🧴',
        'icon': 'science',
        'color': 'cyan-500'
    }
]


def show_page():
    """MISI FALISHA: Onboarding Tutorial + Profil Kulit"""

    # Cek mode: edit profil atau first-time user
    is_edit_mode = app.storage.user.get('onboarding_mode') == 'edit'

    # Container utama untuk state management
    container = ui.column().classes('w-full h-screen')
    
    with container:
        # State management
        page_state = {
            'current_step': 0,  # 0-6 = tutorial steps, 7 = profile setup
            'skin_type': app.storage.user.get('skin_type'),
            'avoid_ingredients': app.storage.user.get('avoid_ingredients', []),
            'skin_issues': app.storage.user.get('skin_issues', []),
            'city': app.storage.user.get('city', 'Jakarta')
        }

        # Jika edit mode, langsung ke step profil
        if is_edit_mode:
            page_state['current_step'] = len(TUTORIAL_STEPS)

        # Container untuk refresh halaman
        main_container = ui.column().classes('w-full h-screen')

        def refresh_view():
            """Refresh tampilan berdasarkan current_step"""
            main_container.clear()
            
            with main_container:
                if page_state['current_step'] < len(TUTORIAL_STEPS):
                    # --- TUTORIAL STEP ---
                    show_tutorial_step(page_state['current_step'])
                else:
                    # --- PROFILE SETUP STEP ---
                    show_profile_setup()

        def show_tutorial_step(step_idx):
            """Tampilkan satu step dari tutorial dengan bahasa sederhana"""
            step = TUTORIAL_STEPS[step_idx]
            
            with ui.column().classes('w-full h-screen items-center justify-center bg-gradient-to-br from-pink-50 to-rose-50 p-6'):
                
                # Progress bar
                progress_percent = ((step_idx + 1) / (len(TUTORIAL_STEPS) + 1)) * 100
                with ui.row().classes('w-full max-w-2xl mb-6 gap-2'):
                    for i in range(len(TUTORIAL_STEPS) + 1):
                        if i <= step_idx:
                            ui.element().classes('h-1 bg-pink-500 rounded-full flex-1')
                        else:
                            ui.element().classes('h-1 bg-gray-300 rounded-full flex-1')
                
                # Card content
                with ui.card().classes('w-full max-w-2xl p-12 shadow-xl rounded-3xl'):
                    
                    # Icon & Title
                    with ui.column().classes('items-center gap-4 mb-8'):
                        ui.icon(step['icon'], size='4rem').classes(f'text-{step["color"]}')
                        ui.label(step['title']).classes('text-3xl font-bold text-gray-800 text-center')
                        ui.label(step['subtitle']).classes('text-lg text-gray-600 text-center')
                    
                    # Description dengan formatting yang bagus
                    ui.separator().classes('mb-6')
                    ui.label(step['description']).classes('text-base text-gray-700 whitespace-pre-line leading-relaxed mb-8')
                    
                    # Action buttons
                    with ui.row().classes('w-full gap-3 mt-8'):
                        # Tombol Skip (hanya di step pertama dan bukan edit mode)
                        if step_idx == 0 and not is_edit_mode:
                            ui.button(
                                'Lewati Tutorial',
                                on_click=lambda: skip_tutorial()
                            ).classes('px-6 py-3 text-gray-600 text-sm').props('flat')
                        
                        # Spacing
                        ui.element().classes('flex-1')
                        
                        # Tombol Previous (jika bukan step pertama)
                        if step_idx > 0:
                            ui.button(
                                '← Sebelumnya',
                                on_click=lambda: prev_step()
                            ).classes('px-6 py-3 bg-gray-200 text-gray-700 rounded-lg')
                        
                        # Tombol Next/Finish
                        if step_idx < len(TUTORIAL_STEPS) - 1:
                            ui.button(
                                'Lanjut →',
                                on_click=lambda: next_step()
                            ).classes('px-6 py-3 bg-pink-500 text-white rounded-lg font-bold')
                        else:
                            ui.button(
                                'Lanjut ke Profil ✓',
                                on_click=lambda: next_step()
                            ).classes('px-6 py-3 bg-pink-600 text-white rounded-lg font-bold')

        def show_profile_setup():
            """Tampilkan form setup profil kulit"""
            with ui.column().classes('w-full h-screen items-center justify-center bg-gradient-to-br from-pink-50 to-rose-50 p-6'):
                
                # Progress bar (sudah di akhir)
                with ui.row().classes('w-full max-w-md mb-6 gap-2'):
                    for i in range(len(TUTORIAL_STEPS) + 1):
                        ui.element().classes('h-1 bg-pink-500 rounded-full flex-1')
                
                with ui.card().classes('w-full max-w-md p-8 shadow-xl rounded-2xl'):
                    
                    # Header
                    with ui.column().classes('items-center gap-2 mb-6'):
                        ui.icon('info', size='3rem').classes('text-pink-500')
                        if is_edit_mode:
                            ui.label('Perbarui Profil Kulit').classes('text-2xl font-bold text-gray-800')
                            ui.label('Kami menyesuaikan rekomendasi berdasarkan profil kulitmu').classes('text-xs text-gray-500')
                        else:
                            ui.label('Kenali Kulit Kamu').classes('text-2xl font-bold text-gray-800')
                            ui.label('Agar kami bisa merekomendasikan produk yang tepat').classes('text-xs text-gray-500')
                    
                    ui.separator().classes('mb-6')
                    
                    # Form fields
                    skin_options = ['Normal', 'Berminyak', 'Kering', 'Kombinasi', 'Sensitif']
                    skin_select = ui.select(
                        skin_options,
                        label='🌸 Tipe Kulitku',
                        value=page_state['skin_type']
                    ).classes('w-full mb-4').props('outlined')
                    
                    ui.label('Bahan yang aku hindari (opsional)').classes('text-sm font-bold text-gray-700 mt-4')
                    ui.label('Pilih bahan yang membuat kulit sensitif atau alergi').classes('text-xs text-gray-400 -mt-2')
                    avoid_options = ['Alcohol', 'Fragrance', 'Paraben', 'Sulfate', 'Essential Oil', 'Silicone']
                    avoid_select = ui.select(
                        avoid_options,
                        multiple=True,
                        label='Bahan sensitif',
                        value=page_state['avoid_ingredients']
                    ).classes('w-full mb-4').props('outlined')
                    
                    ui.label('Masalah kulit utamaku (opsional)').classes('text-sm font-bold text-gray-700')
                    ui.label('Boleh pilih lebih dari satu').classes('text-xs text-gray-400 -mt-2')
                    issues_options = ['Jerawat', 'Kusam', 'Flek Hitam', 'Pori-pori Besar', 'Kerutan', 'Dehidrasi']
                    issues_select = ui.select(
                        issues_options,
                        multiple=True,
                        label='Masalah kulit',
                        value=page_state['skin_issues']
                    ).classes('w-full mb-4').props('outlined')
                    
                    ui.label('Kota tempat tinggalku').classes('text-sm font-bold text-gray-700 mt-4')
                    ui.label('Membantu kami menyesuaikan tips dengan iklim setempat').classes('text-xs text-gray-400 -mt-2')
                    city_options = ['Jakarta', 'Bandung', 'Surabaya', 'Jogja', 'Medan', 'Makassar', 'Semarang', 'Lainnya']
                    city_select = ui.select(
                        city_options,
                        label='Kota',
                        value=page_state['city']
                    ).classes('w-full').props('outlined')
                    
                    ui.separator().classes('my-6')
                    
                    # Action buttons
                    def save_profile():
                        skin = skin_select.value
                        if not skin:
                            ui.notify('Tipe kulit harus dipilih! 🌸', color='warning')
                            return
                        
                        try:
                            # Simpan ke storage
                            app.storage.user['skin_type'] = skin
                            app.storage.user['avoid_ingredients'] = avoid_select.value or []
                            app.storage.user['skin_issues'] = issues_select.value or []
                            app.storage.user['city'] = city_select.value
                            app.storage.user['onboarding_mode'] = None
                            app.storage.user['onboarding_completed'] = True
                            
                            # Simpan ke database
                            email = app.storage.user.get('email')
                            if email:
                                try:
                                    data_mgr.update_user_profile(
                                        email=email,
                                        skin_type=skin,
                                        city=city_select.value
                                    )
                                except Exception:
                                    pass
                            
                            _tambah_riwayat(
                                icon='check_circle',
                                color='green',
                                judul='Menyelesaikan onboarding',
                                subjudul=f'Tipe kulit: {skin}'
                            )
                            
                            ui.notify('✓ Profil disimpan! Selamat datang di Skintify! 🎉', color='positive')
                            
                            if is_edit_mode:
                                ui.navigate.to('/profile')
                            else:
                                ui.navigate.to('/')
                        
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', color='negative')
                            print(f"Error: {e}")
                    
                    with ui.row().classes('w-full gap-3'):
                        if is_edit_mode:
                            ui.button(
                                'Batal',
                                on_click=lambda: ui.navigate.to('/profile')
                            ).classes('flex-1 text-gray-500').props('flat')
                        else:
                            ui.button(
                                '← Kembali',
                                on_click=lambda: prev_step()
                            ).classes('flex-1 bg-gray-200 text-gray-700 rounded-lg')
                        
                        ui.button(
                            'Simpan & Mulai ✓' if is_edit_mode else 'Selesai & Mulai ✓',
                            on_click=save_profile
                        ).classes('flex-1 bg-pink-600 text-white rounded-lg font-bold')

        def next_step():
            page_state['current_step'] += 1
            refresh_view()
        
        def prev_step():
            if page_state['current_step'] > 0:
                page_state['current_step'] -= 1
            refresh_view()
        
        def skip_tutorial():
            page_state['current_step'] = len(TUTORIAL_STEPS)
            refresh_view()
        
        # Initial render
        refresh_view()
