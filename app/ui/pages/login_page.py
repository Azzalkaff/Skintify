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
        with ui.column().classes('w-[400px] glass-panel rounded-[2rem] p-10 z-10 items-center shadow-2xl border border-white/40 relative overflow-hidden'):
            
            # Icon & Judul
            ui.icon('auto_awesome', size='48px').style('color: var(--primary);').classes('mb-2')
            ui.label('Skintify').classes('text-3xl font-black text-[#A84A62] tracking-tight')
            
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
                    .props('outlined rounded bg-white/70').classes('w-full mb-6')

                if state["mode"] == "login":
                    ui.button('Masuk Aplikasi', on_click=proses_login) \
                        .classes('w-full btn-primary text-white rounded-xl py-3 shadow-lg')
                else:
                    ui.button('Daftar & Kirim OTP', on_click=proses_daftar) \
                        .classes('w-full btn-primary text-white rounded-xl py-3 shadow-lg')
                
                # --- DEVELOPER SKIP BUTTON ---
                with ui.row().classes('w-full mt-6 items-center justify-center border-t border-gray-100 pt-4'):
                    ui.button('Developer Skip (No Login/Onboard)', on_click=proses_skip_developer) \
                        .props('flat dense') \
                        .classes('text-xs text-gray-400 hover:text-[#A84A62] transition-colors') \
                        .tooltip('Klik untuk masuk tanpa login (Khusus Developer)')

    # --- LOGIKA AKSI (Stabil & Cepat) ---
    async def proses_login():
        state["is_loading"] = True
        success, message = await AuthManager.login(state["email"], state["password"])
        
        if success:
            ui.navigate.to('/')
        else:
            ui.notify(message, color='negative')
        state["is_loading"] = False

    async def proses_skip_developer():
        """Bypass login dan onboarding untuk kebutuhan pengembangan."""
        state["is_loading"] = True
        await asyncio.sleep(0.5) # Efek loading sebentar biar tidak kaget
        
        # Set session variables
        app.storage.user['authenticated'] = True
        app.storage.user['username'] = 'Developer'
        app.storage.user['email'] = 'dev@skintify.com'
        app.storage.user['skin_type'] = 'Normal' # Skip onboarding
        app.storage.user['skin_issues'] = ['Kusam']
        
        ui.notify('Developer Mode: Login & Onboarding bypassed!', color='info', icon='code')
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
        success, message = await AuthManager.kirim_otp_pendaftaran(state["email"], state["username"], state["password"])
        
        state["is_loading"] = False

        if success:
            ui.notify(message, color='positive')
            state["mode"] = "otp"
            form_kontainer.refresh()
        else:
            ui.notify(message, color='warning')

    async def proses_verifikasi():
        state["is_loading"] = True
        success, message = await AuthManager.verifikasi_dan_daftar(state["email"], state["otp"])
        
        state["is_loading"] = False
        
        if success:
            ui.notify(message, color='positive')
            state["mode"] = "login"
            state["password"] = "" 
            form_kontainer.refresh()
        else:
            ui.notify(message, color='negative')

    # Layout Utama Halaman
    with ui.column().classes('w-full h-screen items-center justify-center relative bg-[#F9F5F6]'):
        form_kontainer()