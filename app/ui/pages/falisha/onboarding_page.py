from nicegui import ui, app
from app.database.database_manager import BasisData

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


def show_page():
    """MISI FALISHA: Profil Kulit (Interactive Multi-Step Wizard)"""

    # Cek mode: edit profil atau first-time user
    is_edit_mode = app.storage.user.get('onboarding_mode') == 'edit'

    # Inisialisasi default agar tidak error NoneType
    if 'skin_type' not in app.storage.user: app.storage.user['skin_type'] = ''
    if 'skin_issues' not in app.storage.user: app.storage.user['skin_issues'] = []
    if 'avoid_ingredients' not in app.storage.user: app.storage.user['avoid_ingredients'] = []
    if 'skincare_goals' not in app.storage.user: app.storage.user['skincare_goals'] = []
    if 'lifestyle' not in app.storage.user: app.storage.user['lifestyle'] = []

    with ui.column().classes('w-full h-screen items-center justify-center bg-gradient-to-br from-pink-50 to-rose-50 p-6 overflow-y-auto'):
        
        with ui.card().classes('w-full max-w-2xl p-8 shadow-xl rounded-2xl'):
            
            # Header
            with ui.column().classes('items-center gap-2 mb-2 w-full'):
                ui.icon('auto_awesome', size='3rem').classes('text-pink-500')
                if is_edit_mode:
                    ui.label('Perbarui Profil Kulit').classes('text-2xl font-bold text-gray-800')
                    ui.label('Sesuaikan profil agar AI kami semakin presisi').classes('text-sm text-gray-500 text-center')
                else:
                    ui.label('Kenali Kulit Kamu').classes('text-2xl font-bold text-gray-800')
                    ui.label('Mari personalisasi pengalaman Skintify khusus untukmu').classes('text-sm text-gray-500 text-center')
            
            ui.separator().classes('mb-4')
            
            # Stepper UI
            with ui.stepper().props('vertical').classes('w-full bg-transparent shadow-none') as stepper:
                
                # STEP 1: Tipe Kulit
                with ui.step('Tipe Kulit', icon='face'):
                    ui.label('Apa tipe kulit dasarmu?').classes('text-md font-bold text-gray-700 mb-2')
                    skin_options = ['Normal', 'Berminyak', 'Kering', 'Kombinasi', 'Sensitif']
                    skin_select = ui.select(
                        skin_options,
                        label='🌸 Tipe Kulitku',
                        value=app.storage.user.get('skin_type')
                    ).classes('w-full mb-2').props('outlined')
                    
                    with ui.stepper_navigation().classes('mt-2 gap-2'):
                        ui.button('Selanjutnya', on_click=stepper.next).classes('bg-pink-600 text-white rounded-lg px-6')
                
                # STEP 2: Masalah & Tujuan
                with ui.step('Masalah & Tujuan', icon='track_changes'):
                    ui.label('Masalah kulit yang sedang dialami (opsional)').classes('text-sm font-bold text-gray-700')
                    issues_options = ['Jerawat', 'Kusam', 'Flek Hitam', 'Pori-pori Besar', 'Kerutan', 'Dehidrasi', 'Kemerahan', 'Tidak ada']
                    issues_select = ui.select(
                        issues_options,
                        multiple=True,
                        label='Pilih masalah kulit',
                        value=app.storage.user.get('skin_issues')
                    ).classes('w-full mb-4').props('outlined use-chips')
                    
                    ui.label('Tujuan Skincare (Goals) 🎯').classes('text-sm font-bold text-gray-700')
                    goals_options = ['Mencerahkan', 'Anti-aging', 'Skin Barrier Kuat', 'Mengurangi Minyak', 'Melembapkan Ekstra', 'Glowing', 'Tidak ada']
                    goals_select = ui.select(
                        goals_options,
                        multiple=True,
                        label='Apa yang ingin kamu capai?',
                        value=app.storage.user.get('skincare_goals')
                    ).classes('w-full mb-2').props('outlined use-chips')
                    
                    with ui.stepper_navigation().classes('mt-2 gap-2'):
                        ui.button('Selanjutnya', on_click=stepper.next).classes('bg-pink-600 text-white rounded-lg px-6')
                        ui.button('Kembali', on_click=stepper.previous).props('flat text-gray-500')

                # STEP 3: Gaya Hidup & Alergi
                with ui.step('Gaya Hidup & Alergi', icon='favorite'):
                    ui.label('Gaya Hidup (opsional)').classes('text-sm font-bold text-gray-700')
                    lifestyle_options = ['Sering di luar ruangan (Outdoor)', 'Full di ruangan ber-AC', 'Sering pakai Makeup', 'Sering Begadang', 'Mudah Berkeringat', 'Tidak ada']
                    lifestyle_select = ui.select(
                        lifestyle_options,
                        multiple=True,
                        label='Pilih yang sesuai dengan keseharianmu',
                        value=app.storage.user.get('lifestyle')
                    ).classes('w-full mb-4').props('outlined use-chips')

                    ui.label('Bahan yang dihindari (opsional)').classes('text-sm font-bold text-gray-700')
                    avoid_options = ['Alcohol', 'Fragrance', 'Paraben', 'Sulfate', 'Essential Oil', 'Silicone', 'Tidak ada']
                    avoid_select = ui.select(
                        avoid_options,
                        multiple=True,
                        label='Pilih bahan alergi/iritasi',
                        value=app.storage.user.get('avoid_ingredients')
                    ).classes('w-full mb-2').props('outlined use-chips')
                    
                    def save_profile():
                        skin = skin_select.value
                        if not skin:
                            ui.notify('Tipe kulit harus dipilih pada Tahap Pertama! 🌸', color='warning')
                            return
                        
                        try:
                            # Update local session storage
                            app.storage.user['skin_type'] = skin
                            app.storage.user['skin_issues'] = issues_select.value or []
                            app.storage.user['skincare_goals'] = goals_select.value or []
                            app.storage.user['lifestyle'] = lifestyle_select.value or []
                            app.storage.user['avoid_ingredients'] = avoid_select.value or []
                            app.storage.user['onboarding_mode'] = None
                            app.storage.user['onboarding_completed'] = True
                            
                            # Simpan ke Database
                            email = app.storage.user.get('email')
                            if email:
                                import json
                                BasisData.update_user_onboarding(
                                    email=email,
                                    skin_type=skin,
                                    avoid_ingredients=json.dumps(app.storage.user['avoid_ingredients']),
                                    skin_issues=json.dumps(app.storage.user['skin_issues']),
                                    skincare_goals=json.dumps(app.storage.user['skincare_goals']),
                                    lifestyle=json.dumps(app.storage.user['lifestyle'])
                                )
                            
                            if is_edit_mode:
                                ui.notify('✓ Profil berhasil diperbarui!', color='positive')
                                ui.navigate.to('/profile')
                            else:
                                _tambah_riwayat(
                                    icon='check_circle',
                                    color='green',
                                    judul='Menyelesaikan profil kulit',
                                    subjudul=f'Tipe kulit: {skin}'
                                )
                                ui.notify('✓ Profil disimpan! Selamat datang di Skintify! 🎉', color='positive')
                                ui.navigate.to('/')
                                
                        except Exception as e:
                            ui.notify(f'Error: {str(e)}', color='negative')
                            print(f"Error saving onboarding: {e}")

                    with ui.stepper_navigation().classes('mt-4 gap-2'):
                        ui.button('Simpan & Selesai ✓', on_click=save_profile).classes('bg-green-600 text-white font-bold rounded-lg px-6 shadow-md')
                        ui.button('Kembali', on_click=stepper.previous).props('flat text-gray-500')
                        
            if is_edit_mode:
                with ui.row().classes('w-full justify-center mt-2'):
                    ui.button('Batal', on_click=lambda: ui.navigate.to('/profile')).props('flat').classes('text-gray-400')
