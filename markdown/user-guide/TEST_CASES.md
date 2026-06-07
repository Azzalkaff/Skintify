# Test Cases - Skintify-C4

## Autentikasi & Akun (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-001 | P1 | Auth | Registrasi dengan email baru | Akun berhasil dibuat dan OTP terkirim ke email | | [ ] Pass [ ] Fail | - |
| TC-002 | P1 | Auth | Verifikasi OTP yang benar | Email terverifikasi, dapat melanjutkan | | [ ] Pass [ ] Fail | - |
| TC-003 | P1 | Auth | Verifikasi OTP yang salah | Muncul pesan error "OTP Tidak Valid" | | [ ] Pass [ ] Fail | - |
| TC-004 | P1 | Auth | Verifikasi OTP expired | Muncul notifikasi "OTP Telah Kadaluarsa, Kirim Ulang" | | [ ] Pass [ ] Fail | - |
| TC-005 | P1 | Auth | Login dengan email & password benar | Berhasil login dan masuk ke dashboard | | [ ] Pass [ ] Fail | - |
| TC-006 | P1 | Auth | Login dengan password salah | Muncul pesan error "Email atau Password Salah" | | [ ] Pass [ ] Fail | - |
| TC-007 | P1 | Auth | Lupa password | Link reset dikirim ke email | | [ ] Pass [ ] Fail | - |
| TC-008 | P2 | Auth | Reset password dengan link valid | Password berhasil direset, dapat login dengan password baru | | [ ] Pass [ ] Fail | - |

## Onboarding (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-009 | P2 | Onboarding | Tampilkan welcome screen | Welcome screen tampil setelah registrasi/login pertama | | [ ] Pass [ ] Fail | - |
| TC-010 | P2 | Onboarding | Intro tutorial fitur utama | Tutorial menjelaskan fitur-fitur utama aplikasi | | [ ] Pass [ ] Fail | - |
| TC-011 | P2 | Onboarding | Input tipe kulit | User dapat memilih/input tipe kulit mereka | | [ ] Pass [ ] Fail | - |
| TC-012 | P2 | Onboarding | Input masalah kulit | User dapat memilih masalah kulit (acne, dryness, sensitivity, dll) | | [ ] Pass [ ] Fail | - |
| TC-013 | P2 | Onboarding | Input preferensi bahan | User dapat memilih bahan yang diinginkan | | [ ] Pass [ ] Fail | - |
| TC-014 | P2 | Onboarding | Skip onboarding | User dapat melewati onboarding dan masuk ke dashboard | | [ ] Pass [ ] Fail | - |
| TC-015 | P2 | Onboarding | Tampilkan rekomendasi awal | Rekomendasi produk pertama ditampilkan berdasarkan data kulit | | [ ] Pass [ ] Fail | - |
| TC-016 | P2 | Onboarding | Navigasi antar step onboarding | Tombol next/previous berfungsi dengan baik | | [ ] Pass [ ] Fail | - |
| TC-017 | P2 | Onboarding | Validasi form onboarding | Form validation berjalan sebelum lanjut ke step berikutnya | | [ ] Pass [ ] Fail | - |
| TC-018 | P3 | Onboarding | Progress indicator onboarding | Progress bar menunjukkan progress onboarding | | [ ] Pass [ ] Fail | - |
| TC-019 | P3 | Onboarding | Edit data onboarding dari profil | User dapat mengubah data kulit dari halaman profil | | [ ] Pass [ ] Fail | - |

