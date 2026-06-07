from nicegui import ui, app

TUTORIAL_STEPS = [
    {
        'title': 'Konsultasi Dengan AI',
        'desc': 'Konsultasi masalah kulit, biaya, dan lain lain kepada ai.',
        'image': '/static/images/illust_diagnosis.png'
    },
    {
        'title': 'Bandingkan Harga Marketplace',
        'desc': 'Setelah mendapatkan rekomendasi, bandingkan harga produk tersebut secara langsung dari tokopedia, lazada, dan shopee (soon).',
        'image': '/static/images/illust_compare.png'
    },
    {
        'title': 'Pemantauan Rutinitas',
        'desc': 'Jadwalkan produk yang telah Anda pilih ke dalam rutinitas pagi atau malam. Pemantauan harian membantu Anda menjaga konsistensi..',
        'image': '/static/images/illust_routine.png'
    }
]

def show_about_dialog():
    """Menampilkan pop-up dialog perkenalan/tutorial secara efisien."""
    
    # ⚡ Optimasi 1: Fast-path. Jika sudah dismiss, return instan tanpa menyusun DOM sama sekali (O(1) time complexity)
    if app.storage.user.get('tutorial_dismissed', False):
        return

    with ui.dialog().classes('backdrop-blur-md') as tutorial_dialog, ui.card().classes('w-full max-w-[850px] max-h-[95vh] flex flex-col no-wrap p-0 rounded-[2.5rem] shadow-2xl border border-white/50 bg-white/95 relative overflow-hidden'):
        # ⚡ Optimasi 2: Fungsi helper tunggal menghindari pembuatan banyak lambda di memori (memory leak prevention)
        def dismiss_tutorial():
            app.storage.user['tutorial_dismissed'] = True
            tutorial_dialog.close()

        # Decorative background glows
        ui.element('div').classes('absolute -right-20 -top-20 w-64 h-64 bg-pink-300/30 rounded-full blur-3xl z-0 pointer-events-none')
        ui.element('div').classes('absolute -left-20 -bottom-20 w-64 h-64 bg-blue-300/30 rounded-full blur-3xl z-0 pointer-events-none')

        with ui.column().classes('w-full flex-1 relative z-10 pt-8 flex flex-col no-wrap overflow-hidden'):
            ui.label('WELCOME TO SKINTIFY').classes('text-lg font-black text-center w-full text-pink-500 tracking-widest px-4 shrink-0')
            
            carousel_container = ui.column().classes('w-full flex-1 relative min-h-0 bg-transparent overflow-hidden')
            with carousel_container:
                pass # Kosong, diisi oleh timer
            
            # Tombol Skip (Lewati) melayang di pojok kiri bawah
            ui.button('Lewati', on_click=dismiss_tutorial) \
                .props('flat no-caps') \
                .classes('absolute bottom-4 left-6 text-gray-400 font-bold hover:text-gray-600 z-50')
                
            def render_carousel():
                with carousel_container:
                    # Gunakan titik navigasi (navigation=True), matikan panah (arrows=False), ubah warna titik jadi abu gelap
                    with ui.carousel(animated=True, arrows=False, navigation=True).props('control-color=grey-8').classes('w-full flex-1 min-h-0 bg-transparent pb-8 overflow-hidden') as carousel:
                        for i, step in enumerate(TUTORIAL_STEPS):
                            with ui.carousel_slide().classes('p-0 bg-transparent flex flex-col items-center w-full h-full relative overflow-hidden'):
                                with ui.column().classes('w-full h-full items-center justify-center p-2 lg:p-6 gap-3 lg:gap-4 no-wrap overflow-hidden'):
                                    # Gunakan rasio 16:9 ketat agar tidak berubah proporsinya, biarkan ia shrink jika layar pendek
                                    ui.image(step['image']).classes('w-[90%] max-w-[550px] aspect-[16/9] object-cover rounded-2xl shadow-sm border border-gray-200 shrink min-h-0')
                                    
                                    ui.label(step['title']).classes('text-xl lg:text-2xl font-black text-gray-800 text-center tracking-tight px-4 mt-2 shrink-0')
                                    ui.label(step['desc']).classes('text-sm text-gray-600 text-center leading-relaxed max-w-[500px] font-medium px-4')
                                    
                                # Tombol hanya muncul di slide terakhir, diletakkan di kanan pojok
                                if i == len(TUTORIAL_STEPS) - 1:
                                    ui.button('Mulai Perjalanan', on_click=dismiss_tutorial) \
                                        .classes('absolute bottom-2 right-6 bg-gradient-to-r from-pink-500 to-rose-400 text-white font-bold py-2 px-6 rounded-xl shadow-lg hover:scale-[1.05] transition-transform z-50') \
                                        .props('no-caps')

            ui.timer(0.01, render_carousel, once=True)
        
        tutorial_dialog.open()
