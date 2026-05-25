from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.ui.safe_render import safe_section
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi, Routine, RoutineItem, Produk
from app.services.routine_service import RoutineService
from sqlalchemy import func, desc
import datetime

def show_page():
    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    if 'recent_products' not in state.__dict__:
        state.__dict__['recent_products'] = []

    user_email = app.storage.user.get('email', 'User')
    user_username = app.storage.user.get('username', '')
    user_skin = app.storage.user.get('skin_type', 'Belum diatur')
    user_issues = app.storage.user.get('skin_issues', [])
    user_city = app.storage.user.get('city', 'Jakarta')
    
    # --- DATA FETCHING (OPTIMIZED & SYNCHRONOUS) ---
    from sqlalchemy.orm import joinedload
    with SessionLocal() as session:
        # 1. Fetch user routines with items and products in ONE go
        user_routines = session.query(Routine).options(
            joinedload(Routine.items).joinedload(RoutineItem.product)
        ).filter(Routine.user.has(email=user_email)).all()
        
        # 2. Optimized Best Deals query
        best_deals = []
        with safe_section("Best Deals", show_error=False):
            best_deals = session.query(SociollaReferensi, Produk).join(
                Produk, SociollaReferensi.keyword_digunakan == Produk.keyword
            ).filter(
                Produk.harga < SociollaReferensi.min_price,
                Produk.harga > 0
            ).order_by(
                (SociollaReferensi.min_price - Produk.harga).desc()
            ).limit(3).all()

        # 3. Aggregate all ingredients from all routines efficiently
        all_ingredients = []
        active_ingredients_found = []
        
        # Get all unique keywords first to avoid duplicate processing
        keywords = set()
        for r in user_routines:
            for item in r.items:
                if item.product and item.product.keyword:
                    keywords.add(item.product.keyword)
        
        if keywords:
            refs = session.query(SociollaReferensi).filter(SociollaReferensi.keyword_digunakan.in_(list(keywords))).all()
            for ref in refs:
                if ref.ingredients:
                    all_ingredients.append({"ingredients": ref.ingredients})
                    profile = data_mgr.get_ingredient_profile({"ingredients": ref.ingredients})
                    if profile and profile.get('active_ingredients'):
                        active_ingredients_found.extend(profile['active_ingredients'])
        
        active_ingredients_found = sorted(list(set([ing.capitalize() for ing in active_ingredients_found])))

    # Analisis bahan + cuaca
    # Gap B FIX: Pisahkan weather dari render awal agar halaman langsung tampil.
    # - Jika cache hit (kota sama dalam 30 menit): langsung dapat data, ~0ms
    # - Jika cache miss (pertama kali): render placeholder dulu, fetch di background
    analysis = {}
    _weather_container_ref = {'el': None}  # Referensi untuk update setelah fetch

    def _load_analysis_sync():
        """Jalankan di thread terpisah agar tidak blokir event loop."""
        try:
            return data_mgr.analyze_routine(all_ingredients, kota=user_city)
        except Exception:
            return {}

    # Cek apakah cache sudah ada SEBELUM bikin timer
    from app.services.weather import WeatherService
    _city_key = user_city.lower().strip() if user_city else ''
    _cache_hit = bool(WeatherService._get_cached(_city_key)) if _city_key else False

    if _cache_hit:
        # Cache ada: ambil sinkron, sudah instan
        with safe_section("Analisis Cuaca", show_error=False):
            analysis = _load_analysis_sync()
    # Cache miss: analysis tetap {} untuk sekarang; weather_widget akan di-refresh via timer

    # --- UI LAYOUT ---
    with ui.column().classes('w-full p-6 lg:p-10 gap-10 bg-transparent'):
        
        # 1. PREMIUM HERO SECTION
        with safe_section("Hero Section"):
          with ui.row().classes('w-full gap-8 items-start'):
            # Welcome & Weather Card
            with ui.card().classes('flex-[2.5] p-0 glass-card border-none overflow-hidden relative'):
                # Decorative Background Gradient
                ui.element('div').classes('absolute inset-0 bg-gradient-to-br from-pink-100/40 via-white/10 to-transparent z-0')
                
                with ui.column().classes('relative z-10 p-10 gap-6 w-full'):
                    with ui.column().classes('gap-1'):
                        hour = datetime.datetime.now().hour
                        greeting = "Selamat Pagi" if 5 <= hour < 12 else "Selamat Siang" if 12 <= hour < 17 else "Selamat Malam"
                        ui.label(f'{greeting},').classes('text-lg font-bold text-pink-400 uppercase tracking-[0.2em]')
                        
                        # Formatter nama premium: dev-user -> Dear Dev User
                        raw_name = user_username if user_username else user_email.split("@")[0]
                        formatted_name = " ".join([word.capitalize() for word in raw_name.replace("-", " ").replace("_", " ").split()])
                        
                        ui.label(f'Annyeong haseyo, {formatted_name}!').classes(
                            'text-4xl font-extrabold tracking-tight leading-tight pb-1 text-gray-800'
                        )
                    
                    with ui.row().classes('items-center gap-3 py-2 px-4 bg-white/40 rounded-2xl w-fit border border-white/60'):
                        ui.icon('location_on', size='18px', color='pink-500')
                        ui.label(f'{user_city}, Indonesia').classes('text-sm text-gray-600 font-bold uppercase tracking-wider')

                    # Gap B FIX: Widget cuaca menjadi @ui.refreshable
                    # Jika cache miss, tampilkan skeleton dulu, timer fetch di background
                    @ui.refreshable
                    def weather_widget():
                        _cur_analysis = analysis
                        if _cur_analysis.get('weather'):
                            w = _cur_analysis['weather']


                            # 7-Day Forecast (Wide Swipeable Carousel with Arrows)
                            if w.get('forecast'):
                                with ui.column().classes('w-full gap-2 mt-4'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('calendar_month', size='18px', color='pink-400')
                                        ui.label('Prakiraan Cuaca 7 Hari').classes('text-[11px] font-black text-gray-500 tracking-[0.2em] uppercase')
                                    
                                    # Carousel minimalis dengan tombol navigasi Quasar
                                    with ui.carousel(animated=True, arrows=True, navigation=False).classes('w-full bg-transparent').style('height: 100px;').props('control-color=pink-500 swipeable transition-prev=slide-right transition-next=slide-left') as weather_carousel:
                                        for i, day in enumerate(w['forecast'][:7]):
                                            with ui.carousel_slide().classes('p-0 bg-transparent flex items-center justify-center'):
                                                # Kartu panjang berjejer dengan layout flex horizontal yang sangat bersih
                                                with ui.card().classes('w-full p-4 glass-card-static flex-row items-center justify-between border border-white/60 shadow-sm rounded-2xl gap-2'):
                                                    
                                                    # Kiri: Hari & Tanggal + Keterangan Selisih Hari
                                                    with ui.column().classes('gap-0 shrink-0'):
                                                        ui.label(day['date_label'].split(',')[0]).classes('text-xs font-black text-pink-400 uppercase tracking-widest')
                                                        ui.label(day['date_label'].split(',')[1].strip()).classes('text-[10px] text-gray-500 font-bold')
                                                        
                                                        # Hitung label selisih hari
                                                        if i == 0:
                                                            day_desc = "Hari Ini"
                                                            badge_cls = "bg-pink-100 text-pink-700"
                                                        elif i == 1:
                                                            day_desc = "Besok"
                                                            badge_cls = "bg-purple-100 text-purple-700"
                                                        else:
                                                            day_desc = f"{i} hari lagi"
                                                            badge_cls = "bg-gray-100 text-gray-600"
                                                            
                                                        ui.label(day_desc).classes(f'text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md mt-1 w-fit {badge_cls}')
                                                    
                                                    # Tengah: Ikon & Kondisi
                                                    with ui.row().classes('items-center gap-2'):
                                                        ui.icon(day['icon'], size='28px').classes('text-blue-500')
                                                        ui.label(day['condition']).classes('text-xs font-extrabold text-blue-900 truncate max-w-[100px]')
                                                    
                                                    # Kanan: Suhu & UV (Metric Kritis Skincare)
                                                    with ui.row().classes('items-center gap-3 shrink-0'):
                                                        ui.label(f"{day['temp_min']}° - {day['temp_max']}°C").classes('text-xs font-black text-gray-800')
                                                        
                                                        # UV Badge minimalis
                                                        with ui.row().classes('items-center gap-1 bg-yellow-50 px-2 py-1 rounded-full border border-yellow-100'):
                                                            ui.icon('light_mode', size='10px').classes('text-yellow-600')
                                                            ui.label(f"UV {day['uv_index']}").classes('text-[9px] font-black text-yellow-700')
                        else:
                            # Skeleton placeholder saat data cuaca belum tersedia
                            with ui.row().classes('items-center gap-2 mt-2 opacity-50 animate-pulse'):
                                ui.icon('cloud_sync', size='18px', color='blue-200')
                                ui.label('Memuat data cuaca...').classes('text-[11px] text-gray-400 font-bold italic')

                    weather_widget()  # Render sekarang (data atau skeleton)

                    # Lazy-load timer: jika cache miss, fetch di background 200ms setelah UI muncul
                    if not _cache_hit:
                        async def _lazy_weather_fetch():
                            nonlocal analysis
                            try:
                                from nicegui import run
                                fetched = await run.io_bound(_load_analysis_sync)
                                analysis = fetched
                                weather_widget.refresh()
                            except Exception:
                                pass  # Gagal silent; skeleton tetap tampil
                        ui.timer(0.2, _lazy_weather_fetch, once=True)


            
            # Skin Health Overview Card
            with ui.column().classes('flex-1 gap-6'):
                @ui.refreshable
                def routine_progress():
                    checked_items = app.storage.user.get('checked_items', {})
                    today_key = datetime.datetime.now().strftime('%Y-%m-%d')
                    total_items = sum(len(r.items) for r in user_routines) if user_routines else 0
                    completed = sum(1 for r in user_routines for item in r.items 
                                if checked_items.get(f"{today_key}_{item.id}", False))
                    pct = int((completed / total_items) * 100) if total_items > 0 else 0
                        
                    with ui.card().classes('w-full p-8 glass-card border-none items-center justify-center relative overflow-hidden'):
                        ui.element('div').classes('absolute w-48 h-48 bg-pink-100/30 rounded-full -bottom-10 -right-10 z-0')
                        with ui.column().classes('relative z-10 items-center gap-3 w-full'):
                            ui.label("Progres Rutinitas Hari Ini").classes('text-sm font-semibold text-gray-500')
                            ui.label(f'{completed}/{total_items}').classes('text-6xl font-black text-transparent bg-clip-text bg-gradient-to-br from-pink-500 to-purple-600 my-2')
                            ui.label('Completed').classes('text-xs font-bold text-gray-400')
                            with ui.element('div').classes('w-full h-3 bg-gray-100 rounded-full overflow-hidden mt-2'):
                                ui.element('div').style(f'width: {pct}%').classes('h-full bg-gradient-to-r from-pink-400 to-purple-500 rounded-full')
                            status = "Belum Mulai" if pct == 0 else "Sedang Berjalan" if pct < 100 else "Selesai! 🎉"
                            status_color = 'bg-green-100 text-green-700' if pct == 100 else 'bg-pink-100 text-pink-700'
                            ui.label(status).classes(f'mt-2 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest {status_color}')
                routine_progress()



                with ui.card().classes('w-full p-6 glass-card-pink text-white items-center flex-row gap-5'):
                    with ui.element('div').classes('p-3 bg-white/20 rounded-2xl'):
                        ui.icon('face', color='white', size='32px')
                    with ui.column().classes('gap-0'):
                        ui.label('Skin Type Focus').classes('text-[10px] text-pink-100 font-bold uppercase tracking-widest')
                        ui.label(user_skin).classes('text-lg font-black text-white')

                # SMART ADVICE (Daily Tips) ditaruh di bawah Skin Type Focus sesuai permintaan user
                if analysis.get('suggestions'):
                    with ui.card().classes('w-full p-5 glass-card-blue text-white relative overflow-hidden'):
                        ui.icon('spa', size='100px', color='white').classes('absolute -right-10 -bottom-10 opacity-10 rotate-12')
                        ui.label('💡 DAILY TIPS').classes('text-[10px] font-black text-blue-100 tracking-[0.2em] mb-2')
                        with ui.carousel(animated=True, arrows=False, navigation=False).classes('bg-transparent w-full').props('autoplay=4000 height=54px'):
                            for s in analysis['suggestions']:
                                with ui.carousel_slide().classes('bg-transparent p-0 flex items-center justify-start'):
                                    with ui.row().classes('items-start gap-2.5 w-full no-wrap'):
                                        ui.label('•').classes('text-white font-black text-base leading-none shrink-0')
                                        ui.label(s).classes('text-xs font-bold text-white leading-normal line-clamp-2')

        # 2. ANALYSIS ALERTS (Immersive Warning)
        with safe_section("Peringatan Rutinitas", show_error=False):
          if analysis.get('warnings'):
            with ui.card().classes('w-full p-8 bg-amber-50/80 border-amber-100/50 rounded-[2.5rem] overflow-hidden relative shadow-sm'):
                ui.element('div').classes('absolute top-0 left-0 w-2 h-full bg-amber-400')
                with ui.row().classes('items-center gap-4 mb-4'):
                    with ui.element('div').classes('p-2 bg-amber-100 rounded-xl'):
                        ui.icon('lightbulb', color='amber-600', size='24px')
                    ui.label('Catatan Penting untuk Kulitmu').classes('font-bold text-amber-900 text-base')

                with ui.grid(columns='1 md:2').classes('w-full gap-4'):
                    for w in analysis['warnings']:
                        with ui.row().classes('items-start gap-3 p-3 bg-white/60 rounded-2xl border border-amber-100/50 shadow-sm'):
                            ui.label('💡').classes('text-lg')
                            ui.label(w).classes('text-sm text-amber-800 font-medium leading-relaxed')

        # 3. MAIN DASHBOARD CONTENT
        with safe_section("Dashboard Utama"):
          with ui.row().classes('w-full gap-10 items-stretch'):
            
            # LEFT COLUMN: Routine & Ingredients
            with ui.column().classes('flex-[2] gap-8'):
                
                # DAILY CHECKLIST
                with ui.column().classes('w-full gap-4'):
                    ui.label('Jadwal Skincare Kamu Hari Ini').classes('text-lg font-bold text-gray-700')

                    if not user_routines:
                        with ui.card().classes('w-full p-16 items-center justify-center border-dashed border-2 border-pink-100 bg-white/20 rounded-[3rem]'):
                            ui.icon('add_task', size='64px', color='pink-100')
                            ui.label('Your routine is empty').classes('text-gray-400 mt-4 font-bold text-lg')
                            ui.button('Create First Routine', on_click=lambda: ui.navigate.to('/routine')).classes('btn-primary mt-4 px-8 py-3 rounded-2xl')
                    else:
                        DAYS_MAP = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
                        today = DAYS_MAP[datetime.datetime.now().weekday()]
                        
                        morning_routine = next((r for r in user_routines if 'morning' in r.name.lower() or 'pagi' in r.name.lower()), None)
                        night_routine = next((r for r in user_routines if today.lower() in r.name.lower() and ('night' in r.name.lower() or 'malam' in r.name.lower())), None)
                        
                        today_routines = [r for r in [morning_routine, night_routine] if r]
                        if not today_routines:
                            today_routines = user_routines[:2]

                        with ui.row().classes('w-full gap-6'):
                            for r in today_routines:
                                is_morning = 'morning' in r.name.lower() or 'pagi' in r.name.lower()
                                header_color = 'from-blue-400 to-blue-600' if is_morning else 'from-blue-600 to-blue-800'
                                
                                with ui.card().classes('flex-1 p-0 glass-card border-none shadow-xl rounded-[2.5rem] overflow-hidden'):
                                    # Header
                                    with ui.row().classes(f'w-full p-6 bg-gradient-to-br {header_color} text-white items-center justify-between'):
                                        with ui.row().classes('items-center gap-4'):
                                            with ui.element('div').classes('p-2 bg-white/20 rounded-xl backdrop-blur-md'):
                                                ui.icon('wb_sunny' if is_morning else 'dark_mode', size='24px')
                                            with ui.column().classes('gap-0'):
                                                ui.label(r.name).classes('font-black text-base')
                                                ui.label(f'{len(r.items)} Steps').classes('text-[10px] font-bold opacity-80 uppercase')
                                    
                                    # Items
                                    with ui.column().classes('p-6 w-full gap-4 bg-white/20'):
                                        checked_items = app.storage.user.get('checked_items', {})
                                        today_key = datetime.datetime.now().strftime('%Y-%m-%d')
                                        for item in r.items[:4]:
                                            item_key = f"{today_key}_{item.id}"
                                            is_checked = checked_items.get(item_key, False)
                                            
                                            def on_check(e, key=item_key):
                                                data = app.storage.user.get('checked_items', {})
                                                data[key] = e.value
                                                app.storage.user['checked_items'] = data
                                                routine_progress.refresh()
                                            
                                            with ui.row().classes('w-full items-center justify-between group'):
                                                with ui.row().classes('items-center gap-4'):
                                                    ui.checkbox(value=is_checked, on_change=on_check).props('color=pink keep-color').classes('scale-110')
                                                    prod_name = item.product.nama if item.product else item.custom_name
                                                    ui.label(prod_name).classes('text-xs font-bold text-gray-700 line-clamp-1 w-full max-w-[200px]')
                                        
                                        if len(r.items) > 4:
                                            ui.label(f'View {len(r.items)-4} more steps...').classes('text-[10px] text-pink-400 font-bold italic ml-14 cursor-pointer')
                                        
                                        ui.button('Manage Routine', on_click=lambda: ui.navigate.to('/routine')).props('flat size=sm icon=settings').classes('w-full mt-4 text-gray-400 font-bold uppercase tracking-widest')

                # INGREDIENT SPOTLIGHT
                if active_ingredients_found:
                    with ui.column().classes('w-full gap-4'):
                        ui.label('Fokus Bahan Aktifmu').classes('text-lg font-bold text-gray-700')
                        with ui.card().classes('w-full p-8 glass-card border-none bg-gradient-to-br from-blue-50/50 to-white/50'):
                            with ui.row().classes('gap-3 flex-wrap'):
                                for ing in active_ingredients_found:
                                    with ui.row().classes('items-center gap-2 px-4 py-2 bg-white rounded-2xl border border-blue-100 shadow-sm hover:shadow-md transition-all'):
                                        ui.element('div').classes('w-2 h-2 rounded-full bg-blue-400')
                                        ui.label(ing).classes('text-xs font-black text-blue-700')

            # RIGHT COLUMN: Insights & Deals
            with ui.column().classes('flex-1 gap-8'):
                
                # MARKETPLACE DEALS
                with ui.column().classes('w-full gap-4'):
                    ui.label('Rekomendasi Hemat Khusus Untukmu').classes('text-lg font-bold text-gray-700')
                    with ui.card().classes('w-full p-8 glass-card border-none'):
                        if not best_deals:
                            with ui.column().classes('items-center gap-2 py-4 w-full'):
                                ui.icon('savings', size='40px', color='gray-200')
                                ui.label('No deals found yet').classes('text-xs text-gray-400 font-bold')
                        else:
                            for sociolla_ref, marketplace_prod in best_deals:
                                with ui.row().classes('w-full items-center justify-between p-4 mb-3 bg-white/40 rounded-3xl border border-white/60 hover:bg-white/60 transition-all cursor-pointer'):
                                    with ui.column().classes('gap-1 flex-1'):
                                        ui.label(sociolla_ref.product_name).classes('text-[11px] font-black text-gray-800 line-clamp-1')
                                        ui.badge(marketplace_prod.platform.upper(), color='green-500').classes('text-[8px] font-black px-2 py-0.5 rounded-lg')
                                    
                                    with ui.column().classes('items-end gap-0'):
                                        diff = int(sociolla_ref.min_price - marketplace_prod.harga)
                                        ui.label(f'SAVE Rp{int(diff/1000)}k').classes('text-[9px] font-black text-green-600 uppercase tracking-wider')
                                        ui.label(f'Rp{int(marketplace_prod.harga/1000)}k').classes('text-sm font-black text-gray-900')

        # 4. RECENTLY VIEWED (Elegant Horizontal Scroll)
        with safe_section("Riwayat Produk Dilihat", show_error=False):
          with ui.column().classes('w-full gap-6 mt-6'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('Terakhir Kamu Lihat').classes('text-lg font-bold text-gray-700')
                ui.button('View Catalog', on_click=lambda: ui.navigate.to('/search')).props('flat size=sm icon=arrow_forward').classes('text-pink-500 font-black uppercase tracking-widest')
                
            recent_products = state.__dict__.get('recent_products', [])
            if recent_products:
                with ui.scroll_area().classes('w-full h-44'):
                    with ui.row().classes('gap-6 no-wrap pb-4'):
                        for p in recent_products[:10]:
                            with ui.card().classes('w-72 p-4 flex-row items-center gap-4 glass-card border-none transition-all cursor-pointer') \
                                .on('click', lambda p=p: (state.__dict__.update({'selected_product': p}), ui.navigate.to('/search'))):
                                
                                with ui.element('div').classes('w-20 h-20 rounded-2xl bg-white p-2 overflow-hidden flex items-center justify-center shrink-0 border border-gray-100'):
                                    if p.get('image_url') and str(p.get('image_url')).startswith('http'):
                                        ui.image(p['image_url']).classes('w-full h-full object-contain')
                                    else:
                                        ui.icon('category', size='24px', color='pink-100')
                                
                                with ui.column().classes('gap-1 flex-1'):
                                    ui.label(p.get('brand', 'Unknown')).classes('text-[9px] text-pink-400 font-black uppercase tracking-widest')
                                    ui.label(p.get('product_name', '-')).classes('text-xs font-black text-gray-800 line-clamp-2 leading-tight')
                                    ui.label(f"Rp{int((p.get('min_price') or 0)/1000)}k").classes('text-sm font-black text-pink-500 mt-1')
            else:
                with ui.card().classes('w-full p-12 glass-card items-center justify-center border-none'):
                    ui.label('Start exploring products to see them here.').classes('text-xs text-gray-400 font-bold italic')




