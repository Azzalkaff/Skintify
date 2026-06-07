# Analisis Algoritma AI Chat (Perspektif Ilmu Komputer)

Sebagai mahasiswa *Computer Science* (Informatika/Ilmu Komputer), kode yang Anda buat pada `ai_chat_page.py` sebenarnya merupakan implementasi langsung dari berbagai teori yang diajarkan pada beberapa mata kuliah inti.

Berikut adalah pembedahan algoritma Anda, efisiensinya (Big O), dan korelasinya dengan fundamental Mata Kuliah Ilmu Komputer.

---

## 1. Algoritma Peracik Paket Skincare (Budgeting)
**Fungsi:** `find_skincare_package(budget)`

### 📚 Pemetaan Mata Kuliah:
1. **Desain dan Analisis Algoritma (DAA) / Strategi Algoritma**
   - **Konsep:** Algoritma *Greedy* dan *Knapsack Problem* (Optimasi Kombinatorial).
   - **Penerapan Anda:** Algoritma memilih produk dengan `quality_score` tertinggi yang harganya masih muat di sisa _budget_ (`max_price_for_this_item`). Ini adalah turunan langsung dari _Fractional/0-1 Knapsack_ menggunakan pendekatan *Greedy by Quality*.
2. **Sistem Pendukung Keputusan (SPK) / Sistem Pakar**
   - **Konsep:** *Multi-Criteria Decision Analysis (MCDA)*.
   - **Penerapan Anda:** Anda tidak hanya mengurutkan harga termurah, tapi menghitung bobot nilai (70% rating, 30% popularitas/reviews). 

### ⏱️ Analisis Kompleksitas & Efisiensi:
- Sorting MCDA memakan waktu $O(N \log N)$ per kategori menggunakan algoritma _Timsort_.
- Pemilihan skenario (CTMP) mengeksekusi maksimal 21 iterasi konstan $O(1)$.
- **Status:** Sangat efisien di tingkat logika program Python.

---

## 2. Pencarian Skincare via Keyword Prompt
**Fungsi:** `fetch_relevant_products(prompt)`

### 📚 Pemetaan Mata Kuliah:
1. **Sistem Basis Data (Manajemen Basis Data)**
   - **Konsep:** *Query Optimization*, *Indexing*, dan *Full Table Scan*.
   - **Penerapan Anda:** Anda menggunakan perintah `.filter(or_(... ilike("%keyword%")))`.
2. **Temu Balik Informasi (Information Retrieval / IR)**
   - **Konsep:** *Keyword Extraction*, *Tokenization*.

### ⏱️ Analisis Kompleksitas & Solusi (Best Practice):
- **Kompleksitas Query:** $O(N \times K)$ dimana $N$ adalah total jumlah data di tabel dan $K$ adalah jumlah kata kunci.
- **Kelemahan (Fundamental Database):** Dalam mata kuliah Sistem Basis Data diajarkan bahwa klausa `LIKE '%...%'` **mematikan** fungsi Index B-Tree secara otomatis. Database terpaksa melakukan *Full Table Scan* (mengecek baris satu persatu dari atas ke bawah).
- **Solusi dari Ilmu *Information Retrieval*:** Daripada menggunakan `LIKE`, sebaiknya implementasikan konsep **Inverted Index**. Pada SQLite, ini bisa dicapai dengan ekstensi **FTS5 (Full-Text Search)**. Dengan Inverted Index, sistem akan memetakan *kata* ke *ID baris* sejak awal, sehingga waktu pencarian berapapun besarnya data akan memakan waktu mendekati $O(1)$.

---

## 3. Ekstraksi Nominal Uang (Parser)
**Fungsi:** `parse_budget_from_text(text)`

### 📚 Pemetaan Mata Kuliah:
- **Teori Bahasa dan Automata (TBA) / Teknik Kompilasi**
   - **Konsep:** *Finite State Automata (FSA)*, *Regular Expression (Regex)*, dan *Lexical Analysis* (Scanner).
   - **Penerapan Anda:** Mengekstrak konvensi mata uang kasual ("100k", "50rb", dll) menggunakan mesin *Regex* `r"(\d+(?:\.\d+)?)\s*(?:rb|k|ribu)"`.

