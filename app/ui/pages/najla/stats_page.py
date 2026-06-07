from nicegui import ui, app as nicegui_app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi
from collections import Counter
from typing import List, Dict, Any

import base64
from functools import lru_cache


# ── WARNA ──────────────────────────────────────────
PINK_PRIMARY = '#EC4899'
PINK_LIGHT = '#F9A8D4'
PINK_SOFT = '#FCE7F3'
ACCENT_TEAL = '#06B6D4'
ACCENT_INDIGO = '#6366F1'
CARD_SHADOW = 'box-shadow:0 8px 20px rgba(15,23,42,0.06); border:1px solid rgba(15,23,42,0.04);'
CARD_BG_NEUTRAL = '#FFFFFF'
PALETTE = ['#EC4899', '#A78BFA', '#60A5FA', '#FB923C', '#F472B6']
HEADER_GRADIENT = 'linear-gradient(90deg, #EC4899 0%, #A78BFA 50%, #60A5FA 100%)'

SKINCARE_CATEGORIES = {
    'Cleanser', 'Toner', 'Serum', 'Moisturizer', 'Sunscreen',
    'Mask', 'Sheet Mask', 'Lotion', 'Essence', 'Ampoule',
    'Facial Oil', 'Mist', 'Scrub', 'Peeling', 'Treatment',
    'Eye Cream', 'Neck Cream', 'Sleep Mask'
}


def is_skincare_category(category: str) -> bool:
    if not category:
        return False
    normalized = str(category).strip()
    return normalized in SKINCARE_CATEGORIES


# ── AX STYLE ───────────────────────────────────────
def setup_ax(ax, title: str, show_grid_x=False, show_grid_y=True):

    ax.set_title(
        title,
        fontsize=13,
        fontweight='bold',
        color='#1F2937',
        pad=14,
        loc='left'
    )

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')

    ax.tick_params(colors='#6B7280', labelsize=9)

    if show_grid_y:
        ax.yaxis.grid(
            True,
            linestyle='--',
            linewidth=0.5,
            color='#F3F4F6',
            alpha=0.8
        )

        ax.set_axisbelow(True)

    if show_grid_x:
        ax.xaxis.grid(
            True,
            linestyle='--',
            linewidth=0.5,
            color='#F3F4F6',
            alpha=0.8
        )

        ax.set_axisbelow(True)

    ax.set_facecolor('#FAFAFA')


# ── DATA ───────────────────────────────────────────
def get_trending_products(limit: int = 10) -> List[Dict[str, Any]]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        # Jika database kosong, gunakan fallback dari DataManager (JSON)
        if not products:
            try:
                fallback = data_mgr.get_paginated_products(page=1, items_per_page=1000)
                items = fallback.get('items', [])
                products = []
                for it in items:
                    # Normalisasi ke objek dict yang mirip ORM
                    products.append(type('P', (), {
                        'product_name': it.get('product_name'),
                        'brand': it.get('brand'),
                        'category': it.get('category'),
                        # map JSON average_rating -> rating_sociolla
                        'rating_sociolla': it.get('rating') or it.get('average_rating') or 0,
                        'total_reviews': it.get('total_reviews') or 0,
                        # correct field: JSON uses 'total_wishlist'
                        'total_wishlist': int(it.get('total_wishlist') or 0),
                        'image_url': it.get('image_url') or it.get('gambar') or ''
                    }))
            except Exception:
                products = []
        scored = []

        for p in products:
            if not is_skincare_category(getattr(p, 'category', None)):
                continue

            wishlist = p.total_wishlist or 0
            reviews = p.total_reviews or 0
            rating = p.rating_sociolla or 0

            score = (
                wishlist + reviews
            ) * (
                rating / 5.0 if rating else 0.5
            )

            scored.append({
                'name': p.product_name,
                'brand': p.brand or '',
                'category': p.category or '',
                'rating': rating,
                'reviews': reviews,
                'wishlist': wishlist,
                'score': score,
                'image_url': p.image_url or '',
            })

        scored.sort(
            key=lambda x: x['score'],
            reverse=True
        )

        return scored[:limit]


