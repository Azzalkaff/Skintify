from nicegui import ui, app

def show_about_dialog():
    """Menampilkan pop-up dialog perkenalan/tutorial."""
    if not app.storage.user.get('tutorial_dismissed', False):
        with ui.dialog().classes('backdrop-blur-md') as tutorial_dialog, ui.card().classes('w-full max-w-[600px] p-0 rounded-[2.5rem] shadow-2xl border border-white/50 overflow-hidden bg-white/95 relative'):
            # Decorative background glows
            ui.element('div').classes('absolute -right-20 -top-20 w-64 h-64 bg-pink-300/30 rounded-full blur-3xl z-0 pointer-events-none')
            ui.element('div').classes('absolute -left-20 -bottom-20 w-64 h-64 bg-blue-300/30 rounded-full blur-3xl z-0 pointer-events-none')

            TUTORIAL_STEPS = [
                {
                    'title': 'Konsultasi & Diagnosis AI',
                    'desc': 'Ceritakan keluhan kulit Anda kepada sistem AI kami. Sistem akan menganalisis masalah secara spesifik dan merekomendasikan produk atau kandungan yang paling relevan dengan kondisi kulit Anda.',
                    'image': 'https://via.placeholder.com/400x300/FCE7F3/BE185D?text=Ilustrasi+Diagnosis+AI'
                },
                {
                    'title': 'Perbandingan Harga Terintegrasi',
                    'desc': 'Setelah mendapatkan rekomendasi, bandingkan harga produk tersebut secara langsung dari berbagai platform marketplace. Fitur ini dirancang agar Anda selalu mendapatkan harga terbaik tanpa harus mencari secara manual.',
                    'image': 'https://via.placeholder.com/400x300/DBEAFE/1D4ED8?text=Ilustrasi+Banding+Harga'
                },
                {
                    'title': 'Pemantauan Rutinitas Konsisten',
                    'desc': 'Jadwalkan produk yang telah Anda pilih ke dalam rutinitas pagi atau malam. Pemantauan harian membantu Anda menjaga konsistensi, yang merupakan kunci utama dalam mencapai kondisi kulit yang sehat.',
                    'image': 'https://via.placeholder.com/400x300/F3E8FF/6B21A8?text=Ilustrasi+Rutinitas'
                }
            ]
            
            with ui.column().classes('w-full relative z-10 pt-8'):
                ui.label('WELCOME TO SKINTIFY').classes('text-lg font-black text-center w-full text-pink-500 tracking-widest px-4')
                
                with ui.carousel(animated=True, arrows=False, navigation=True).classes('w-full h-[400px] bg-transparent') as carousel:
                    for step in TUTORIAL_STEPS:
                        with ui.carousel_slide().classes('p-0 bg-transparent flex flex-col items-center w-full h-full'):
                            with ui.column().classes('w-full h-full items-center p-6 gap-4'):
                                # Tempat gambar wireframe
                                ui.image(step['image']).classes('w-[240px] h-[160px] object-cover rounded-2xl shadow-sm border border-gray-200')
                                
                                ui.label(step['title']).classes('text-2xl font-black text-gray-800 text-center tracking-tight px-4 mt-2')
                                ui.label(step['desc']).classes('text-sm text-gray-600 text-center leading-relaxed max-w-[460px] font-medium')
                
                with ui.row().classes('w-full p-6 items-center justify-between bg-gray-50/80 border-t border-gray-100/80 backdrop-blur-md'):
                    with ui.row().classes('gap-2'):
                        ui.button(icon='chevron_left', on_click=carousel.previous).props('flat dense round size=md').classes('text-gray-400 hover:text-pink-500 transition-colors')
                        ui.button(icon='chevron_right', on_click=carousel.next).props('flat dense round size=md').classes('text-gray-400 hover:text-blue-500 transition-colors')
                    
                    ui.button('Mulai Perjalanan', on_click=lambda: (app.storage.user.__setitem__('tutorial_dismissed', True), tutorial_dialog.close())).classes('bg-gradient-to-r from-pink-500 to-rose-400 text-white font-bold px-8 py-3 rounded-2xl shadow-lg hover:scale-[1.02] transition-transform').props('no-caps')
        
        tutorial_dialog.open()
