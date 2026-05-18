"""
safe_render.py — Komponen Error Boundary untuk NiceGUI
=======================================================
Menyediakan isolasi per-seksi agar satu bagian yang crash
TIDAK merusak seluruh halaman atau halaman lain.

Pemakaian:
    from app.ui.safe_render import safe_section

    with safe_section("Cuaca Hari Ini"):
        # kode yang mungkin crash (misal: weather API)
        render_weather_widget()

    with safe_section("Katalog Produk"):
        # jika bagian di atas crash, bagian ini tetap jalan
        render_catalog()
"""

from contextlib import contextmanager
import logging
import traceback
from nicegui import ui

logger = logging.getLogger(__name__)


@contextmanager
def safe_section(section_name: str, show_error: bool = True, compact: bool = False):
    """
    Context manager yang mengisolasi error dalam satu seksi UI.

    Args:
        section_name: Nama seksi (untuk log & error message).
        show_error:   Tampilkan pesan error kecil di UI jika True.
                      Set False untuk seksi kecil/widget agar silent.
        compact:      Tampilkan error versi ringkas (hanya ikon, tanpa teks panjang).
    """
    try:
        yield
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[SafeSection] '{section_name}' error: {e}\n{tb}")

        if show_error:
            if compact:
                # Versi ringkas untuk widget kecil (misal: badge navbar)
                with ui.row().classes('items-center gap-1 px-2 py-1 bg-red-50/60 rounded-lg border border-red-100/50'):
                    ui.icon('error_outline', size='14px', color='red-300')
                    ui.label(f'{section_name} tidak tersedia').classes(
                        'text-[9px] font-bold text-red-400'
                    )
            else:
                # Versi standar untuk seksi besar
                with ui.card().classes(
                    'w-full p-6 bg-red-50/40 border border-red-100/50 '
                    'rounded-2xl flex flex-row items-start gap-4'
                ):
                    ui.icon('warning_amber', size='28px', color='red-300')
                    with ui.column().classes('gap-1'):
                        ui.label(f'Seksi "{section_name}" tidak dapat dimuat').classes(
                            'text-sm font-black text-red-600'
                        )
                        ui.label(
                            'Fitur ini sedang dalam perbaikan. Halaman lain tetap berjalan normal.'
                        ).classes('text-xs text-red-400 font-medium')

                        # Detail error untuk developer (collapsed by default)
                        with ui.expansion('Detail Error (Developer)').classes(
                            'text-[10px] text-red-300 mt-1'
                        ):
                            ui.code(str(e)).classes('text-[10px] bg-red-50 p-3 rounded-lg w-full')
