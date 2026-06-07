# Persiapan Presentasi Skintify-C4

Dokumen ini berisi panduan dan penjelasan teknis dengan bahasa yang sederhana (low cognitive load) untuk persiapan presentasi di depan dosen. Anda dapat menggunakan istilah-istilah di bawah ini agar terlihat menguasai program tanpa membuat audiens kebingungan.

## 1. Konsep Utama Aplikasi

**Apa itu Skintify-C4?**
Skintify-C4 adalah aplikasi desktop dan web cerdas berbasis Python yang membantu pengguna membandingkan, mencari, dan mencatat produk perawatan kulit (skincare). Aplikasi ini dirancang agar ringan, responsif, dan mudah digunakan.

## 2. Arsitektur & Teknologi (Tech Stack)

Saat menjelaskan teknologi, gunakan analogi yang relevan:

*   **Frontend & Backend (Python + NiceGUI):**
    Kita tidak menggunakan framework web tradisional yang rumit. Aplikasi dibangun menggunakan **NiceGUI**, sebuah framework Python yang menyatukan logika backend (pemrosesan data) dan antarmuka visual (frontend) dalam satu bahasa. 
    *   *Analogi:* Ibarat koki (backend) dan pelayan (frontend) yang berada di satu ruangan, komunikasi menjadi jauh lebih cepat tanpa jeda.

*   **Database (SQLite & SQLAlchemy):**
    Kita menggunakan dua database lokal (`data_skintify.db` untuk data pengguna dan `tokopedia.db` untuk data produk) menggunakan format **SQLite**. Untuk menghubungkan Python ke database, kita memakai **SQLAlchemy (ORM)**.
    *   *Penjelasan Dosen:* "Kami menggunakan SQLite agar aplikasinya mandiri (standalone) tanpa perlu server database terpisah. SQLAlchemy membantu kami mengolah data tabel sebagai 'Objek Python', sehingga kodenya lebih bersih dan minim error (SQL Injection)."

*   **Arsitektur SPA (Single Page Application):**
    Aplikasi menerapkan konsep router SPA kustom.
    *   *Penjelasan Dosen:* "Aplikasi kami memuat halaman utama (kerangka/navbar) hanya satu kali di awal. Ketika user pindah halaman dari Home ke Profile, kami hanya membongkar-pasang konten bagian tengahnya saja. Ini menghemat penggunaan data dan membuat aplikasi terasa instan tanpa loading layar putih."

## 3. Istilah Teknis Penting (Glosarium)

Pahami istilah ini, jika ditanya dosen, jawablah dengan tenang:

*   **Scraping (Web Scraping):** 
    Proses otomatis mengambil data dari sumber eksternal (seperti Sociolla atau Tokopedia). 
    * *Jawaban:* "Kami menggunakan library seperti `requests` dan `curl-cffi` untuk mengumpulkan data produk e-commerce agar database kami selalu memiliki referensi harga dan kandungan yang relevan."
*   **Fuzzy Matching / Pencarian Fuzzy (RapidFuzz):**
    Algoritma pintar untuk mencari teks meskipun ada salah ketik (typo).
    * *Jawaban:* "Karena nama skincare sering kali sulit dieja (misal *Niacinamide*), algoritma pencarian kami tidak menuntut kecocokan 100%. Kami menggunakan RapidFuzz sehingga sistem tetap bisa menebak maksud pencarian user dengan akurat."
*   **State Management / app.storage (Kritik Best Practice):**
    Teknik menyimpan status *session* atau *cache* sementara di memori/storage aplikasi (menggunakan fitur bawaan NiceGUI `app.storage.user`).
    * *Penjelasan & Kritik (Jika ditanya Dosen):* "Saat ini kami menggunakan `app.storage` untuk menyimpan riwayat aktivitas dan *state* sementara agar memori aplikasi tidak membebani database (sebagai *cache* lokal). **Namun, secara *Best Practice* rekayasa perangkat lunak**, data krusial seperti *Wishlist* seharusnya disimpan (persisted) ke dalam Database relasional secara permanen. Hal ini kami sadari sebagai *trade-off* (kompromi) untuk mempercepat performa *prototype* ini, dan rencana pengembangannya (Future Work) adalah melakukan sinkronisasi dari *storage* lokal ke Database secara berkala."
*   **Asynchronous Programming (Non-Blocking UI):**
    Teknik menjalankan tugas berat tanpa membuat layar aplikasi *freeze* atau macet.
    * *Jawaban:* "Karena NiceGUI berjalan secara *asynchronous*, kami menggunakan `asyncio.to_thread` saat melakukan kueri database yang berat atau saat mengirim email OTP. Hal ini memastikan UI (Antarmuka) tetap responsif dan tidak membeku (*blocking*) saat menunggu proses dari server/database selesai."
*   **Keamanan Kriptografi (Password Hashing):**
    Cara menyimpan password agar tidak bisa dibaca, bahkan oleh pembuat aplikasi.
    * *Jawaban:* "Kami sangat memperhatikan keamanan data. Password pengguna tidak disimpan dalam bentuk teks biasa (plain-text), melainkan dienkripsi menggunakan algoritma **PBKDF2-SHA256** ditambah *salt* acak (kriptografi). Jadi, jika database kami bocor sekalipun, password pengguna tetap aman."
*   **Graceful Error Handling (Penanganan Error Elegan):**
    Sistem pencegahan agar aplikasi tidak langsung mati mendadak saat terjadi *bug*.
    * *Jawaban:* "Pada router SPA utama kami di `main.py`, kami membungkus pemanggilan halaman dengan blok `try-except`. Jika terjadi error teknis di satu halaman, aplikasi tidak akan *crash* (mati) seluruhnya, melainkan hanya menampilkan layar peringatan khusus dan *sidebar* tetap bisa digunakan untuk pindah ke halaman lain yang aman."
