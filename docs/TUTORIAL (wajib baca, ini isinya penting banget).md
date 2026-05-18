# 🌟 SKINTIFY: PANDUAN LENGKAP ENGINEER TIM (EDISI PEMULA)

Halo Syaqila, Najla, dan Falisha! Selamat datang di proyek **Skintify**. 

Dokumen ini ditulis khusus untuk kalian. Jangan panik kalau melihat banyak baris kode. Aplikasi ini dibangun seperti menyusun balok Lego. Pelajari dokumen ini pelan-pelan, ikuti aturannya, dan kita pasti bisa menyelesaikan proyek ini dan dapat nilai A dari Dosen! 🚀

---

## 🔄 RESET VENV (Jika Error / Pertama Kali Setup Ulang)

Jalankan perintah ini **satu per satu** secara berurutan di terminal PowerShell, dari folder `Skintify`:

**Langkah 1 — Deactivate venv yang aktif (kalau ada file venv, kalau tidak ada tidak usah):**
```powershell
.\venv\Scripts\deactivate
```
**Langkah 2 — Hapus folder venv lama (kalau tidak ada tidak usah):**
```powershell
Remove-Item -Recurse -Force venv
```
**Langkah 3 — Buat venv baru:**
```powershell
python -m venv venv
```
**Langkah 4 — Aktifkan venv baru:**
```powershell
.\venv\Scripts\activate
```
**Langkah 5 — Upgrade pip:**
```powershell
python -m pip install --upgrade pip
```
**Langkah 6 — Install semua dependencies:**
```powershell
pip install -r requirements.txt
```

---

> [!TIP]
> Kalau mau **satu blok sekaligus**, copy-paste ini ke terminal:
> ```powershell
> deactivate; Remove-Item -Recurse -Force venv; python -m venv venv; .\venv\Scripts\activate; python -m pip install --upgrade pip; pip install -r requirements.txt
> ```
> Tapi cara satu per satu lebih aman agar bisa melihat jika ada error di tahap tertentu.

> [!IMPORTANT]
> Pastikan terminal kamu sudah berada di folder `Skintify` sebelum mulai. Cek dengan `pwd` — hasilnya harus `...\main program\Skintify`.

---

## 🛠️ BAB 0: SETUP WAJIB (Lakukan Ini Dulu!)
Sebelum mulai ngoding, kalian **WAJIB** melakukan setup "ruangan kerja" (Virtual Environment) agar laptop kalian tidak error saat menjalankan aplikasi. Ikuti 3 langkah ini di Terminal VS Code:

1. **Hapus venv lama (jika ada):**
   ```powershell
   Remove-Item -Recurse -Force venv
   ```
2. **Buat venv baru:**
   ```powershell
   python -m venv venv
   ```
3. **Aktivasi & Install Library:**
   ```powershell
   .\venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
> **⚠️ PENTING:** Jika muncul tulisan `(venv)` di sebelah kiri nama folder di terminal, artinya kalian sudah berhasil masuk ke "ruangan kerja" yang benar.

---

## 🐍 BAB 1: PENYEGARAN PYTHON (Senjata Utama Kita)
Di proyek ini, kita mengambil data dari internet (hasil *scraping* Sociolla) yang bentuknya teks, lalu mengubahnya menjadi tampilan UI yang cantik. Untuk itu, kalian **wajib** ingat 2 hal ini:

### 1. List (Daftar/Kumpulan Data)
List itu ibarat rak sepatu. Isinya berderet dan punya urutan (dimulai dari 0).
```python
# Membuat List produk
daftar_skincare = ["Toner", "Serum", "Moisturizer"]

# Mengambil data (Serum)
print(daftar_skincare[1]) 

# Menambahkan data baru
daftar_skincare.append("Sunscreen")

# Menampilkan semua data dengan Looping (SANGAT SERING DIPAKAI!)
for produk in daftar_skincare:
    print(f"Saya pakai {produk}")
```

### 2. Dictionary (Kamus Data)
Dictionary itu ibarat kartu identitas. Ada **Kunci (Key)** dan ada **Nilai (Value)**. Data dari database/JSON kita bentuknya selalu seperti ini!
```python
# Membuat Dictionary produk
produk_detail = {
    "nama": "Serum Somethinc",
    "harga": 150000,
    "tipe_kulit": "Oily"
}