def get_rating_distribution() -> Dict[str, int]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        # Fallback ke JSON via data_mgr jika DB kosong
        if not products:
            try:
                items = data_mgr.get_paginated_products(page=1, items_per_page=1000).get('items', [])
                # adapt items to expected shape
                products = [type('P', (), { 'rating_sociolla': it.get('rating') or it.get('average_rating') or 0 }) for it in items]
            except Exception:
                products = []
        distribution = {
            '4.5–5.0': 0,
            '4.0–4.4': 0,
            '3.5–3.9': 0,
            '3.0–3.4': 0,
            '<3.0': 0
        }

        for p in products:

            rating = p.rating_sociolla or 0

            if rating >= 4.5:
                distribution['4.5–5.0'] += 1

            elif rating >= 4.0:
                distribution['4.0–4.4'] += 1

            elif rating >= 3.5:
                distribution['3.5–3.9'] += 1

            elif rating >= 3.0:
                distribution['3.0–3.4'] += 1

            else:
                distribution['<3.0'] += 1

        return distribution


def get_top_brands(limit: int = 8) -> Dict[str, int]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        # Fallback to data_mgr JSON when empty
        if not products:
            try:
                items = data_mgr.get_paginated_products(page=1, items_per_page=1000).get('items', [])
                products = [type('P', (), { 'brand': it.get('brand'), 'category': it.get('category') }) for it in items]
            except Exception:
                products = []
        brand_counter = Counter()

        for p in products:
            if p.brand and is_skincare_category(getattr(p, 'category', None)):
                brand_counter[p.brand] += 1

        return dict(
            brand_counter.most_common(limit)
        )


def get_category_distribution() -> Dict[str, int]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        # Fallback to data_mgr JSON when empty
        if not products:
            try:
                items = data_mgr.get_paginated_products(page=1, items_per_page=1000).get('items', [])
                products = [type('P', (), { 'category': it.get('category') }) for it in items]
            except Exception:
                products = []
        category_counter = Counter()

        for p in products:
            category = getattr(p, 'category', None)
            if category and is_skincare_category(category):
                category_counter[category] += 1

        return dict(category_counter)

def get_avg_price_by_category() -> Dict[str, float]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        # Fallback to JSON via data_mgr if DB empty
        if not products:
            try:
                items = data_mgr.get_paginated_products(page=1, items_per_page=1000).get('items', [])
                products = [type('P', (), { 'category': it.get('category'), 'min_price': it.get('min_price') or it.get('min_price', 0), 'max_price': it.get('max_price') or it.get('min_price', 0) }) for it in items]
            except Exception:
                products = []
        category_prices = {}

        for p in products:
            category = getattr(p, 'category', None)
            if (
                category and
                is_skincare_category(category) and
                getattr(p, 'min_price', None) and
                getattr(p, 'max_price', None)
            ):

                avg_price = (
                    p.min_price +
                    p.max_price
                ) / 2

                if category not in category_prices:
                    category_prices[category] = []

                category_prices[category].append(
                    avg_price
                )

        final_avg = {}

        for cat, prices in category_prices.items():
            final_avg[cat] = sum(prices) / len(prices)

        return final_avg


def get_personal_stats() -> Dict[str, Any]:

    try:

        username = nicegui_app.storage.user.get(
            'username',
            ''
        )

        wishlist = state.wishlist if state.wishlist else []
        routine = state.routine if state.routine else []

        categories = []

        for p in wishlist:

            cat = p.get('category')

            if cat:
                categories.append(cat)

        if categories:
            fav_category = Counter(categories).most_common(1)[0][0]

        else:
            fav_category = '-'

        ingredients = []

        for p in wishlist:

            ing = p.get('ingredients', '')

            if ing:

                ingredients.extend([
                    x.strip()
                    for x in ing.split(',')
                    if len(x.strip()) > 2
                ])

        fav_ingredient = (
            Counter(ingredients).most_common(1)[0][0]
            if ingredients else '-'
        )

        return {
            'username': username or 'User',
            'wishlist_count': len(wishlist),
            'routine_count': len(routine),
            'fav_category': fav_category,
            'fav_ingredient': fav_ingredient,
        }

    except Exception as e:

        print(f'Error personal stats: {e}')

        return {
            'username': 'User',
            'wishlist_count': 0,
            'routine_count': 0,
            'fav_category': '-',
            'fav_ingredient': '-',
        }


