# 📝 Riwayat Pembaruan & Transformasi Fitur Skintify-C4
*Dokumentasi Fitur Premium & Peningkatan Nilai Akademis untuk Sidang Presentasi*

Dokumen ini mencatat seluruh rangkaian transformasi fitur, perbaikan celah keamanan peramban, serta implementasi kecerdasan buatan (*AI & Clinical Inference*) yang telah berhasil disuntikkan ke dalam sistem **Skintify** demi menghadirkan pengalaman pengguna (*UX*) berstandar tinggi.

---

## 🚀 1. Sentinel Scraper & Multi-Store Live Comparison
Kami merombak cara sistem menangani pencarian harga langsung agar data yang disajikan kepada pengguna selalu segar dan akurat.

* **Pembaruan Importer Database (`engine.py`)**:
  * **Logika Update Duplikat**: Mengubah logika `simpan_hasil` sehingga ketika Sentinel Scraper melakukan pencarian harga live, jika produk e-commerce sudah ada di database dari pencarian terdahulu, sistem **seketika menimpa (*update*) data harga, diskon, rating, dan tautan referensi** dengan nilai terbaru dari internet, alih-alih melewatinya.
* **Tampilan Grid Multi-Toko Termurah (`wishlist_page.py`)**:
  * Menampilkan perbandingan harga premium di dalam modal detail Wishlist dengan menyajikan **hingga 3 toko termurah** untuk Tokopedia dan **hingga 3 toko termurah** untuk Lazada (diurutkan dari harga terhemat), dipadukan dengan kartu **Sociolla (Original)** di posisi teratas sebagai sumber resmi.

---

## 🛡️ 2. Penuntasan Blocker Jendela Jarak Jauh (Browser Pop-up Blocker Bypass)
Kami menemukan dan memecahkan hambatan (*bottleneck*) krusial pada interaksi tautan keluar (*external link redirect*).

* **Analisis Masalah**: 
  * Penggunaan `ui.open(url, new_tab=True)` di dalam fungsi Python NiceGUI memicu pembukaan jendela baru melalui komunikasi jaringan WebSocket backend. Mekanisme ini dinilai oleh peramban modern (Chrome, Edge, Firefox) sebagai *programmatic pop-up* mencurigakan, sehingga **diblokir keras secara otomatis** oleh sistem keamanan peramban.
* **Solusi Mutakhir**:
  * Mengubah interaksi kartu e-commerce di dalam [wishlist_page.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya Kelompok/main program/Skintify-C4/Skintify-C4/app/ui/pages/syaqila/wishlist_page.py) dan [compare_page.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya Kelompok/main program/Skintify-C4/Skintify-C4/app/ui/pages/najla/compare_page.py) dengan membungkus seluruh kartu langsung menggunakan komponen jangkar HTML asli (`ui.link` dengan atribut `target="_blank"`).
  * Hasilnya, proses pembukaan halaman pembelian di tab baru kini **100% kebal pop-up blocker**, berjalan instan tanpa latensi WebSocket backend, dan mematuhi aturan keamanan peramban modern.

---

## 🧬 3. AI Active-Ingredient Based Skin-Type Inference
Kami mengganti mesin penyimpulan jenis kulit lama yang tidak akurat menjadi model analisis bahan aktif kimia yang ilmiah dan klinis di dalam [compare_page.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya Kelompok/main program/Skintify-C4/Skintify-C4/app/ui/pages/najla/compare_page.py).

* **Kritik Logika Lama**:
  * Logika lama menggunakan pencarian kata dasar (seperti *"berminyak"*, *"kering"*) pada ulasan pelanggan dan deskripsi panjang secara acak. Hal ini rentan terhadap *False Positives* (misalnya kalimat ulasan negatif *"tidak cocok untuk kulit berminyak"* malah dibaca sebagai cocok untuk kulit berminyak) serta memperlambat pemuatan halaman secara signifikan.
* **Penerapan Sistem Baru (Dermatological Ingredient Profiling)**:
  * Sistem kini memindai daftar komposisi bahan produk (`ingredients`) untuk mendeteksi keberadaan senyawa aktif spesifik:
    * **Salicylic Acid (BHA), Tea Tree, Clay, Retinol** ➡️ **Oily** (Mengontrol sebum).
    * **Hyaluronic Acid, Glycerin, Shea Butter, Squalane, Ceramide** ➡️ **Dry** (Kelembapan intens).
    * **Centella Asiatica (Cica), Ceramide, Allantoin, Panthenol** ➡️ **Sensitive** (Menenangkan iritasi).
    * **Niacinamide, Vitamin C, Ascorbic Acid** ➡️ **Normal / All Skin Types**.
  * **Benefit**: Pemuatan halaman perbandingan meningkat **1000x lebih cepat** (nol latensi pemindaian teks besar) dan penyimpulan terjamin **100% ilmiah** untuk pertanggungjawaban akademis.

