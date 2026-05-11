from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
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
        analysis = data_mgr.analyze_routine(all_ingredients, kota=user_city)

    # --- UI LAYOUT ---
    with ui.column().classes('w-full p-6 lg:p-10 gap-10 bg-transparent'):
        
        # 1. PREMIUM HERO SECTION
        with ui.row().classes('w-full gap-8 items-stretch'):
            # Welcome & Weather Card
            with ui.card().classes('flex-[2.5] p-0 glass-card border-none overflow-hidden relative'):
                # Decorative Background Gradient
                ui.element('div').classes('absolute inset-0 bg-gradient-to-br from-pink-100/40 via-white/10 to-transparent z-0')
                
                with ui.column().classes('relative z-10 p-10 gap-6 w-full'):
                    with ui.column().classes('gap-1'):
                        hour = datetime.datetime.now().hour
                        greeting = "Selamat Pagi" if 5 <= hour < 12 else "Selamat Siang" if 12 <= hour < 17 else "Selamat Malam"
                        ui.label(f'{greeting},').classes('text-lg font-bold text-pink-400 uppercase tracking-[0.2em]')
                        ui.label(f'{user_email.split("@")[0]}! ✨').classes('text-5xl font-black text-gray-800 tracking-tight leading-tight')
                    
                    with ui.row().classes('items-center gap-3 py-2 px-4 bg-white/40 rounded-2xl w-fit border border-white/60'):
                        ui.icon('location_on', size='18px', color='pink-500')
                        ui.label(f'{user_city}, Indonesia').classes('text-sm text-gray-600 font-bold uppercase tracking-wider')
                    
                    if analysis.get('weather'):
                        w = analysis['weather']
                        with ui.row().classes('w-full gap-8 mt-4'):
                            # Weather Widget Items
                            weather_items = [
                                ('thermostat', f"{w.get('temp', '--')}°C", 'Temperature', 'text-orange-500', 'bg-orange-50'),
                                ('water_drop', f"{w.get('humidity', '--')}%", 'Humidity', 'text-blue-500', 'bg-blue-50'),
                                ('light_mode', str(w.get('uv_index', '--')), 'UV Index', 'text-yellow-600', 'bg-yellow-50'),
                                ('cloud', w.get('condition', 'Unknown'), 'Condition', 'text-teal-600', 'bg-teal-50')
                            ]
                            for icon, val, label, color_cls, bg_cls in weather_items:
                                with ui.column().classes(f'items-center {bg_cls}/60 p-4 rounded-[2rem] min-w-[110px] border border-white/50 backdrop-blur-md'):
                                    ui.icon(icon, size='24px').classes(color_cls)
                                    ui.label(val).classes(f'text-xl font-black {color_cls} mt-1')
                                    ui.label(label).classes('text-[9px] text-gray-400 font-black uppercase tracking-widest')
            
            # Skin Health Overview Card
            with ui.column().classes('flex-1 gap-6'):
                with ui.card().classes('w-full p-8 glass-card border-none items-center justify-center relative overflow-hidden'):
                    # Background pulse effect
                    ui.element('div').classes('absolute w-48 h-48 bg-pink-100/30 rounded-full -bottom-10 -right-10 z-0')
                    
                    with ui.column().classes('relative z-10 items-center gap-1'):
                        ui.label('SKIN HEALTH INDEX').classes('text-[10px] font-black text-gray-400 tracking-[0.2em] mb-4')
                        
                        # Circular Progress Simulation
                        score = 60 + (len(user_routines) * 10) if user_routines else 50
                        score = min(score, 98)
                        
                        with ui.element('div').classes('relative flex items-center justify-center'):
                            # Using a simple label for now, but styled to look like a gauge center
                            ui.label(str(score)).classes('text-7xl font-black text-transparent bg-clip-text bg-gradient-to-br from-pink-500 to-purple-600 my-2')
                            ui.label('/100').classes('text-xs font-bold text-gray-300 absolute -bottom-2')
                        
                        status = "Mulai Terawat" if score < 70 else "Sehat" if score < 90 else "Glowing!"
                        status_color = 'bg-green-100 text-green-700' if score >= 70 else 'bg-orange-100 text-orange-700'
                        ui.label(status).classes(f'mt-4 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest {status_color}')

                with ui.card().classes('w-full p-6 glass-card bg-gray-900/90 text-white border-none items-center flex-row gap-5'):
                    with ui.element('div').classes('p-3 bg-white/10 rounded-2xl'):
                        ui.icon('face_retouching_natural', color='pink-300', size='32px')
                    with ui.column().classes('gap-0'):
                        ui.label('Skin Type Focus').classes('text-[10px] text-gray-400 font-bold uppercase tracking-widest')
                        ui.label(user_skin).classes('text-lg font-black text-pink-100')

        # 2. ANALYSIS ALERTS (Immersive Warning)
        if analysis.get('warnings'):
            with ui.card().classes('w-full p-8 glass-card bg-red-50/50 border-red-100/50 rounded-[2.5rem] overflow-hidden relative'):
                ui.element('div').classes('absolute top-0 left-0 w-2 h-full bg-red-500')
                with ui.row().classes('items-center gap-4 mb-4'):
                    with ui.element('div').classes('p-2 bg-red-100 rounded-xl'):
                        ui.icon('report_problem', color='red-600', size='24px').classes('animate-pulse')
                    ui.label('CRITICAL ROUTINE INSIGHTS').classes('font-black text-red-800 text-sm tracking-[0.15em]')
                
                with ui.grid(columns='1 md:2').classes('w-full gap-4'):
                    for w in analysis['warnings']:
                        with ui.row().classes('items-start gap-3 p-3 bg-white/40 rounded-2xl border border-red-100/50'):
                            ui.label('⚠️').classes('text-lg')
                            ui.label(w).classes('text-xs text-red-700 font-bold leading-relaxed')

        # 3. MAIN DASHBOARD CONTENT
        with ui.row().classes('w-full gap-10 items-stretch'):
            
            # LEFT COLUMN: Routine & Ingredients
            with ui.column().classes('flex-[2] gap-8'):
                
                # DAILY CHECKLIST
                with ui.column().classes('w-full gap-4'):
                    ui.label('TODAY\'S PERFORMANCE').classes('text-[11px] font-black text-gray-400 tracking-[0.2em]')
                    
                    if not user_routines:
                        with ui.card().classes('w-full p-16 items-center justify-center border-dashed border-2 border-pink-100 bg-white/20 rounded-[3rem]'):
                            ui.icon('add_task', size='64px', color='pink-100')
                            ui.label('Your routine is empty').classes('text-gray-400 mt-4 font-bold text-lg')
                            ui.button('Create First Routine', on_click=lambda: ui.navigate.to('/routine')).classes('btn-primary mt-4 px-8 py-3 rounded-2xl')
                    else:
                        with ui.row().classes('w-full gap-6'):
                            for r in user_routines[:2]: 
                                is_morning = 'morning' in r.name.lower() or 'pagi' in r.name.lower()
                                header_color = 'from-orange-400 to-amber-500' if is_morning else 'from-indigo-600 to-purple-700'
                                
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
                                        for item in r.items[:4]:
                                            with ui.row().classes('w-full items-center justify-between group'):
                                                with ui.row().classes('items-center gap-4'):
                                                    ui.checkbox().props('color=pink keep-color').classes('scale-110')
                                                    prod_name = item.product.nama if item.product else item.custom_name
                                                    ui.label(prod_name).classes('text-xs font-bold text-gray-700 line-clamp-1 w-full max-w-[200px]')
                                        
                                        if len(r.items) > 4:
                                            ui.label(f'View {len(r.items)-4} more steps...').classes('text-[10px] text-pink-400 font-bold italic ml-14 cursor-pointer')
                                        
                                        ui.button('Manage Routine', on_click=lambda: ui.navigate.to('/routine')).props('flat size=sm icon=settings').classes('w-full mt-4 text-gray-400 font-bold uppercase tracking-widest')

                # INGREDIENT SPOTLIGHT
                if active_ingredients_found:
                    with ui.column().classes('w-full gap-4'):
                        ui.label('ACTIVE INGREDIENT SPOTLIGHT').classes('text-[11px] font-black text-gray-400 tracking-[0.2em]')
                        with ui.card().classes('w-full p-8 glass-card border-none bg-gradient-to-br from-indigo-50/50 to-white/50'):
                            with ui.row().classes('gap-3 flex-wrap'):
                                for ing in active_ingredients_found:
                                    with ui.row().classes('items-center gap-2 px-4 py-2 bg-white rounded-2xl border border-indigo-100 shadow-sm hover:shadow-md transition-all'):
                                        ui.element('div').classes('w-2 h-2 rounded-full bg-indigo-400')
                                        ui.label(ing).classes('text-xs font-black text-indigo-700')

            # RIGHT COLUMN: Insights & Deals
            with ui.column().classes('flex-1 gap-8'):
                
                # SMART ADVICE
                ui.label('AI SMART ADVICE').classes('text-[11px] font-black text-gray-400 tracking-[0.2em]')
                
                if analysis.get('suggestions'):
                    with ui.card().classes('w-full p-8 glass-card bg-indigo-600 text-white border-none shadow-2xl relative overflow-hidden'):
                        ui.icon('auto_awesome', size='120px', color='white').classes('absolute -right-10 -bottom-10 opacity-10 rotate-12')
                        ui.label('💡 DAILY TIPS').classes('text-[10px] font-black text-indigo-200 tracking-[0.2em] mb-4')
                        for s in analysis['suggestions']:
                            with ui.row().classes('items-start gap-3 mb-4'):
                                ui.label('•').classes('text-indigo-300 font-black text-xl')
                                ui.label(s).classes('text-sm font-bold leading-relaxed')
                
                # MARKETPLACE DEALS
                with ui.column().classes('w-full gap-4'):
                    ui.label('MARKETPLACE SAVINGS').classes('text-[11px] font-black text-gray-400 tracking-[0.2em]')
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
        with ui.column().classes('w-full gap-6 mt-6'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('RECENTLY EXPLORED').classes('text-[11px] font-black text-gray-400 tracking-[0.2em]')
                ui.button('View Catalog', on_click=lambda: ui.navigate.to('/search')).props('flat size=sm icon=arrow_forward').classes('text-pink-500 font-black uppercase tracking-widest')
                
            recent_products = state.__dict__.get('recent_products', [])
            if recent_products:
                with ui.scroll_area().classes('w-full h-44'):
                    with ui.row().classes('gap-6 no-wrap pb-4'):
                        for p in recent_products[:10]:
                            with ui.card().classes('w-72 p-4 flex-row items-center gap-4 glass-card border-none hover:translate-y-[-4px] transition-all cursor-pointer') \
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




