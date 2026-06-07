import sqlite3
import os
import hashlib
import secrets

class BasisData:
    """Manajer Database SQLite sederhana untuk pemula (Separation of Concerns)."""
    
    # Path absolut untuk file database (Mendukung packaging PyInstaller .exe)
    import sys
    if getattr(sys, 'frozen', False):
        BASE_DIR = os.path.dirname(sys.executable)
    else:
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
            # Migrasi: Tambah kolom wishlist jika belum ada
            if 'wishlist' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN wishlist TEXT DEFAULT '[]'")
            
            # Migrasi: Kolom untuk Onboarding Profile
            if 'skin_type' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN skin_type TEXT")
            if 'avoid_ingredients' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN avoid_ingredients TEXT DEFAULT '[]'")
            if 'skin_issues' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN skin_issues TEXT DEFAULT '[]'")
            if 'skincare_goals' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN skincare_goals TEXT DEFAULT '[]'")
            if 'lifestyle' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN lifestyle TEXT DEFAULT '[]'")
            if 'onboarding_completed' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN onboarding_completed INTEGER DEFAULT 0")
            if 'has_seen_about' not in kolom:
                kursor.execute("ALTER TABLE pengguna ADD COLUMN has_seen_about INTEGER DEFAULT 0")

            # Membuat tabel relasional untuk wishlist (O(1) updates)
            kursor.execute('''
                CREATE TABLE IF NOT EXISTS pengguna_wishlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    product_slug TEXT NOT NULL,
                    product_data TEXT,
                    UNIQUE(email, product_slug)
                )
            ''')
            
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
    def update_pengguna_wishlist(email: str, wishlist_json: str) -> bool:
        """[DEPRECATED] Update wishlist data for the user in the database."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('UPDATE pengguna SET wishlist = ? WHERE email = ?', (wishlist_json, email))
                koneksi.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def tambah_ke_wishlist(email: str, product_slug: str, product_data_json: str) -> bool:
        """Menambahkan satu item ke wishlist menggunakan tabel relasional O(1)."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('''
                    INSERT OR REPLACE INTO pengguna_wishlist (email, product_slug, product_data) 
                    VALUES (?, ?, ?)
                ''', (email, product_slug, product_data_json))
                koneksi.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def hapus_dari_wishlist(email: str, product_slug: str) -> bool:
        """Menghapus satu item dari wishlist O(1)."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('DELETE FROM pengguna_wishlist WHERE email = ? AND product_slug = ?', (email, product_slug))
                koneksi.commit()
            return True
        except Exception:
            return False

    @staticmethod
    def ambil_wishlist(email: str) -> list:
        """Mengambil semua wishlist pengguna secara instan."""
        import json
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('SELECT product_data FROM pengguna_wishlist WHERE email = ?', (email,))
                rows = kursor.fetchall()
                wishlist = []
                for row in rows:
                    if row[0]:
                        try:
                            wishlist.append(json.loads(row[0]))
                        except: pass
                return wishlist
        except Exception:
            return []

    @staticmethod
    def update_user_onboarding(email: str, skin_type: str, avoid_ingredients: str, skin_issues: str, skincare_goals: str, lifestyle: str) -> bool:
        """Update data profil dari hasil onboarding ke database."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute('''
                    UPDATE pengguna 
                    SET skin_type = ?, avoid_ingredients = ?, skin_issues = ?, skincare_goals = ?, lifestyle = ?, onboarding_completed = 1
                    WHERE email = ?
                ''', (skin_type, avoid_ingredients, skin_issues, skincare_goals, lifestyle, email))
                koneksi.commit()
            return True
        except Exception as e:
            print(f"Error update_user_onboarding: {e}")
            return False

    @staticmethod
    def update_profil(email: str, city: str, skin_type: str, avoid_ingredients: list, skin_issues: list, skincare_goals: list, lifestyle: list):
        """Menyimpan data profil dan hasil onboarding."""
        import json
        with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
            kursor = koneksi.cursor()
            kursor.execute('''
                UPDATE pengguna 
                SET city = ?, 
                    skin_type = ?,
                    avoid_ingredients = ?,
                    skin_issues = ?,
                    skincare_goals = ?,
                    lifestyle = ?,
                    onboarding_completed = 1
                WHERE email = ?
            ''', (
                city, 
                skin_type,
                json.dumps(avoid_ingredients),
                json.dumps(skin_issues),
                json.dumps(skincare_goals),
                json.dumps(lifestyle),
                email
            ))
            koneksi.commit()
            
    @staticmethod
    def set_has_seen_about(email: str):
        """Menandai bahwa pengguna telah melihat About Card."""
        try:
            with sqlite3.connect(BasisData.DB_NAMA) as koneksi:
                kursor = koneksi.cursor()
                kursor.execute("UPDATE pengguna SET has_seen_about = 1 WHERE email = ?", (email,))
                koneksi.commit()
                return True
        except Exception as e:
            print(f"Error set_has_seen_about: {e}")
            return False