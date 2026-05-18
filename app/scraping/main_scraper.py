"""
CLI Scraper Utama untuk Proyek Skintify
Menyatukan Scraping Sociolla, E-Commerce, dan Analisis Ingredient dengan Antarmuka Interaktif
"""
import sys
import os
import json
import time
import random
from pathlib import Path

# Fix Pathing - Pastikan root directory ada di sys.path agar 'from app' bisa terbaca
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# External libs
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.progress import track

# Import dari struktur Clean Architecture baru
from app.database.engine import (
    init_db, SessionLocal,
    simpan_hasil,
    simpan_sociolla_referensi,
    tandai_sudah_di_scrape,
)
from app.scraping.tokopedia_scraper import ambil_top_toko as ambil_tokopedia, cari_produk
from app.scraping.lazada_scraper import ambil_top_toko as ambil_lazada
from app.scraping.shopee_scraper import ambil_top_toko as ambil_shopee
from app.scraping.sociolla_scraper import scrape_all_products, save_to_json, validate_json
from app.scraping.ingredient_conflict import load_data, cek_konflik_rutin

console = Console()
SOCIOLLA_JSON = Path("data/products_sociolla.json")


def bangun_keyword(brand: str, product_name: str) -> str:
    return f"{brand} {product_name}".strip()


def scrape_tokopedia(session, keyword: str, top_n: int, referensi_id: int = None):
    try:
        # ambil_tokopedia already returns total_data as the third element of the tuple
        produk_list, toko_list, total_data = ambil_tokopedia(keyword, top_n=top_n)
            
        simpan_hasil(session, "tokopedia", keyword, produk_list, toko_list, total_data, referensi_id=referensi_id)
        return len(produk_list), len(toko_list)
    except Exception as e:
        console.print(f"[red]x [Tokopedia] Error pada '{keyword}':[/red] {e}")
        return 0, 0


def scrape_lazada(session, keyword: str, top_n: int, referensi_id: int = None):
    try:
        produk_list, toko_list = ambil_lazada(keyword, top_n=top_n)
        total_data = len(produk_list)
        simpan_hasil(session, "lazada", keyword, produk_list, toko_list, total_data, referensi_id=referensi_id)
        return len(produk_list), len(toko_list)
    except Exception as e:
        console.print(f"[red]x [Lazada] Error pada '{keyword}':[/red] {e}")
        return 0, 0


def scrape_shopee(session, keyword: str, top_n: int, referensi_id: int = None):
    try:
        produk_list, toko_list = ambil_shopee(keyword, top_n=top_n)
        total_data = len(produk_list)
        simpan_hasil(session, "shopee", keyword, produk_list, toko_list, total_data, referensi_id=referensi_id)
        return len(produk_list), len(toko_list)
    except Exception as e:
        console.print(f"[red]x [Shopee] Error pada '{keyword}':[/red] {e}")
        return 0, 0


def load_sociolla() -> list:
    if not SOCIOLLA_JSON.exists():
        console.print(f"[bold red]File {SOCIOLLA_JSON} tidak ditemukan![/bold red]")
        return []
    with open(SOCIOLLA_JSON, encoding="utf-8") as f:
        data = json.load(f)
    produk_list = data.get("products", [])
    for p in produk_list:
        p["keyword_digunakan"] = bangun_keyword(p["brand"], p["product_name"])
    return produk_list


# ===================== Menu 1 =====================
def run_sociolla_scraping():
    console.print(Panel("[bold yellow][START] Memulai Scraping Sociolla[/bold yellow]", expand=False))
    products = scrape_all_products()
    if products:
        val = validate_json(products)
        if not val["valid"]:
            console.print("[yellow]Peringatan Validasi:[/yellow]")
            for err in val["errors"]:
                console.print(f"- {err}")
        save_to_json(products, str(SOCIOLLA_JSON), "All")
        console.print(f"[green][SUCCESS] Berhasil mengumpulkan {len(products)} produk.[/green]")


from threading import Lock
print_lock = Lock()

def proses_satu_produk(produk, i, total):
    keyword = produk["keyword_digunakan"]
    brand = produk["brand"]
    product_name = produk["product_name"]
    
    # Ambil ID referensi dari database agar bisa di-link
    with SessionLocal() as session:
        ref = session.query(SociollaReferensi).filter_by(brand=brand, product_name=product_name).first()
        ref_id = ref.id if ref else None

    # Optimasi: Scrape Tokopedia, Lazada & Shopee secara PARALEL (Concurrency)
    # Gunakan max_workers=3 untuk 3 platform
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_tokped = executor.submit(scrape_tokopedia, SessionLocal(), keyword, 5, ref_id)
        future_lazada = executor.submit(scrape_lazada, SessionLocal(), keyword, 5, ref_id)
        future_shopee = executor.submit(scrape_shopee, SessionLocal(), keyword, 5, ref_id)
        
        pt, tt = future_tokped.result()
        pl, tl = future_lazada.result()
        ps, ts = future_shopee.result()

    with SessionLocal() as session:
        tandai_sudah_di_scrape(session, brand, product_name)
        
    with print_lock:
        console.print(f"  [green]  - Done: {keyword} (Tokped: {pt}, Lazada: {pl}, Shopee: {ps})[/green]")

    # Jeda kecil antar produk untuk menghindari rate limit agresif
    time.sleep(random.uniform(1.0, 3.0))

