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

    # --- UI LAYOUT (RESTRUCTURED FOR HIGH LEVERAGE) ---
    with ui.column().classes('w-full p-6 lg:p-10 gap-8 bg-transparent max-w-[1200px] mx-auto'):
        
        # 1. SEARCH BAR BESAR (SMART PROBLEM SOLVER)
        with safe_section("Search & Compare Section"):
            with ui.card().classes('w-full p-8 glass-card border-none flex flex-col gap-5 shadow-lg rounded-[2.5rem] overflow-hidden relative bg-white/40'):
                # Decorative background glow
                ui.element('div').classes('absolute -right-20 -top-20 w-64 h-64 bg-pink-100/30 rounded-full blur-3xl z-0')
                ui.element('div').classes('absolute -left-20 -bottom-20 w-64 h-64 bg-blue-100/30 rounded-full blur-3xl z-0')
                
                with ui.column().classes('w-full relative z-10 gap-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('psychology_alt', size='28px', color='pink-500')
                        ui.label('Apa masalah kulitmu hari ini?').classes('text-2xl font-black text-gray-800 tracking-tight')
                    
                    with ui.row().classes('w-full items-center gap-4 no-wrap'):
                        search_input = ui.input(
                            placeholder='Misal: Jerawat meradang, kusam, atau nama produk...'
                        ).classes('flex-grow bg-white/80 rounded-2xl px-6 py-2 border border-pink-100/80 text-base shadow-inner transition-all focus:border-pink-300 focus:bg-white').props('borderless dense clearable')
                        
                        with search_input.add_slot('prepend'):
                            ui.icon('search', color='pink-500').classes('text-xl pl-2')
                        
                        def go_search(query=None):
                            import time
                            print(f"[TRACE-BOTTLENECK] {time.time()} - home_page: go_search started")
                            q = query if query is not None else search_input.value or ''
                            if q.strip():
                                app.storage.user['ai_initial_query'] = q.strip()
                                print(f"[TRACE-BOTTLENECK] {time.time()} - home_page: navigating to /chat")
                                UIComponents.safe_navigate('/chat')
                            else:
                                ui.notify('Harap masukkan pertanyaan atau keluhan!', color='warning')
                        
                        search_input.on('keydown.enter', lambda: go_search())
                        
                        # The real Elevate feature: Scan Barcode
                        ui.button(
                            on_click=lambda: ui.notify('Fitur Kamera/Barcode segera hadir!', color='info')
                        ).classes('bg-white text-blue-500 rounded-2xl py-3 px-4 shadow-sm hover:scale-[1.05] transition-all shrink-0 border border-blue-100').props('icon=qr_code_scanner outline')

                        ui.button(
                            'Temukan Solusi', 
                            on_click=lambda: go_search()
                        ).classes('bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-2xl font-bold py-3 px-8 shadow-md hover:scale-[1.02] transition-all shrink-0').props('no-caps icon=auto_awesome')

                    # 1-Click Contextual Filters (Zero-Typing)
                    with ui.row().classes('w-full gap-3 items-center flex-wrap pt-2'):
                        ui.label('Pencarian Instan:').classes('text-xs text-gray-400 font-bold uppercase tracking-widest mr-1')
                        
                        chips = [
                            ('Jerawat Meradang', 'local_hospital', 'pink'),
                            ('Skin Barrier', 'healing', 'blue'),
                            ('Kulit Kusam', 'flare', 'pink'),
                            ('Diskon Spesial', 'sell', 'blue')
                        ]
                        
                        for label, icon, color in chips:
                            ui.button(
                                label, 
                                on_click=lambda l=label: (
                                    app.storage.user.__setitem__('ai_initial_query', l),
                                    UIComponents.safe_navigate('/chat')
                                )
                            ).classes(f'bg-{color}-50 text-{color}-600 border border-{color}-100 rounded-xl px-4 py-1.5 font-bold text-xs hover:bg-{color}-100 hover:shadow-sm transition-all').props(f'icon={icon} size=sm outline no-caps')

        # 2. WISHLIST ALERTS & ROUTINE SUMMARY
        with safe_section("Actionable Dashboard"):
            with ui.row().classes('w-full gap-6 items-stretch'):
                
                # WISHLIST ALERT (Harga Turun)
                with ui.card().classes('flex-[3] p-8 glass-card border-none shadow-sm rounded-[2.5rem] bg-white/40 hover:bg-white/60 transition-all'):
                    with ui.row().classes('w-full items-center justify-between mb-6'):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes('p-2.5 bg-pink-100 rounded-xl'):
                                ui.icon('savings', color='pink-600', size='24px')
                            ui.label('Wishlist Alert').classes('font-black text-gray-800 text-xl tracking-tight')
                        if best_deals:
                            ui.label(f'{len(best_deals)} Produk Turun Harga').classes('text-[11px] font-black uppercase tracking-widest bg-pink-100 text-pink-700 px-3 py-1.5 rounded-lg')
                    
                    if not best_deals:
                        ui.label('Belum ada diskon signifikan untuk produk incaranmu hari ini.').classes('text-sm text-gray-500 font-medium')
                    else:
                        with ui.column().classes('w-full gap-4'):
                            for sociolla_ref, marketplace_prod in best_deals[:2]:
                                plat_name = marketplace_prod.platform.capitalize()
                                with ui.row().classes('w-full items-center justify-between py-3 px-4 bg-white/70 rounded-2xl border border-pink-50 shadow-sm'):
                                    with ui.row().classes('items-center gap-4 flex-1'):
                                        if sociolla_ref.image_url:
                                            ui.image(sociolla_ref.image_url).classes('w-12 h-12 object-contain rounded-xl bg-white p-1 border border-gray-100')
                                        else:
                                            ui.icon('inventory', size='32px', color='gray-300').classes('w-12 h-12 flex items-center justify-center bg-gray-50 rounded-xl')
                                            
                                        with ui.column().classes('gap-0'):
                                            ui.label(sociolla_ref.product_name).classes('text-sm font-bold text-gray-800 line-clamp-1 max-w-[200px]')
                                            with ui.row().classes('items-center gap-2 mt-0.5'):
                                                ui.label(f'Rp{int(sociolla_ref.min_price/1000)}k').classes('text-[10px] text-gray-400 line-through font-semibold')
                                                ui.icon('arrow_forward', size='10px', color='pink-500')
                                                ui.label(f'Rp{int(marketplace_prod.harga/1000)}k').classes('text-xs font-black text-pink-600')
                                    
                                    ui.button(f'Beli di {plat_name}', on_click=lambda p=sociolla_ref: (
                                        state.__dict__.update({'selected_product': {
                                            'slug': p.slug, 'product_name': p.product_name, 'min_price': p.min_price, 
                                            'brand': p.brand, 'image_url': p.image_url, 'url': p.url_sociolla, 
                                            'ingredients': p.ingredients, 'rating': p.rating_sociolla
                                        }}),
                                        ui.navigate.to('/search')
                                    )).props('rounded size=sm color=pink').classes('font-bold shadow-md')
                        
                        ui.button('Cari Lebih Banyak Diskon →', on_click=lambda: ui.navigate.to('/search')).props('flat no-caps color=blue').classes('w-full mt-2 font-bold')

                # ROUTINE ACTION (Contextual)
                with ui.card().classes('flex-[2] p-8 glass-card border-none shadow-sm rounded-[2.5rem] bg-white/40 hover:bg-white/60 transition-all flex flex-col justify-between'):
                    hour = datetime.datetime.now().hour
                    is_morning = 5 <= hour < 15
                    routine_type = "Morning" if is_morning else "Night"
                    icon_name = "wb_sunny" if is_morning else "dark_mode"
                    icon_color = "pink-500" if is_morning else "blue-500"
                    bg_icon = "pink-100" if is_morning else "blue-100"
                    
                    target_routine = None
                    for r in user_routines:
                        if is_morning and ('morning' in r.name.lower() or 'pagi' in r.name.lower()):
                            target_routine = r
                            break
                        elif not is_morning and ('night' in r.name.lower() or 'malam' in r.name.lower()):
                            target_routine = r
                            break
                    if not target_routine and user_routines:
                        target_routine = user_routines[0]

                    with ui.row().classes('w-full items-center gap-3 mb-6'):
                        with ui.element('div').classes(f'p-2.5 {bg_icon} rounded-xl'):
                            ui.icon(icon_name, color=icon_color, size='24px')
                        ui.label(f'{routine_type} Routine').classes('font-black text-gray-800 text-xl tracking-tight')

                    if not target_routine:
                        with ui.column().classes('gap-1 mb-6'):
                            ui.label('Kamu belum mengatur rutinitas.').classes('text-sm text-gray-500 font-medium')
                        ui.button('Atur Sekarang →', on_click=lambda: ui.navigate.to('/routine')).props('flat no-caps color=blue').classes('w-full mt-auto font-bold')
                    else:
                        checked_items = app.storage.user.get('checked_items', {})
                        today_key = datetime.datetime.now().strftime('%Y-%m-%d')
                        total_steps = len(target_routine.items)
                        completed_steps = sum(1 for item in target_routine.items if checked_items.get(f"{today_key}_{item.id}"))
                        remaining = total_steps - completed_steps
                        
                        if remaining > 0:
                            with ui.column().classes('gap-1 mb-6'):
                                ui.label(f'{remaining} Langkah Tersisa').classes('text-3xl font-black text-gray-800 leading-none tracking-tighter')
                                ui.label('Selesaikan rutinitasmu untuk hari ini.').classes('text-xs text-gray-500 font-bold mt-1')
                        else:
                            with ui.column().classes('gap-1 mb-6'):
                                ui.label('Selesai!').classes('text-3xl font-black text-blue-600 leading-none tracking-tighter')
                                ui.label('Kulitmu berterima kasih.').classes('text-xs text-gray-500 font-bold mt-1')
                            
                        ui.button('Mulai Sekarang →' if remaining > 0 else 'Lihat Routine', on_click=lambda: ui.navigate.to('/routine')).classes('w-full bg-gray-900 text-white font-bold py-3 rounded-2xl shadow-lg hover:scale-[1.02] transition-all mt-auto').props('no-caps')

        # 3. SHORTCUT KATEGORI (Actionable Navigation)
        with safe_section("Category Shortcuts"):
            with ui.row().classes('w-full gap-4'):
                categories = [
                    ('Serum', 'water_drop', 'bg-blue-50 text-blue-600 border-blue-100 hover:bg-blue-100'),
                    ('Moisturizer', 'spa', 'bg-pink-50 text-pink-600 border-pink-100 hover:bg-pink-100'),
                    ('Sunscreen', 'wb_sunny', 'bg-blue-50 text-blue-600 border-blue-100 hover:bg-blue-100'),
                    ('Toner', 'waves', 'bg-pink-50 text-pink-600 border-pink-100 hover:bg-pink-100')
                ]
                for cat, icon, color_cls in categories:
                    def go_to_cat(c=cat):
                        state.category = c
                        ui.navigate.to('/search')
                    
                    with ui.card().classes(f'flex-1 p-6 border rounded-[2rem] cursor-pointer transition-all shadow-sm {color_cls} items-center justify-center hover:scale-[1.03] hover:shadow-md group') \
                        .on('click', lambda c=cat: go_to_cat(c)):
                        ui.icon(icon, size='32px').classes('mb-2 group-hover:scale-110 transition-transform')
                        ui.label(cat).classes('text-sm font-black uppercase tracking-widest')