### ⏱️ Analisis Kompleksitas:
- *Regular Expression* dikompilasi menjadi *Deterministic Finite Automaton* (DFA).
- Algoritma DFA ini memindai kalimat huruf-demi-huruf tanpa mundur (hanya bergerak maju).
- **Kompleksitas:** $O(L)$ dimana $L$ adalah panjang karakter dari kalimat pengguna.
- **Status:** **Best Practice**. Ini adalah metode paling efisien (*State of the Art*) untuk *parsing string* di ilmu komputer dibandingkan menggunakan kombinasi logika sintaks `.split()` dan iterasi `.replace()` manual.

---

## 4. Mesin Pembuat Keputusan Tanpa AI (Offline Mock)
**Fungsi:** `get_smart_mock_response(prompt)`

### 📚 Pemetaan Mata Kuliah:
- **Kecerdasan Buatan (Artificial Intelligence) Tradisional**
   - **Konsep:** *Rule-based Expert System* dan *Forward Chaining* (Heuristik).
   - **Penerapan Anda:** Anda tidak memakai *Neural Networks* di fungsi ini, melainkan membuat *Decision Tree* berbasis kondisi (`if...else` bercabang) berdasarkan deteksi sinonim ("retinol", "kusam", "panas"). AI menelusuri fakta (keluhan user) lalu menarik konklusi (rekomendasi produk). Ini adalah bentuk murni dari sistem AI Era-80an (Sistem Pakar).

---

## 5. Algoritma Prompting (LLM Ops & Prompt Engineering)
**Fungsi:** `query_gemini_api()`, `query_groq_api()`, serta konstruksi variabel `context`

### 📚 Pemetaan Mata Kuliah:
- **Kecerdasan Buatan Lanjut (Advanced AI) / Pengolahan Bahasa Alami (NLP)**
   - **Konsep:** *Retrieval-Augmented Generation (RAG)*, *Prompt Engineering*, *Context Window Truncation* (Sliding Window), dan *Prompt Injection Security*.
   - **Penerapan Anda:** Menyuntikkan riwayat `chat_history` terbatas bersama instruksi statis (`CORE_SYSTEM_PROMPT`) dan injeksi konteks dinamis (kondisi lingkungan, medis pengguna).

### ⏱️ Analisis Efisiensi (Waktu Proses AI):
- **Beban Pemrosesan (*Attention Mechanism* LLM):** Algoritma *Transformers* (otak dari Gemini/Groq) memiliki kompleksitas waktu kuadratik $O(N^2)$ terhadap panjang *token* ($N$). 
- **Efisiensi Struktur Anda:** **Sangat Efisien**. Anda menggunakan algoritma pemotongan *Sliding Window* (`chat_history[-8:]`) yang membatasi konteks agar tidak menggelembung menjadi *Token Overflow*. Dengan menjaga *prompt* tetap ringkas, *Time-To-First-Token* (kecepatan balas) dari AI akan sangat rendah (cepat) dan biaya API akan tetap murah.
- **Konstruksi *Prompt* (Python):** Menggunakan teknik *f-string* (format string interpolation) di Python dieksekusi dalam tingkat bahasa C yang memiliki efisiensi linear $O(L)$, yang artinya sama sekali tidak membebani komputasi lokal.

### 🚀 Solusi Optimisasi LLMOps (*Best Practice*):
Meskipun penyusunan *prompt* Anda sudah sangat efisien, ada beberapa arsitektur *Prompting* tingkat korporat yang bisa dipertimbangkan jika jumlah pengguna melonjak:
1. **Semantic Caching:** Daripada selalu memanggil API Groq/Gemini untuk pertanyaan umum berulang (contoh: "Apa itu eksfoliasi?"), gunakan *Cache* berbasis vektor agar jawaban dari LLM yang sebelumnya bisa langsung disajikan tanpa *delay* internet ($O(1)$).
2. **Context Distillation:** Daripada memotong mentah-mentah 8 _chat_ terakhir, gunakan _background worker_ untuk merangkum obrolan lama menjadi satu kalimat padat (*Summarized Context*).

---

## Kesimpulan

Bagi mahasiswa *Computer Science*, proyek ini sangat kaya akan fundamental struktur data dan algoritma. 

Hal yang paling berpotensi dipertanyakan saat sidang (atau ditanyakan oleh senior *engineer*) adalah: **"Mengapa kamu pakai pencarian LIKE ganda untuk jutaan produk?"** 
Jika Anda ingin kode ini menjadi standar *Enterprise* sungguhan, pertimbangkan untuk merefaktor bagian pencariannya dari pendekatan *Sistem Basis Data* konvensional ke arsitektur algoritma *Information Retrieval* (Inverted Index / Full Text Search).