## Katalog & Browse Produk (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-020 | P1 | Katalog | Menampilkan semua kategori produk | Kategori tampil lengkap (Cleanser, Toner, Serum, dll) | | [ ] Pass [ ] Fail | - |
| TC-021 | P1 | Katalog | Filter produk berdasarkan kategori | Produk terurutkan sesuai kategori yang dipilih | | [ ] Pass [ ] Fail | - |
| TC-022 | P1 | Katalog | Filter produk berdasarkan harga | Produk terurutkan sesuai range harga | | [ ] Pass [ ] Fail | - |
| TC-023 | P1 | Katalog | Pencarian produk dengan keyword | Hasil pencarian relevan muncul | | [ ] Pass [ ] Fail | - |
| TC-024 | P1 | Katalog | Pencarian produk dengan keyword tidak ada | Muncul pesan "Produk tidak ditemukan" | | [ ] Pass [ ] Fail | - |
| TC-025 | P2 | Katalog | Menampilkan detail produk | Info produk lengkap tampil (nama, harga, stock, deskripsi) | | [ ] Pass [ ] Fail | - |
| TC-026 | P2 | Katalog | Gambar produk loading | Gambar tampil dengan jelas tanpa error | | [ ] Pass [ ] Fail | - |

## Keranjang Belanja (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-027 | P1 | Keranjang | Menambah produk ready ke keranjang | Produk masuk keranjang, jumlah item bertambah | | [ ] Pass [ ] Fail | - |
| TC-028 | P1 | Keranjang | Menambah produk dengan quantity lebih dari stok | Muncul peringatan "Stok Tidak Mencukupi" | | [ ] Pass [ ] Fail | - |
| TC-029 | P1 | Keranjang | Menambah produk habis ke keranjang | Muncul peringatan "Stok Habis" dan tombol disable | | [ ] Pass [ ] Fail | - |
| TC-030 | P1 | Keranjang | Menampilkan keranjang | Semua item di keranjang tampil dengan benar | | [ ] Pass [ ] Fail | - |
| TC-031 | P1 | Keranjang | Mengubah quantity produk di keranjang | Quantity terupdate dan total harga berubah | | [ ] Pass [ ] Fail | - |
| TC-032 | P1 | Keranjang | Menghapus item dari keranjang | Item terhapus dari keranjang | | [ ] Pass [ ] Fail | - |
| TC-033 | P1 | Keranjang | Menghapus semua item keranjang | Keranjang kosong | | [ ] Pass [ ] Fail | - |
| TC-034 | P2 | Keranjang | Hitung total harga otomatis | Total harga akurat (jumlah item × harga satuan) | | [ ] Pass [ ] Fail | - |
| TC-035 | P2 | Keranjang | Persisten data keranjang | Item tetap ada setelah refresh halaman | | [ ] Pass [ ] Fail | - |

## Checkout & Pembayaran (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-036 | P1 | Checkout | Checkout dengan keranjang kosong | Disabled atau muncul peringatan | | [ ] Pass [ ] Fail | - |
| TC-037 | P1 | Checkout | Checkout dengan produk ready | Masuk ke halaman checkout form | | [ ] Pass [ ] Fail | - |
| TC-038 | P1 | Checkout | Verifikasi form checkout (nama, alamat, telepon) | Form validation berjalan dengan baik | | [ ] Pass [ ] Fail | - |
| TC-039 | P1 | Checkout | Checkout tanpa mengisi form lengkap | Muncul error "Form harus dilengkapi" | | [ ] Pass [ ] Fail | - |
| TC-040 | P1 | Pembayaran | Pilih metode pembayaran | Opsi pembayaran tersedia (Transfer Bank, E-wallet, COD) | | [ ] Pass [ ] Fail | - |
| TC-041 | P1 | Pembayaran | Checkout dengan metode Transfer Bank | Ditampilkan nomor rekening dan instruksi transfer | | [ ] Pass [ ] Fail | - |
| TC-042 | P1 | Pembayaran | Checkout dengan metode E-wallet | Masuk ke halaman pembayaran e-wallet | | [ ] Pass [ ] Fail | - |
| TC-043 | P1 | Pembayaran | Checkout dengan metode COD | Pesanan dibuat dengan status menunggu verifikasi | | [ ] Pass [ ] Fail | - |
| TC-044 | P2 | Pembayaran | Konfirmasi pembayaran diterima | Order status berubah menjadi "Terkonfirmasi" | | [ ] Pass [ ] Fail | - |
| TC-045 | P2 | Pembayaran | Invoice tergenerate otomatis | File invoice dapat didownload | | [ ] Pass [ ] Fail | - |

