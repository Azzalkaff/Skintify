import os
import sys
import subprocess
import time
from typing import Optional, List
from pathlib import Path
from collections import deque

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("Harap install dependensi: pip install questionary rich")
    sys.exit(1)

console = Console()

# Pre-calculate paths for efficiency
BASE_DIR = Path(__file__).parent.absolute()
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "cli_runtime.log"
DB_FOLDER = BASE_DIR / "data" / "db"

def append_to_log(message: str):
    """Append a message to the log file with a timestamp."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        # Don't let logging failures crash the CLI
        pass

class ProcessManager:
    def __init__(self):
        self.app_proc: Optional[subprocess.Popen] = None
        self.background_procs = {}
        self._db_cache = {}
        self._last_db_check = 0

    def run_in_background(self, command: list, name: str):
        append_to_log(f"Starting {name} background process: {' '.join(command)}")
        try:
            # redirect stdout and stderr to the log file
            log_handle = open(LOG_FILE, "a", encoding="utf-8")
            proc = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR)
            )
            self.background_procs[name] = {"proc": proc, "log_handle": log_handle}
            console.print(f"[bold green]✅ {name} berhasil dijalankan di latar belakang.[/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Gagal menjalankan {name}: {e}[/bold red]")
            append_to_log(f"Failed to start {name}: {e}")

    def launch_app(self, reload: bool = False):
        if self.app_proc and self.app_proc.poll() is None:
            console.print("[yellow]⚠️ Aplikasi sudah berjalan.[/yellow]")
            return

        cmd = [sys.executable, "main.py"]
        env = os.environ.copy()
        if reload:
            env["SKINTIFY_RELOAD"] = "True"
            console.print("[bold cyan]Menjalankan Aplikasi (Mode Dev/Reload)...[/bold cyan]")
        else:
            console.print("[bold green]Menjalankan Aplikasi (Mode Normal)...[/bold green]")

        try:
            log_handle = open(LOG_FILE, "a", encoding="utf-8")
            self.app_proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=str(BASE_DIR)
            )
            append_to_log(f"Started main.py (Reload={reload})")
            
            # Auto-open browser in background thread only if not running in native desktop mode
            is_native = False
            try:
                import webview
                is_native = True
            except ImportError:
                pass

            if not is_native:
                import webbrowser
                import threading
                def delayed_browser_open():
                    time.sleep(1.5)
                    webbrowser.open("http://127.0.0.1:8081")
                threading.Thread(target=delayed_browser_open, daemon=True).start()
        except Exception as e:
            console.print(f"[bold red]❌ Gagal menjalankan aplikasi: {e}[/bold red]")
            append_to_log(f"Failed to start main.py: {e}")

    def stop_app(self):
        if self.app_proc and self.app_proc.poll() is None:
            console.print("[red]🛑 Menghentikan Aplikasi...[/red]")
            self._kill_process_tree(self.app_proc)
            self.app_proc = None
            append_to_log("Stopped main.py")
        else:
            console.print("[dim]Aplikasi tidak sedang berjalan.[/dim]")

    def _kill_process_tree(self, proc):
        """Robustly kill a process and its children."""
        # 1. Kill immediately using native Python handle (highly reliable, instant, non-blocking)
        try:
            proc.kill()
        except Exception:
            pass
        
        # 2. Run taskkill asynchronously in background to clean up children, without hanging cli.py
        try:
            if os.name == 'nt':
                subprocess.Popen(['taskkill', '/F', '/T', '/PID', str(proc.pid)], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.terminate()
        except Exception:
            pass

    def stop_all_backgrounds(self):
        for name, data in list(self.background_procs.items()):
            proc = data["proc"]
            if proc.poll() is None:
                console.print(f"[red]🛑 Menghentikan {name}...[/red]")
                self._kill_process_tree(proc)
            
            try:
                data["log_handle"].close()
            except:
                pass
            del self.background_procs[name]
            append_to_log(f"Stopped {name}")

    def run_script_sync(self, command: list, name: str):
        console.print(f"[bold cyan]Menjalankan {name}...[/bold cyan]")
        append_to_log(f"Running script sync: {' '.join(command)}")
        try:
            # We want to see output directly in terminal for sync scripts
            subprocess.run(command, check=True, cwd=str(BASE_DIR))
            console.print(f"[bold green]✅ {name} selesai.[/bold green]")
            append_to_log(f"{name} completed successfully.")
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]❌ Terjadi kesalahan pada {name}: {e}[/bold red]")
            append_to_log(f"{name} failed: {e}")
        except Exception as e:
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
        
        questionary.press_any_key_to_continue().ask()

    def get_status_table(self):
        table = Table(box=None, padding=(0, 2), show_header=True, header_style="bold blue")
        table.add_column("Komponen", style="cyan")
        table.add_column("Status", style="bold")

        # App Status
        app_running = self.app_proc and self.app_proc.poll() is None
        app_status = "[green]RUNNING[/green]" if app_running else "[red]STOPPED[/red]"
        table.add_row("Frontend (main.py)", app_status)

        # Background Procs
        for name, data in self.background_procs.items():
            is_alive = data["proc"].poll() is None
            status = "[green]RUNNING[/green]" if is_alive else "[red]STOPPED[/red]"
            table.add_row(f"Process: {name}", status)

        table.add_section()
        
        # DB Checks (with caching to avoid frequent I/O)
        now = time.time()
        if now - self._last_db_check > 5:  # Check every 5 seconds max
            dbs = ["skintify.db", "tokopedia.db", "data_skintify.db"]
            self._db_cache = {}
            for db in dbs:
                db_path = DB_FOLDER / db
                self._db_cache[db] = db_path.exists()
            self._last_db_check = now

        for db, exists in self._db_cache.items():
            status = "[green]OK[/green]" if exists else "[red]MISSING[/red]"
            table.add_row(f"DB File: {db}", status)

        return table

def tail_log(filename: Path, n: int = 20) -> List[str]:
    """Efficiently get the last n lines of a file without reading it all into memory."""
    try:
        if not filename.exists():
            return []
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            return list(deque(f, n))
    except Exception as e:
        return [f"Error reading log: {e}"]

def show_logs():
    console.clear()
    console.print(Panel("[bold magenta]📄 Log Sistem (20 Terakhir)[/bold magenta]", expand=False))
    
    lines = tail_log(LOG_FILE, 20)
    if not lines:
        console.print("[dim]Belum ada log.[/dim]")
    else:
        for line in lines:
            console.print(line.strip(), soft_wrap=True)
            
    questionary.press_any_key_to_continue().ask()

def cek_transparansi_cli():
    """Menampilkan audit transparansi kemiripan produk dan pencocokan data."""
    from app.database.engine import SessionLocal, hitung_kemiripan
    from app.database.models import SociollaReferensi, Produk
    from rich.prompt import Prompt
    import time
    
    console.clear()
    console.print(Panel("[bold magenta]🔍 Audit Transparansi & Kecocokan Produk (Similarity)[/bold magenta]", expand=False))
    
    with SessionLocal() as session:
        total_refs = session.query(SociollaReferensi).count()
        total_tokped = session.query(Produk).filter(Produk.platform == 'tokopedia', Produk.referensi_id != None).count()
        total_lazada = session.query(Produk).filter(Produk.platform == 'lazada', Produk.referensi_id != None).count()
        
        console.print(f"📊 [bold]Ringkasan Pemetaan Database:[/bold]")
        console.print(f"   • Total Master Referensi Sociolla  : [bold cyan]{total_refs}[/bold cyan]")
        console.print(f"   • Produk Terhubung Tokopedia       : [bold green]{total_tokped}[/bold green]")
        console.print(f"   • Produk Terhubung Lazada          : [bold blue]{total_lazada}[/bold blue]")
        console.print("-" * 60)
        
        query_str = Prompt.ask("Cari Master Produk (Ketik nama/brand, atau 'Exit' untuk keluar)")
        if not query_str or query_str.strip().lower() == 'exit':
            return
            
        st = f"%{query_str.strip()}%"
        refs = session.query(SociollaReferensi).filter(
            SociollaReferensi.product_name.ilike(st) |
            SociollaReferensi.brand.ilike(st)
        ).limit(10).all()
        
        if not refs:
            console.print("[bold red]❌ Master referensi tidak ditemukan.[/bold red]")
            time.sleep(1.5)
            return
            
        for ref in refs:
            console.print(f"\n🏷️  [bold yellow]Master Ref ID {ref.id}: {ref.brand} - {ref.product_name}[/bold yellow]")
            console.print(f"   [dim]Keyword Lookup: '{ref.keyword_digunakan}'[/dim]")
            
            # Ambil produk marketplace terhubung
            prods = session.query(Produk).filter_by(referensi_id=ref.id).all()
            if not prods:
                console.print("   [bold red]⚠️  Belum ada produk marketplace terhubung.[/bold red]")
                continue
                
            table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
            table.add_column("Platform", style="cyan")
            table.add_column("Nama Produk Marketplace", style="white")
            table.add_column("Harga", style="green")
            table.add_column("Score Kemiripan", style="bold yellow")
            
            for p in prods:
                score, _ = hitung_kemiripan(p.nama, ref.brand, ref.product_name)
                table.add_row(
                    p.platform.upper(),
                    (p.nama or "")[:50] + "...",
                    f"Rp {int(p.harga or 0):,}",
                    f"{score:.1f}%"
                )
            console.print(table)
            
    questionary.press_any_key_to_continue().ask()

def main():
    pm = ProcessManager()
    
    # Ensure logs file exists
    if not LOG_FILE.exists():
        LOG_FILE.touch()

    while True:
        console.clear()
        console.print(Panel(
            Text.assemble(
                ("SKINTIFY ", "bold magenta"),
                ("DEVELOPER CONTROL CENTER\n", "bold white"),
                ("Full Control for all components and background jobs.", "italic dim")
            ),
            border_style="magenta",
            expand=False
        ))

        console.print(Panel(pm.get_status_table(), title="[bold]System Dashboard[/bold]", border_style="blue", expand=False))

        choice = questionary.select(
            "Pilih Operasi:",
            choices=[
                questionary.Separator(""),
                questionary.Separator("─── APLIKASI UTAMA ───"),
                "🚀 Run App (Normal)",
                "🛠️ Run App (Dev Mode)",
                "🛑 Stop App",
                questionary.Separator(""),
                questionary.Separator("─── DATABASE & SCRIPTS ───"),
                "📂 Setup Database",
                "📥 Import Data Sociolla",
                "📈 View Statistics",
                "🔍 Database Explorer",
                "🔍 Cek Transparansi Pemetaan (Similarity)",
                "🗑️ Hapus Data Marketplace",
                "🔄 Reset Status Scraping",
                questionary.Separator(""),
                questionary.Separator("─── SCRAPER MANAGEMENT ───"),
                "🕷️ Start Main Scraper",
                "🔍 Run Specific Scraper",
                "🛍️ Scrape Marketplace (JSON)",
                "🔗 Merge Scraping Results",
                "💾 Import Marketplace to DB",
                questionary.Separator(""),
                questionary.Separator("─── SYSTEM ───"),
                "📄 View System Logs",
                "📛 Stop All Background Jobs",
                "👋 Exit",
                questionary.Separator("")
            ],
            style=questionary.Style([
                ('qmark', 'fg:#FF9D00 bold'),
                ('question', 'bold'),
                ('answer', 'fg:#00FF00 bold'),
                ('pointer', 'fg:#FF9D00 bold'),
                ('highlighted', 'fg:#000000 bg:#FF9D00 bold'),
                ('selected', 'fg:#00FF00'),
            ])
        ).ask()

        if not choice or choice == "👋 Exit":
            pm.stop_app()
            pm.stop_all_backgrounds()
            console.print("[bold green]👋 Menutup Control Center...[/bold green]")
            break

        # Actions
        if choice == "🚀 Run App (Normal)":
            pm.launch_app(reload=False)
            time.sleep(0.2)
        elif choice == "🛠️ Run App (Dev Mode)":
            pm.launch_app(reload=True)
            time.sleep(0.2)
        elif choice == "🛑 Stop App":
            pm.stop_app()
            time.sleep(0.2)
        elif choice == "📂 Setup Database":
            pm.run_script_sync([sys.executable, "scripts/migrations/setup_databases.py"], "setup_databases.py")
        elif choice == "📥 Import Data Sociolla":
            pm.run_script_sync([sys.executable, "scripts/data_ops/json_to_database.py"], "json_to_database.py")
        elif choice == "📈 View Statistics":
            pm.run_script_sync([sys.executable, "scripts/utils/view_results.py"], "view_results.py")
        elif choice == "🔍 Database Explorer":
            pm.run_script_sync([sys.executable, "scripts/utils/db_explorer.py"], "db_explorer.py")
        elif choice == "🔍 Cek Transparansi Pemetaan (Similarity)":
            cek_transparansi_cli()
        elif choice == "🗑️ Hapus Data Marketplace":
            if questionary.confirm("Apakah Anda yakin ingin menghapus SEMUA data Tokopedia dan Lazada?").ask():
                pm.run_script_sync([sys.executable, "scripts/data_ops/hapus_data_marketplace.py"], "hapus_data_marketplace.py")
        elif choice == "🔄 Reset Status Scraping":
            if questionary.confirm("Apakah Anda yakin ingin mereset semua status progress? (Bot akan mengulang dari awal)").ask():
                pm.run_script_sync([sys.executable, "scripts/data_ops/reset_scrape_status.py"], "reset_scrape_status.py")
        elif choice == "🕷️ Start Main Scraper":
            pm.run_in_background([sys.executable, "app/scraping/main_scraper.py"], "Main Scraper")
            time.sleep(0.2)
        elif choice == "🔍 Run Specific Scraper":
            scraper_choice = questionary.select(
                "Pilih Scraper:",
                choices=[
                    "lazada_scraper.py",
                    "sociolla_scraper.py",
                    "tokopedia_scraper.py",
                    "youtube_scraper.py",
                    "halal_scraper.py",
                    "Kembali"
                ]
            ).ask()
            if scraper_choice and scraper_choice != "Kembali":
                pm.run_in_background([sys.executable, f"app/scraping/{scraper_choice}"], f"Scraper: {scraper_choice}")
                time.sleep(0.2)
        elif choice == "🛍️ Scrape Marketplace (JSON)":
            pm.run_script_sync([sys.executable, "scripts/data_ops/scrape_marketplace.py"], "scrape_marketplace.py")
        elif choice == "🔗 Merge Scraping Results":
            pm.run_script_sync([sys.executable, "scripts/data_ops/merge_scraped_results.py"], "merge_scraped_results.py")
        elif choice == "💾 Import Marketplace to DB":
            pm.run_script_sync([sys.executable, "scripts/data_ops/marketplace_to_database.py"], "marketplace_to_database.py")
        elif choice == "📄 View System Logs":
            show_logs()
        elif choice == "📛 Stop All Background Jobs":
            pm.stop_all_backgrounds()
            time.sleep(0.2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Proses dihentikan paksa.[/red]")
        sys.exit(0)
