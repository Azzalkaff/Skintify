from nicegui import ui, app as nicegui_app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi
from collections import Counter
from typing import List, Dict, Any

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt  # type: ignore[import-untyped]
import matplotlib.patches as mpatches  # type: ignore[import-untyped]

import io
import base64
from functools import lru_cache


# ── WARNA ──────────────────────────────────────────
PINK_PRIMARY = '#EC4899'
PINK_LIGHT = '#F9A8D4'
PINK_SOFT = '#FCE7F3'


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

        scored = []

        for p in products:

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

        brand_counter = Counter()

        for p in products:

            if p.brand:
                brand_counter[p.brand] += 1

        return dict(
            brand_counter.most_common(limit)
        )


def get_category_distribution() -> Dict[str, int]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        category_counter = Counter()

        for p in products:

            if p.category:
                category_counter[p.category] += 1

        return dict(category_counter)

def get_avg_price_by_category() -> Dict[str, float]:

    with SessionLocal() as session:

        products = session.query(
            SociollaReferensi
        ).all()

        category_prices = {}

        for p in products:

            if (
                p.category and
                p.min_price and
                p.max_price
            ):

                avg_price = (
                    p.min_price +
                    p.max_price
                ) / 2

                if p.category not in category_prices:
                    category_prices[p.category] = []

                category_prices[p.category].append(
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
def plot_to_base64(fig) -> str:

    buf = io.BytesIO()

    fig.savefig(
        buf,
        format='png',
        dpi=130,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none'
    )

    buf.seek(0)

    img_base64 = base64.b64encode(
        buf.read()
    ).decode()

    plt.close(fig)

    return f"data:image/png;base64,{img_base64}"


# ── CHARTS ─────────────────────────────────────────
@lru_cache(maxsize=1)
def chart_rating_distribution():

    rating_dist = get_rating_distribution()

    labels = [
        k for k, v in rating_dist.items()
        if v > 0
    ]

    sizes = [
        v for v in rating_dist.values()
        if v > 0
    ]

    fig, ax = plt.subplots(figsize=(6, 5))

    fig.patch.set_facecolor('white')

    if not sizes:

        ax.text(
            0.5,
            0.5,
            'Belum ada data rating.',
            ha='center',
            va='center'
        )

        ax.axis('off')

        return plot_to_base64(fig)

    colors = [
        PINK_PRIMARY,
        '#F97316',
        '#EAB308',
        '#22C55E',
        '#06B6D4'
    ][:len(labels)]

    ax.pie(
        sizes,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        wedgeprops={
            'width': 0.45,
            'edgecolor': 'white'
        },
        textprops={
            'fontsize': 12,
            'fontweight': 'bold'
        }
    )

    legend_labels = [
        f'{label} ({size})'
        for label, size in zip(labels, sizes)
    ]

    ax.legend(
        legend_labels,
        loc='lower center',
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        fontsize=9,
        frameon=False
    )

    ax.set_title(
        'Distribusi Rating',
        fontsize=13,
        fontweight='bold',
        color='#1F2937',
        loc='left'
    )

    fig.patch.set_facecolor('#FFF7FB')
    ax.set_facecolor('#FFF7FB')

    plt.tight_layout(pad=2)

    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_top_brands():

    brands = get_top_brands()

    names = list(brands.keys())
    counts = list(brands.values())

    fig, ax = plt.subplots(figsize=(7, 5))

    fig.patch.set_facecolor('white')

    if not counts:

        ax.text(
            0.5,
            0.5,
            'Belum ada data brand.',
            ha='center',
            va='center'
        )

        ax.axis('off')

        return plot_to_base64(fig)

    bars = ax.bar(
        names,
        counts,
        color='#EC4899',
        width=0.7
    )

    for bar in bars:
        bar.set_linewidth(0)

    setup_ax(ax, 'Top Brands')

    plt.xticks(rotation=30)

    plt.tight_layout()

    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_category_distribution():

    categories = get_category_distribution()

    names = list(categories.keys())
    counts = list(categories.values())

    fig, ax = plt.subplots(figsize=(6, 5))

    fig.patch.set_facecolor('white')

    if not counts:

        ax.text(
            0.5,
            0.5,
            'Belum ada data kategori.',
            ha='center',
            va='center'
        )

        ax.axis('off')

        return plot_to_base64(fig)

    colors = [
        '#EC4899',
        '#F97316',
        '#EAB308',
        '#22C55E',
        '#06B6D4',
        '#8B5CF6'
    ]

    bars = ax.barh(
        names,
        counts,
        color='#F472B6'
    )

    for bar in bars:
        bar.set_linewidth(0)

    setup_ax(
        ax,
        'Distribusi Kategori',
        show_grid_x=True,
        show_grid_y=False
    )

    fig.patch.set_facecolor('#FFF7FB')
    ax.set_facecolor('#FFF7FB')

    plt.tight_layout(pad=2)

    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_avg_price():

    prices = get_avg_price_by_category()

    names = list(prices.keys())
    vals = list(prices.values())

    fig, ax = plt.subplots(figsize=(8, 5))

    fig.patch.set_facecolor('white')

    if not vals:

        ax.text(
            0.5,
            0.5,
            'Belum ada data harga.',
            ha='center',
            va='center'
        )

        ax.axis('off')

        return plot_to_base64(fig)

    bars = ax.bar(
        names,
        vals,
        color='#F9A8D4',
        width=0.6
    )

    for bar in bars:
        bar.set_linewidth(0)

    setup_ax(
        ax,
        'Rata-rata Harga per Kategori'
    )

    plt.xticks(
        rotation=15,
        ha='right'
    )

    fig.patch.set_facecolor('#FFF7FB')
    ax.set_facecolor('#FFF7FB')
    plt.tight_layout()

    return plot_to_base64(fig)


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


                ui.image(p.get('image_url', '')).style(
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

    with ui.card().classes(
        'w-full p-6 shadow-sm rounded-3xl border border-pink-100'
    ).style(
        'background:#FFF7FB;'
    ):

        ui.label(
            f'Halo, {stats["username"]}!'
        ).classes(
            'text-3xl font-bold text-black mb-1'
        )

        ui.label(
            'Ini insight skincare personal mu'
        ).classes(
            'text-gray-500 mb-5'
        )

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

                with ui.card().classes(
                    'flex-1 rounded-2xl p-5'
                ).style(
                    '''
                    background:#FFF1F7;
                    border:1px solid #FBCFE8;
                    box-shadow:none;
                    '''
                ):

                    ui.icon(icon).style(
                        '''
                        color:#EC4899;
                        font-size:22px;
                        margin-bottom:10px;
                        '''
                    )

                    ui.label(value).style(
                        '''
                        color:#FF4DA6;
                        font-size:34px;
                        font-weight:800;
                        line-height:1;
                        '''
                    )

                    ui.label(label).style(
                        '''
                        color:#BDBDBD;
                        font-size:14px;
                        font-weight:700;
                        margin-top:10px;
                        '''
                    )


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

            ui.label(
                'Beauty Insights'
            ).classes(
                'text-2xl font-bold text-gray-800'
            )

            ui.label(
                'Insight & analitik data produk Sociolla'
            ).classes(
                'text-sm text-gray-400'
            )
        
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
        'w-full p-5 shadow-sm rounded-3xl border border-pink-100 mb-5'
    ).style(
        'background:#FFF7FB;'
    ):

        ui.label(
            'Trending (Top 10)'
        ).classes(
            'font-bold text-xl mb-4'
        )

        trending = get_trending_products()

        if trending:
            build_trending_list(trending)

        else:
            ui.label(
                'Belum ada data produk.'
            )

    # CHARTS
    with ui.row().classes(
        'w-full gap-4 mb-4'
    ):

        with ui.card().classes(
            'flex-1 p-4 shadow-sm rounded-2xl border border-pink-100'
        ).style('background:#FFF7FB;'):

            ui.image(
                chart_rating_distribution()
            ).classes(
                'w-full rounded-lg'
            )

        with ui.card().classes(
            'flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'
        ):

            ui.image(
                chart_top_brands()
            ).classes(
                'w-full rounded-lg'
            )

    with ui.row().classes(
        'w-full gap-4 mb-5'
    ):

        with ui.card().classes(
            'flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'
        ).style('background:#FFF7FB;'):

            ui.image(
                chart_category_distribution()
            ).classes(
                'w-full rounded-lg'
            )

        with ui.card().classes(
            'flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'
        ).style('background:#FFF7FB;'):

            ui.image(
                chart_avg_price()
            ).classes(
                'w-full rounded-lg'
            )

    # PERSONAL
    with ui.row().classes(
        'items-center gap-2 mt-4 mb-3'
    ):

        ui.label(
            'Insight Personal'
        ).classes(
            'text-3xl font-bold text-black'
        )

        ui.label(
            '(dari wishlist & routine-mu)'
        ).style(
            'color:#94A3B8; text-decoration:underline; font-size:18px;'
        )

    build_personal_section(
        get_personal_stats()
    )