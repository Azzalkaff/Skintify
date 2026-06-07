---

### `coding_standards.md`

# Coding Standards & AI Engineering SOP: Skintify-C4

Tujuan dari dokumen ini adalah untuk memastikan seluruh *source code* (baik yang ditulis manusia maupun AI) memenuhi standar kualitas industri: **Clean, Modular, Scalable, dan Maintainable** yang disesuaikan untuk arsitektur **Python 3.12, NiceGUI, dan SQLAlchemy**.

## 1. Core Principles (The "Clean Code" Mantra)

* **KISS (Keep It Simple, Stupid):** Jangan melakukan *over-engineering*. Jika masalah bisa diselesaikan dengan 5 baris, jangan gunakan 20 baris.
* **DRY (Don't Repeat Yourself):** Jika logika diulang lebih dari 2 kali, pindahkan ke fungsi atau *utility* terpisah.
* **Separation of Concerns (SoC) dalam Three-Tier Architecture:**
  * **UI (NiceGUI Components):** Tidak boleh berisi logika bisnis berat atau *query* database langsung. Berada di `app/ui/`.
  * **Business Logic (Services):** Logika seperti scraping (`scraper.py`) atau analisa AI (`data_manager.py`) harus berada di folder `app/services/`.
  * **Data Layer (Database/Models):** Semua interaksi dengan SQLite melalui SQLAlchemy ORM harus berada di `app/database/`.
* **Self-Explanatory:** Gunakan penamaan variabel yang deskriptif ala Pythonic (`snake_case`). `days_until_expiry` lebih baik daripada `d`.

## 2. Modularity & Scalability

* **Single Responsibility Principle (SRP):** Satu file atau satu fungsi hanya boleh melakukan **satu** hal utama.
* **Component-Based UI:** Antarmuka NiceGUI harus dipecah menjadi komponen-komponen kecil yang *reusable* (seperti Navbar, Sidebar, Card) di `app/ui/components.py`.
* **Strict Typing (Python Type Hinting):** Hindari tipe data dinamis yang ambigu. Selalu gunakan *Type Hints* (contoh: `def get_user(user_id: int) -> User:`) untuk fungsi, argumen, dan nilai kembali (*return value*).

## 3. Anti-Code Smells & Best Practices

* **Zero Magic Strings:** Simpan konfigurasi, URL *endpoint*, atau *string* statis yang sering digunakan ke dalam file konstanta (contoh: di file `config.py` atau kelas Enum).
* **Error Handling:** Jangan pernah menelan error (`except Exception as e: pass`). Selalu berikan log yang bermakna atau tangkap exception spesifik, dan tampilkan notifikasi yang informatif bagi user menggunakan `ui.notify()`.
* **Asynchronous Safety:** Selalu berhati-hati saat menggunakan fungsi `async/await` di NiceGUI. Tangani error dengan `try-except` yang baik untuk mencegah aplikasi tertutup (crash) akibat *unhandled exception*.
* **State Management:** Kelola *state* pengguna atau aplikasi dengan aman melalui `app.storage.user` atau manajemen sesi pada file `app/context.py`. Hindari memanipulasi *global state* yang tidak *thread-safe*.

## 4. AI-Agent Interaction Guidelines

Setiap kali meminta bantuan AI (seperti Gemini) untuk menulis kode pada Skintify-C4, gunakan instruksi berikut:

1. **Context-Aware:** "Berikan kode yang mengikuti arsitektur Three-Tier Skintify-C4 (NiceGUI, SQLAlchemy)."
2. **Modular First:** "Pastikan kode ini bisa di-*import* sebagai modul Python terpisah sesuai direktori `app/`."
3. **Clean Exit:** "Jika ada *error*, tangkap menggunakan `try-except` dan tampilkan notifikasi `ui.notify` kepada pengguna akhir."

## 5. Maintenance Checklist (Sebelum Commit)

### General Checklist
* [ ] Apakah fungsi ini terlalu panjang (> 50 baris)? Jika ya, pecah.
* [ ] Apakah variabel sudah memiliki nama dengan format `snake_case` yang menjelaskan fungsinya?
* [ ] Apakah tidak ada API Key atau kredensial yang tertulis *hardcoded* di kode? (Gunakan `os.getenv` atau file `.env`).
* [ ] Apakah *docstring* (komentar multi-baris `"""`) sudah ditambahkan untuk menjelaskan fungsi atau *class* kompleks?
* [ ] Apakah file baru diletakkan sesuai struktur direktori yang ditentukan (`app/ui/`, `app/services/`, atau `app/database/`)?

### Page-Specific Checklist
Pastikan untuk mengecek fungsionalitas berikut jika Anda melakukan perubahan pada halaman-halaman utama:

* **`main.py` / `home_page.py`**
  * [ ] Apakah *routing* NiceGUI (`@ui.page`) terdefinisi dengan benar dan tidak duplikat?
  * [ ] Apakah pemuatan awal (inisialisasi database/state) berjalan mulus tanpa menghambat UI (*blocking*)?
* **`search_page.py`**
  * [ ] Apakah fitur pencarian (*search*) atau penyaringan (*filter*) mengeksekusi *query* yang efisien di database (tidak ada N+1 query)?
* **`wishlist_page.py`**
  * [ ] Apakah state *Multi-Select Wishlist* dan *Floating Compare Dock* tersinkronisasi dengan baik, terutama saat pergantian sesi akun?
* **`routine_planner.py` / `routine_page.py`**
  * [ ] Apakah *AI Skin Safety Routine Analyzer* merender kartu peringatan konflik bahan aktif dengan akurat?
  * [ ] Apakah sistem *Real-Time Weather Guardian* menangani kondisi sensor/cuaca error dengan *fallback* UI yang elegan?
* **`ai_chat_page.py`**
  * [ ] Apakah *AI Chatbot* menangani *timeout* atau pemrosesan lama dengan indikator *loading* (spinner) yang jelas agar tidak terlihat *hang*?
  * [ ] Apakah *Action Buttons* (seperti "Bandingkan ↗") di dalam *chat bubble* berfungsi memanggil modul dengan benar?

---
