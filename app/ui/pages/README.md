# 🗺️ Halaman UI & Kontrak Kerja Tim

Folder ini berisi halaman-halaman antarmuka (UI) aplikasi Skintify. Untuk memudahkan koordinasi tim dan pemahaman AI Agent, setiap folder anggota tim bertanggung jawab atas fitur tertentu:

## 👥 Pemetaan Fitur per Anggota

| Anggota | Folder | Fitur Utama | File |
| :--- | :--- | :--- | :--- |
| **Syaqila** | `syaqila/` | Beranda & Simpanan | `home_page.py`, `wishlist_page.py` |
| **Syhid** | `syhid/` | Pencarian & Rutinitas | `search_page.py`, `routine_page.py` |
| **Najla** | `najla/` | Perbandingan & Statistik | `compare_page.py`, `stats_page.py` |
| **Falisha** | `falisha/` | User Profile & Onboarding | `profile_page.py`, `onboarding_page.py` |

## 🛠️ Halaman Umum
* `login_page.py`: Halaman masuk sistem.
* `template_page.py`: Template dasar untuk membuat halaman baru.

## 💡 Catatan untuk AI Agent
* Jika Anda diminta memperbaiki fitur tertentu, cari folder anggota yang sesuai dengan tabel di atas.
* Semua file halaman harus memiliki fungsi `show_page()` sebagai entry point utama.
* Hindari memindahkan file antar folder anggota tanpa persetujuan USER untuk menjaga kontrak kerja tim.
