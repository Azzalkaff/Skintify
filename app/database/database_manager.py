import sqlite3
import os
import hashlib
import secrets

class BasisData:
    """Manajer Database SQLite sederhana untuk pemula (Separation of Concerns)."""
    
    # Path absolut untuk file database
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DB_FOLDER = os.path.join(BASE_DIR, "data", "db")
    DB_NAMA = os.path.join(DB_FOLDER, "data_skintify.db")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password menggunakan PBKDF2-SHA256 dengan salt acak yang aman."""
        salt = secrets.token_hex(16)
        pwd_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        hashed = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
        return f"pbkdf2_sha256$100000${salt}${hashed.hex()}"

    @staticmethod
    def verifikasi_password(password: str, stored_hash: str) -> bool:
        """Verifikasi password dengan hash yang disimpan. 
        Mendukung kompatibilitas dengan password teks polos lama.
        """
        if not stored_hash:
            return False
            
        # Kompatibilitas mundur dengan data lama (teks polos)
        if not stored_hash.startswith("pbkdf2_sha256$"):
            return stored_hash == password

        try:
            parts = stored_hash.split('$')
            if len(parts) != 4:
                return False
            algorithm, iterations, salt, hashed_hex = parts
            iterations = int(iterations)
            
            pwd_bytes = password.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            
            new_hashed = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, iterations)
            return secrets.compare_digest(new_hashed.hex(), hashed_hex)
        except Exception:
            return False

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
            # Kolom profil kulit (Tambahan Falisha)
            for col, default in [
                ('skin_type',         "''"),
                ('avoid_ingredients', "''"),
                ('skin_issues',       "''"),
            ]:
                if col not in kolom:
                    kursor.execute(f"ALTER TABLE pengguna ADD COLUMN {col} TEXT DEFAULT {default}")
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
        """Memasukkan pengguna baru ke database permanen dengan password ter-hashing."""
        try:
            hashed_password = BasisData.hash_password(password)
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('INSERT INTO pengguna (email, username, password, role) VALUES (?, ?, ?, ?)', (email, username, hashed_password, role))
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
            
            # Jika hasil ditemukan, verifikasi hash password
            if hasil:
                stored_hash = hasil[0]
                return BasisData.verifikasi_password(password, stored_hash)
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

    @staticmethod
    def ambil_pengguna_by_identifier(identifier: str) -> dict:
        """Ambil data lengkap user termasuk profil kulit. Return dict atau {}."""
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            koneksi.row_factory = sqlite3.Row
            kursor = koneksi.cursor()
            kursor.execute(
                "SELECT * FROM pengguna WHERE email = ? OR username = ?",
                (identifier, identifier)
            )
            hasil = kursor.fetchone()
            if hasil:
                d = dict(hasil)
                # Normalkan list yang disimpan sebagai string CSV
                for kolom in ("avoid_ingredients", "skin_issues"):
                    val = d.get(kolom, "") or ""
                    d[kolom] = [x.strip() for x in val.split(",") if x.strip()]
                return d
            return {}

    @staticmethod
    def simpan_profil_kulit(email: str, skin_type: str,
                            avoid_ingredients: list, skin_issues: list,
                            city: str = "Jakarta") -> bool:
        """Simpan data kulit user ke DB. Dipanggil oleh onboarding_page setelah survey."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute(
                    """UPDATE pengguna
                       SET skin_type = ?, avoid_ingredients = ?, skin_issues = ?, city = ?
                       WHERE email = ?""",
                    (skin_type, ", ".join(avoid_ingredients), ", ".join(skin_issues), city, email)
                )
                koneksi.commit()
            return True
        except Exception as e:
            print(f"[DB] Gagal simpan profil kulit: {e}")
            return False

