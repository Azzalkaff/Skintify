import os
import sys
import subprocess
import shutil
from pathlib import Path

# Set text colors for premium console output
def print_success(msg):
    print(f"[OK] {msg}")

def print_info(msg):
    print(f"[*] {msg}")

def print_warning(msg):
    print(f"[!] {msg}")

def print_error(msg):
    print(f"[FAIL] {msg}")

def main():
    print("=" * 60)
    print("      SKINTIFY APPLICATION COMPILER (.EXE BUILDER)")
    print("=" * 60)
    
    # 1. Pastikan folder kerja berada di root project
    base_dir = Path(__file__).resolve().parent
    os.chdir(base_dir)
    print_info(f"Directory Kerja: {base_dir}")

    # 2. Periksa Virtual Environment
    venv_python = base_dir / "venv" / "Scripts" / "python.exe"
    venv_pip = base_dir / "venv" / "Scripts" / "pip.exe"
    
    if venv_python.exists():
        print_success("Virtual Environment ditemukan di ./venv/")
        python_exe = str(venv_python)
        pip_exe = str(venv_pip)
    else:
        print_warning("Virtual Environment ./venv/ tidak ditemukan. Menggunakan interpreter sistem.")
        python_exe = sys.executable
        pip_exe = os.path.join(os.path.dirname(sys.executable), "pip.exe")
        if not os.path.exists(pip_exe):
            pip_exe = "pip"

    # 3. Validasi & Install PyInstaller & Dependensi
    print_info("Memeriksa instalasi PyInstaller...")
    try:
        # Panggil pyinstaller --version dengan python_exe
        subprocess.run([python_exe, "-m", "PyInstaller", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print_success("PyInstaller sudah terinstall.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("PyInstaller belum terinstall. Menginstall PyInstaller otomatis...")
        try:
            subprocess.run([pip_exe, "install", "pyinstaller"], check=True)
            print_success("PyInstaller berhasil diinstall!")
        except Exception as e:
            print_error(f"Gagal menginstall PyInstaller: {e}")
            sys.exit(1)

    # 4. Cari File Data yang Perlu Di-bundle
    print_info("Menganalisis file database referensi JSON di data/...")
    data_dir = base_dir / "data"
    add_data_args = []
    
    # Bundle folder 'app' berisi UI, styling, dan auth
    add_data_args.append(("--add-data", "app;app"))
    
    # Cari semua file .json di data/ yang dibutuhkan saat aplikasi berjalan
    json_files = ["ingredient_data.json", "products_sociolla_ALL.json", "categories_to_scrape.json", "products_sociolla.json", "bahan.json"]
    for file_name in json_files:
        file_path = data_dir / file_name
        if file_path.exists():
            print_success(f"Menyertakan database referensi: data/{file_name}")
            add_data_args.append(("--add-data", f"data/{file_name};data"))
        else:
            if file_name in ["ingredient_data.json", "products_sociolla_ALL.json"]:
                print_warning(f"File penting data/{file_name} tidak ditemukan. Pastikan data sudah siap.")

    # 5. Persiapkan Perintah PyInstaller
    # --onefile: Menghasilkan 1 file executable mandiri (.exe)
    # --windowed: Menyembunyikan jendela cmd hitam saat aplikasi UI berjalan
    # --collect-all nicegui: Menyertakan semua static assets & templates milik NiceGUI
    # --name: Nama output file exe
    
    command = [
        python_exe, "-m", "PyInstaller",
        "main.py",
        "--name=Skintify-C4",
        "--onefile",
        "--windowed",
        "--collect-all=nicegui"
    ]
    
    # Deteksi jika webview (pywebview) terinstall untuk native desktop mode
    try:
        subprocess.run([python_exe, "-c", "import webview"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print_success("Modul native desktop window (webview) terdeteksi. Menyertakan modul webview...")
        command.append("--hidden-import=webview")
        command.append("--collect-all=webview")
    except subprocess.CalledProcessError:
        print_info("Aplikasi akan berjalan dalam mode Web Browser (webview tidak terinstall).")

    # Tambahkan argumen --add-data
    for arg_type, path_val in add_data_args:
        command.append(arg_type)
        command.append(path_val)

    # 6. Jalankan Proses Kompilasi
    print("\n" + "=" * 60)
    print("             MEMULAI PROSES KOMPILASI PYINSTALLER")
    print("=" * 60)
    print_info(f"Command: {' '.join(command)}")
    print_info("Silakan tunggu beberapa saat (biasanya memakan waktu 1-3 menit)...\n")
    
    try:
        subprocess.run(command, check=True)
        print("\n" + "=" * 60)
        print("          PROSES SELESAI - APLIKASI BERHASIL DICOMPILE!")
        print("=" * 60)
        print_success("Executable file berhasil dibuat!")
        print_info(f"Lokasi File: {base_dir / 'dist' / 'Skintify-C4.exe'}")
        print_info("Anda dapat menyalin file 'Skintify-C4.exe' ke folder mana pun.")
        print_info("Database SQLite 'data_skintify.db' & 'tokopedia.db' akan otomatis dibuat")
        print_info("di folder 'data/db/' bersebelahan dengan file exe untuk pertama kali jalankan.")
    except subprocess.CalledProcessError as e:
        print_error(f"Kompilasi gagal dengan error code {e.returncode}. Silakan periksa log di atas.")
    except Exception as e:
        print_error(f"Terjadi kesalahan tak terduga: {e}")

if __name__ == "__main__":
    main()
