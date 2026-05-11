from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager

def show_page():
    """MISI SYAQILA: Membuat Galeri Wishlist"""
    
    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    # --- 🚀 MULAI KERJAKAN DI SINI (AREA BELAJAR SYAQILA) ---
    
    # Data produk wishlist (nanti bisa diganti dari data_mgr)
    # --- 🚀 AREA WISHLIST DINAMIS ---

    with ui.column().classes('w-full p-8 bg-rose-50/30 min-h-screen gap-4'):

        # HEADER (Poin 4: Tipografi & Sudut Modern)
        with ui.row().classes('w-full items-center justify-between pb-4 border-b border-pink-100/50'):
            ui.label('Wishlist').classes('text-3xl font-extrabold tracking-tight text-gray-800')
            with ui.element('div').classes('bg-gradient-to-r from-pink-100 to-rose-100 px-5 py-2 rounded-2xl shadow-sm'):
                skin_type = app.storage.user.get('skin_type', 'Belum diisi')
                ui.label(f'Tipe Kulit: {skin_type}').classes('text-pink-600 text-sm font-bold tracking-wide')

        @ui.refreshable
        def render_wishlist():
            wishlist_products = state.wishlist
            
            def hapus_produk(slug: str):
                state.wishlist = [p for p in state.wishlist if p.get('slug') != slug]
                ui.notify('Produk dihapus dari Wishlist', color='pink')
                render_wishlist.refresh()

            # jumlah produk
            if wishlist_products:
                ui.label(f'{len(wishlist_products)} PRODUK TERSIMPAN').classes(
                    'text-xs font-bold text-gray-400 tracking-widest mt-4 mb-2 uppercase'
                )

            # Poin 5: EMPTY STATE YANG LEBIH MENARIK DENGAN SVG
            if not wishlist_products:
                with ui.column().classes('w-full items-center justify-center py-20 gap-4'):
                    # SVG Heart Broken / Empty Box
                    ui.html('''
                        <svg xmlns="http://www.w3.org/2000/svg" class="w-28 h-28 text-pink-200 drop-shadow-[0_10px_15px_rgba(236,72,153,0.2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
                        </svg>
                    ''')
                    ui.label("Wishlist masih kosong").classes('text-2xl font-extrabold text-gray-800 mt-2')
                    ui.label("Simpan produk incaranmu di sini agar tidak lupa!").classes('text-gray-500 text-center max-w-sm font-medium')
                    ui.button('Eksplorasi Produk', on_click=lambda: ui.navigate.to('/')).classes(
                        'mt-6 bg-gradient-to-r from-pink-500 to-rose-400 text-white rounded-2xl px-8 py-3 shadow-[0_8px_20px_rgba(244,63,94,0.3)] hover:scale-105 transition-transform duration-300 font-bold'
                    ).props('no-caps')

            # LIST PRODUK
            with ui.grid(columns=1).classes('w-full gap-4'):
                for product in wishlist_products:

                    # Poin 4: Sudut membulat (rounded-2xl)
                    with ui.card().classes(
                        'w-full p-4 rounded-2xl shadow-sm border border-gray-100/80 '
                        'bg-white/80 backdrop-blur-sm'
                    ):
                        with ui.row().classes('w-full items-center justify-between no-wrap'):

                            # KIRI
                            with ui.row().classes('items-center gap-5 no-wrap flex-1'):

                                # Poin 6: Peningkatan Visual Gambar / Ikon Produk dengan SVG dan Gradient
                                with ui.element('div').classes('w-16 h-16 rounded-2xl overflow-hidden shadow-sm flex items-center justify-center flex-shrink-0'):
                                    if product.get('image_url') and str(product.get('image_url')).startswith('http'):
                                        ui.image(product['image_url']).classes('w-full h-full object-contain bg-white')
                                    else:
                                        cat = product.get('category', '')
                                        
                                        if 'Serum' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-blue-100 to-indigo-50 text-blue-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 2.25c-1.353 3.036-3.834 6.75-5.625 9.375-1.748 2.56-2.625 5.25-2.625 7.875 0 4.5 3.75 8.25 8.25 8.25s8.25-3.75 8.25-8.25c0-2.625-.877-5.315-2.625-7.875C15.834 9 13.353 5.286 12 2.25z" /></svg>'
                                        elif 'Moisturizer' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-teal-100 to-emerald-50 text-teal-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" /></svg>'
                                        elif 'Sunscreen' in str(cat):
                                            bg_cls = 'bg-gradient-to-br from-orange-100 to-amber-50 text-orange-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" /></svg>'
                                        else:
                                            bg_cls = 'bg-gradient-to-br from-pink-100 to-rose-50 text-pink-500'
                                            svg_icon = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8"><path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" /></svg>'
                                        
                                        with ui.element('div').classes(f'w-full h-full flex items-center justify-center {bg_cls}'):
                                            ui.html(svg_icon)

                                with ui.column().classes('gap-1'):
                                    ui.label(product.get('product_name', product.get('name', '-'))).classes(
                                        'text-lg font-extrabold text-gray-800 leading-tight'
                                    )
                                    ui.label(
                                        f'{product.get("brand", "-")} · {product.get("category", "-")}'
                                    ).classes('text-sm text-gray-500 font-medium')

                            # TENGAH
                            with ui.column().classes('items-end gap-1 mr-6'):
                                ui.label(f"Rp{product.get('min_price', 0):,.0f}".replace(',', '.')).classes(
                                    'text-lg font-extrabold text-pink-500'
                                )
                                rating_val = product.get('average_rating') or product.get('rating') or '-'
                                with ui.row().classes('items-center gap-1'):
                                    ui.html('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-yellow-400"><path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.007 5.404.433c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.433 2.082-5.006z" clip-rule="evenodd" /></svg>')
                                    ui.label(f'{rating_val}').classes(
                                        'text-sm text-gray-600 font-bold'
                                    )

                            # KANAN
                            ui.button(
                                'Hapus',
                                on_click=lambda p=product: hapus_produk(p.get('slug'))
                            ).props('outline no-caps').classes(
                                'text-pink-500 border-pink-200 rounded-xl px-6 py-2 hover:bg-pink-50 font-bold transition-colors'
                            )

        # Panggil render function
        render_wishlist()