# ── IMAGE ──────────────────────────────────────────
# ── CHARTS ─────────────────────────────────────────
@lru_cache(maxsize=1)
def chart_rating_distribution():
    """Return ECharts option dict for rating distribution (donut)."""
    rating_dist = get_rating_distribution()
    data = [ { 'name': k, 'value': v } for k, v in rating_dist.items() if v > 0 ]

    if not data:
        return {
            'title': { 'text': 'Belum ada data rating.', 'left': 'center', 'top': '40%', 'textStyle': { 'color': '#6B7280' } }
        }

    option = {
        'tooltip': { 'trigger': 'item', 'formatter': '{b}: {c} ({d}%)' },
        'legend': { 'orient': 'horizontal', 'bottom': 0, 'data': [d['name'] for d in data], 'textStyle': { 'fontSize': 12 } },
        'color': PALETTE,
        'series': [ {
            'name': 'Rentang Rating',
            'type': 'pie',
            'radius': ['45%', '70%'],
            'avoidLabelOverlap': False,
            'label': { 'show': True, 'position': 'center', 'formatter': '{d}%\n{b}', 'fontSize': 14, 'fontWeight': 'bold' },
            'labelLine': { 'show': False },
            'data': data
        } ]
    }
    return option


@lru_cache(maxsize=1)
def chart_top_brands():
    """Return ECharts option dict for top brands bar chart."""
    brands = get_top_brands()
    pairs = sorted(brands.items(), key=lambda x: x[1], reverse=True)
    names = [p[0] for p in pairs]
    counts = [p[1] for p in pairs]

    if not counts:
        return { 'title': { 'text': 'Belum ada data brand.', 'left': 'center', 'top': '40%', 'textStyle': { 'color': '#6B7280' } } }

    option = {
        'tooltip': { 'trigger': 'axis', 'axisPointer': { 'type': 'shadow' } },
        'grid': { 'left': 20, 'right': 20, 'top': 20, 'bottom': 80 },
        'xAxis': { 'type': 'category', 'data': names, 'axisLabel': { 'rotate': 30, 'interval': 0, 'fontSize': 11 } },
        'yAxis': { 'type': 'value' },
        'color': [ ACCENT_INDIGO ],
        'series': [ {
            'data': counts,
            'type': 'bar',
            'barWidth': '50%',
            'label': { 'show': True, 'position': 'top', 'fontWeight': '700' }
        } ]
    }
    return option


@lru_cache(maxsize=1)
def chart_category_distribution():
    """Return ECharts option dict for category distribution (horizontal bar)."""
    categories = get_category_distribution()
    pairs = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    names = [p[0] for p in pairs]
    counts = [p[1] for p in pairs]

    if not counts:
        return { 'title': { 'text': 'Belum ada data kategori.', 'left': 'center', 'top': '40%', 'textStyle': { 'color': '#6B7280' } } }

    total = sum(counts) or 1
    # Prepare labels showing value and percent
    data = []
    for name, val in zip(names, counts):
        pct = int(round(val / total * 100))
        data.append({ 'value': val, 'name': name, 'label': { 'show': True, 'position': 'right', 'formatter': f"{val} ({pct}%)" } })

    option = {
        'tooltip': { 'trigger': 'axis', 'axisPointer': { 'type': 'shadow' } },
        'grid': { 'left': 20, 'right': 20, 'top': 20, 'bottom': 40 },
        'xAxis': { 'type': 'value' },
        'yAxis': { 'type': 'category', 'data': names, 'inverse': True, 'axisLabel': { 'fontSize': 12 } },
        'color': [ '#FB923C' ],
        'series': [ {
            'type': 'bar',
            'data': data,
            'barWidth': '35%',
            'label': { 'show': True, 'position': 'right', 'fontSize': 10 }
        } ]
    }
    return option


@lru_cache(maxsize=1)
def chart_avg_price():
    """Return ECharts option dict for average price per category."""
    prices = get_avg_price_by_category()
    pairs = sorted(prices.items(), key=lambda x: x[1], reverse=True)
    names = [p[0] for p in pairs]
    vals = [p[1] for p in pairs]

    if not vals:
        return { 'title': { 'text': 'Belum ada data harga.', 'left': 'center', 'top': '40%', 'textStyle': { 'color': '#6B7280' } } }

    # format labels as Rupiah
    def fmt(v):
        try:
            return f"Rp{int(round(v)):,}".replace(',', '.')
        except Exception:
            return str(int(v))

    option = {
        'tooltip': { 'trigger': 'axis', 'axisPointer': { 'type': 'shadow' } },
        'grid': { 'left': 20, 'right': 20, 'top': 20, 'bottom': 70 },
        'xAxis': { 'type': 'category', 'data': names, 'axisLabel': { 'rotate': 20, 'interval': 0, 'fontSize': 11 } },
        'yAxis': { 'type': 'value' },
        'color': [ ACCENT_TEAL ],
        'series': [ {
            'type': 'bar',
            'data': [ { 'value': v, 'label': { 'show': True, 'position': 'top', 'fontSize': 10, 'formatter': fmt(v) } } for v in vals ],
            'barWidth': '45%'
        } ]
    }
    return option


