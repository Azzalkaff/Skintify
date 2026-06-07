# 🎓 Panduan Presentasi Kode Syahid (Skintify-C4)

Halo Syahid! Jangan panik buat presentasinya ya. Ini adalah **Cheat Sheet / Panduan** lengkap untuk menjelaskan semua kode yang kamu kerjakan di folder `app/ui/pages/syhid`. 

Kamu bertanggung jawab atas 4 halaman utama yang memiliki fitur-fitur sangat canggih dan keren. Kalau ditanya dosen atau penguji, kamu bisa gunakan penjelasan di bawah ini agar terlihat menguasai arsitektur dan fungsionalitas aplikasinya!

---

## 1. 🔍 Halaman Pencarian Produk (`search_page.py`)
Halaman ini adalah pusat katalog produk skincare di mana pengguna bisa mencari dan memfilter produk.

### Fitur & Konsep Kunci:
- **Filter Dinamis Multi-Kriteria:** Terdapat filter untuk kategori, brand, tipe kulit, range harga, dan urutan. Filter ini dihubungkan langsung dengan backend menggunakan `data_mgr.get_paginated_products` (di-run secara asynchronous `asyncio.to_thread` agar UI tidak freeze).
- **Live Scraping E-Commerce:** Saat produk dicari, kode dapat memicu fungsi `scrape_marketplace_live` untuk mengambil data harga *real-time* dari Tokopedia dan Lazada, lalu menyimpannya ke database sebagai *cache*.
- **Integrasi Modal & Wishlist:** Produk yang tampil berupa kartu (Grid UI). Pengguna bisa menambahkannya ke *Wishlist* (menggunakan operasi O(1) set lookup `state.wishlist_slugs` agar cepat), atau mengklik tombol "Bandingkan Harga Marketplace" yang akan memanggil modal detail bersama.
- **Admin Privileges:** Jika yang login adalah *Admin*, mereka akan melihat tombol "Tambah Produk Baru" serta ikon pensil dan tong sampah di tiap kartu produk untuk melakukan operasi CRUD (Create, Read, Update, Delete) langsung dari UI.

**💡 Tips Presentasi:**
> *"Pada halaman pencarian, saya menggunakan NiceGUI untuk merender grid produk secara asinkron (asyncio.to_thread) agar UI tidak nge-lag saat memproses ribuan data. Selain itu, saya membuat logika filter dinamis yang menggabungkan filter dari database SociollaReferensi dengan live scraping e-commerce untuk mendapatkan komparasi harga terbaik."*

---

## 2. 🤖 Halaman AI Chatbot (`ai_chat_page.py`)
Ini adalah asisten virtual "Skintif AI" dengan persona ala cewek Gen-Z Indonesia yang sangat ekspresif.

### Fitur & Konsep Kunci:
- **Dual LLM Engine:** Menggunakan API dari **Gemini** (`gemini-3.1-flash-lite`) dan **Groq** (`llama-3.3-70b-versatile`) via HTTP POST *request*. Jika satu limit/error, bisa memakai yang lain.
- **Prompt Engineering & Keamanan:** Terdapat `CORE_SYSTEM_PROMPT` yang sangat ketat untuk mencegah *prompt injection* (memaksa AI melakukan tugas di luar ranah skincare).
- **Voice / Audio Input (Speech-to-Text):** Pengguna bisa mengirim *voice note*. Suara ini diubah menjadi teks menggunakan Whisper API dari Groq atau kapabilitas *multimodal* dari Gemini.
- **Offline / Heuristic Fallback (`get_smart_mock_response`):** Jika AI dimatikan atau API error, sistem memiliki logika *If-Else* offline yang cerdas untuk mendeteksi *budgeting* (menggunakan NLP sederhana berbasis regex untuk parsing nominal uang), konflik bahan aktif (misal Retinol + AHA/BHA), dan analisis sirkadian kulit (Pagi/Malam).
- **Tool Calling (Parse AI Action):** AI dirancang agar dapat merespons dengan JSON `CREATE_ROUTINE`. Sistem menggunakan *Regular Expression* (Regex) untuk mengekstrak ID produk rekomendasi dan format JSON, lalu memunculkan UI *pop-up* untuk menambahkannya ke Planner!