## Pesanan (Order Management) (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-046 | P1 | Pesanan | Menampilkan riwayat pesanan | Daftar pesanan tampil dengan status | | [ ] Pass [ ] Fail | - |
| TC-047 | P1 | Pesanan | Filter pesanan berdasarkan status | Pesanan terurutkan sesuai status (Pending, Confirmed, Shipped, Delivered) | | [ ] Pass [ ] Fail | - |
| TC-048 | P1 | Pesanan | Lihat detail pesanan | Detail lengkap pesanan tampil (items, total, status, tracking) | | [ ] Pass [ ] Fail | - |
| TC-049 | P2 | Pesanan | Tracking pesanan | Status pesanan dapat dipantau real-time | | [ ] Pass [ ] Fail | - |
| TC-050 | P2 | Pesanan | Batalkan pesanan (sebelum konfirmasi) | Pesanan berhasil dibatalkan | | [ ] Pass [ ] Fail | - |
| TC-051 | P3 | Pesanan | Batalkan pesanan (sudah dikonfirmasi) | Muncul notifikasi "Pesanan tidak dapat dibatalkan" | | [ ] Pass [ ] Fail | - |

## AI Rekomendasi (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-052 | P2 | Rekomendasi AI | Akses halaman rekomendasi | Halaman rekomendasi tampil | | [ ] Pass [ ] Fail | - |
| TC-053 | P2 | Rekomendasi AI | Input data kulit (tipe, masalah kulit) | Form input data kulit berfungsi | | [ ] Pass [ ] Fail | - |
| TC-054 | P2 | Rekomendasi AI | Generate rekomendasi produk | Produk yang direkomendasikan sesuai dengan data kulit | | [ ] Pass [ ] Fail | - |
| TC-055 | P2 | Rekomendasi AI | Tampilkan alasan rekomendasi | Penjelasan mengapa produk direkomendasikan tampil | | [ ] Pass [ ] Fail | - |
| TC-056 | P3 | Rekomendasi AI | Tambahkan rekomendasi ke keranjang | Produk direkomendasikan masuk ke keranjang | | [ ] Pass [ ] Fail | - |

## Ingredient & Kompatibilitas (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-057 | P2 | Ingredients | Lihat ingredient produk | Daftar ingredient tampil dengan detail | | [ ] Pass [ ] Fail | - |
| TC-058 | P2 | Ingredients | Cek ingredient konflikt | Sistem mendeteksi ingredient yang berpotensi konflik | | [ ] Pass [ ] Fail | - |
| TC-059 | P2 | Ingredients | Melihat informasi ingredient (INCI) | Deskripsi dan fungsi ingredient tampil | | [ ] Pass [ ] Fail | - |
| TC-060 | P3 | Kompatibilitas | Cek kompatibilitas antar produk | Sistem menampilkan apakah produk dapat digunakan bersamaan | | [ ] Pass [ ] Fail | - |

## Review & Rating (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-061 | P2 | Review | Berikan rating produk | Rating tersimpan | | [ ] Pass [ ] Fail | - |
| TC-062 | P2 | Review | Tulis review produk | Review tersimpan dan tampil di detail produk | | [ ] Pass [ ] Fail | - |
| TC-063 | P2 | Review | Tampilkan review produk | Review dari user lain dapat dilihat | | [ ] Pass [ ] Fail | - |
| TC-064 | P3 | Review | Hitung rating rata-rata produk | Rating rata-rata akurat | | [ ] Pass [ ] Fail | - |