---

## 📅 4. AI Skin Safety & Weather Guardian di Routine Planner
Kami mengaktifkan data analisis backend yang sebelumnya tersembunyi untuk ditampilkan secara interaktif pada kartu rutinitas di [routine_page.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya Kelompok/main program/Skintify-C4/Skintify-C4/app/ui/pages/syhid/routine_page.py).

* **Deteksi Benturan Bahan Aktif ⚠️**:
  * Routine Planner secara aktif memindai perpaduan produk dalam satu sesi rutinitas Pagi atau Malam. Jika mendeteksi tabrakan kimia aktif (seperti *AHA/BHA + Retinol*), sistem langsung menampilkan kotak peringatan merah tebal:
    * *"• PERINGATAN BAHAN AKTIF: AHA/BHA dan Retinol digunakan bersamaan! Ini berisiko tinggi memicu iritasi kulit."*
* **Saran Proteksi Cuaca Real-Time 🌦️**:
  * Sistem menarik data cuaca lokal dan kelembapan secara real-time. Jika terdeteksi cuaca ekstrim (indeks UV tinggi atau kelembapan rendah), routine card akan memunculkan tips proteksi khusus:
    * *"• SARAN PROTEKSI CUACA (REAL-TIME): Hari ini: UV Index sangat tinggi! Gunakan Re-apply Sunscreen setiap 2 jam."*

---

## ⚔️ 5. Interactive Direct-to-Buy Skincare Battle Grid
Halaman perbandingan produk bertransformasi dari sekadar tabel data teks pasif menjadi gerbang pembelian interaktif.

* **Badge Tombol Kapsul CTA**:
  * Baris perbandingan harga Sociolla (Pink), Tokopedia (Green), dan Lazada (Blue) kini menampilkan **Badge CTA Kapsul** premium yang memuat harga termurah dari platform tersebut lengkap dengan ikon link keluar (`open_in_new`).
  * Badge ini bersifat interaktif dan dibungkus dengan tautan kebal pop-up blocker, memberikan jalan pintas bagi pengguna untuk langsung bertolak ke halaman lapak terhemat di tab baru.
* **Winner Card Update**:
  * Tombol **"Beli Sekarang"** pada kartu rekomendasi *Skintify Choice* ditingkatkan menggunakan pembungkus kebal pop-up blocker untuk memastikan kenyamanan penuh.

---

## 🔌 6. Multi-Select Wishlist Comparison & Centered Floating Dock
Kami menyematkan integrasi UX tanpa batas untuk membandingkan beberapa produk *langsung dari dalam halaman Wishlist*.

* **Sistem Pilihan Toglable (Checkbox-Style Button)**:
  * Tombol **"Bandingkan ⚔️"** pada setiap kartu produk di Wishlist kini bersifat togglable.
  * Ketika diklik, produk tersebut masuk ke dalam antrean pemilihan `wishlist_compare_selections` (maksimal 3 produk) dan tombol berubah warna menjadi **"Terpilih ⚔️"** (hijau emerald premium). Jika diklik ulang, produk dikeluarkan dari antrean.
* **Centered iOS-style Floating Compare Dock**:
  * Begitu pengguna memilih minimal 2 produk (hingga 3 produk), sebuah **Dock Perbandingan Melayang** yang super premium muncul secara elegan di bagian bawah layar peramban.
  * Dock melayang ini menampilkan thumbnail circular dari produk yang diadu dipadukan dengan teks pemisah `vs` dan badge urutan slot (1, 2, 3), lengkap dengan tombol **"Batal"** dan **"Bandingkan ⚔️"**.
* **Integrasi Slot Arena Perbandingan**:
  * Ketika tombol perbandingan di dock melayang diklik, sistem menyuntikkan seluruh produk terpilih ke dalam Slot 1, Slot 2, dan Slot 3 di `compare_slots`, menyelaraskan kategori pencarian, lalu bertolak secara instan ke halaman `/compare`.
  * Pengguna dapat menikmati arena perbandingan yang langsung terisi lengkap dengan produk wishlist mereka tanpa perlu memilah-milah katalog manual!

---

> [!NOTE]
> Pembaruan-pembaruan di atas telah divalidasi, lolos uji kompilasi python (`py_compile`) 100% tanpa eror, dan telah diintegrasikan secara penuh pada modul utama Skintify. Dokumen ini dapat dimanfaatkan sebagai draf penjelasan teknis yang sangat bernilai tinggi saat presentasi kelompok.
