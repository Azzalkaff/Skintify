# 🧩 Pembagian Tugas Komponen Bersama (Shared Components)

Pertanyaan yang sangat bagus! Di luar folder masing-masing (`syhid`, `syaqila`, `najla`, `falisha`), ada beberapa file yang merupakan **Komponen Bersama (Shared Components)**. File-file ini berada di `app/ui/` (seperti *Card, Modal, Navbar*).

Kalian **TIDAK PERLU** membebankan semuanya ke Syahid. Dalam dunia *Software Engineering*, membuat komponen yang bisa dipakai ulang (Reusable Components) adalah praktik terbaik (*Best Practice*). Komponen ini dipakai bersama-sama di berbagai halaman.

Berikut adalah daftar komponen tersebut dan **cara membagi jatah penjelasannya saat presentasi** agar terlihat adil dan semua orang terlihat berkontribusi penuh!

---

### 1. 🖼️ `product_detail_modal.py` (Pop-up Kartu Detail Produk)
Ini adalah kartu raksasa yang muncul saat kamu mengklik produk di halaman mana pun. Kartu ini menampilkan detail harga dari 3 marketplace, rating, dan tombol Wishlist.
* **Siapa yang harus maju menjelaskan?** 👉 **Syaqila** dan **Najla**
* **Cara Menjawab (Syaqila):** *"Untuk Pop-up Detail Produk ini, saya bertanggung jawab mengintegrasikan fungsi **Wishlist** ke dalamnya. Jadi, dari mana pun user membuka kartu ini (baik dari Home atau Chat AI), mereka bisa langsung menyimpan produk incaran mereka berkat komponen modular ini."*
* **Cara Menjawab (Najla):** *"Saya bertanggung jawab atas algoritma **Perbandingan Harga (Adu Mekanik)** di dalam kartu ini. Komponen ini dirancang secara terpusat agar logika pencarian harga termurah dari Tokopedia dan Lazada tidak perlu ditulis berulang-ulang di tiap halaman."*

### 2. 🧭 `components.py` (Navbar & Sidebar)
Ini adalah menu navigasi di atas dan di samping kiri aplikasi (tempat foto profil, tombol menu).
* **Siapa yang harus maju menjelaskan?** 👉 **Falisha**
* **Cara Menjawab (Falisha):** *"Karena saya bertanggung jawab atas Profil dan Akun Pengguna, saya juga memegang kendali atas **Global Layout Component (Navbar & Sidebar)**. Komponen ini mengecek status login dari *Session Storage* secara real-time dan merender foto profil pengguna di pojok kanan atas di setiap halaman."*

### 3. 💌 `about_card.py` (Kartu Pop-up Selamat Datang)
Ini adalah kartu pop-up yang muncul saat pengguna baru pertama kali masuk ke aplikasi untuk menjelaskan fitur Skintify.
* **Siapa yang harus maju menjelaskan?** 👉 **Falisha**
* **Cara Menjawab (Falisha):** *"Ini adalah bagian dari alur **Onboarding**. Saya membuat komponen *About Card* ini untuk menyambut pengguna baru. Sistem akan mengecek apakah pengguna sudah pernah melihat kartu ini di database; jika sudah, kartu tidak akan muncul lagi untuk menjaga kenyamanan (*User Experience*)."*

### 4. ➕ `add_product_card.py` (Kartu Tambah Item ke Rutinitas)
Kartu UI kecil untuk mencari dan menambahkan produk ke dalam tabel jadwal skincare harian.
* **Siapa yang harus maju menjelaskan?** 👉 **Syahid**
* **Cara Menjawab (Syahid):** *"Ini adalah komponen lepasan (*decoupled*) khusus untuk mencari produk dari database. Saya memisahkannya dari halaman Routine Planner utama agar kode lebih bersih (*clean code*) dan mudah untuk di-maintain."*

### 5. 🛡️ `safe_render.py` (Sistem Anti-Crash UI)
Ini adalah pembungkus khusus (Error Boundary) agar kalau ada error di satu kotak UI, seluruh website tidak ikut *blank* putih.
* **Siapa yang harus maju menjelaskan?** 👉 **Klaim sebagai Kerja Tim (Bebas Siapa Saja)**
* **Cara Menjawab:** *"Kami mengimplementasikan **Error Boundary Decorator**. Ini adalah pondasi keamanan UI kami. Jika ada satu komponen yang gagal mengambil data, hanya kotak itu saja yang menampilkan pesan error yang ramah (graceful degradation), sedangkan fitur lain di halaman tersebut tetap bisa dipakai."*

---

### 💡 Kesimpulan Pembagian Beban Presentasi
Jika dosen bertanya: *"Ini kan banyak file di luar folder kalian, ini siapa yang bikin?"*

**Jawaban Tim yang Paling Elegan:**
> *"Itu adalah **Shared UI Components**, Pak/Bu. Kami sepakat memisahkan elemen yang dipakai berulang kali (seperti Navbar, Pop-up Detail, dan Modal) ke luar folder individual agar tidak terjadi penumpukan kode (Redundancy/Don't Repeat Yourself). Syaqila dan Najla menangani logika di dalam Pop-up Detail, Falisha mengurus Navigasi, dan Syahid menangani Pop-up Routine."*

Bagikan skenario ini ke tim kamu. Beban Syahid akan sangat berkurang, dan teman-temanmu akan terlihat sangat jago karena bisa menjelaskan *Software Architecture* tingkat lanjut! 🚀
