import sqlite3
import os

class BasisData:
    """Manajer Database SQLite sederhana untuk pemula (Separation of Concerns)."""
    
    # Path absolut untuk file database
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DB_FOLDER = os.path.join(BASE_DIR, "data", "db")
    DB_NAMA = os.path.join(DB_FOLDER, "data_skintify.db")

    @staticmethod
    def inisialisasi():
        """Membuat file database dan tabel jika belum ada."""
        os.makedirs(BasisData.DB_FOLDER, exist_ok=True)
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            kursor = koneksi.cursor()
            # Membuat tabel pengguna
            kursor.execute('''
                CREATE TABLE IF NOT EXISTS pengguna (
                    email TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password TEXT NOT NULL,
                    city TEXT DEFAULT 'Jakarta'
                )
            ''')
            # Cek apakah kolom city sudah ada (untuk update DB lama)
            kursor.execute("PRAGMA table_info(pengguna)")
            kolom = [info[1] for info in kursor.fetchall()]
            if 'city' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN city TEXT DEFAULT 'Jakarta'")
            # Migrasi: Tambah kolom role jika belum ada
            if 'role' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN role TEXT DEFAULT 'user'")
            koneksi.commit()

    @staticmethod
    def cek_identifier_terdaftar(identifier: str) -> bool:
        """Mengembalikan True jika email atau username sudah ada di database."""
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            kursor = koneksi.cursor()
            # Tanda '?' digunakan untuk mencegah SQL Injection (Keamanan Dasar)
            kursor.execute('SELECT email FROM pengguna WHERE email = ? OR username = ?', (identifier, identifier))
            return kursor.fetchone() is not None

    @staticmethod
    def tambah_pengguna(email: str, username: str, password: str, role: str = 'user') -> bool:
        """Memasukkan pengguna baru ke database permanen."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('INSERT INTO pengguna (email, username, password, role) VALUES (?, ?, ?, ?)', (email, username, password, role))
                koneksi.commit()
            return True
        except sqlite3.IntegrityError:
            # Gagal karena email atau username mungkin sudah ada (Duplikat)
            return False 

    @staticmethod
    def verifikasi_login(identifier: str, password: str) -> bool:
        """Mengecek apakah kombinasi email/username dan password cocok di database."""
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            kursor = koneksi.cursor()
            kursor.execute('SELECT password FROM pengguna WHERE email = ? OR username = ?', (identifier, identifier))
            hasil = kursor.fetchone()
            
            # Jika hasil ditemukan, dan password cocok
            if hasil and hasil[0] == password:
                return True
            return False

    @staticmethod
    def get_pengguna(identifier: str) -> dict:
        """Mengambil data lengkap pengguna berdasarkan email atau username."""
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            koneksi.row_factory = sqlite3.Row
            kursor = koneksi.cursor()
            kursor.execute('SELECT * FROM pengguna WHERE email = ? OR username = ?', (identifier, identifier))
            hasil = kursor.fetchone()
            return dict(hasil) if hasil else None

    @staticmethod
    def update_pengguna_profil(email: str, city: str) -> bool:
        """Update profil pengguna (lokasi)."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('UPDATE pengguna SET city = ? WHERE email = ?', (city, email))
                koneksi.commit()
            return True
        except Exception:
            return False