# Mengambil nilai (Misal mau ambil harga)
print(produk_detail["harga"]) # Output: 150000

# Mengganti nilai
produk_detail["harga"] = 120000
```
> **💡 Rumus Rahasia:** Nanti, data kita adalah **List yang berisi banyak Dictionary** (Rak yang isinya banyak kartu identitas produk).

---

## 🖥️ BAB 2: CARA KERJA "NiceGUI" (Framework Kita)
Biasanya Python cuma muncul di layar hitam putih (Terminal). Di Skintify, kita pakai **NiceGUI** agar Python bisa jadi halaman Web (UI).

Konsepnya sangat sederhana:
1. **Tidak perlu ngetik HTML/CSS ribet.** Kita panggil fungsi Python, NiceGUI yang menggambarnya.
2. **Semua berawalan `ui.`**
    * Mau bikin teks? Tulis `ui.label('Halo!')`
    * Mau bikin tombol? Tulis `ui.button('Klik Saya')`
    * Mau bikin baris ke samping? Tulis `with ui.row():`
    * Mau bikin kolom ke bawah? Tulis `with ui.column():`

**Contoh Sederhana Halaman Web:**
```python
from nicegui import ui

def show_page():
    with ui.column().classes('w-full items-center p-4'): # Bikin kolom di tengah
        ui.label('Selamat Datang di Skintify').classes('text-2xl font-bold')
        
        def sapa_user():
            ui.notify('Tombol berhasil diklik!') # Muncul pop-up kecil
            
        ui.button('Klik Aku', on_click=sapa_user)
```

### 3. Konsep Super Penting: State & Data Manager (Wajib Baca!)
Saat ngoding nanti, kalian **DILARANG KERAS** mengetik data produk palsu secara manual. Skintify sudah punya ribuan data asli dari Sociolla (`product_sociolla_ALL.json`). 

Kalian akan selalu berteman dengan dua "asisten" ini di setiap halaman:
1. **`data_mgr` (Bank Data):** Asisten yang tugasnya mengambilkan data asli dari database atau file JSON.
2. **`state` (Ingatan Sementara):** Asisten yang mengingat status aplikasi (misalnya: "User sedang mencari tipe kulit kering").

**Contoh Cara Memanggil Data Asli:**
```python
from app.context import data_mgr, state
from nicegui import ui

def show_page():
    # Asisten data_mgr mengambilkan 12 produk asli pertama dari database
    katalog = data_mgr.get_paginated_products(page=1, items_per_page=12)
    
    # Isi katalog adalah Dictionary, kita loop menggunakan For!
    for produk in katalog["items"]:
        ui.label(produk["product_name"])
        ui.label(f"Rp {produk['min_price']}")