*   **Environment Variables (.env):**
    Menyimpan kode rahasia di luar *source code*.
    * *Jawaban:* "Kami menerapkan praktik keamanan standar industri dengan memisahkan *credentials* (seperti password email SMTP dan kunci enkripsi *Storage Secret*) ke dalam file `.env`. File ini tidak diunggah ke repositori GitHub, sehingga mencegah kebocoran data sensitif."
*   **Modularization (Modularisasi Kode):**
    Memecah satu program raksasa menjadi kepingan modul (seperti `home_page`, `search_page`, `compare_page`).
    * *Jawaban:* "Sesuai dengan praktik rekayasa perangkat lunak (Software Engineering), kami menerapkan pemisahan tanggung jawab (Separation of Concerns). Setiap anggota tim (Syaqila, Najla, Falisha) bertanggung jawab atas modulnya sendiri sehingga kode lebih rapi dan bebas konflik saat digabungkan."
*   **PyInstaller / Deployment Executable:**
    Aplikasi dapat dibungkus menjadi `.exe`.
    * *Jawaban:* "Agar bisa digunakan oleh user awam, kami menggunakan PyInstaller untuk mem-bundle aplikasi beserta engine Python-nya ke dalam satu file siap klik. User tidak perlu menginstal Python di komputernya."

## 4. Antisipasi Pertanyaan Dosen (Q&A)

1.  **Dosen:** *"Mengapa kalian menggunakan NiceGUI dibandingkan React/Vue untuk antarmukanya?"*
    **Jawaban Anda:** "Karena fokus utama kami adalah pengolahan data produk dan logika di backend menggunakan Python. NiceGUI memungkinkan kami membuat UI yang modern tanpa harus berpindah bahasa pemrograman, dan komunikasi datanya (antara UI dan backend) berjalan seketika via WebSocket. Waktu pengembangan menjadi lebih efisien."

2.  **Dosen:** *"Bagaimana sistem aplikasi memastikan keamanan data user (Login)?"*
    **Jawaban Anda:** "Pertama, di level database, kami meng-hash password dengan algoritma PBKDF2. Kedua, kami memiliki modul *Router Guard*. Jika user mencoba mengetik URL secara paksa ke halaman rahasia (misal `/profile`), router kami akan mengecek token otentikasinya, lalu secara otomatis memblokir dan melemparnya kembali ke halaman login."

3.  **Dosen:** *"Apakah aplikasi ini berat/lemot jika data produknya (ribuan) ditampilkan semua?"*
    **Jawaban Anda:** "Tidak, Pak/Bu. Ini poin penting yang sudah kami atasi. Di backend, database SQLite kami menggunakan *indexing*. Di sisi tampilan (frontend), kami menerapkan sistem **Pagination** (pembagian halaman) lewat fungsi `get_paginated_products`. Alih-alih memuat 10.000 produk ke RAM, kami hanya mengambil dan mengirimkan 12 produk per halaman. Hal ini membuat aplikasi sangat ringan."

4.  **Dosen:** *"Bagaimana cara kerja pencarian pintar AI kalian di AI Chat?"*
    **Jawaban Anda (Senjata Pamungkas AI):** "Arsitektur AI kami sangat kompleks dan berlapis (Hybrid System), Pak/Bu. Kami menggabungkan beberapa teknik *Computer Science* tingkat lanjut:
    *   **Retrieval-Augmented Generation (RAG) & Context-Aware:** AI (seperti Gemini/Groq) tidak dibiarkan menjawab bebas (halusinasi). Kami menyuntikkan *system prompt* yang berisi profil medis pengguna (tipe kulit, daftar *ingredients* yang dihindari) secara dinamis sebelum merespons.
    *   **Chronodermatology (Sirkadian Waktu):** Sistem kami mengekstrak waktu lokal (`datetime.now().hour`). Jika user *chat* di pagi hari, AI difokuskan merekomendasikan *Sunscreen*. Jika malam, AI merekomendasikan pemulihan *barrier* atau *Retinol*.
    *   **Multi-Criteria Decision Analysis (MCDA):** Untuk skenario *budgeting* (misal user mengetik 'budget 150 ribu'), kami menggunakan algoritma MCDA (pembobotan 70% rating, 30% popularitas) untuk meracik paket *skincare* terbaik secara otomatis tanpa koneksi API (Offline Heuristik).
    *   **Token-Based Regex Parsing:** Saat AI memunculkan teks rekomendasi produk, kami mencegatnya menggunakan *Regular Expression (Regex)*, memecah kata-katanya menjadi *token*, dan melakukan pencarian `AND Query` ke database SQLite agar produk yang direkomendasikan AI 100% akurat dengan stok di toko."

## Tips Presentasi
- Jangan membaca teks kodenya baris per baris. Tunjukkan **alur** (cara kerjanya) dan **arsitektur** besarnya.
- Jika ada *error* saat demo (seperti *KeyboardInterrupt* yang biasa terjadi di console saat server dimatikan), tetap tenang dan sebutkan: *"Ini adalah log wajar saat proses dihentikan secara manual (graceful shutdown), di sisi pengguna, aplikasinya tertutup dengan aman."*
- Buka dan tunjukkan file `main.py` bagian *Router SPA* (`create_spa_router()`) atau file `database_manager.py` (bagian *Hashing Password*) sebagai "senjata pamungkas" untuk menunjukkan kompleksitas teknis yang elegan yang telah grup Anda bangun.