# ===================== Menu 2 =====================
def run_ecommerce_scraping():
    console.print(Panel("[bold blue][START] Memulai Scraping Tokopedia, Lazada & Shopee (Parallel Batch)[/bold blue]", expand=False))
    init_db()
    semua_produk = load_sociolla()
    if not semua_produk:
        return
        
    with SessionLocal() as session:
        simpan_sociolla_referensi(session, semua_produk)

    from concurrent.futures import ThreadPoolExecutor
    
    # Tentukan jumlah worker paralel (3-5 direkomendasikan untuk menghindari ban masal)
    MAX_WORKERS = 3 
    
    console.print(f"\n[cyan]Menjalankan pipeline untuk {len(semua_produk)} produk dengan {MAX_WORKERS} thread...[/cyan]")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit semua tugas
        futures = []
        for i, produk in enumerate(semua_produk, start=1):
            futures.append(executor.submit(proses_satu_produk, produk, i, len(semua_produk)))
        
        # Tunggu semua selesai (opsional: bisa tambahkan progress bar di sini)
        for f in futures:
            f.result() # Ini akan raise exception jika ada error di worker

    console.print("\n[bold green][SUCCESS] Seluruh scraping batch selesai![/bold green]")


# ===================== Menu 3 =====================
def run_competitor_insights():
    console.print(Panel("[bold magenta][SEARCH] Competitor Insights (Custom Product)[/bold magenta]", expand=False))
    keyword = questionary.text("Masukkan nama produk untuk dicek harga pasarnya:").ask()
    if not keyword:
        return
        
    init_db()
    with console.status(f"[cyan]Scraping data untuk {keyword}..."):
        with SessionLocal() as session:
            pt, tt = scrape_tokopedia(session, keyword, top_n=5)
            pl, tl = scrape_lazada(session, keyword, top_n=5)
            ps, ts = scrape_shopee(session, keyword, top_n=5)
    
    console.print(f"\n[bold green][SUCCESS] Hasil Scraping '{keyword}':[/bold green]")
    console.print(f"- Tokopedia: Ditemukan {pt} produk dari {tt} toko unik.")
    console.print(f"- Lazada: Ditemukan {pl} produk dari {tl} toko unik.")
    console.print(f"- Shopee: Ditemukan {ps} produk dari {ts} toko unik.")
    console.print("Data telah tersimpan di Database SQLite.")


# ===================== Menu 4 =====================
def run_auto_ingredient_matches():
    console.print(Panel("[bold cyan][TEST] Auto-Ingredient Matches (Simulasi Konflik)[/bold cyan]", expand=False))
    try:
        produk_db, bahan_db = load_data()
    except Exception as e:
        console.print(f"[red]Gagal memuat JSON lokal: {e}[/red]")
        return
        
    choices = [f"{p['brand']} - {p['product_name']}" for p in produk_db[:50]] # Tampilkan top 50 saja
    selected = questionary.checkbox(
        "Pilih 2 atau lebih produk untuk dicek konflik bahan aktifnya:",
        choices=choices
    ).ask()
    
    if not selected or len(selected) < 2:
        console.print("[yellow]Minimal pilih 2 produk untuk membandingkan rutin skincare.[/yellow]")
        return
        
    selected_products = [p for p in produk_db if f"{p['brand']} - {p['product_name']}" in selected]
    hasil = cek_konflik_rutin(selected_products, bahan_db)
    
    console.print("\n[bold]Hasil Analisis:[/bold]")
    if hasil:
        for err in hasil:
            console.print(f"[bold red][CONFLICT] {err}[/bold red]")
    else:
        console.print("[bold green][SUCCESS] AMAN! Tidak ada indikasi bahan aktif yang bertabrakan.[/bold green]")


# ===================== Main TUI =====================
def main():
    while True:
        console.clear()
        console.print(Panel("""[bold cyan]Sistem Sentinel Scraper Skintify[/bold cyan]
[white]Gunakan tombol panah ATAS / BAWAH untuk memilih menu, lalu tekan Enter.[/white]""", expand=False))
        
        choice = questionary.select(
            "Pilih Operasi:",
            choices=[
                "1. Scraping Sociolla (Raw Catalog Data)",
                "2. Scraping Tokopedia, Lazada & Shopee (Pipeline Utama Harga)",
                "3. Custom Competitor Insights (Cari Harga Spesifik)",
                "4. Auto-Ingredient Matches (Uji Konflik Skincare)",
                "5. Keluar"
            ]
        ).ask()

        if not choice or choice.startswith("5"):
            console.print("[bold green]Selamat tinggal! Bye![/bold green]")
            sys.exit(0)
            
        elif choice.startswith("1"):
            run_sociolla_scraping()
            
        elif choice.startswith("2"):
            run_ecommerce_scraping()
            
        elif choice.startswith("3"):
            run_competitor_insights()
            
        elif choice.startswith("4"):
            run_auto_ingredient_matches()
            
        questionary.press_any_key_to_continue().ask()

if __name__ == "__main__":
    main()