from typing import Any, Callable
from nicegui import ui

def render_search_result_card(p: Any, on_click: Callable) -> None:
    """
    Render a shared product search result card.
    Supports both SQLAlchemy objects and dictionaries.
    """
    def _get(field):
        if isinstance(p, dict):
            return p.get(field)
        return getattr(p, field, None)
        
    image_url = _get('image_url') or _get('image')
    brand = _get('brand') or '-'
    product_name = _get('product_name') or _get('nama') or '-'
    
    with ui.row().classes('w-full items-center justify-between p-3 hover:bg-pink-50 rounded-xl cursor-pointer border border-transparent hover:border-pink-200 transition-all group') \
        .on('click', lambda: on_click()):
        with ui.row().classes('items-center gap-3 flex-1 overflow-hidden'):
            with ui.element('div').classes('w-12 h-12 bg-white rounded-lg p-1 border border-gray-100 flex items-center justify-center flex-shrink-0'):
                if image_url and str(image_url).startswith('http'):
                    ui.image(image_url).classes('w-full h-full object-contain')
                else:
                    ui.icon('inventory_2', size='24px').classes('text-pink-200')
            with ui.column().classes('gap-0 flex-1 overflow-hidden'):
                ui.label(brand).classes('text-[10px] font-black text-pink-400 uppercase tracking-widest truncate w-full')
                ui.label(product_name).classes('text-xs font-bold text-gray-800 line-clamp-2 w-full')
        ui.button(icon='add', on_click=lambda e: (e.sender.consume(), on_click())).props('flat round size=sm').classes('bg-pink-50 text-pink-500 opacity-50 group-hover:opacity-100 transition-opacity ml-2 flex-shrink-0')
