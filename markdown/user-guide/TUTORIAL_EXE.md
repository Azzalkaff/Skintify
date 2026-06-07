# 🧴 Skintify Desktop App Compilation Guide
> **Panduan Resmi Distribusi & Pembungkusan Aplikasi Python NiceGUI Menjadi Standalone Windows Executable (.exe)**

Dokumen ini berisi tutorial lengkap, penjelasan arsitektur pembungkusan, dan panduan pemecahan masalah (troubleshooting) untuk mengubah proyek **Skintify-C4** menjadi file executable `.exe` yang siap didistribusikan ke pengguna akhir (user) atau dosen penguji.

---

## 🚀 1. Cara Cepat (Rekomendasi Utama)

Kami telah membuat skrip kompilator otomatis bernama `build_exe.py` di root folder Anda. Skrip ini cerdas: mendeteksi virtual environment, menginstal dependensi yang kurang, menyaring database referensi JSON, dan memanggil PyInstaller dengan konfigurasi terbaik.

Cukup buka terminal/CMD/PowerShell di folder proyek dan jalankan:
```bash
python build_exe.py
```

### Apa yang Dilakukan oleh Skrip?
1. **Deteksi Lingkungan**: Menggunakan Python dari `./venv/` jika ada, jika tidak maka menggunakan Python sistem.
2. **Auto-Install PyInstaller**: Menginstal modul `pyinstaller` secara otomatis ke dalam env jika belum terpasang.
3. **Analisis Database Aset**: Mendeteksi keberadaan file database referensi JSON seperti `products_sociolla_ALL.json` dan `ingredient_data.json` di dalam folder `data/` dan membungkusnya sebagai static resources di dalam exe.
4. **Kompilasi Standalone**: Menghasilkan satu file `dist/Skintify-C4.exe` yang menyertakan GUI, backend, database referensi, dan file statis Quasar/Vue bawaan NiceGUI.

---

## 🛠️ 2. Cara Manual (Menggunakan Command Line)

Jika Anda ingin menyesuaikan konfigurasi atau menjalankannya secara manual tanpa skrip pembantu, ikuti langkah berikut:

### Langkah A: Aktifkan Virtual Environment & Install PyInstaller
```bash
# 1. Aktifkan venv Anda
venv\Scripts\activate

# 2. Install PyInstaller
pip install pyinstaller
```

### Langkah B: Jalankan PyInstaller Command
Gunakan perintah berikut (disesuaikan untuk Windows dengan pemisah titik koma `;` untuk parameter `--add-data`):
```bash
pyinstaller main.py --name "Skintify-C4" --onefile --windowed --add-data "app;app" --add-data "data/ingredient_data.json;data" --add-data "data/products_sociolla_ALL.json;data" --add-data "data/categories_to_scrape.json;data" --collect-all nicegui
```

### Penjelasan Parameter Penting:
* `--name "Skintify-C4"`: Menentukan nama file `.exe` yang dihasilkan.
* `--onefile`: Menggabungkan seluruh interpreter Python, dependensi, dan aset ke dalam **satu file tunggal** `.exe`. Sangat praktis untuk distribusi.
* `--windowed` (atau `-w`): Menyembunyikan jendela CMD hitam di belakang aplikasi saat dibuka. Aplikasi akan langsung muncul sebagai jendela desktop native premium.
* `--add-data "app;app"`: Menyertakan seluruh folder modul `app/` (berisi halaman UI, style CSS statis, logika backend, dan modul auth) ke dalam exe.
* `--add-data "data/ingredient_data.json;data"`: Memaketkan file referensi bahan skincare agar fitur analisis konflik bekerja.
* `--collect-all nicegui`: **CRITICAL!** NiceGUI dibangun di atas FastAPI, Vue, Quasar, dan Tailwind. Parameter ini memerintahkan PyInstaller untuk menyalin seluruh file static HTML/JS/CSS dan template NiceGUI ke dalam bundle `.exe`. Tanpa ini, aplikasi exe akan blank/gagal memuat tampilan UI.

---

## 📐 3. Arsitektur Jalur Penyimpanan SQLite (Sangat Penting!)