**💡 Tips Presentasi:**
> *"Chatbot ini tidak hanya sekadar memanggil API AI biasa. Saya membuat sistem yang mengekstraksi tag khusus atau JSON (menggunakan Regex) dari respons AI agar sistem bisa melakukan aksi nyata, seperti langsung memasukkan rekomendasi produk ke Routine Planner. Selain itu, saya menambahkan fitur STT (Speech-to-Text) untuk memproses input suara."*

---

## 3. 📅 Halaman Routine Planner (`routine_page.py`)
Tempat di mana pengguna bisa menyusun langkah-langkah pemakaian skincare mereka.

### Fitur & Konsep Kunci:
- **CRUD Rutin & Item:** Pengguna bisa membuat banyak jadwal rutin (misal: "Rutin Pagi", "Rutin Malam"), lalu menambahkan produk ke dalamnya. Item bisa digeser urutannya (Reordering) dan diganti.
- **Poka-Yoke / Peringatan Keamanan Otomatis:** Saat rutin dirender, sistem akan memanggil fungsi `analyze_routine`. Jika sistem mendeteksi ada bahan aktif yang bertabrakan (misalnya Retinol dengan Exfoliating Toner) dalam 1 rutin, UI akan menampilkan *Peringatan Merah* (Conflict Detection).
- **Template Generator (1-Click Schedule):** Fitur keren di mana pengguna memilih tipe kulit (contoh: *Oily*), lalu sistem secara otomatis men-generate **1 Rutin Pagi** dan **7 Rutin Malam** (Senin-Minggu) dengan rotasi serum yang direkomendasikan secara dermatologis (Skin Cycling).
- **Rekomendasi Cuaca Real-Time:** Integrasi dengan *Weather Service* untuk memberikan saran berdasarkan cuaca hari itu (misal: "Hari ini terik, perbanyak sunscreen").

**💡 Tips Presentasi:**
> *"Di Routine Planner, fokus utama saya adalah 'Cognitive Load' yang rendah. Saya membuat fitur Generator Template agar pengguna pemula bisa mendapatkan jadwal 7 hari secara otomatis. Yang paling penting, saya mengimplementasikan sistem deteksi konflik bahan aktif, sehingga jika user memasukkan produk yang bertabrakan, sistem akan langsung memberikan peringatan."*

---

## 4. ⚙️ Halaman Admin Panel (`admin_page.py`)
Ini adalah *Dashboard* khusus untuk super-user.

### Fitur & Konsep Kunci:
- **Role-Based Access Control (RBAC):** Memiliki pengecekan `app.storage.user.get('role') != 'admin'`. Jika user biasa mencoba mengakses halaman ini, mereka akan langsung ditendang kembali ke Home (`/`).
- **Tabbed Interface:** Terdiri dari berbagai tab seperti Manajemen Produk, Template Routine, Data Ops, dan Control Center.
- **Manajemen Marketplace (CRUD Lengkap):** Menampilkan tabel yang memuat data produk gabungan dari master database (Sociolla) dan hasil scraping e-commerce (Tokopedia, Lazada, Shopee). Admin bisa mengedit harga, rating, menambah URL *Affiliate*, hingga menghapus toko bodong.
- **Data Ops & CLI Integration:** Admin bisa memicu script scraper Python di *background* menggunakan subproses tanpa harus membuka terminal secara manual.

**💡 Tips Presentasi:**
> *"Untuk panel Admin, saya memastikan keamanannya dengan pengecekan RBAC ganda. Panel ini sangat fungsional, admin bisa memonitor dan mengedit data dari berbagai sumber marketplace, memasukkan link affiliate, hingga menjalankan operasi Data Scraping langsung dari dalam web tanpa perlu menyentuh terminal server."*

---

## 🚀 Kesimpulan Singkat untuk Dosen
Kalau ditanya apa kontribusi terbesarmu, jawab dengan ini:
*"Saya bertanggung jawab dalam membangun jembatan antara logika backend AI dan e-commerce dengan interaksi pengguna (UI/UX) menggunakan *framework* NiceGUI. Saya mengembangkan sistem pencarian dinamis, integrasi bot AI interaktif yang bisa melakukan *speech-to-text* dan aksi UI, serta membuat sistem Routine Planner cerdas yang mampu mendeteksi tabrakan bahan kimia secara otomatis."*

Semoga sukses presentasinya! Tarik napas panjang, kamu pasti bisa menjawab semuanya! 🔥