# ── TRENDING ───────────────────────────────────────
def build_trending_list(products: List[Dict[str, Any]]):

    for rank, p in enumerate(products, start=1):

        with ui.row().classes(
            'w-full items-center justify-between py-4'
        ).style(
            'border-bottom:1px solid #FCE7F3;'
        ):

            with ui.row().classes(
                'items-center gap-4'
            ):

                with ui.element('div').style(
                    '''
                    width:42px;
                    height:42px;
                    border-radius:9999px;
                    background:#E9F99D;
                    border:2px solid #D9F99D;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    font-weight:700;
                    color:#EC4899;
                    font-size:20px;
                    '''
                ):
                    ui.label(str(rank))


                # Provide a small SVG fallback when image_url missing
                img_src = p.get('image_url') or ''
                if not img_src:
                    # simple SVG placeholder with brand initial
                    initial = (p.get('brand') or 'X')[0:1].upper()
                    svg = (
                        f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
                        '<rect width="100%" height="100%" fill="#FFF1F7"/>'
                        f'<text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
                        f'fill="#EC4899" font-size="28" font-weight="700">{initial}</text>'
                        '</svg>'
                    )
                    img_src = f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"

                ui.image(img_src).style(
                    '''
                    width:64px;
                    height:64px;
                    border-radius:8px;
                    object-fit:cover;
                    border:1px solid #F3F4F6;
                    '''
                )

                with ui.column().classes('gap-0'):

                    ui.label(
                        (p['brand'] or 'MEREK PRODUK').upper()
                    ).style(
                        '''
                        font-size:10px;
                        font-weight:700;
                        color:#FF69B4;
                        '''
                    )

                    ui.label(
                        p['name'] or 'NAMA PRODUK'
                    ).style(
                        '''
                        font-size:13px;
                        font-weight:800;
                        color:black;
                        '''
                    )

            with ui.row().classes(
                'items-center gap-1'
            ):

                ui.label('⭐')

                ui.label(
                    f'{p["rating"]:.1f}/5'
                ).style(
                    '''
                    font-size:18px;
                    font-weight:800;
                    color:black;
                    '''
                )


# ── PERSONAL ───────────────────────────────────────
def build_personal_section(stats: Dict[str, Any]):

    with ui.card().classes('w-full p-6 rounded-3xl') .style(f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW};'):

        ui.label(f'Halo, {stats["username"]}!').classes('text-2xl font-bold text-gray-900 mb-1').style('font-size:20px;')

        ui.label('Ini insight skincare personal mu').classes('text-gray-500 mb-5').style('font-size:13px;')

        with ui.row().classes(
            'w-full gap-4'
        ):

            tiles = [
                ('Produk Wishlist', str(stats['wishlist_count']), 'favorite'),
                ('Produk di Routine', str(stats['routine_count']), 'calendar_month'),
                ('Kategori Favorit', stats['fav_category'], 'star'),
                ('Bahan Favorit', stats['fav_ingredient'], 'spa'),
            ]

            for label, value, icon in tiles:

                with ui.card().classes('flex-1 rounded-2xl p-5') .style(f'background:{CARD_BG_NEUTRAL}; border:1px solid rgba(15,23,42,0.04);'):

                    ui.icon(icon).style(f'color:{ACCENT_INDIGO}; font-size:20px; margin-bottom:10px;')

                    ui.label(value).style('color:#111827; font-size:28px; font-weight:800; line-height:1;')

                    ui.label(label).style('color:#6B7280; font-size:13px; font-weight:700; margin-top:10px;')


