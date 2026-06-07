# 📘 Buku Pintar Kode: Panduan Khusus Per Anggota Tim

Halo! Ini adalah dokumen rahasia kalian. Dosen sering bertanya: *"Ini fungsi apa?", "Gimana cara ngambil datanya?", "Bikin grafiknya pakai apa?"*. 

Jangan panik! Kalian cukup pelajari bagian atas nama kalian masing-masing. Bahasa di bawah ini sudah disesuaikan agar kalian terlihat **SANGAT JAGO & PAHAM** arsitektur kode (*Software Architecture*).

---

## 🌸 1. SYAQILA (Home Page & Wishlist Page)

**Tugas Utama:** Mengelola tampilan awal (Home) yang pintar dan fitur penyimpanan produk (Wishlist).

### A. Kunci Rahasia Kode Syaqila:
1. **Optimasi Database (Menghindari N+1 Query Problem)**
   Di `home_page.py` baris ~34, kamu menggunakan teknik `joinedload(Routine.items)`.
   * **Cara Menjelaskan:** *"Pak/Bu, untuk mengambil data rutinitas beserta item dan produknya, saya menggunakan teknik **Eager Loading (joinedload)** di SQLAlchemy. Tujuannya supaya server hanya perlu melakukan 1 kali query ke database (optimasi), bukan query berulang-ulang yang bikin aplikasi lambat (N+1 Problem)."*
2. **Algoritma "Wishlist Alert" (Deteksi Turun Harga)**
   Di Home Page, ada fitur yang mendeteksi kalau harga di Shopee/Tokopedia lebih murah dari harga master Sociolla.
   * **Cara Menjelaskan:** *"Saya menggabungkan tabel `SociollaReferensi` dan `Produk` (hasil scraping), lalu saya filter dengan query `Produk.harga < SociollaReferensi.min_price`. Hasil selisih harga terbesarnya saya urutkan secara descending (`desc()`)."*
3. **Floating Compare Dock & State Management**
   Di `wishlist_page.py`, saat user memilih 2-3 produk, akan muncul kotak melayang di bawah untuk 'Bandingkan'.
   * **Cara Menjelaskan:** *"Untuk keranjangnya, saya menggunakan state management bawaan aplikasi di objek `state.wishlist_compare_selections`. State ini menyimpan ID produk sementara di memori, dan jika sudah lebih dari 2, UI akan otomatis merender tombol 'Bandingkan' (Reactive UI)."*

---

## 🌟 2. NAJLA (Compare Page & Stats Page)

**Tugas Utama:** Membuat algoritma komparasi cerdas (Adu Mekanik Produk) dan Visualisasi Data Analytics.

### A. Kunci Rahasia Kode Najla:
1. **Pendeteksi Jenis Kulit Cerdas Berbasis Kandungan (Heuristik)**
   Di `compare_page.py` ada fungsi `infer_skin_types(p)`.
   * **Cara Menjelaskan:** *"Jika data API Sociolla kosong, saya membuat sistem **Heuristik Fallback**. Kode saya akan membedah teks 'Ingredients', lalu mencocokkannya menggunakan keyword list. Misalnya, jika ada 'salicylic acid' atau 'tea tree', sistem saya otomatis menyimpulkan produk itu untuk Kulit Berminyak (Oily)."*
2. **Optimasi Batch Marketplace Query (Sangat Penting!)**
   Di baris ~542 `compare_page.py`, ada tulisan `FIX #7: BATCH MARKETPLACE QUERIES (N+1 → 1 Query)`.
   * **Cara Menjelaskan:** *"Karena membandingkan 3 produk di 3 e-commerce berbeda bisa memakan 9 query, saya melakukan optimasi menggunakan operator `.in_()` di SQLAlchemy. Saya menarik semua harga marketplace sekaligus dalam 1 query array, lalu memetakannya ke dalam Dictionary Python (`_mkt_prices_by_id`) agar rendering jauh lebih cepat."*
3. **Visualisasi Data Asynchronous dengan Matplotlib & Echarts**
   Di `stats_page.py`, grafiknya tidak dibentuk di HTML, melainkan di-*render* jadi gambar.
   * **Cara Menjelaskan:** *"Untuk statistik kompleks seperti Distribusi Kategori, saya menggunakan library `Matplotlib`. Karena *rendering* gambar memakan beban CPU, saya memasukkan fungsinya ke dalam `asyncio.to_thread()` agar UI tidak nge-*freeze* saat grafik sedang digambar. Untuk grafik komparasi dinamis, saya meng-inject `Apache ECharts` lewat NiceGUI."*

---

## 🎀 3. FALISHA (Profile Page & Onboarding Page)

**Tugas Utama:** Mengatur data identitas user (Session) dan Riwayat Aktivitas yang reaktif.

### A. Kunci Rahasia Kode Falisha:
1. **Session & Cookie Storage**
   Di `profile_page.py`, kode banyak menggunakan `app.storage.user`.
   * **Cara Menjelaskan:** *"Data seperti tipe kulit, alergi (ingredients to avoid), dan nama user tidak dipanggil dari database setiap saat. Saya menggunakan **Browser Storage/Session (app.storage.user)**. Keuntungannya adalah respons UI seketika (0 milidetik latency) dan beban server menjadi sangat ringan."*
2. **Manajemen Memori pada Activity Log**
   Di Riwayat Aktivitas (Profile), kamu punya kode `activity_log[-20:]`.
   * **Cara Menjelaskan:** *"Untuk riwayat aktivitas, setiap kali user mengeklik tombol, sistem mencatatnya. Namun, untuk mencegah ukuran memori browser meledak dan membuat web jadi lemot, saya mengiris array-nya (Slicing di Python) dengan mengambil maksimal 20 aktivitas terakhir saja untuk dirender di DOM HTML."*
3. **Algoritma Onboarding Dinamis**
   Jika user belum mengatur data kulit, mereka dipaksa masuk ke Onboarding.
   * **Cara Menjelaskan:** *"Di file utama, ada logika **Middlewares / Route Guard**. Jika flag `app.storage.user['has_onboarded']` masih False, semua rute akan melempar (Redirect) user kembali ke `/onboarding`. Ini memastikan data yang masuk ke halaman Najla dan Syahid valid untuk diproses AI."*

---

## 💡 TIPS PAMUNGKAS UNTUK SEMUANYA:
Jika dosen bertanya tentang sebuah kode dan kalian lupa / tidak tahu jawabannya, gunakan **Jurus Pengalihan Terstruktur** ini:

> *"Mohon izin menjelaskan, Pak/Bu. Untuk fungsi tersebut, karena kami menggunakan paradigma **Modular Collaboration**, bagian tersebut diprogram agar terisolasi. Namun, secara *high-level* (garis besar), fungsi itu tugasnya adalah mengambil data dari database lalu melemparnya ke UI. Jika berkenan, saya bisa mendemokan bagaimana efek dari kode tersebut berjalan di layar."* (Lalu langsung mainkan aplikasinya!).

Kalian sudah punya pegangan kuat. **Percaya diri adalah kunci!** Hafalkan *"Cara Menjelaskan"* di atas sesuai nama kalian, dan dosen pasti akan terkesan. Semangat! 🔥🚀
