from typing import Dict, Any, Callable, List, Optional
from nicegui import ui
from app.auth.auth import AuthManager

class UIComponents:
    """
    Kumpulan komponen visual mandiri (Stateless Component).
    Menerapkan prinsip UI Deklaratif tanpa mencampuri urusan pengolahan data.
    """

    @staticmethod
    def navbar(status_widget: Callable[[], None] = None) -> None:
        """Merender bagian header navigasi atas. Membuka 'slot' untuk Widget Dinamis."""
        # Menerapkan panel kaca transparan di header
        with ui.header().classes('flex items-center justify-between px-8 py-4 glass-panel z-50').style('background: rgba(255,255,255,0.4); border-bottom: 1px solid var(--glass-border);'):
            with ui.row().classes('items-center gap-3'):
                ui.image('/static/logo.png').classes('h-10 w-auto object-contain')
            
            # Area Kanan: Taskbar Widget & Logout
            with ui.row().classes('items-center gap-6'):
                if status_widget:
                    status_widget() # Render Widget Kesehatan Rutinitas di sini
                ui.button('Logout', on_click=lambda: (AuthManager.logout(), ui.navigate.to('/login'))).classes('btn-primary').props('unelevated size=sm')

    @staticmethod
    def sidebar() -> None:
        """Merender sidebar kiri dengan gaya Glassmorphism."""
        with ui.left_drawer(value=True).classes('bg-transparent p-0 overflow-hidden border-none').props('width=280'):
            # Background blur container
            with ui.column().classes('w-full h-full glass-panel p-6 gap-6'):
                # Logo / Header Sidebar
                with ui.row().classes('items-center gap-3 mb-4 px-2'):
                    ui.icon('auto_awesome', size='32px', color='pink-400')
                    ui.label('Menu Utama').classes('text-xl font-black text-gray-800')

                # Menu Items
                menu_items = [
                    ('home', 'HOME', '/'),
                    ('search', 'Cari Produk', '/search'),
                    ('compare_arrows', 'Bandingkan', '/compare'),
                    ('event_note', 'Routine Planner', '/routine'),
                    ('favorite', 'Wishlist', '/wishlist'),
                    ('bar_chart', 'Statistik', '/stats'),
                    ('person', 'Profil', '/profile'),
                ]

                with ui.column().classes('w-full gap-2'):
                    for icon, label, path in menu_items:
                        with ui.row().classes('w-full items-center gap-4 px-4 py-3 rounded-2xl cursor-pointer transition-all hover:bg-white/40 hover:translate-x-2 group') \
                            .on('click', lambda p=path: ui.navigate.to(p)):
                            ui.icon(icon, size='24px').classes('text-gray-500 group-hover:text-[#C8607A]')
                            ui.label(label).classes('text-sm font-bold text-gray-600 group-hover:text-gray-800 tracking-wide')

                # Footer Sidebar
                ui.space()
                with ui.column().classes('w-full p-4 rounded-2xl bg-white/20 border border-white/40'):
                    ui.label('Skintify v1.0').classes('text-[10px] font-bold text-gray-400 uppercase text-center w-full')

    @staticmethod
    def routine_status_badge(analysis_data: Dict[str, Any]) -> None:
        """Komponen Traffic Light System untuk Taskbar (Self-Explanatory UX)."""
        
        status = analysis_data.get("status", "empty")
        warnings_count = len(analysis_data.get("warnings", []))

        # Kotak Badge dengan Flexbox bergaya Glassmorphism
        with ui.row().classes('items-center gap-2 px-4 py-2 rounded-full glass-badge transition-all'):
            if status == "empty":
                ui.icon('radio_button_unchecked', size='18px', color='grey-400')
                ui.label('Rutinitas Kosong').classes('text-xs font-bold text-gray-500 tracking-wide uppercase')
            elif status == "safe":
                ui.icon('check_circle', size='18px', color='green-500').classes('animate-pulse-soft')
                ui.label('Status: Aman').classes('text-xs font-extrabold text-green-700 tracking-wide uppercase')
            elif status == "danger":
                ui.icon('warning', size='18px', color='red-500').classes('animate-pulse-soft')
                ui.label(f'Konflik: {warnings_count} Bahaya!').classes('text-xs font-extrabold text-red-600 tracking-wide uppercase')

    @staticmethod
    def review_badge(reviews: List[Dict[str, Any]]) -> None:
        """Badge ringkas agregasi sentimen review YouTube dengan efek Glassmorphism."""
        if not reviews:
            return

        sentiments = [r.get("sentiment", "neutral") for r in reviews]
        total = len(sentiments)
        pos = sentiments.count("positive")
        neg = sentiments.count("negative")

        if total == 0:
            return

        # Warna semi-transparan untuk efek frosted glass
        if pos / total >= 0.7:
            bg, border, text_color, icon, label = "rgba(232, 245, 233, 0.6)", "rgba(165, 214, 167, 0.8)", "#2E7D32", "thumb_up", f"{pos}/{total} Positif"
        elif neg / total >= 0.5:
            bg, border, text_color, icon, label = "rgba(255, 235, 238, 0.6)", "rgba(239, 154, 154, 0.8)", "#C62828", "thumb_down", f"{neg}/{total} Negatif"
        else:
            bg, border, text_color, icon, label = "rgba(255, 248, 225, 0.6)", "rgba(255, 224, 130, 0.8)", "#F57F17", "thumbs_up_down", f"{total} Review"

        with ui.row().classes('items-center gap-1 px-2 py-0.5 rounded-full mt-1 backdrop-blur-sm').style(
            f'background: {bg}; border: 1px solid {border}; width: fit-content;'
        ):
            ui.icon(icon, size='11px').style(f'color: {text_color}')
            ui.label(f"YT: {label}").classes('text-[9px] font-bold').style(f'color: {text_color}')

    @staticmethod
    def comedogenicity_badge(profile: Optional[Dict]) -> None:
        """
        Badge kecil indikator risiko comedogenicity & irritancy dari INCIDecoder.
        Tidak render apapun jika profile None (DB belum di-scrape) — zero visual noise.
        """
        if not profile:
            return

        max_com = profile.get("max_comedogenicity", 0)
        high_irr_count = len(profile.get("high_irritancy_ingredients", []))

        if max_com == 0 and high_irr_count == 0:
            return  # Produk ini bersih — tidak perlu badge

        # Tentukan level risiko tertinggi untuk warna badge
        if max_com >= 4 or high_irr_count >= 4:
            bg, border, text, icon = "rgba(255,235,238,0.7)", "rgba(239,83,80,0.5)", "#C62828", "block"
            label = f"Pori: {'Tinggi' if max_com >= 4 else 'OK'} · Iritasi: {high_irr_count} bahan"
        elif max_com >= 3 or high_irr_count >= 2:
            bg, border, text, icon = "rgba(255,243,224,0.7)", "rgba(255,183,77,0.5)", "#E65100", "warning_amber"
            label = f"Pori: {'Sedang' if max_com >= 3 else 'OK'} · Iritasi: {high_irr_count} bahan"
        else:
            return  # Risiko rendah — tidak perlu badge, hindari visual noise

        with ui.row().classes('items-center gap-1 px-2 py-0.5 rounded-full mt-1 backdrop-blur-sm').style(
            f'background: {bg}; border: 1px solid {border}; width: fit-content;'
        ):
            ui.icon(icon, size='11px').style(f'color: {text}')
            ui.label(f"INCIDecoder: {label}").classes('text-[9px] font-bold').style(f'color: {text}')

    @staticmethod
    def product_card(product: Dict[str, Any], on_add_click: Callable[[Dict[str, Any]], None], reviews: Optional[List] = None, on_scrape_click: Optional[Callable] = None, ingredient_profile: Optional[Dict] = None) -> None:
        """Komponen visual kartu katalog produk bergaya Modern Glassmorphism."""
        """Komponen visual kartu katalog produk bergaya Modern Glassmorphism."""

        with ui.card().classes('glass-card w-full p-0 gap-0 flex flex-col justify-between h-full overflow-hidden'):
            # Fallback gambar yang lebih elegan & Robust (Pilihan B)
            raw_img = product.get('image_url') or product.get('image')
            img_url = raw_img if raw_img and str(raw_img).startswith('http') else 'https://via.placeholder.com/400x400?text=No+Image'
            
            # Ambil kategori (Gunakan list kategori jika ada, ambil yang pertama)
            all_cats = product.get('all_categories', [])
            category = product.get('category') or (all_cats[0] if all_cats else 'Skincare')
            
            # Area Gambar dengan "Skeleton Loading" feel
            with ui.column().classes('w-full h-56 bg-white/40 relative overflow-hidden'):
                # Background logo samar jika gambar gagal
                ui.icon('image', size='64px', color='pink-100').classes('absolute center-absolute opacity-20')
                
                ui.image(img_url).classes('w-full h-full object-contain relative z-10 transition-opacity hover:opacity-90') \
                    .style('background: transparent;')
                
                # Glass Badge Kategori melayang
                ui.label(category).classes('absolute top-3 left-3 glass-badge text-[10px] px-3 py-1 rounded-full font-extrabold uppercase tracking-widest text-gray-700 z-20')
            
            with ui.column().classes('p-5 w-full flex-grow justify-between gap-4 bg-white/30 backdrop-blur-sm'):
                # Seksi Informasi Produk
                with ui.column().classes('gap-1 w-full'):
                    ui.label(product.get('brand', 'Unknown')).classes('text-[10px] font-extrabold uppercase tracking-widest text-gray-500')
                    ui.label(product.get('product_name', 'Nama Produk')).classes('text-[15px] font-bold line-clamp-2 leading-snug text-gray-800')
                    
                    # Rating & Review
                    # Rating & Review
                    rating = product.get('average_rating', 0)
                    reviews_count = product.get('total_reviews', 0)
                    
                    with ui.row().classes('items-center gap-1 mt-1 min-h-[20px]'):
                        if float(rating) > 0:
                            ui.icon('star', size='14px', color='#F59E0B')
                            ui.label(f"{rating}").classes('text-xs font-bold text-gray-700')
                            ui.label(f"({reviews_count} ulasan)").classes('text-[10px] text-gray-500 font-medium')
                        else:
                            ui.label("Belum ada ulasan").classes('text-[10px] text-gray-400 italic')

                    # Badge Review YouTube
                    UIComponents.review_badge(reviews or [])

                    # Badge INCIDecoder Comedogenicity Risk (hanya tampil jika DB aktif)
                    UIComponents.comedogenicity_badge(ingredient_profile)

                    # Seksi Aksi (Harga & Tombol)
                with ui.column().classes('w-full mt-auto gap-2'):
                    # Format harga yang lebih "pro" (Rp 100.000)
                    min_p = product.get('min_price')
                    if isinstance(min_p, (int, float)):
                        price_sociolla = f"Rp {int(min_p):,}".replace(',', '.')
                    else:
                        price_sociolla = product.get('price_after_discount_range') or product.get('price_range') or f"Rp {min_p or '-'}"
                    
                    toped_data = product.get('tokopedia_data')

                    if toped_data:
                        # Box Komparasi Harga: Sociolla vs Tokopedia
                        with ui.column().classes('w-full gap-0 p-2 rounded-lg bg-white/40 border border-white/60 shadow-sm backdrop-blur-sm mt-1'):
                            with ui.row().classes('justify-between w-full items-center'):
                                ui.label('Sociolla').classes('text-[9px] font-bold text-gray-500 uppercase tracking-wider')
                                ui.label(str(price_sociolla)).classes('text-[11px] font-semibold text-gray-400 line-through')
                            with ui.row().classes('justify-between w-full items-center mt-0.5'):
                                ui.label('Tokopedia').classes('text-[11px] font-black text-[#42B549] uppercase tracking-wide')
                                
                                # Format harga Tokopedia jika angka
                                t_harga = toped_data.get('tokopedia_harga')
                                if isinstance(t_harga, (int, float)):
                                    t_text = f"Rp {int(t_harga):,}".replace(',', '.')
                                else:
                                    t_text = toped_data.get('tokopedia_harga_text', 'N/A')
                                ui.label(t_text).classes('text-sm font-black text-[#42B549]')
                            
                            terjual = toped_data.get('tokopedia_terjual', 0)
                            if terjual > 0:
                                toko_toped = toped_data.get('tokopedia_toko', 'Toko')
                                ui.label(f"Terjual {terjual:,}+ di {toko_toped}".replace(',', '.')).classes('text-[9px] font-bold text-gray-500 mt-1 italic line-clamp-1')
                    else:
                        # Tampilan standar jika tidak ada data Tokopedia
                        ui.label(str(price_sociolla)).classes('text-lg font-extrabold text-[#A84A62] mt-1')

                    with ui.row().classes('w-full gap-2 mt-1 items-center'):
                        if on_add_click:
                            ui.button('Tambah', icon='add', on_click=lambda: on_add_click(product)) \
                                .classes('flex-1 btn-primary shadow-lg').props('unelevated rounded size=sm')

                        # Tombol Eksternal: CTA Beli di Tokopedia
                        if toped_data and toped_data.get('tokopedia_link'):
                            link = toped_data['tokopedia_link']
                            ui.button(icon='shopping_bag', on_click=lambda l=link: ui.navigate.to(l, new_tab=True)) \
                                .classes('bg-[#42B549] text-white hover:bg-[#318B36] min-w-0 transition-colors rounded p-2 shadow-sm') \
                                .props('unelevated size=sm') \
                                .tooltip('Beli di Tokopedia')

                        if on_scrape_click:
                            has_reviews = bool(reviews)
                            btn_icon = 'refresh' if has_reviews else 'play_circle'
                            btn_color = 'text-[#C8607A]' if has_reviews else 'text-gray-400'
                            btn_tooltip = 'Perbarui Review' if has_reviews else 'Cari Review YouTube'
                            
                            ui.button(icon=btn_icon, on_click=on_scrape_click) \
                                .classes(f'{btn_color} hover:text-[#A84A62] min-w-0 transition-colors bg-white/50 rounded-full p-2 shadow-sm border border-white/60')\
                                .props('flat dense') \
                                .tooltip(btn_tooltip)
    @staticmethod
    def pagination_controls(current_page: int, total_pages: int, on_change: Callable[[int], None]) -> None:

        # kontrol navigasi halaman (Prev, Status, Next) yang bersih.

        with ui.row().classes('w-full items-center justify-center gap-4 mt-8 p-2 rounded-lg').style('background-color: var(--surface2); border: 1px solid var(--border-lt);'):
            # Tombol Prev (Disable jika di halaman 1)
            prev_btn = ui.button(icon='chevron_left', on_click=lambda: on_change(current_page - 1)) \
                .props('outline round size=sm').classes('text-gray-600')
            if current_page <= 1:
                prev_btn.disable()
            
            ui.label(f"Halaman {current_page} dari {total_pages}").classes('text-sm font-bold').style('color: var(--text2);')
            
            # Tombol Next (Disable jika di halaman terakhir)
            next_btn = ui.button(icon='chevron_right', on_click=lambda: on_change(current_page + 1)) \
                .props('outline round size=sm').classes('text-gray-600')
            if current_page >= total_pages:
                next_btn.disable()

    @staticmethod
    def empty_state_svg() -> None:
        """Merender SVG Animasi saat keranjang rutinitas kosong (Self Explanatory UX)."""
        # SVG Kosmetik/Skincare Botol minimalis
        svg_code = """
        <svg width="100" height="100" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="animate-float">
            <path d="M7 8V6C7 4.89543 7.89543 4 9 4H15C16.1046 4 17 4.89543 17 6V8" stroke="#F2C2CE" stroke-width="2" stroke-linecap="round"/>
            <path d="M5 10C5 8.89543 5.89543 8 7 8H17C18.1046 8 19 8.89543 19 10V20C19 21.1046 18.1046 22 17 22H7C5.89543 22 5 21.1046 5 20V10Z" fill="#FFF8F6" stroke="#C8607A" stroke-width="2" stroke-linejoin="round"/>
            <circle cx="12" cy="15" r="3" fill="#F2C2CE" class="animate-pulse-soft"/>
        </svg>
        """
        with ui.column().classes('w-full items-center justify-center py-10 gap-3'):
            ui.html(svg_code)
            ui.label('Rutinitas Masih Kosong').classes('text-md font-bold text-gray-500 mt-2')
            ui.label('Pilih produk dari katalog di sebelah kiri untuk mulai mengecek kecocokan bahan.').classes('text-xs text-gray-400 text-center px-4 leading-relaxed')
    @staticmethod
    def analysis_dashboard(analysis_data: Dict[str, Any]) -> None:
        #"""Merender komponen interaktif hasil evaluasi mesin pintar dengan estetika Kaca transparan."""
        warnings = analysis_data.get("warnings", [])
        suggestions = analysis_data.get("suggestions", [])
        weather = analysis_data.get("weather", None)

        if weather and weather.get("status") == "success":
            with ui.row().classes('w-full items-center justify-between p-4 rounded-2xl mb-4 glass-badge').style('background: rgba(227, 242, 253, 0.5); border-left: 4px solid #1E88E5;'):
                with ui.column().classes('gap-1'):
                    ui.label('Kondisi Cuaca Saat Ini').classes('text-[10px] font-bold text-blue-800 uppercase tracking-widest')
                    ui.label(f"{weather['desc']}").classes('text-sm font-extrabold text-blue-900')
                with ui.row().classes('gap-5'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('UV Index').classes('text-[10px] text-blue-700 font-bold')
                        ui.label(str(weather['uv_index'])).classes('text-sm font-black text-blue-900')
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Humidity').classes('text-[10px] text-blue-700 font-bold')
                        ui.label(f"{weather['humidity']}%").classes('text-sm font-black text-blue-900')

        if warnings:
            with ui.column().classes('conflict-warning w-full mb-4'):
                ui.label("🚨 Peringatan Interaksi & Keamanan!").classes('font-extrabold text-red-700 text-sm tracking-wide')
                for w in warnings:
                    ui.label(w).classes('text-xs text-red-600 mt-1.5 leading-relaxed font-medium')
        
        if suggestions:
            with ui.column().classes('w-full p-4 rounded-2xl mb-4 glass-badge').style('background: rgba(255, 243, 224, 0.5); border: 1px solid rgba(255, 204, 128, 0.5); border-left: 4px solid #FF9800;'):
                ui.label("💡 Saran Berdasarkan Cuaca").classes('font-extrabold text-orange-800 text-sm tracking-wide')
                for s in suggestions:
                    ui.label(s).classes('text-xs text-orange-700 mt-1.5 leading-relaxed font-medium')

        # Panel INCIDecoder Aggregate — hanya render jika data tersedia
        aggregate = analysis_data.get("incidecoder_aggregate")
        if aggregate:
            max_com = aggregate.get("max_comedogenicity", 0)
            max_irr = aggregate.get("max_irritancy", 0)
            high_com = aggregate.get("high_comedogenic_ingredients", [])
            high_irr = aggregate.get("high_irritancy_ingredients", [])

            with ui.column().classes('w-full p-4 rounded-2xl mb-4 glass-badge').style(
                'background: rgba(237,231,246,0.5); border: 1px solid rgba(179,157,219,0.4); border-left: 4px solid #7B1FA2;'
            ):
                ui.label("🔬 Analisis INCIDecoder").classes('font-extrabold text-purple-800 text-sm tracking-wide mb-2')
                with ui.row().classes('w-full gap-6 mt-1'):
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Comedogenicity').classes('text-[9px] font-bold text-purple-700 uppercase tracking-wider')
                        ui.label(f"{max_com}/5").classes('text-lg font-black text-purple-900')
                        ui.label('Max Score').classes('text-[9px] text-purple-500')
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Irritancy').classes('text-[9px] font-bold text-purple-700 uppercase tracking-wider')
                        ui.label(f"{max_irr}/5").classes('text-lg font-black text-purple-900')
                        ui.label('Max Score').classes('text-[9px] text-purple-500')
                    with ui.column().classes('items-center gap-0'):
                        ui.label('Bahan Irritant').classes('text-[9px] font-bold text-purple-700 uppercase tracking-wider')
                        ui.label(f"{len(high_irr)}").classes('text-lg font-black text-purple-900')
                        ui.label('≥ Score 2').classes('text-[9px] text-purple-500')
                if high_com:
                    ui.label(f"Pori berisiko: {', '.join(high_com[:3])}").classes('text-[10px] text-purple-700 mt-2 font-semibold')

        if not warnings and analysis_data:
            with ui.column().classes('safe-status w-full mb-4'):
                ui.label("✅ Rutinitas Aman").classes('text-sm font-extrabold text-green-800 tracking-wide')
                ui.label("Tidak terdeteksi konflik bahan aktif yang berbahaya.").classes('text-xs text-green-700 mt-1 font-medium')