Salah satu kendala terbesar saat membuat aplikasi berbasis SQLite menjadi `.exe` (khususnya dengan mode `--onefile`) adalah **hilangnya data**.

### ⚠️ Masalah Default PyInstaller:
Saat menggunakan `--onefile`, ketika user membuka `.exe`, PyInstaller akan mengekstrak semua file internal ke folder temporer Windows (misalnya di `C:\Users\<Name>\AppData\Local\Temp\_MEIxxxxxx`).
Jika database SQLite diletakkan secara relatif ke file program, aplikasi akan menulis database baru ke folder temporer tersebut. Ketika aplikasi ditutup, **folder temporer tersebut akan dihapus oleh Windows, dan seluruh data pengguna (akun pendaftar, hasil scraping baru) akan hilang permanen!**

### ✅ Solusi Premium yang Telah Kami Terapkan:
Kami telah melakukan modifikasi pintar di modul `app/database/database_manager.py` (untuk `data_skintify.db`) dan `app/database/engine.py` (untuk `tokopedia.db` / SQLAlchemy).

Logikanya menggunakan deteksi lingkungan `sys.frozen`:
```python
import sys
import os

if getattr(sys, 'frozen', False):
    # JIKA BERJALAN SEBAGAI EXE:
    # Letakkan folder database 'data/db/' secara permanen di folder yang sama dengan file .exe berada!
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # JIKA BERJALAN DALAM DEV MODE (Python cli.py / main.py):
    # Letakkan di root proyek standard
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
```

### Keuntungan Pendekatan Ini:
1. **Portabilitas Penuh**: Anda dapat menyalin file `Skintify-C4.exe` ke Flashdisk atau folder lain. Saat dijalankan pertama kali, aplikasi akan membuat folder `data/db/` di sebelahnya secara otomatis.
2. **Data Abadi & Aman**: Semua data registrasi user, riwayat aktivitas, dan data perbandingan produk yang ditambahkan user akan tetap tersimpan di folder luar dan tidak akan terhapus saat aplikasi diperbarui atau ditutup.

---

## 🔍 4. Troubleshooting (Mengatasi Masalah Umum)

### Jendela Aplikasi Terbuka tapi Putih/Blank
* **Penyebab**: File aset statis Quasar/NiceGUI tidak tersalin sempurna.
* **Solusi**: Pastikan perintah kompilasi Anda menyertakan parameter `--collect-all nicegui`. Jika masih terjadi, bersihkan cache PyInstaller dengan menambahkan opsi `--clean` saat membuild (misalnya: `python build_exe.py --clean`).

### Database Locked / SQLite Disk I/O Error
* **Penyebab**: Aplikasi `.exe` mencoba menulis database di folder program files yang membutuhkan akses administrator (Read-only folder).
* **Solusi**: Pindahkan file `Skintify-C4.exe` ke folder pengguna biasa (seperti Desktop atau Documents) yang memiliki izin menulis (Write Permission) penuh tanpa memerlukan hak administrator.

### Aplikasi Langsung Close Begitu Dibuka
* **Penyebab**: Terjadi crash error saat startup (misalnya port `8081` sedang digunakan proses lain). Karena menggunakan `--windowed`, Anda tidak bisa melihat pesan error-nya di terminal.
* **Solusi Sementara untuk Debug**: Compile ulang aplikasi tanpa opsi `--windowed` (hapus `--windowed` dari command) sehingga jendela CMD hitam tetap muncul. Jalankan `.exe` melalui CMD untuk melihat pesan error log yang menyebabkan aplikasi tertutup.

---

## 📦 5. Distribusi ke Pengguna Lain

Untuk membagikan aplikasi ini kepada orang lain (tim kelompok, asisten praktikum, atau dosen):
1. Masuk ke folder `dist/` setelah kompilasi selesai.
2. Ambil file `Skintify-C4.exe`.
3. Anda dapat membagikan file `.exe` ini langsung. (Jika ada database default awal, Anda juga bisa menyertakan folder `data/` di sebelahnya agar mereka langsung memiliki data yang sudah terisi).
