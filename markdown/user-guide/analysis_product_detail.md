# Analisis Algoritma & Rekomendasi Efisiensi (`product_detail_modal.py`)

Berdasarkan analisis pada file `app/ui/product_detail_modal.py`, berikut adalah daftar algoritma yang digunakan beserta tingkat efisiensinya (Notasi Big O) dan perbaikan yang telah ditawarkan serta diimplementasikan.

## 1. Algoritma yang Digunakan

### A. Deduplikasi Produk per Toko (Hash Map / Dictionary)
- **Fungsi:** `get_best_products` (di dalam `refresh_prices`)
- **Algoritma:** Menggunakan tipe data *Dictionary* (`unique_stores`) untuk menyimpan produk terbaik untuk tiap toko yang ada.
- **Efisiensi:** $O(N)$ di mana N adalah jumlah produk dari *database* untuk satu kali muat.
- **Analisis:** **Sangat Efisien (Best Practice)**. Operasi pengecekan kunci (apakah toko sudah tercatat) pada struktur data *Dictionary* terjadi secara instan $O(1)$. Sehingga iterasi seluruh N elemen hanya memakan waktu $O(N)$.

### B. Pengurutan Kandidat Harga Terbaik (Timsort)
- **Fungsi:** `get_best_products`
- **Algoritma:** `candidates.sort(key=lambda x: (-(x.get('terjual') or 0), abs(x['harga'] - baseline_price)))`
- **Efisiensi:** $O(K \log K)$ di mana K adalah jumlah kandidat unik (setelah deduplikasi).
- **Analisis:** **Efisien**. Python menggunakan algoritma internal *Timsort* (kombinasi *Merge Sort* dan *Insertion Sort*), yang mana sangat optimal untuk data di dunia nyata yang terstruktur secara parsial.

### C. Ekstraksi Ukuran Kemasan ML/Gr (Regular Expression)
- **Fungsi:** `extract_size`
- **Algoritma:** Pencocokan teks berulang dengan pola sintaks *Regex* `r'(\d+(?:[.,]\d+)?)\s*(?:ml|ML|Ml)'` untuk menangkap variabel angka terbesar dari ukuran mililiter atau gram.
- **Efisiensi:** $O(L)$ di mana L adalah total panjang teks nama produk.
- **Analisis:** **Efisien**. Tidak perlu loop manual untuk validasi karakter angka.

### D. Pemisahan Data Platform Marketplace (Multiple Linear Search)
- **Kondisi Awal:** Menggunakan *List Comprehension* berulang `[p for p in mapped_products if p['platform'] == '...']` sebanyak tiga kali (untuk Tokopedia, Shopee, dan Lazada).
- **Efisiensi Awal:** $O(3N)$ yang mana cukup mubazir karena melooping array besar berulang-ulang untuk tugas yang sama.
- **Solusi yang Diimplementasikan (O(N) Single-Pass Grouping):** 
  Diganti menggunakan `collections.defaultdict(list)`. Semua produk kini disaring hanya dalam **1 kali loop**.
  ```python
  from collections import defaultdict
  platform_dbs = defaultdict(list)
  for p in mapped_products:
      platform_dbs[p['platform'].lower()].append(p)
  ```

### E. Pencarian & Klasifikasi Bahan Skincare (Nested Linear Search)
- **Kondisi Awal:** Fungsi `render_chips` akan menghitung secara manual (mencocokkan *string*) apakah sebuah bahan bersifat "Active", "Soothing", atau "Hydrating" di dalam *loop* setiap kali *user* mengetik di kolom pencarian.
- **Efisiensi Awal:** $O(I \times A \times L)$ di mana I=jumlah ingredients, A=jumlah kata pencocokan (*active set*), L=panjang karakter. Proses ini berjalan secara *Real-Time* memblokir siklus antarmuka (UI Thread), yang bisa menyebabkan "lag" saat pengetikan.
- **Solusi yang Diimplementasikan (O(1) Pre-Compute Categorization):**
  Alih-alih mencari kecocokan kategori saat tombol *keyboard* diketik, kini daftar bahan diklasifikasi ke dalam "kategori" **hanya satu kali** saat modal dibuka pertama kali. Kemudian saat ada interaksi di kolom pencarian, sistem murni hanya mencocokkan kemiripan teks tanpa menghitung ulang klasifikasi kategori secara ilmiah.

## Kesimpulan
Keseluruhan fitur pada `product_detail_modal.py` sebagian besar sudah mengadopsi efisiensi bawaan yang sangat baik. Beberapa kekurangan pada iterasi loop berulang dan beban pemrosesan *Real-Time UI* telah berhasil ditambal secara komprehensif menggunakan arsitektur *Single-Pass* dan *Pre-Computation*.
