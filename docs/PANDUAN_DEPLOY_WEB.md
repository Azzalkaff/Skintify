# 🌐 Panduan Lengkap Deploy Web Skintify-C4

Panduan ini menjelaskan langkah demi langkah untuk men-deploy aplikasi **Skintify-C4** (yang dibangun menggunakan **NiceGUI**) sebagai aplikasi web publik yang dapat diakses oleh dosen, anggota kelompok, maupun pengguna umum.

---

## ⚖️ Analisis Performa: Apakah NiceGUI Baik untuk Web Publik?

Secara teknis, **Ya**. NiceGUI dibangun di atas kerangka kerja **FastAPI** dan **Vue.js**, sehingga ia merupakan aplikasi web sejati. Namun, penting untuk memahami karakteristik kinerjanya sebelum merilisnya secara publik:

**✅ Kelebihan Utama:**
*   **Sangat Cepat Dikembangkan:** Tim tidak perlu belajar ekosistem JavaScript (React/Next.js) yang rumit. Semuanya diatur lewat Python.
*   **Real-time Bawaan:** Interaksi *live* (seperti *scraping* atau sinkronisasi data antar pengguna) ditangani secara mulus melalui WebSocket bawaan tanpa perlu *setup* tambahan.

**⚠️ Keterbatasan untuk Skala Produksi:**
*   **Bergantung Sepenuhnya pada WebSocket:** Setiap interaksi pengguna (misalnya, klik tombol atau mengisi teks) dikirim bolak-balik ke *server* melalui WebSocket. Jika koneksi internet pengguna buruk (*ping* tinggi), respons UI akan terasa agak *lag*.
*   **Kurang Ramah SEO:** Karena sebagian besar UI dibangun dan dirender secara dinamis melalui koneksi *socket*, *web crawler* seperti Googlebot kesulitan mengindeks konten halaman Anda.
*   **Beban Server (Stateful):** Menangani ribuan koneksi WebSocket aktif secara bersamaan memakan lebih banyak memori *server* dibandingkan model REST API (stateless) tradisional.

**Kesimpulan:** Untuk prototipe presentasi, alat internal (*admin tools*), atau peluncuran awal skala kecil, NiceGUI **berfungsi dengan sangat baik**. Namun, jika Anda menargetkan jutaan pengunjung organik, pertimbangkan untuk bermigrasi ke arsitektur *frontend* khusus seperti React/Next.js di masa depan.

---

## 🚀 1. Persiapan & Penyesuaian Kode (Sudah Selesai!)

Aplikasi NiceGUI pada dasarnya adalah aplikasi web berbasis **FastAPI** (Python). Agar dapat berjalan di server cloud, kami telah memodifikasi blok eksekusi `main.py` menjadi sangat dinamis dan cerdas:

* **Deteksi Port Dinamis (`PORT` Env)**: Server PaaS (seperti Render/Railway) akan memberikan port acak melalui environment variable `PORT`. Kode kita sekarang membaca `os.environ.get("PORT", 8081)` secara otomatis.
* **Host Binding (`0.0.0.0`)**: Jika mendeteksi lingkungan server, aplikasi akan melakukan bind ke `0.0.0.0` (menerima trafik dari internet), bukan `127.0.0.1` (hanya lokal).
* **Headless Mode (`show=False`)**: Mencegah aplikasi mencoba membuka browser lokal secara otomatis di server tanpa tampilan visual (headless), yang biasanya menyebabkan crash/warning di server Linux.
* **Aman & Fleksibel**: Logika Desktop Native (menggunakan `pywebview` / `--windowed`) tetap berfungsi 100% saat dijalankan di komputer lokal Anda!

---

## 💾 2. Strategi Persistensi Database SQLite (Sangat Penting!)

Skintify menggunakan dua database berbasis SQLite:
1. `data_skintify.db` (data registrasi, autentikasi pengguna, kota, dan riwayat).
2. `tokopedia.db` (menyimpan data produk hasil scraping, statistik, dan relasi).

