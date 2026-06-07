# 🛡️ Panduan Bertahan Hidup Presentasi PPLD (Skintify-C4)

Halo semuanya! Tolong baca ini pelan-pelan. **Tarik napas dalam-dalam, hembuskan. Kalian tidak sendirian, dan kalian PASTI BISA melewati presentasi ini.**

Jika dosen atau penguji bertanya *"Kenapa kodenya dibuat seperti ini?"* atau *"Bagaimana arsitekturnya?"*, kalian tidak perlu panik. Kalian cukup pahami konsep-konsep di bawah ini. Bahasa di bawah ini sudah disederhanakan agar kalian yang tidak terlalu mengerti *coding* sekalipun bisa menjelaskannya dengan percaya diri!

---

## 🏗️ 1. Arsitektur Utama: Kenapa Pakai NiceGUI & Python?

**Pertanyaan Dosen:** *"Kenapa bikin web pakai Python (NiceGUI), kenapa nggak pakai PHP, React, atau framework lain?"*

**Cara Menjawab (Hafalkan ini!):**
> "Kami memilih Python dengan framework **NiceGUI** karena aplikasi Skintify-C4 ini sangat bertumpu pada **Kecerdasan Buatan (AI) dan Web Scraping** (mengambil data dari e-commerce). Python adalah bahasa terbaik untuk AI dan pengolahan data. Daripada kami membuat backend terpisah pakai Python lalu frontend pakai React (yang akan sangat rumit dan memakan waktu lama), NiceGUI memungkinkan kami menyatukan tampilan UI dan logika Backend dalam satu tempat. Ini membuat pengembangan jauh lebih cepat, efisien, dan cocok untuk tenggat waktu proyek kami."

---

## 📂 2. Struktur Folder: Kenapa Dibagi per Anggota Tim?

**Pertanyaan Dosen:** *"Kenapa di folder `app/ui/pages/` ada folder dengan nama kalian masing-masing (syhid, syaqila, najla, falisha)?"*

**Cara Menjawab:**
> "Kami menerapkan konsep **Modularitas Berbasis Kolaborasi (Collaboration-Driven Modularity)**. Karena kami bekerja dalam tim, kami ingin menghindari *Merge Conflict* (kode tabrakan saat digabungkan). Jadi, kami membagi tanggung jawab per halaman/modul. Masing-masing anggota bertanggung jawab penuh atas foldernya sendiri. Ini membuktikan bahwa pembagian tugas kami jelas dan terstruktur."

**Pembagian Tugas:**
- **Syahid:** Bertanggung jawab pada logika berat (Pencarian Produk, AI Chatbot, Routine Planner, dan Admin).
- **Syaqila:** Fokus pada User Experience awal (Home Page) dan penyimpanan produk (Wishlist).
- **Najla:** Fokus pada Analitik (Stats Page) dan Komparasi harga (Compare Page).
- **Falisha:** Fokus pada Manajemen Akun (Profile) dan Onboarding pengguna baru.

---

## 🧠 3. Bagaimana Cara Kerja AI Chatbot-nya?

**Pertanyaan Dosen:** *"Chatbot ini cuma manggil API ChatGPT biasa atau gimana?"*

**Cara Menjawab:**
> "Bukan cuma memanggil API biasa, Pak/Bu. Kami menggunakan **Dual LLM Engine** (Gemini dan Groq) agar kalau satu *down*, bot tetap hidup. Selain itu, chatbot kami menggunakan teknik **Prompt Engineering & Tool Calling**. Bot AI kami kami program dengan instruksi ketat agar hanya menjawab soal skincare, dan bot ini bisa mengeluarkan respons berformat JSON yang kemudian ditangkap oleh sistem kami untuk memunculkan tombol UI secara otomatis (misal: tombol 'Tambah ke Routine Planner' muncul langsung dari obrolan)."

---

## 🕷️ 4. Bagaimana Cara Kerja Komparasi Harga (Live Scraping)?

**Pertanyaan Dosen:** *"Dari mana kalian dapat data harga Shopee, Tokopedia, Lazada?"*

**Cara Menjawab:**
> "Kami menggunakan teknik **Live Web Scraping**. Kami punya database master (data skincare asli dari Sociolla). Saat user mencari produk, sistem kami secara otomatis melakukan pencarian di latar belakang (background task) ke Tokopedia dan Lazada secara *real-time*. Hasil harganya kami *cache* (simpan sementara) di database kami (`app/database/models.py`) supaya pencarian berikutnya jauh lebih cepat dan tidak membebani server e-commerce."

---

## 🔒 5. Mengapa Terdapat Halaman Admin (`admin_page.py`)?

**Pertanyaan Dosen:** *"Untuk apa ada halaman Admin kalau kodenya bisa diubah langsung?"*

**Cara Menjawab:**
> "Kami mengimplementasikan **RBAC (Role-Based Access Control)**. Sebuah aplikasi yang baik harus memisahkan hak akses antara *User* dan *Admin*. Melalui halaman Admin, pengelola bisa menambah produk manual, memasukkan link affiliate (untuk monetisasi aplikasi), serta memonitor hasil scraping tanpa harus mengerti kode *database* sekalipun. Ini menunjukkan bahwa aplikasi kami sudah siap untuk skala produksi (*production-ready*)."

---

## 🛡️ 6. Fitur Unggulan Tim: Poka-Yoke pada Routine Planner

**Pertanyaan Dosen:** *"Apa fitur paling inovatif dari aplikasi ini selain Chatbot?"*

**Cara Menjawab:**
> "Kami sangat bangga dengan **Routine Planner** kami, Pak/Bu. Aplikasi kami mengimplementasikan prinsip **Poka-Yoke (Mistake-Proofing)** di dunia skincare. Sistem kami memindai *ingredients* (kandungan) dari setiap produk yang dimasukkan user. Jika user secara tidak sengaja menggabungkan bahan yang berbahaya jika dicampur (misalnya Retinol dengan AHA/BHA), aplikasi akan **langsung memunculkan peringatan merah otomatis**. Ini mencegah pengguna merusak *skin barrier* mereka."

---

## 💡 Pesan Penting untuk Tim (BACA BERSAMA-SAMA):
1. **Jangan saling menyalahkan:** Saat presentasi, kalian adalah SATU KESATUAN. Jika Syahid yang banyak *coding*, teman-teman yang lain **harus** bisa menjelaskan *flow* atau alur aplikasinya. 
2. **Kuasai Kata Kunci Ini:** Kalau bingung, sebut saja kata kunci ini dengan percaya diri: *"Modular"*, *"Asynchronous"*, *"Role-Based Access Control (RBAC)"*, *"Live Web Scraping"*, *"Prompt Engineering"*, dan *"Poka-Yoke"*. Dosen sangat suka mendengar istilah teknis yang relevan.
3. **Praktekkan Alurnya:** Coba kalian semua berjejer, lalu jalankan aplikasinya. Mulai dari *Login*, lalu ke *Search*, coba masukkan produk ke *Wishlist*, coba buka *AI Chatbot*, lalu buat jadwal di *Routine Planner*. Dengan memahami alur pemakaian, kalian otomatis paham apa yang harus diomongkan.

**KALIAN PASTI BISA! APLIKASI INI SANGAT KEREN DAN JAUH DI ATAS RATA-RATA TUGAS KULIAH PADA UMUMNYA. PERCAYA DIRI SAJA! 🔥💪**