```

---

## 🏗️ BAB 3: PETA FOLDER SKINTIFY (Wajib Paham!)
Aplikasi kita menggunakan pola **Modular Monolith**. Artinya, setiap bagian aplikasi punya "kamarnya" masing-masing agar rapi. Dosen sangat suka mahasiswa yang paham struktur kodenya!

Berikut adalah peta proyek kita. Pahami baik-baik mana area kerjamu dan mana area yang **TIDAK BOLEH** disentuh:

* 📄 **`main.py`** 👉 **Pintu Masuk Utama.** Ini file yang pertama kali dijalankan untuk menyalakan aplikasi. Jangan diubah kecuali oleh Syahid!

* 📂 **`app/`** (Jantung Aplikasi)
  Ini adalah folder paling penting yang berisi seluruh sistem Skintify, terbagi menjadi beberapa "divisi":
  * 📄 **`context.py` (Pusat Komando):** Tempat tinggal asisten `state` dan `data_mgr` yang bisa kalian panggil di halaman mana saja.
  * 🎨 **`ui/` (Wajah Aplikasi):** **INI WILAYAH KERJA KALIAN!**
    * `components.py`: Cetakan untuk desain yang dipakai berulang (seperti Navbar & Sidebar).
    * `pages/`: Tempat kalian membuat halaman web. Syaqila, Najla, dan Falisha sudah punya folder masing-masing di sini (`pages/syaqila`, dll). **Hanya fokus di folder namamu sendiri!**
  * 🤖 **`scraping/` (Pabrik Data):** Berisi robot-robot Python (`_scraper.py`) yang otomatis berkeliling internet untuk mengambil data produk.
  * 🗄️ **`database/` (Gudang Data):** Mengatur cara data disimpan ke dalam tabel agar mudah dicari.
  * 🧠 **`services/` (Otak Analitis):** Tempat menyimpan rumus dan logika pintar. Contoh: `analyzer.py` untuk mencocokkan *ingredients*, dan `weather.py` untuk cek cuaca.
  * 🔐 **`auth/` (Satpam):** Mengurus sistem *login* dan keamanan akun pengguna.

* 📂 **`scripts/`** (Alat Bengkel)
  👉 Berisi file bantuan (`debug.py`, `database_migration.py`) yang dipakai teknisi/Syahid untuk memperbaiki sistem di belakang layar. Abaikan folder ini.

* 📂 **`data/`** (Brankas)
  👉 Tempat menyimpan hasil buruan data mentah, seperti file `.json` dan *database* `.db`. Jangan buka dan jangan edit file di sini secara manual agar sistem tidak *error*!

* 📂 **`static/`** (Lemari Aksesoris)
  👉 Menyimpan file `style.css` untuk mengatur warna, *font*, dan animasi global aplikasi.

* ⚙️ **File Sistem & Konfigurasi (JANGAN DISENTUH/DIHAPUS)**
  Ada beberapa file/folder abu-abu yang mungkin kalian lihat di VS Code. Biarkan saja mereka bekerja di balik layar:
  * 📄 **`.env` (Sangat Rahasia):** File brankas yang menyimpan *password* atau *API Key*. File ini tidak akan dan **tidak boleh** dikirim ke Github.
  * 📄 **`requirements.txt`**: Catatan daftar *library* Python yang dibutuhkan aplikasi (seperti NiceGUI, dll).
  * 📄 **`.gitignore`**: Penjaga pintu Github. File ini memastikan file rahasia/berat (seperti database dan folder *venv*) tidak ikut terkirim ke Github.
  * 📂 **`venv/`**: *Virtual Environment*. Ini adalah "kamar" isolasi tempat Python menginstal semua *library*. Folder ini sangat berat dan tidak boleh dikirim ke Github.
  * 🗄️ **`data_skintify.db` / `*.db`**: Ini adalah wujud asli dari database SQLite yang menyimpan akun *login* pengguna dan data lokal.
  * 📂 **`__pycache__/` & `.nicegui/`**: Folder sampah otomatis yang dibuat oleh sistem saat aplikasi berjalan agar proses lebih cepat (*cache*). Abaikan saja.

---

## 🎯 BAB 4: PEMBAGIAN TUGAS & CONTOH KODE

### 👧 1. SYAQILA (`home_page.py` & `wishlist_page.py`)
**Fokus Tugas:** Membuat Halaman Beranda (Katalog Utama) dan Fitur Daftar Keinginan (Wishlist) untuk menampilkan produk yang sudah disimpan *user*.

**Contoh Kode Dasar untuk Wishlist:**
```python
from app.context import state
from nicegui import ui

def show_page():
    ui.label('Wishlist Skincare Kamu').classes('text-xl font-bold mb-4')
    
    # Menampilkan produk yang sudah disimpan user di dalam 'state.routine'
    if len(state.routine) == 0:
        ui.label('Belum ada produk yang disimpan di Wishlist.').classes('text-gray-500')
    else:
        with ui.grid(columns=3).classes('w-full gap-4'):
            for produk in state.routine:
                with ui.card():
                    ui.label(produk.get('product_name', 'Tanpa Nama')).classes('font-bold')
                    ui.label(f"Rp {produk.get('min_price', 0)}").classes('text-pink-500')
                    
                    def hapus_item(p=produk):
                        state.routine.remove(p)
                        ui.notify("Produk dihapus dari Wishlist!", color="warning")
                        # (Catatan: Butuh fungsi refresh tambahan di versi aslinya)
                        
                    ui.button('Hapus', on_click=hapus_item, color='red').classes('mt-2')