## Wishlist / Favorit (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-065 | P2 | Wishlist | Tambah produk ke wishlist | Produk masuk ke wishlist | | [ ] Pass [ ] Fail | - |
| TC-066 | P2 | Wishlist | Hapus produk dari wishlist | Produk terhapus dari wishlist | | [ ] Pass [ ] Fail | - |
| TC-067 | P2 | Wishlist | Tampilkan wishlist | Daftar wishlist tampil dengan benar | | [ ] Pass [ ] Fail | - |
| TC-068 | P2 | Wishlist | Pindahkan wishlist ke keranjang | Produk masuk keranjang | | [ ] Pass [ ] Fail | - |
| TC-069 | P2 | Wishlist | Buat multiple wishlist | User dapat membuat lebih dari satu list wishlist | | [ ] Pass [ ] Fail | - |
| TC-070 | P2 | Wishlist | Rename wishlist | User dapat mengubah nama wishlist | | [ ] Pass [ ] Fail | - |
| TC-071 | P2 | Wishlist | Hapus wishlist | Wishlist dan isinya dapat dihapus | | [ ] Pass [ ] Fail | - |
| TC-072 | P2 | Wishlist | Pindah produk antar wishlist | Produk dapat dipindahkan ke wishlist lain | | [ ] Pass [ ] Fail | - |
| TC-073 | P2 | Wishlist | Sort wishlist items | Wishlist dapat disort (harga, nama, terbaru, dll) | | [ ] Pass [ ] Fail | - |
| TC-074 | P2 | Wishlist | Tambah catatan pada item wishlist | User dapat menambah catatan/notes pada produk di wishlist | | [ ] Pass [ ] Fail | - |
| TC-075 | P2 | Wishlist | Set private/public wishlist | User dapat membuat wishlist public atau private | | [ ] Pass [ ] Fail | - |
| TC-076 | P2 | Wishlist | Share wishlist dengan link | User dapat membagikan wishlist via link | | [ ] Pass [ ] Fail | - |
| TC-077 | P3 | Wishlist | Price drop notification | User menerima notifikasi jika harga produk di wishlist turun | | [ ] Pass [ ] Fail | - |
| TC-078 | P3 | Wishlist | Back in stock notification | User menerima notifikasi jika produk habis di wishlist kembali ready | | [ ] Pass [ ] Fail | - |

## Profil Pengguna (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-079 | P2 | Profil | Tampilkan profil pengguna | Data profil tampil lengkap | | [ ] Pass [ ] Fail | - |
| TC-080 | P2 | Profil | Edit profil (nama, nomor telepon, alamat) | Profil berhasil diupdate | | [ ] Pass [ ] Fail | - |
| TC-081 | P2 | Profil | Upload foto profil | Foto profil berhasil diupload | | [ ] Pass [ ] Fail | - |
| TC-082 | P2 | Profil | Kelola alamat pengiriman | User dapat menambah/edit/hapus alamat | | [ ] Pass [ ] Fail | - |
| TC-083 | P2 | Profil | Ubah password | Password berhasil diubah | | [ ] Pass [ ] Fail | - |

## Notifikasi & Email (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-084 | P2 | Notifikasi | Terima notifikasi order confirmation | Email konfirmasi terkirim | | [ ] Pass [ ] Fail | - |
| TC-085 | P2 | Notifikasi | Terima notifikasi perubahan status pesanan | Email update status terkirim | | [ ] Pass [ ] Fail | - |
| TC-086 | P2 | Notifikasi | Terima notifikasi promosi/diskon | User dapat menerima email promosi | | [ ] Pass [ ] Fail | - |
| TC-087 | P3 | Notifikasi | Push notifikasi tersedia | Push notifikasi berfungsi (jika ada) | | [ ] Pass [ ] Fail | - |

## Database & Data Integrity (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-088 | P1 | Database | Data produk tersimpan dengan benar | Semua field produk tersimpan akurat | | [ ] Pass [ ] Fail | - |
| TC-089 | P1 | Database | Data pengguna tersimpan aman | Password ter-hash, data personal aman | | [ ] Pass [ ] Fail | - |
| TC-090 | P1 | Database | Update stock real-time | Stok produk terupdate setelah order | | [ ] Pass [ ] Fail | - |
| TC-091 | P2 | Database | Konsistensi data inventory | Data inventory konsisten di semua modul | | [ ] Pass [ ] Fail | - |