Secara default, platform cloud PaaS (seperti Render / Railway / Hugging Face) bersifat **ephemeral** (kontainer akan di-reset setiap kali ada push baru atau server masuk ke mode sleep). Jika dibiarkan default, **semua akun pengguna baru dan data scraping akan hilang setiap kali server restart!**

### ✅ Solusi Terbaik:
* **Pada VPS**: SQLite aman secara default karena disk VPS bersifat permanen.
* **Pada Render/Railway**: Gunakan fitur **Persistent Volume / Disk** dan arahkan folder `/app/data` ke disk tersebut. Karena kode Anda menaruh database di `data/db/...`, menduplikasi folder `/data` ke persistent volume akan menyelamatkan seluruh data Anda selamanya!

---

## 🛠️ 3. Opsi Deployments (Pilih Salah Satu)

Berikut adalah 4 opsi deployment terbaik dari yang termudah hingga yang paling direkomendasikan untuk produksi jangka panjang:

### Opsi A: Deploy di Render (Mudah, Populer, Ada Free Tier)
Render sangat populer untuk mahasiswa karena mudah dihubungkan dengan GitHub.

1. **Push Proyek ke GitHub**: Pastikan folder `Skintify-C4` berada di repositori GitHub Anda.
2. **Daftar di [Render](https://render.com/)** dan buat akun.
3. Klik **New +** > **Web Service**.
4. Hubungkan repositori GitHub Anda.
5. Konfigurasikan detail berikut:
   * **Name**: `skintify-c4`
   * **Runtime**: `Python`
   * **Build Command**: `pip install -r Skintify-C4/requirements.txt`
   * **Start Command**: `python Skintify-C4/main.py` (sesuaikan path jika file `main.py` berada di subfolder).
6. **Tambahkan Environment Variables (Advanced > Add Env Var)**:
   * `API_PROVIDER` = `gemini` atau `groq`
   * `GEMINI_API_KEY` = `[API KEY ANDA]`
   * `GROQ_API_KEY` = `[API KEY ANDA]`
   * `STORAGE_SECRET` = `[String Acak untuk Enkripsi Kuki]`
7. **PENTING: Pasang Persistent Disk (Agar Data Akun Tidak Hilang)**:
   * Scroll ke bawah ke bagian **Disks**.
   * Klik **Add Disk**.
   * **Name**: `skintify-db-storage`
   * **Mount Path**: `/app/Skintify-C4/data`
   * **Size**: `1 GB` (Sangat cukup untuk database SQLite).
8. Klik **Deploy Web Service**. Aplikasi Anda akan aktif dalam beberapa menit!

---

### Opsi B: Deploy di Hugging Face Spaces (100% Gratis & Sangat Cepat)
Cocok untuk demo/portfolio karena Hugging Face menyediakan hosting web Python gratis yang sangat stabil.

1. Buka [Hugging Face Spaces](https://huggingface.co/spaces) dan buat akun.
2. Klik **Create new Space**.
3. Beri nama Space Anda (misalnya `skintify-web`).
4. Pilih SDK: **Docker** (paling aman & fleksibel untuk NiceGUI) atau **Blank (Python)**.
5. Jika memilih **Docker**, buat file bernama `Dockerfile` di root folder proyek Anda (lihat template di bawah).
6. Commit & Push semua file proyek ke Space Git Hugging Face Anda.
7. Masuk ke tab **Settings** di Space Anda untuk memasukkan API Keys di bagian **Variables and Secrets** (tambahkan sebagai Secret agar API Key Anda aman dari publik).
8. Hugging Face akan membangun kontainer Docker dan menyajikan aplikasi web Anda secara otomatis!

---

### Opsi C: Deploy di Railway (Sangat Cepat & Modern)
Railway mirip dengan Heroku namun jauh lebih cepat dan andal untuk WebSockets (yang sangat dibutuhkan NiceGUI).

1. Daftar di [Railway.app](https://railway.app/).
2. Buat **New Project** > **Deploy from GitHub repo**.
3. Pilih repositori Skintify Anda.
4. Masuk ke tab **Variables** di Railway dan masukkan seluruh isi `.env` Anda.
5. **Tambahkan Volume (Disk)** agar SQLite Anda abadi:
   * Klik **Settings** > **Volumes** > **Add Volume**.
   * Mount volume tersebut ke `/app/data` (atau path database Anda).
6. Klik Deploy. Railway akan otomatis mendeteksi Python, menginstal dependensi, dan menjalankan `python main.py`.

---

### Opsi D: Deploy di VPS (Hostinger, DigitalOcean, AWS, dll. — Rekomendasi Utama Dosen)
Sangat stabil, database SQLite Anda 100% aman tanpa setup disk tambahan, dan Anda memiliki kendali penuh.

#### Langkah 1: Hubungkan ke VPS melalui SSH
```bash
ssh root@ip_address_vps_anda
```

#### Langkah 2: Install Docker & Docker Compose
```bash
sudo apt update && sudo apt install -y docker.io docker-compose git
```

#### Langkah 3: Clone Repositori Proyek
```bash
git clone https://github.com/username-anda/Skintify-C4.git
cd Skintify-C4/Skintify-C4
```

#### Langkah 4: Buat File `.env` Produksi
Buat file `.env` di VPS dan masukkan konfigurasi Anda:
```bash
nano .env
# Masukkan API Key dan Konfigurasi Anda di sini, lalu simpan (Ctrl+O, Enter, Ctrl+X)
```

#### Langkah 5: Jalankan Menggunakan Docker Compose
Kami telah menyediakan template `docker-compose.yml` di bawah. Cukup jalankan:
```bash
docker-compose up -d --build
```
Aplikasi Anda sekarang aktif secara permanen di latar belakang VPS dan akan otomatis restart jika server menyala ulang!

---

## 🐳 4. Lampiran Template File Deployment

Untuk menunjang deploy dengan **Docker** (sangat disarankan untuk Hugging Face, VPS, atau Railway), Anda dapat membuat dua file berikut di root folder proyek Anda:

### 1. `Dockerfile`
Buat file dengan nama `Dockerfile` (tanpa ekstensi):

```dockerfile
# Gunakan image Python resmi yang ringan
FROM python:3.11-slim

# Set environment variables agar output langsung dicetak ke terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# Set working directory di dalam kontainer
WORKDIR /app

# Install sistem dependensi yang dibutuhkan (opsional untuk pywebview compile, dsb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Salin requirements file dan instal dependensi python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek ke dalam kontainer
COPY . .

# Buat folder penyimpanan database
RUN mkdir -p data/db

# Ekspos port yang digunakan
EXPOSE 8081

# Jalankan aplikasi web
CMD ["python", "main.py"]
```

### 2. `docker-compose.yml`
Sangat cocok untuk VPS agar pengelolaan kontainer menjadi sangat mudah:

```yaml
version: '3.8'

services:
  skintify-app:
    build: .
    container_name: skintify-web-app
    restart: always
    ports:
      - "80:8081" # Map port 80 (HTTP standar) ke port kontainer 8081
    environment:
      - PORT=8081
      - API_PROVIDER=groq
      - GEMINI_API_KEY=your_gemini_api_key_here # Ganti dengan env VPS yang aman
      - GROQ_API_KEY=your_groq_api_key_here
    volumes:
      # Mount folder data lokal VPS ke dalam kontainer agar SQLite persisten & tidak hilang saat kontainer di-update
      - ./data:/app/data
```

---

## 💡 Tips & Trik Tambahan
1. **Keamanan Cookie (`STORAGE_SECRET`)**: Gantilah string `'skintify-secret-key-2026'` di `.env` produksi Anda dengan karakter acak yang panjang untuk mengamankan data enkripsi kuki browser user Anda.
2. **Reverse Proxy (SSL/HTTPS)**: Jika mendeploy di VPS, disarankan menggunakan **Nginx** dengan **Certbot (Let's Encrypt)** sebagai reverse proxy agar aplikasi Anda memiliki URL `https://` yang aman dan terpercaya!