# ── PAGE ───────────────────────────────────────────
def show_page():

    chart_rating_distribution.cache_clear()
    chart_top_brands.cache_clear()
    chart_category_distribution.cache_clear()
    chart_avg_price.cache_clear()

    auth_redirect = AuthManager.require_auth()

    if auth_redirect:
        return auth_redirect

    UIComponents.navbar()
    UIComponents.sidebar()

    with ui.row().classes(
        'items-center gap-3 mt-4 mb-6'
    ):

        ui.label('✨').classes('text-3xl')

        with ui.column().classes('gap-0'):

            ui.label('Beauty Insights').classes('text-3xl font-extrabold text-gray-800').style(f'font-size:28px; line-height:1; background:{HEADER_GRADIENT}; -webkit-background-clip:text; color:transparent;')
            ui.label('Insight & analitik data produk Sociolla').classes('text-sm text-gray-500').style('font-size:14px;')
        
        with ui.button(
            'Refresh Data',
            icon='refresh',
            on_click=lambda: ui.navigate.reload()
        ).props(
            'outline'
        ).classes(
            'ml-auto'
        ).style(
            '''
            color:#60A5FA;
            border:1px solid #93C5FD;
            border-radius:12px;
            font-weight:700;
            '''
        ):
            pass

    # TOP 10

    with ui.card().classes(
        'w-full p-5 rounded-3xl mb-5'
    ).style(
        f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW} padding:20px;'
    ):

        ui.label('Trending (Top 10)').classes('font-bold mb-4').style('font-size:13px; text-transform:uppercase; letter-spacing:1px; color:'+ACCENT_INDIGO+';')

        trending = get_trending_products()

        if trending:
            build_trending_list(trending)

        else:
            ui.label('Belum ada data produk.')

    # CHARTS
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes('flex-1 p-4 rounded-2xl') .style(f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW};'):
            ui.label('Distribusi Rating').style('font-size:19px; text-transform:uppercase; letter-spacing:1px; color:'+ACCENT_INDIGO+'; font-weight:700; margin-bottom:8px;')
            ui.echart(chart_rating_distribution()).classes('w-full rounded-lg')
            ui.label('Chart menunjukkan persentase produk berdasarkan rentang rating dari sumber Sociolla/fallback.').classes('text-sm text-gray-500 mt-2').style('font-size:13px;')

        with ui.card().classes('flex-1 p-5 rounded-2xl') .style(f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW};'):
            ui.label('Top Brands').style('font-size:19px; text-transform:uppercase; letter-spacing:1px; color:'+ACCENT_INDIGO+'; font-weight:700; margin-bottom:8px;')
            ui.echart(chart_top_brands()).classes('w-full rounded-lg')
            ui.label('Top brands: jumlah produk per merek (urut dari paling banyak).').classes('text-sm text-gray-500 mt-2').style('font-size:13px;')

    with ui.row().classes('w-full gap-4 mb-5'):
        with ui.card().classes('flex-1 p-5 rounded-2xl') .style(f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW};'):
            ui.label('Distribusi Kategori').style('font-size:19px; text-transform:uppercase; letter-spacing:1px; color:'+ACCENT_INDIGO+'; font-weight:700; margin-bottom:8px;')
            ui.echart(chart_category_distribution()).classes('w-full rounded-lg')
            ui.label('Distribusi kategori: proporsi produk per kategori. Angka di samping adalah jumlah produk dan persentase.').classes('text-sm text-gray-500 mt-2').style('font-size:13px;')

        with ui.card().classes('flex-1 p-5 rounded-2xl') .style(f'background:{CARD_BG_NEUTRAL}; {CARD_SHADOW};'):
            ui.label('Rata-rata Harga per Kategori').style('font-size:19px; text-transform:uppercase; letter-spacing:1px; color:'+ACCENT_INDIGO+'; font-weight:700; margin-bottom:8px;')
            ui.echart(chart_avg_price()).classes('w-full rounded-lg')
            ui.label('Rata-rata harga per kategori (dalam Rupiah). Nilai di atas bar menunjukkan estimasi rata-rata.').classes('text-sm text-gray-500 mt-2').style('font-size:13px;')

    # PERSONAL
    with ui.row().classes('items-center gap-2 mt-4 mb-3'):
        ui.label('Insight Personal').classes('text-3xl font-extrabold text-gray-800').style(f'font-size:28px; line-height:1; background:{HEADER_GRADIENT}; -webkit-background-clip:text; color:transparent;')
        ui.label('(dari wishlist & routine-mu)').classes('text-sm text-gray-500').style('font-size:13px;')

    build_personal_section(
        get_personal_stats()
    )