## UI/UX (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-092 | P2 | UI/UX | Navigasi antar halaman | Semua link berfungsi dengan baik | | [ ] Pass [ ] Fail | - |
| TC-093 | P2 | UI/UX | Responsif di mobile | Tampilan responsif di berbagai ukuran layar | | [ ] Pass [ ] Fail | - |
| TC-094 | P2 | UI/UX | Responsif di tablet | Tampilan responsif di tablet | | [ ] Pass [ ] Fail | - |
| TC-095 | P2 | UI/UX | Responsif di desktop | Tampilan responsif di desktop | | [ ] Pass [ ] Fail | - |
| TC-096 | P3 | UI/UX | Loading time halaman | Halaman loading dalam waktu < 3 detik | | [ ] Pass [ ] Fail | - |
| TC-097 | P3 | UI/UX | Error message jelas | Pesan error informatif dan membantu | | [ ] Pass [ ] Fail | - |

## Keamanan (P1 - Critical)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-098 | P1 | Security | SQL Injection protection | Aplikasi tidak rentan SQL injection | | [ ] Pass [ ] Fail | - |
| TC-099 | P1 | Security | XSS protection | Aplikasi tidak rentan XSS attack | | [ ] Pass [ ] Fail | - |
| TC-100 | P1 | Security | CSRF protection | Aplikasi tidak rentan CSRF attack | | [ ] Pass [ ] Fail | - |
| TC-101 | P1 | Security | Session security | Session tidak dapat didijacking | | [ ] Pass [ ] Fail | - |
| TC-102 | P2 | Security | Rate limiting login | Login attempt dibatasi setelah N kali gagal | | [ ] Pass [ ] Fail | - |
| TC-103 | P2 | Security | API authorization | API endpoints terproteksi dengan baik | | [ ] Pass [ ] Fail | - |

## Performance (P3 - Medium)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-104 | P3 | Performance | Caching efektif | Cache images dan static assets | | [ ] Pass [ ] Fail | - |
| TC-105 | P3 | Performance | Database query optimization | Query cepat dan tidak overload | | [ ] Pass [ ] Fail | - |
| TC-106 | P3 | Performance | Pagination produk | Pagination berfungsi smooth | | [ ] Pass [ ] Fail | - |
| TC-107 | P3 | Performance | Concurrent users | Aplikasi stabil dengan multiple concurrent users | | [ ] Pass [ ] Fail | - |

## Home (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-108 | P2 | Home | Tampilkan halaman home | Homepage tampil dengan lengkap | | [ ] Pass [ ] Fail | - |
| TC-109 | P2 | Home | Tampilkan banner/carousel produk | Banner atau carousel produk tampil dengan gambar | | [ ] Pass [ ] Fail | - |
| TC-110 | P2 | Home | Navigasi banner/carousel | User dapat scroll atau klik next/prev di carousel | | [ ] Pass [ ] Fail | - |
| TC-111 | P2 | Home | Tampilkan produk trending | Produk trending ditampilkan dengan benar | | [ ] Pass [ ] Fail | - |
| TC-112 | P2 | Home | Tampilkan kategori produk | Kategori produk tampil sebagai quick access | | [ ] Pass [ ] Fail | - |
| TC-113 | P2 | Home | Klik kategori dari home | Redirect ke halaman kategori produk tersebut | | [ ] Pass [ ] Fail | - |
| TC-114 | P2 | Home | Tampilkan rekomendasi personal | Rekomendasi produk berdasarkan user tampil | | [ ] Pass [ ] Fail | - |
| TC-115 | P2 | Home | Tampilkan promo/diskon | Promosi atau diskon terbaru ditampilkan | | [ ] Pass [ ] Fail | - |
| TC-116 | P2 | Home | Klik promo menuju detail promo | Klik promo membuka halaman detail/listing produk promo | | [ ] Pass [ ] Fail | - |
| TC-117 | P3 | Home | Tampilkan notifikasi/badge | Badge notifikasi terlihat jika ada update | | [ ] Pass [ ] Fail | - |
| TC-118 | P3 | Home | Tampilkan featured brands | Brand-brand pilihan ditampilkan | | [ ] Pass [ ] Fail | - |

