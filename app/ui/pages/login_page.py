from nicegui import ui, app
import asyncio
from app.auth.auth import AuthManager

def show_page():
    """Antarmuka Login & Daftar dengan State Binding dan Loading Animation."""
    
    if AuthManager.is_authenticated():
        ui.navigate.to('/')
        return

    # State UI: Mengikat data form agar tidak hilang saat refresh
    state = {
        "mode": "login", # login | register | otp
        "email": "",
        "username": "",
        "password": "",
        "otp": "",
        "role": "user",  # Pilihan role saat register: 'user' | 'admin'
        "is_loading": False # Status untuk memunculkan animasi loading
    }

    # --- ELEMENT LOADING GLOBAL ---
    # Ditempatkan di luar refreshable agar DOM stabil dan tidak pernah dihapus/dibuat ulang
    loading_overlay = ui.column().classes('absolute inset-0 bg-white/70 backdrop-blur-[2px] z-50 flex items-center justify-center') \
        .bind_visibility_from(state, 'is_loading')
    with loading_overlay:
        ui.spinner('dots', size='lg', color='#A84A62')
        ui.label('Mohon tunggu sebentar...').classes('text-[#A84A62] font-bold mt-2 text-sm')

    @ui.refreshable
    def form_kontainer():
        # Kontainer Utama tanpa loading overlay di dalamnya
        with ui.column().classes('w-[480px] glass-panel rounded-[2rem] p-10 z-10 items-center shadow-2xl border border-white/40 relative'):
            
            # Logo (Besar & Anggun tanpa duplikasi teks)
            ui.image('/static/logo-skintify-fix.png').classes('w-36 h-36 object-contain mb-2')
            
            # --- TAMPILAN OTP ---
            if state["mode"] == "otp":
                ui.label('Verifikasi Email').classes('text-lg font-bold text-gray-700 mt-4')
                ui.label(f'Masukkan kode yang dikirim ke {state["email"]}').classes('text-[11px] text-gray-500 mb-6 text-center')
                
                ui.input('Kode OTP 6-Digit').bind_value(state, 'otp') \
                    .props('outlined rounded bg-white/70 text-center tracking-[10px] font-bold') \
                    .classes('w-full mb-6')

                with ui.row().classes('w-full gap-2'):
                    ui.button('Verifikasi', on_click=proses_verifikasi) \
                        .classes('flex-1 btn-primary text-white rounded-xl py-3')
                    
                    def batal():
                        state["mode"] = "register"
                        form_kontainer.refresh()
                        
                    ui.button('Batal', on_click=batal) \
                        .props('flat').classes('text-gray-400')

            # --- TAMPILAN LOGIN / DAFTAR ---
            else:
                with ui.tabs().classes('w-full mb-6 bg-transparent') as tabs:
                    ui.tab('Masuk')
                    ui.tab('Daftar')
                
                def ganti_tab(e):
                    mode_baru = "login" if e.value == "Masuk" else "register"
                    if state["mode"] != mode_baru:
                        state["mode"] = mode_baru
                        form_kontainer.refresh()

                tabs.on_value_change(ganti_tab)
                tabs.set_value('Masuk' if state["mode"] == "login" else 'Daftar')

                if state["mode"] == "register":
                    ui.input('Username').bind_value(state, 'username') \
                        .props('outlined rounded bg-white/70').classes('w-full mb-4')
                    ui.input('Email').bind_value(state, 'email') \
                        .props('outlined rounded bg-white/70').classes('w-full mb-4')
                else:
                    ui.input('Username / Email').bind_value(state, 'email') \
                        .props('outlined rounded bg-white/70').classes('w-full mb-4')
                
                ui.input('Password', password=True, password_toggle_button=True).bind_value(state, 'password') \
                    .props('outlined rounded bg-white/70').classes('w-full mb-4')

                # --- PILIHAN TIPE AKUN (Hanya di Register) ---
                if state["mode"] == "register":
                    with ui.column().classes('w-full mb-6'):
                        ui.label('Tipe Akun').classes('text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider')
                        with ui.row().classes('w-full gap-2'):
                            def set_role(role: str):
                                state["role"] = role
                                form_kontainer.refresh()
                            
                            # Tombol User
                            user_active = state["role"] == "user"
                            # User btn — aktif: pink solid, tidak aktif: outline abu
                            ui.button(
                                '👤 User',
                                on_click=lambda: set_role('user')
                            ).classes(
                                'flex-1 rounded-xl py-2 text-sm font-bold transition-all '
                                + ('bg-[#A84A62] text-white shadow-md ring-2 ring-[#A84A62] ring-offset-1'
                                   if user_active else
                                   'bg-transparent text-gray-400 border-2 border-gray-200 hover:border-[#A84A62] hover:text-[#A84A62]')
                            ).props('unelevated no-caps')

                            # Admin btn — aktif: biru solid, tidak aktif: outline abu
                            admin_active = state["role"] == "admin"
                            ui.button(
                                '🛡️ Admin',
                                on_click=lambda: set_role('admin')
                            ).classes(
                                'flex-1 rounded-xl py-2 text-sm font-bold transition-all '
                                + ('bg-[#A84A62] text-white shadow-md ring-2 ring-[#A84A62] ring-offset-1'
                                   if admin_active else
                                   'bg-transparent text-gray-400 border-2 border-gray-200 hover:border-[#A84A62] hover:text-[#A84A62]')
                            ).props('unelevated no-caps')

                if state["mode"] == "login":
                    ui.button('Masuk Aplikasi', on_click=proses_login) \
                        .classes('w-full btn-primary text-white rounded-xl py-3 shadow-lg')
                else:
                    ui.button('Daftar & Kirim OTP', on_click=proses_daftar) \
                        .classes('w-full btn-primary text-white rounded-xl py-3 shadow-lg')
                
                # --- DEVELOPER SKIP BUTTONS (2 tombol: User & Admin) ---
                with ui.column().classes('w-full mt-6 border-t border-gray-100 pt-4 gap-2'):
                    ui.label('Developer Shortcut').classes('text-[10px] text-gray-400 uppercase tracking-widest text-center font-bold')
                    with ui.row().classes('w-full gap-2 justify-center'):
                        ui.button('👤 User Skip', on_click=lambda: proses_skip_developer('user')) \
                            .props('flat dense no-caps') \
                            .classes('text-xs text-gray-400 hover:text-[#A84A62] transition-colors px-4 py-1 rounded-lg hover:bg-pink-50') \
                            .tooltip('Masuk sebagai User tanpa login')
                        ui.button('🛡️ Admin Skip', on_click=lambda: proses_skip_developer('admin')) \
                            .props('flat dense no-caps') \
                            .classes('text-xs text-gray-400 hover:text-[#1E88E5] transition-colors px-4 py-1 rounded-lg hover:bg-blue-50') \
                            .tooltip('Masuk sebagai Admin tanpa login')

    # --- LOGIKA AKSI (Stabil & Cepat) ---
    async def proses_login():
        """
        Login → muat SELURUH profil dari DB ke storage → langsung ke Home.
        Tanpa ini, skin_type kosong dan main.py dulu redirect ke onboarding.
        """
        state["is_loading"] = True
        success, message = await AuthManager.login(state["email"], state["password"])

        if success:
            # Muat email asli, username, skin_type, dll dari DB ke storage
            # sehingga halaman profil dan home langsung punya semua data
            try:
                from main import muat_profil_ke_storage
                muat_profil_ke_storage(state["email"])
            except Exception as e:
                print(f"[login] Gagal muat profil dari DB: {e}")
            ui.navigate.to('/')
        else:
            ui.notify(message, color='negative')
        state["is_loading"] = False

    async def proses_skip_developer(role: str = 'user'):
        """Bypass login dan onboarding untuk kebutuhan pengembangan."""
        state["is_loading"] = True
        await asyncio.sleep(0.5) # Efek loading sebentar biar tidak kaget
        
        # Set session variables
        app.storage.user['authenticated'] = True
        app.storage.user['username'] = f'Dev-{"Admin" if role == "admin" else "User"}'
        app.storage.user['email'] = f'dev-{role}@skintify.com'
        app.storage.user['skin_type'] = 'Normal' # Skip onboarding
        app.storage.user['skin_issues'] = ['Kusam']
        app.storage.user['role'] = role
        
        role_label = "Admin 🛡️" if role == "admin" else "User 👤"
        ui.notify(f'Developer Mode: Login sebagai {role_label}', color='info', icon='code')
        ui.navigate.to('/')
        state["is_loading"] = False

    async def proses_daftar():
        if state["mode"] == "register" and not state["username"]:
            ui.notify('Username wajib diisi!', color='warning')
            return
        if not state["email"] or "@" not in state["email"]:
            ui.notify('Masukkan alamat email yang valid!', color='warning')
            return
        if len(state["password"]) < 6:
            ui.notify('Password minimal 6 karakter!', color='warning')
            return
            
        state["is_loading"] = True
        success, message = await AuthManager.kirim_otp_pendaftaran(
            state["email"], state["username"], state["password"], state["role"]
        )
        
        state["is_loading"] = False

        if success:
            ui.notify(message, color='positive')
            state["mode"] = "otp"
            form_kontainer.refresh()
        else:
            ui.notify(message, color='warning')

    async def proses_verifikasi():
        """
        Verifikasi OTP → login otomatis → ke Onboarding (alur DAFTAR).
        Setelah onboarding selesai baru masuk Home.
        Berbeda dengan login biasa yang langsung ke Home.
        """
        state["is_loading"] = True
        success, message = await AuthManager.verifikasi_dan_daftar(state["email"], state["otp"])
        state["is_loading"] = False

        if success:
            ui.notify(message, color='positive')

            # Login otomatis setelah daftar berhasil — tidak perlu input ulang
            app.storage.user['authenticated']     = True
            app.storage.user['email']             = state["email"]
            app.storage.user['username']          = state["username"]
            app.storage.user['skin_type']         = ''   # belum diisi → onboarding
            app.storage.user['avoid_ingredients'] = []
            app.storage.user['skin_issues']       = []
            app.storage.user['city']              = 'Jakarta'
            app.storage.user['role']              = state.get("role", "user")
            app.storage.user['onboarding_mode']   = None  # mode pertama kali

            # ALUR DAFTAR: OTP selesai → Onboarding (bukan Home, bukan form login)
            ui.navigate.to('/onboarding')
        else:
            ui.notify(message, color='negative')

    # Layout Utama Halaman
    with ui.column().classes('w-full h-screen items-center justify-center relative'):
        form_kontainer()