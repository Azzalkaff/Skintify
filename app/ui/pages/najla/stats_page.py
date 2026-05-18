from nicegui import ui, app as nicegui_app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.database.models import SociollaReferensi, Routine, RoutineItem
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


# ── Query helpers ─────────────────────────────────────────────────

def get_trending_products(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Top produk berdasarkan skor trending = total_wishlist + total_reviews.
    Lebih meaningful daripada sort by rating saja karena mencerminkan
    seberapa banyak orang tertarik & memberikan ulasan.
    """
    with SessionLocal() as session:
        products = session.query(SociollaReferensi).filter(
            SociollaReferensi.is_in_stock == True
        ).all()

        scored = []
        for p in products:
            wishlist = p.total_wishlist  or 0
            reviews  = p.total_reviews   or 0
            rating   = p.rating_sociolla or 0
            # Skor gabungan: aktivitas user (wishlist + review) x bobot rating
            score = (wishlist + reviews) * (rating / 5.0 if rating else 0.5)
            scored.append({
                'name'      : p.product_name,
                'brand'     : p.brand or '',
                'category'  : p.category or '',
                'rating'    : rating,
                'reviews'   : reviews,
                'wishlist'  : wishlist,
                'score'     : score,
                'image_url' : p.image_url or '',
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:limit]


def get_rating_distribution() -> Dict[str, int]:
    from sqlalchemy import func, case
    with SessionLocal() as session:
        results = session.query(
            func.sum(case(((SociollaReferensi.rating_sociolla >= 4.5), 1), else_=0)),
            func.sum(case(((SociollaReferensi.rating_sociolla >= 4.0) & (SociollaReferensi.rating_sociolla < 4.5), 1), else_=0)),
            func.sum(case(((SociollaReferensi.rating_sociolla >= 3.5) & (SociollaReferensi.rating_sociolla < 4.0), 1), else_=0)),
            func.sum(case(((SociollaReferensi.rating_sociolla >= 3.0) & (SociollaReferensi.rating_sociolla < 3.5), 1), else_=0)),
            func.sum(case(((SociollaReferensi.rating_sociolla < 3.0) & (SociollaReferensi.rating_sociolla != None), 1), else_=0))
        ).first()
        
        distribution = {
            '4.5–5.0': int(results[0] or 0),
            '4.0–4.4': int(results[1] or 0),
            '3.5–3.9': int(results[2] or 0),
            '3.0–3.4': int(results[3] or 0),
            '<3.0': int(results[4] or 0)
        }
        return distribution

def get_top_brands(limit: int = 8) -> Dict[str, int]:
    from sqlalchemy import func
    with SessionLocal() as session:
        results = session.query(
            SociollaReferensi.brand,
            func.count(SociollaReferensi.brand)
        ).filter(SociollaReferensi.brand != None)\
         .group_by(SociollaReferensi.brand)\
         .order_by(func.count(SociollaReferensi.brand).desc())\
         .limit(limit).all()
        return dict(results)

def get_category_distribution() -> Dict[str, int]:
    from sqlalchemy import func
    with SessionLocal() as session:
        results = session.query(
            SociollaReferensi.category,
            func.count(SociollaReferensi.category)
        ).filter(SociollaReferensi.category != None)\
         .group_by(SociollaReferensi.category)\
         .order_by(func.count(SociollaReferensi.category).desc()).all()
        return dict(results)

def get_avg_price_by_category() -> Dict[str, float]:
    from sqlalchemy import func
    with SessionLocal() as session:
        results = session.query(
            SociollaReferensi.category,
            func.avg((SociollaReferensi.min_price + SociollaReferensi.max_price) / 2)
        ).filter(
            SociollaReferensi.category != None,
            SociollaReferensi.min_price != None,
            SociollaReferensi.max_price != None
        ).group_by(SociollaReferensi.category).all()
        return {cat: float(avg_price) for cat, avg_price in results if avg_price is not None}

def get_personal_stats() -> Dict[str, Any]:
    """Ambil statistik personal user yang sedang login."""
    try:
        username = nicegui_app.storage.user.get('username', '')
        wishlist = state.wishlist or []
        routine  = state.routine  or []

        cats = [
            p.get('category', '')
            for p in wishlist
            if p.get('category')
        ]

        makeup_categories = [
            'Lip Product',
            'Powder',
            'Blush',
            'Cushion',
            'Eye Product'
        ]

        skincare_categories = [
            'Serum',
            'Moisturizer',
            'Sunscreen',
            'Cleanser',
            'Toner',
            'Mask'
        ]

        makeup_count = sum(
            1 for c in cats
            if c in makeup_categories
        )

        skincare_count = sum(
            1 for c in cats
            if c in skincare_categories
        )

        if makeup_count > skincare_count:
            fav_category = 'Makeup'

        elif skincare_count > makeup_count:
            fav_category = 'Skincare'

        elif makeup_count == 0 and skincare_count == 0:
            fav_category = '-'

        else:
            fav_category = 'Mix Makeup & Skincare'

        # FAVORITE INGREDIENT
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
def chart_rating_distribution():
    rating_dist = get_rating_distribution()
    labels = [k for k, v in rating_dist.items() if v > 0]
    sizes  = [v for v in rating_dist.values() if v > 0]
    
    if not sizes:
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor('white')
        ax.text(0.5, 0.5, 'Belum ada data rating.', ha='center', va='center', fontsize=10, color='gray')
        ax.set_title('Distribusi Rating', fontsize=13, fontweight='bold', color='#1F2937', pad=10, loc='left')
        ax.axis('off')
        plt.tight_layout(pad=1.5)
        return plot_to_base64(fig)

    colors = [PINK_PRIMARY, '#F97316', '#EAB308', '#22C55E', '#06B6D4'][:len(labels)]
    star_labels = ['5 bintang', '4 bintang', '3 bintang', '2 bintang', '1 bintang'][:len(labels)]

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

    if not brand_counts:
        fig, ax = plt.subplots(figsize=(7, 5))
        fig.patch.set_facecolor('white')
        setup_ax(ax, 'Top Brands', show_grid_y=True)
        ax.text(0.5, 0.5, 'Belum ada data brand.', ha='center', va='center', fontsize=10, color='gray')
        plt.tight_layout(pad=1.5)
        return plot_to_base64(fig)

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

    if not cat_counts:
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor('white')
        ax.text(0.5, 0.5, 'Belum ada data kategori.', ha='center', va='center', fontsize=10, color='gray')
        ax.set_title('Distribusi Kategori', fontsize=13, fontweight='bold', color='#1F2937', pad=10, loc='left')
        ax.axis('off')
        plt.tight_layout(pad=1.5)
        return plot_to_base64(fig)

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

    if not prices:
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.patch.set_facecolor('white')
        setup_ax(ax, 'Rata-rata Harga per Kategori', show_grid_y=True)
        ax.text(0.5, 0.5, 'Belum ada data harga.', ha='center', va='center', fontsize=10, color='gray')
        plt.tight_layout(pad=1.5)
        return plot_to_base64(fig)

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

    for bar, price in zip(bars, prices):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + max_p * 0.015,
                f'Rp {int(price):,}', ha='center', va='bottom',
                fontsize=8, fontweight='bold', color='#9D174D', rotation=0)

    plt.tight_layout(pad=1.5)
    return plot_to_base64(fig)


# ── Komponen UI ───────────────────────────────────────────────────

def _badge_color(rank: int) -> tuple:
    """Kembalikan (bg_color, text_color) untuk badge ranking."""
    if rank == 1:   return ('#FDE68A', '#92400E')
    elif rank == 2: return ('#E5E7EB', '#374151')
    elif rank == 3: return ('#FBCFE8', '#9D174D')
    else:           return ('#F3F4F6', '#6B7280')


def build_trending_list(products: List[Dict[str, Any]]):
    """
    Render daftar Top 10 Trending sebagai card list dengan gambar produk.
    Gambar diambil dari field image_url di tabel SociollaReferensi (Sociolla CDN).
    """
    for rank, p in enumerate(products, start=1):
        bg, fg = _badge_color(rank)
        with ui.row().classes('w-full items-center gap-3 py-2').style(
            'border-bottom: 1px solid #FCE7F3;'
        ):
            # Badge ranking
            ui.label(str(rank)).style(
                f'min-width:28px; height:28px; border-radius:50%; '
                f'background:{bg}; color:{fg}; '
                f'display:flex; align-items:center; justify-content:center; '
                f'font-weight:700; font-size:12px; flex-shrink:0;'
            )

            # Gambar produk dari Sociolla (image_url)
            img_src = (
                p['image_url']
                if p['image_url']
                else 'https://placehold.co/48x48/FCE7F3/9D174D?text=SK'
            )
            ui.image(img_src).style(
                'width:52px; height:52px; border-radius:8px; '
                'object-fit:cover; flex-shrink:0; border:1px solid #FCE7F3;'
            )

            # Info produk
            with ui.column().classes('flex-1 gap-0').style('min-width:0;'):
                ui.label(p['name']).classes('text-sm font-semibold text-gray-800').style(
                    'white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:320px;'
                )
                ui.label(f"{p['brand']}  ·  {p['category']}").classes('text-xs text-gray-400')

            # Rating & wishlist count
            with ui.column().classes('items-end gap-0').style('flex-shrink:0;'):
                ui.label(f'★ {p["rating"]:.1f}').classes('text-xs font-bold text-yellow-500')
                ui.label(f'♥ {p["wishlist"]:,}').classes('text-xs text-pink-400')


def build_personal_section(stats: Dict[str, Any]):
    """
    Render kartu insight personal user di bagian bawah halaman.
    Diletakkan di bawah karena sifatnya pelengkap personal,
    bukan informasi utama yang dibutuhkan semua pengguna.
    """
    with ui.card().classes('w-full p-5 shadow-sm rounded-2xl border border-pink-100'):
        with ui.row().classes('items-center gap-3 mb-4'):
            ui.label('✨').classes('text-2xl')
            with ui.column().classes('gap-0'):
                ui.label(f'Halo, {stats["username"]}!').classes(
                    'text-base font-semibold text-gray-800'
                )
                ui.label('Ini insight skincare personalmu').classes('text-xs text-gray-400')

        with ui.row().classes('w-full gap-3'):
            tiles = [
                ('Produk Wishlist',    str(stats['wishlist_count']), '🛍️'),
                ('Produk di Routine',  str(stats['routine_count']),  '📋'),
                ('Kategori Favorit',   stats['fav_category'],        '🧴'),
                ('Ingredient Favorit', stats['fav_ingredient'],      '🔬'),
            ]
            for label, value, icon in tiles:
                with ui.card().classes('flex-1 p-3 rounded-xl').style(
                    'background:#FDF2F8; border:1px solid #FCE7F3;'
                ):
                    ui.label(icon).classes('text-lg mb-1')
                    ui.label(value).classes('text-base font-bold text-pink-600')
                    ui.label(label).classes('text-xs text-gray-400 mt-0.5')


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
        ui.label('✨').classes('text-3xl')
        with ui.column().classes('gap-0'):
            ui.label('Beauty Insights').classes('text-2xl font-bold text-gray-800')
            ui.label('Insight & analitik data produk Sociolla').classes('text-sm text-gray-400')

        ui.space()

        def refresh_stats():
            chart_rating_distribution.cache_clear()
            chart_top_brands.cache_clear()
            chart_category_distribution.cache_clear()
            chart_avg_price.cache_clear()
            ui.notify('Data statistik diperbarui!', color='positive')
            ui.navigate.to('/stats')

        ui.button('Refresh Data', icon='refresh', on_click=refresh_stats).props('outline').classes(
            'rounded-xl text-pink-500 border-pink-200'
        )

    # ── ROW 1: Top 10 Trending (full width) ───────────────────────
    # Data dari: SociollaReferensi.total_wishlist + total_reviews + rating_sociolla
    # Gambar dari: SociollaReferensi.image_url (Sociolla CDN)
    with ui.card().classes('w-full p-5 shadow-sm rounded-2xl border border-pink-100 mb-4'):
        ui.label('🔥 Trending Minggu Ini (Top 10)').classes('font-semibold text-gray-700 mb-3')
        trending = get_trending_products()
        if trending:
            build_trending_list(trending)
        else:
            ui.label('Belum ada data produk.').classes('text-sm text-gray-400 italic')

    # ── ROW 2: Distribusi Rating + Top Brands ─────────────────────
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('⭐ Distribusi Rating').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_rating_distribution()).classes('w-full rounded-lg')

        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('🏷️ Top Brands').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_top_brands()).classes('w-full rounded-lg')

    # ── ROW 3: Kategori Produk + Rata-rata Harga ──────────────────
    with ui.row().classes('w-full gap-4 mb-4'):
        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('🧴 Kategori Produk').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_category_distribution()).classes('w-full rounded-lg')

        with ui.card().classes('flex-1 p-5 shadow-sm rounded-2xl border border-pink-100'):
            ui.label('💰 Rata-rata Harga per Kategori').classes('font-semibold text-gray-700 mb-3')
            ui.image(chart_avg_price()).classes('w-full rounded-lg')

    # ── BAGIAN BAWAH: Insight Personal ───────────────────────────
    # Diletakkan paling bawah karena bersifat pelengkap personal,
    # bukan informasi utama. User yang sudah lihat semua insight global
    # baru scroll ke sini untuk info dirinya sendiri.
    with ui.row().classes('items-center gap-2 mt-4 mb-2'):
        ui.label('Insight Personal Kamu').classes('text-base font-semibold text-gray-700')
        ui.label('(dari wishlist & routine-mu)').classes('text-xs text-gray-400')

    build_personal_section(get_personal_stats())