## Page Compare (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-119 | P2 | Compare | Tambah produk 1 ke compare | Produk masuk halaman compare | | [ ] Pass [ ] Fail | - |
| TC-120 | P2 | Compare | Tambah produk 2+ ke compare | Multiple produk dapat dibandingkan | | [ ] Pass [ ] Fail | - |
| TC-121 | P2 | Compare | Tampilkan perbandingan produk side-by-side | Produk ditampilkan dalam format kolom | | [ ] Pass [ ] Fail | - |
| TC-122 | P2 | Compare | Bandingkan spesifikasi produk | Spec produk (harga, ingredients, rating) tampil | | [ ] Pass [ ] Fail | - |
| TC-123 | P2 | Compare | Bandingkan ingredient antar produk | Ingredient comparison tampil dengan highlight perbedaan | | [ ] Pass [ ] Fail | - |
| TC-124 | P2 | Compare | Highlight conflict ingredient | Ingredient konflikt di-highlight dengan warna berbeda | | [ ] Pass [ ] Fail | - |
| TC-125 | P2 | Compare | Hapus produk dari compare | Produk terhapus dari halaman compare | | [ ] Pass [ ] Fail | - |
| TC-126 | P2 | Compare | Hapus semua produk compare | Compare page kosong atau kembali ke tampilan awal | | [ ] Pass [ ] Fail | - |
| TC-127 | P2 | Compare | Tambah produk dari compare ke keranjang | Produk bisa langsung ditambah ke keranjang | | [ ] Pass [ ] Fail | - |
| TC-128 | P3 | Compare | Share compare result | User dapat share hasil compare ke social media | | [ ] Pass [ ] Fail | - |
| TC-129 | P3 | Compare | Limit jumlah produk compare | System membatasi max produk yang dibanding (misal 5) | | [ ] Pass [ ] Fail | - |

## Statistik (P2 - High)

| ID | Prioritas | Fitur | Skenario Pengujian | Hasil yang Diharapkan | Hasil Sebenarnya | Status | Link Bug / Screenshot |
|---|---|---|---|---|---|---|---|
| TC-130 | P2 | Statistik | Akses halaman statistik | Halaman statistik dapat diakses | | [ ] Pass [ ] Fail | - |
| TC-131 | P2 | Statistik | Tampilkan total pembelian | Total jumlah pembelian user ditampilkan | | [ ] Pass [ ] Fail | - |
| TC-132 | P2 | Statistik | Tampilkan total pengeluaran | Total pengeluaran user ditampilkan dengan currency | | [ ] Pass [ ] Fail | - |
| TC-133 | P2 | Statistik | Tampilkan kategori favorit | Kategori produk paling sering dibeli tampil | | [ ] Pass [ ] Fail | - |
| TC-134 | P2 | Statistik | Tampilkan brand favorit | Brand yang paling sering dibeli tampil | | [ ] Pass [ ] Fail | - |
| TC-135 | P2 | Statistik | Tampilkan chart pembelian bulanan | Chart/graph pembelian per bulan ditampilkan | | [ ] Pass [ ] Fail | - |
| TC-136 | P2 | Statistik | Filter statistik berdasarkan periode | User dapat filter data per bulan/tahun/custom range | | [ ] Pass [ ] Fail | - |
| TC-137 | P2 | Statistik | Tampilkan produk paling sering dibeli | Top 5-10 produk favorit ditampilkan | | [ ] Pass [ ] Fail | - |
| TC-138 | P2 | Statistik | Tampilkan analisis skin profile | Summary tipe kulit dan masalah kulit tampil | | [ ] Pass [ ] Fail | - |
| TC-139 | P3 | Statistik | Export statistik (PDF/Excel) | User dapat export data statistik | | [ ] Pass [ ] Fail | - |
| TC-140 | P3 | Statistik | Download report bulanan | User dapat download monthly report | | [ ] Pass [ ] Fail | - |

---

**Catatan:**
- **P1 (Critical)**: Harus di-test sebelum release
- **P2 (High)**: Harus di-test, dampak signifikan jika gagal
- **P3 (Medium)**: Nice to have, dapat ditestkan lebih lanjut

Kolom "Hasil Sebenarnya" dapat diisi dengan hasil testing manual, dan Status diubah sesuai hasil test.
