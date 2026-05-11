from nicegui import ui
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi
from collections import Counter
from typing import List, Dict, Any
import matplotlib.pyplot as plt  # type: ignore[import-untyped]
import matplotlib.patches as mpatches  # type: ignore[import-untyped]
import io
import base64
from functools import lru_cache

# ── Warna tema konsisten ──────────────────────────────────────────
PINK_PRIMARY   = '#EC4899'
PINK_LIGHT     = '#F9A8D4'
PINK_SOFT      = '#FCE7F3'
PINK_DARK      = '#9D174D'
PINK_SHADES    = ['#F472B6', '#EC4899', '#DB2777', '#BE185D', '#9D174D',
                  '#831843', '#500724', '#FDA4AF', '#FB7185']

def setup_ax(ax, title: str, show_grid_x=False, show_grid_y=True):
    """Terapkan styling modern ke axes"""
    ax.set_title(title, fontsize=13, fontweight='bold', color='#1F2937',
                 pad=14, loc='left')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E5E7EB')
    ax.spines['bottom'].set_color('#E5E7EB')
    ax.tick_params(colors='#6B7280', labelsize=9)
    if show_grid_y:
        ax.yaxis.grid(True, linestyle='--', linewidth=0.5, color='#F3F4F6', alpha=0.8)
        ax.set_axisbelow(True)
    if show_grid_x:
        ax.xaxis.grid(True, linestyle='--', linewidth=0.5, color='#F3F4F6', alpha=0.8)
        ax.set_axisbelow(True)
    ax.set_facecolor('#FAFAFA')


# ── Query helpers (tidak diubah) ──────────────────────────────────
def get_trending_products() -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        products = session.query(SociollaReferensi).order_by(
            SociollaReferensi.rating_sociolla.desc()
        ).limit(10).all()
        return [
            {'name': p.product_name, 'rating': p.rating_sociolla or 0, 'reviews': p.total_reviews or 0}
            for p in products
        ]

def get_rating_distribution() -> Dict[str, int]:
    with SessionLocal() as session:
        products = session.query(SociollaReferensi.rating_sociolla).all()
        distribution = {
            '4.5–5.0': 0, '4.0–4.4': 0, '3.5–3.9': 0, '3.0–3.4': 0, '<3.0': 0
        }
        for (rating,) in products:
            if rating is None:
                continue
            if rating >= 4.5:   distribution['4.5–5.0'] += 1
            elif rating >= 4.0: distribution['4.0–4.4'] += 1
            elif rating >= 3.5: distribution['3.5–3.9'] += 1
            elif rating >= 3.0: distribution['3.0–3.4'] += 1
            else:               distribution['<3.0']    += 1
        return distribution

def get_top_brands(limit: int = 8) -> Dict[str, int]:
    with SessionLocal() as session:
        brands = session.query(SociollaReferensi.brand).all()
        brand_counts = Counter(b[0] for b in brands if b[0])
        return dict(brand_counts.most_common(limit))

def get_category_distribution() -> Dict[str, int]:
    with SessionLocal() as session:
        categories = session.query(SociollaReferensi.category).all()
        cat_counts = Counter(c[0] for c in categories if c[0])
        return dict(cat_counts.most_common())

def get_avg_price_by_category() -> Dict[str, float]:
    with SessionLocal() as session:
        categories = session.query(
            SociollaReferensi.category,
            (SociollaReferensi.min_price + SociollaReferensi.max_price) / 2
        ).all()
        cat_prices, cat_counts = {}, {}
        for cat, price in categories:
            if cat and price:
                cat_prices[cat] = cat_prices.get(cat, 0) + price
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        return {cat: cat_prices[cat] / cat_counts[cat] for cat in cat_prices}

def plot_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=130, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{img_base64}"


