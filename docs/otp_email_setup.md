# 📧 Panduan Integrasi OTP Nyata dengan SMTP Gmail (Skintify)

Masalah di mana kode OTP tidak benar-benar dikirim ke email pengguna (hanya disimulasikan dalam mock service) kini telah diselesaikan sepenuhnya. Kami telah menghubungkan sistem pendaftaran dengan **SMTP Gmail riil** secara asinkron tanpa memblokir antarmuka pengguna (NiceGUI).

---

## 🛠️ Ringkasan Perubahan Kode

Kami telah memodifikasi beberapa file utama untuk menerapkan pengiriman OTP yang nyata:

### 1. [email_service.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya%20Kelompok/main%20program/Skintify-C4/Skintify-C4/app/auth/email_service.py)
* Mengubah konfigurasi hardcoded menjadi dinamis menggunakan variabel lingkungan (`os.getenv`).
* Menambahkan inisialisasi `load_dotenv()` agar file konfigurasi `.env` dibaca dengan benar.

### 2. [auth.py](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya%20Kelompok/main%20program/Skintify-C4/Skintify-C4/app/auth/auth.py)
* Mengimpor `LayananEmail` nyata dari `app.auth.email_service`.
* Membungkus fungsi SMTP blocking menggunakan `asyncio.to_thread` agar proses koneksi ke server Gmail berjalan di thread terpisah. Ini mencegah UI NiceGUI dari membeku (*freezing*) selama pengiriman email.
* Menambahkan **Development Fallback**: Jika pengiriman email gagal (misalnya karena kredensial belum diatur), kode OTP akan dicetak di konsol terminal sehingga proses pengembangan lokal tidak terganggu.

### 3. [.env](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya%20Kelompok/main%20program/Skintify-C4/Skintify-C4/.env)
* Menambahkan template variabel lingkungan untuk mempermudah konfigurasi tanpa perlu menyentuh kode program.

---

## 🚀 Panduan Konfigurasi SMTP Gmail

Untuk mengaktifkan pengiriman OTP riil ke kotak masuk Gmail pengguna, ikuti langkah-langkah berikut:

### Langkah 1: Buat App Password di Akun Google Anda
Karena Google melarang login langsung menggunakan password akun biasa demi keamanan, Anda wajib menggunakan **App Password** (Sandi Aplikasi):

1. Buka halaman [Google Account Security](https://myaccount.google.com/security).
2. Pastikan **2-Step Verification** (Verifikasi 2 Langkah) sudah dalam keadaan **Aktif (ON)**.
3. Di kolom pencarian bagian atas, cari dan pilih **"App passwords"** (Sandi Aplikasi).
4. Berikan nama aplikasi (misal: `Skintify OTP`) lalu klik **Create**.
5. Salin kode sandi 16 digit yang muncul (contoh format: `abcd efgh ijkl mnop`).

### Langkah 2: Perbarui file [.env](file:///c:/Pemrograman/Kuliah/PPLD/Pra%20ETS/Proyek%20Punya%20Kelompok/main%20program/Skintify-C4/Skintify-C4/.env)
Buka file `.env` di root proyek Skintify Anda, lalu temukan baris berikut di bagian paling bawah dan perbarui nilainya dengan email serta sandi aplikasi yang sudah Anda dapatkan:

```env
# Konfigurasi SMTP Gmail untuk Pengiriman OTP
EMAIL_PENGIRIM=your-email@gmail.com
PASSWORD_APLIKASI=abcd efgh ijkl mnop
```

> [!IMPORTANT]
> Pastikan tidak ada spasi tambahan di sekitar tanda sama dengan (`=`). Masukkan password aplikasi 16 karakter persis seperti yang diberikan oleh Google (boleh menyertakan spasi bawaannya maupun digabung rapat, sistem tetap mendukungnya).

---

## 🧪 Cara Pengujian

1. **Jalankan Aplikasi**:
   Jalankan `main.py` menggunakan python:
   ```powershell
   python main.py
   ```
2. **Lakukan Pendaftaran**:
   * Masuk ke menu **Daftar**.
   * Isi kolom Username, Email (gunakan email aktif Anda yang lain atau email yang sama untuk pengujian), dan Password.
   * Pilih tipe akun, lalu klik tombol **Daftar & Kirim OTP**.
3. **Cek Konsol & Email**:
   * Jika konfigurasi `.env` Anda sudah benar dan Anda terhubung ke internet, OTP akan segera masuk ke kotak masuk email tujuan.
   * Jika belum dikonfigurasi, konsol terminal akan menampilkan pesan:
     `💡 [Development Fallback] OTP Anda adalah: XXXXXX` sehingga Anda tetap dapat menyalin kode tersebut ke antarmuka aplikasi untuk menyelesaikan registrasi.