```

---

### 👧 2. NAJLA (`compare_page.py` & `stats_page.py`)
**Fokus Tugas:** Membuat fitur Perbandingan 2 Produk bersebelahan dan menampilkan visualisasi data/statistik.

**Contoh Kode Dasar untuk Compare:**
```python
from nicegui import ui

def show_page():
    ui.label('Bandingkan Produk').classes('text-xl font-bold')
    
    # ui.row() membuat elemen berjejer ke samping (kiri dan kanan)
    with ui.row().classes('w-full justify-evenly mt-5'):
        
        # Produk Kiri
        with ui.column().classes('items-center'):
            ui.label('Produk A').classes('text-lg font-bold')
            ui.image('link_gambar_a.jpg').classes('w-32 h-32')
            ui.label('Harga: Rp 150.000')
            ui.label('Rating: ⭐ 4.5')
            
        # Produk Kanan
        with ui.column().classes('items-center'):
            ui.label('Produk B').classes('text-lg font-bold')
            ui.image('link_gambar_b.jpg').classes('w-32 h-32')
            ui.label('Harga: Rp 90.000')
            ui.label('Rating: ⭐ 4.8')
```

---

### 👧 3. FALISHA (`profile_page.py` & `onboarding_page.py`)
**Fokus Tugas:** Membuat halaman sambutan (survey tipe kulit) saat user pertama kali masuk, dan halaman profil.

**Contoh Kode Dasar untuk Onboarding:**
```python
from nicegui import ui

def show_page():
    ui.label('Selamat datang di Skintify!').classes('text-2xl font-bold text-center')
    ui.label('Mari kenali kulitmu.').classes('text-gray-500 mb-4')
    
    # Variabel penyimpan jawaban
    tipe_kulit = ui.radio(['Berminyak', 'Kering', 'Sensitif', 'Kombinasi'], value='Berminyak')
    masalah_kulit = ui.select(['Jerawat', 'Kusam', 'Flek Hitam', 'Kerutan'], value='Jerawat')
    
    def simpan_data():
        # Nantinya ini disimpan ke database, sekarang kita tampilkan saja
        ui.notify(f"Data Disimpan! Tipe: {tipe_kulit.value}, Masalah: {masalah_kulit.value}", color='positive')
        # Setelah simpan, pindah ke halaman Home
        ui.navigate.to('/')

    ui.button('Selesai & Mulai Eksplorasi', on_click=simpan_data).classes('mt-4 bg-blue-500 text-white')
```

---

## 💻 BAB 5: PERINTAH TERMINAL DASAR (Wajib Tahu!)
Terminal (atau *Command Line*) adalah layar hitam tempat kita memberikan perintah langsung ke sistem. Di VS Code, kalian bisa membuka Terminal dengan cepat dengan menekan tombol **`` Ctrl + ` ``** (tombol *backtick* ada di bawah tombol `Esc`).

Berikut adalah perintah wajib yang akan kalian gunakan setiap hari:

1. **Menjalankan Aplikasi Skintify**
   ```bash
   python main.py
   ```
   *(Perintah ini menyalakan server. Tunggu sampai muncul tulisan `NiceGUI ready to go on http://127.0.0.1:8000`, lalu tahan tombol `Ctrl` dan klik link tersebut agar terbuka di browser).*

2. **Mematikan Aplikasi (Wajib!)**
   Klik area dalam terminal, lalu tekan **`Ctrl + C`**.
   *(Sangat Penting! Jika kalian mengubah kode atau aplikasi error, selalu matikan dulu server dengan `Ctrl + C` sebelum menjalankannya lagi. Jika lupa, aplikasi akan bentrok dan muncul error "Port is already in use").*

3. **Memperbarui Pustaka / Modul**
   ```bash
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
   *(Gunakan perintah ini jika muncul pesan error `ModuleNotFoundError`. Ini akan memastikan semua alat Python terbaru milik Syahid terpasang di laptop kalian).*

---

## 🐙 BAB 6: ATURAN KERJA & GIT (Selamat Tinggal Copy-Paste)
Mulai sekarang kita memakai Git. Ini wajib agar kode kita tidak saling timpa. Buka Terminal di VS Code (tekan tombol `` Ctrl + ` ``), lalu ikuti panduan ini:

### A. Alur Kerja Harian (Wajib Dihafal!)
Setiap kali mau mulai ngoding dan setelah selesai ngoding, lakukan urutan ini:

**1. AMBIL KODE TERBARU (SEBELUM NGODING)**
```bash
git pull origin main
```
*(Jangan pernah mulai ngetik kode sebelum `pull`, supaya pekerjaanmu tidak bentrok dengan kode terbaru dari Syahid/temanmu!)*

**2. CEK STATUS KODE (SETELAH NGODING)**
```bash
git status
```
*(Pastikan file yang muncul warna merah/hijau hanya file di folder tugasmu. Jangan sampai ada file database atau file temanmu yang ikut terubah!)*

**3. BUNGKUS PERUBAHAN (HATI-HATI!)**
```bash
git add app/ui/pages/namamu/
```
*(Disarankan untuk menyebut nama folder tugasmu saja agar file berbahaya/database tidak ikut terkirim. Jika terpaksa, baru gunakan `git add .` asalkan kamu yakin tidak mengubah file sistem).*

**4. BERI NAMA PAKET KODE (COMMIT)**
```bash
git commit -m "fitur: Syaqila menambah filter pencarian tipe kulit"
```
*(Gunakan format pesan yang rapi: `[jenis]: [Nama] [Penjelasan]`).*

**5. SINKRONISASI KODE TEMAN (SANGAT WAJIB!)**
```bash
git pull origin main
```
*(Kenapa pull lagi? Karena saat kamu asyik ngoding 2 jam, mungkin Najla sudah mengirim kodenya ke Github. Kamu wajib menarik kodenya dulu sebelum kamu bisa mengirim kodemu).*

**6. KIRIM KE GITHUB (PUSH)**
```bash
git push origin main
```
*(Setelah `push` berhasil, wajib lapor ke Syahid di grup WhatsApp).*

### B. Panduan Darurat (Bantuan Kalau Error)

* **Muncul tulisan "Merge Conflict" saat `git pull`?**
  Itu artinya kamu dan temanmu tidak sengaja mengedit baris kode yang sama. Di VS Code, akan muncul menu pilihan *(Accept Current Change / Incoming Change / Both)*.
  **Solusi:** Jangan panik. Diskusikan dengan temanmu mana kode yang benar, klik pilihan yang sesuai, lalu lakukan `git add .` dan `git commit` lagi. Kalau takut salah, langsung panggil Syahid!

* **Tidak sengaja mengotak-atik file orang lain?**
  Kalau saat `git status` kamu melihat ada file di luar tugasmu yang ikut berubah, jangan di-`add`. Kembalikan file tersebut ke kondisi aslinya dengan perintah:
  ```bash
  git restore nama_file_yang_salah.py
  ```

---

## 🎓 BAB 7: STRATEGI PRESENTASI DOSEN (BACA!)
Saat demo ke Dosen, kalian jangan cuma klik-klik aplikasinya. Ucapkan poin-poin ini agar nilai kita A:

1. **"Aplikasi kami menggunakan Modular Architecture"**
   *Katakan ini sambil menunjukkan folder `ui`, `services`, `scraping`. Dosen suka struktur kode yang rapi dan terpisah, bukan numpuk di 1 file.*

2. **"Data kami Dinamis hasil Web Scraping"**
   *Jelaskan bahwa data Skintify bukan diketik manual satu-satu, melainkan menggunakan script robot yang menarik data JSON dari e-commerce.*

3. **"UI/UX yang Konsisten (Reusable Components)"**
   *Tunjukkan file `components.py` dan jelaskan bahwa Navbar dan Sidebar dibuat satu kali tapi bisa dipanggil di semua halaman, sehingga desainnya rapi dan tidak makan banyak memory.*

4. **"Pendekatan Event-Driven dengan NiceGUI"**
   *Jelaskan bahwa website kita ini interaktif, tidak perlu reload halaman terus menerus karena menggunakan teknologi *state* NiceGUI yang modern.*

---

Semangat codingnya! Kalau *error*, baca pesan error-nya pelan-pelan (biasanya kelihatan di baris berapa error-nya). Mentok? Tanya AI (Gemini/ChatGPT). Masih mentok? Panggil Syahid! 🔥