# ── Komponen chart ────────────────────────────────────────────────
@lru_cache(maxsize=1)
def chart_trending():
    trending = get_trending_products()
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor('white')

    names   = [p['name'][:18] for p in trending]
    ratings = [p['rating'] for p in trending]

    # Gradasi warna berdasarkan urutan
    colors = [PINK_SHADES[min(i, len(PINK_SHADES) - 1)] for i in range(len(names))]
    colors.reverse()

    bars = ax.barh(names, ratings, color=colors, height=0.6, zorder=2)

    # Rounded feel dengan alpha overlay
    for bar in bars:
        bar.set_linewidth(0)

    ax.set_xlim(4.0, 5.05)
    ax.set_xlabel('Rating', fontsize=9, color='#6B7280', labelpad=6)
    setup_ax(ax, 'Produk Trending (Top 10)', show_grid_x=True, show_grid_y=False)

    # Value label di dalam bar
    for bar, rating in zip(bars, ratings):
        ax.text(bar.get_width() - 0.03, bar.get_y() + bar.get_height() / 2,
                f'★ {rating:.1f}', va='center', ha='right',
                fontsize=8.5, fontweight='bold', color='white')

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_rating_distribution():
    rating_dist = get_rating_distribution()
    labels = [k for k, v in rating_dist.items() if v > 0]
    sizes  = [v for v in rating_dist.values() if v > 0]
    colors = [PINK_PRIMARY, '#F97316', '#EAB308', '#22C55E', '#06B6D4'][:len(labels)]
    star_labels = ['★★★★★', '★★★★', '★★★', '★★', '★'][:len(labels)]

    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor('white')

    wedges, _, autotexts = ax.pie(
        sizes,
        labels=None,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2.5),
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight('bold')
        at.set_color('white')

    # Legend manual
    legend_labels = [f'{s}  {l} ({v})' for s, l, v in zip(star_labels, labels, sizes)]
    patches = [mpatches.Patch(color=c, label=lbl) for c, lbl in zip(colors, legend_labels)]
    ax.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.18),
              ncol=1, fontsize=8, frameon=False, labelcolor='#374151')

    ax.set_title('Distribusi Rating', fontsize=13, fontweight='bold',
                 color='#1F2937', pad=10, loc='left')

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_top_brands():
    brands = get_top_brands()
    brand_names  = list(brands.keys())
    brand_counts = list(brands.values())

    # Warna: bar tertinggi lebih gelap
    max_c = max(brand_counts)
    colors = [PINK_PRIMARY if c == max_c else PINK_LIGHT for c in brand_counts]

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor('white')

    bars = ax.bar(brand_names, brand_counts, color=colors, width=0.55,
                  zorder=2, linewidth=0)
    setup_ax(ax, 'Top Brands', show_grid_y=True)
    ax.set_ylabel('Jumlah Produk', fontsize=9, color='#6B7280', labelpad=6)
    ax.set_ylim(0, max_c * 1.25)
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.xticks(rotation=35, ha='right', fontsize=8.5)

    # Value labels di atas bar
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.05,
                str(int(h)), ha='center', va='bottom',
                fontsize=9, fontweight='bold', color='#9D174D')

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_category_distribution():
    categories = get_category_distribution()
    cat_names  = list(categories.keys())
    cat_counts = list(categories.values())

    palette = [PINK_PRIMARY, '#F97316', '#EAB308', '#22C55E', '#06B6D4',
               '#8B5CF6', '#EC4899', '#14B8A6']
    colors = palette[:len(cat_names)]

    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor('white')

    wedges, _, autotexts = ax.pie(
        cat_counts,
        labels=None,
        colors=colors,
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.72,
        wedgeprops=dict(width=0.55, edgecolor='white', linewidth=2.5),
    )
    for at in autotexts:
        at.set_fontsize(9)
        at.set_fontweight('bold')
        at.set_color('white')

    # Legend
    patches = [mpatches.Patch(color=c, label=f'{n} ({v})')
               for c, n, v in zip(colors, cat_names, cat_counts)]
    ax.legend(handles=patches, loc='lower center', bbox_to_anchor=(0.5, -0.22),
              ncol=2, fontsize=8, frameon=False, labelcolor='#374151')

    ax.set_title('Distribusi Kategori', fontsize=13, fontweight='bold',
                 color='#1F2937', pad=10, loc='left')

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


@lru_cache(maxsize=1)
def chart_avg_price():
    avg_prices    = get_avg_price_by_category()
    sorted_prices = dict(sorted(avg_prices.items(), key=lambda x: x[1], reverse=True))
    cat_names     = list(sorted_prices.keys())
    prices        = list(sorted_prices.values())

    # Gradasi intensitas berdasarkan harga
    max_p  = max(prices)
    alphas = [0.45 + 0.55 * (p / max_p) for p in prices]
    r, g, b = 0xEC / 255, 0x48 / 255, 0x99 / 255
    colors = [(r, g, b, a) for a in alphas]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('white')

    bars = ax.bar(cat_names, prices, color=colors, width=0.55, zorder=2, linewidth=0)
    setup_ax(ax, 'Rata-rata Harga per Kategori', show_grid_y=True)
    ax.set_ylabel('Harga (Rp)', fontsize=9, color='#6B7280', labelpad=6)
    ax.set_ylim(0, max_p * 1.2)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'Rp {int(x):,}'))
    plt.xticks(rotation=35, ha='right', fontsize=8.5)

    # Value labels
    for bar, price in zip(bars, prices):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + max_p * 0.015,
                f'Rp {int(price):,}', ha='center', va='bottom',
                fontsize=8, fontweight='bold', color='#9D174D', rotation=0)

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


# ── Page utama ────────────────────────────────────────────────────
def show_page():
    """MISI NAJLA: Membuat Visualisasi Statistik dengan Matplotlib"""

    # --- JANGAN DIUBAH (Wajib untuk Navigasi) ---
    auth_redirect = AuthManager.require_auth()
    if auth_redirect: return auth_redirect
    UIComponents.navbar()
    UIComponents.sidebar()
    # -------------------------------------------

    # ── Header ───────────────────────────────────────────────────
    with ui.row().classes('items-center gap-3 mt-4 mb-6'):
        ui.label('📊').classes('text-3xl')
        with ui.column().classes('gap-0'):
            ui.label('Statistik Produk Skincare').classes('text-2xl font-bold text-gray-800')
            ui.label('Insight & analitik data produk Sociolla').classes('text-sm text-gray-400')
        
        ui.space()
        
        def refresh_stats():
            chart_trending.cache_clear()
            chart_rating_distribution.cache_clear()
            chart_top_brands.cache_clear()
            chart_category_distribution.cache_clear()
            chart_avg_price.cache_clear()
            ui.notify('Data statistik diperbarui!', color='positive')
            ui.navigate.to('/stats')

        ui.button('Refresh Data', icon='refresh', on_click=refresh_stats).props('outline').classes('rounded-xl text-pink-500 border-pink-200')

    # ── ROW 1: Trending + Rating Distribution ─────────────────────
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('🔥 Produk Trending (Top 10)').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_trending()).classes('w-full rounded-lg')

        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('⭐ Distribusi Rating').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_rating_distribution()).classes('w-full rounded-lg')

    # ── ROW 2: Top Brands + Category Distribution ─────────────────
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('🏷️ Top Brands').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_top_brands()).classes('w-full rounded-lg')

        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('🧴 Kategori Produk').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_category_distribution()).classes('w-full rounded-lg')

    # ── ROW 3: Rata-rata Harga ────────────────────────────────────
    with ui.row().classes('w-full gap-4'):
        with ui.card().classes('w-full p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('💰 Rata-rata Harga per Kategori').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_avg_price()).classes('w-full rounded-lg')