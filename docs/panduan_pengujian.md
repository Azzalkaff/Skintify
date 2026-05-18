# 🧪 Panduan Pengujian Sistem & Demo Aplikasi (Skintify-C4)

Dokumen ini memuat panduan langkah-demi-langkah (manual book) bagi dosen penguji dan anggota kelompok untuk melakukan demo dan mengevaluasi seluruh fitur canggih aplikasi **Skintify-C4**.

---

## 🔑 1. Kredensial Akun Default Pengujian

Gunakan akun pra-konfigurasi berikut untuk masuk ke dalam aplikasi:

| Peran (Role) | Username | Password | Deskripsi |
| :--- | :--- | :--- | :--- |
| **Regular User** | `user` | `rahasia` | Akun pengujian utama untuk menjajal Chatbot AI, Wishlist, dan Planner. |
| **Administrator** | `admin` | `admin123` | Akses penuh ke dashboard admin, konsol scraping, dan pemetaan database. |

---

## 🚀 2. Cara Menjalankan Aplikasi

1. Buka terminal (CMD / PowerShell / Bash) di direktori utama `Skintify-C4`.
2. Jalankan perintah bootstrap berikut:
   ```bash
   python main.py
   ```
3. Aplikasi akan otomatis mengudara pada port default:
   * **URL Akses**: [http://localhost:8081](http://localhost:8081)

---

## 🔬 3. Skenario Pengujian Fitur Unggulan

### 🟢 FITUR A: Wishlist Detail Pop-up & Live Scraping Tokopedia & Lazada
*Skenario ini membuktikan integrasi asinkron scraper Tokopedia & Lazada yang dipicu secara langsung oleh pengguna melalui antarmuka wishlist.*

1. **Masuk ke Halaman Wishlist**:
   * Login sebagai `user` dengan password `rahasia`.
   * Klik ikon **Wishlist** pada bilah menu samping (sidebar).
2. **Buka Pop-up Detail**:
   * Pada kartu produk yang tersimpan, klik tombol **Detail 🔬** atau klik langsung pada gambar/nama produk.
   * Dialog pop-up premium berukuran besar akan muncul di layar.
3. **Eksplorasi Analisis Kandungan Skincare & Review**:
   * Buka tab **🔬 Bahan Aktif**: Sistem secara instan menganalisis tingkat comedogenic, irritant rating, kecocokan kulit, serta menyajikan daftar bahan aktif utama beserta peringatan bahaya konflik rutin skincare (misal: *Retinol + AHA/BHA*).
   * Buka tab **⭐ Ulasan Asli**: Menyajikan daftar ulasan pelanggan asli berformat bintang dan komentar langsung dari database.
4. **Jalankan Sentinel Live Scraping**:
   * Pada sisi kanan pop-up, cari tombol **Cari Harga Live ⚡**.
   * Klik tombol tersebut. Sentinel Scraper akan bekerja di latar belakang secara asinkron (UI tetap responsif).
   * Setelah selesai, daftar harga terbaru di **Tokopedia** dan **Lazada** akan langsung ter-update di layar pop-up secara real-time lengkap dengan link toko aslinya!

---

### 🔵 FITUR B: Kalkulator Paket Budget Pintar (AI Chatbot)
*Skenario ini menguji kecerdasan buatan dalam merumuskan paket skincare dasar lengkap yang dijamin 100% di bawah batas budget pengguna.*

1. **Masuk ke Halaman AI Chatbot**:
   * Klik menu **AI Chatbot** pada sidebar.
2. **Kirim Perintah Anggaran**:
   * Ketik pesan berikut di kolom chat:
     ```text
     saya butuh paket skincare harga 100rb
     ```
   * *atau:*
     ```text
     rekomendasi paket di bawah 150rb
     ```
3. **Analisis Output**:
   * AI Interceptor akan mendeteksi angka budget tersebut secara otomatis.
   * Sistem melakukan query relasional SQLite untuk mencari 3 produk skincare dasar termurah (**Cleanser + Moisturizer + Sunscreen**) yang jika dijumlahkan total harganya tidak melebihi budget Anda.
   * AI akan membalas dengan rincian harga presisi (misal: total Rp71.000 untuk paket Emina) dan menampilkan kartu produk interaktif yang bisa langsung Anda tambahkan ke wishlist atau routine planner dengan satu klik!
