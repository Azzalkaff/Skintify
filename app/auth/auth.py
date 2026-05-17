import time
import random
import asyncio
from typing import Dict, Any, Tuple
from nicegui import app

from app.database.database_manager import BasisData

class LayananEmail:
    """Simulasi Mock Service untuk pengiriman OTP."""
    @staticmethod
    async def kirim_otp(email: str, otp: str) -> bool:
        # Menghapus artificial delay untuk menghilangkan bottleneck
        print(f"📧 [Email Service] Mengirim OTP {otp} ke {email}")
        return True

class AuthManager:
    """Mengelola pendaftaran, OTP, dan login pengguna dengan Database Permanen.
    
    CATATAN: Modul ini murni Logika Bisnis. 
    TIDAK BOLEH memanggil ui.notify agar tidak crash konteks.
    """

    PENYIMPANAN_OTP: Dict[str, Any] = {}

    @staticmethod
    def is_authenticated() -> bool:
        return app.storage.user.get('authenticated', False)

    @staticmethod
    def is_admin() -> bool:
        """Mengembalikan True jika user saat ini memiliki role admin."""
        return app.storage.user.get('role') == 'admin'

    @staticmethod
    def require_admin():
        """Route Guard: Redirect ke home jika bukan admin (keamanan level 3B)."""
        from fastapi.responses import RedirectResponse
        if not AuthManager.is_authenticated():
            return RedirectResponse('/login')
        if not AuthManager.is_admin():
            return RedirectResponse('/')

    @staticmethod
    async def login(identifier: str, password: str) -> Tuple[bool, str]:
        """Memvalidasi kredensial login secara asinkron."""
        if BasisData.cek_identifier_terdaftar(identifier):
            if BasisData.verifikasi_login(identifier, password):
                user_data = BasisData.get_pengguna(identifier)
                app.storage.user['authenticated'] = True
                app.storage.user['email']         = user_data.get('email')
                app.storage.user['username']      = user_data.get('username')
                app.storage.user['city']          = user_data.get('city', 'Jakarta')
                app.storage.user['role']          = user_data.get('role', 'user')
                return True, "Login berhasil!"
            return False, "Password salah!"
        elif identifier in AuthManager.DATABASE_PENGGUNA:
            mock = AuthManager.DATABASE_PENGGUNA[identifier]
            if mock['password'] == password:
                app.storage.user['authenticated'] = True
                app.storage.user['role']          = mock.get('role', 'user')
                return True, "Login berhasil (Mock Account)!"
            return False, "Password (Mock) salah!"
        else:
            return False, "Email/Username belum terdaftar!"

    @staticmethod
    async def kirim_otp_pendaftaran(email: str, username: str, password: str, role: str = 'user') -> Tuple[bool, str]:
        """Membuat OTP dan mengirim secara asinkron."""
        if BasisData.cek_identifier_terdaftar(email):
            return False, "Email ini sudah memiliki akun!"
        if BasisData.cek_identifier_terdaftar(username):
            return False, "Username ini sudah digunakan!"

        kode_otp = str(random.randint(100000, 999999))
        
        # Kirim Email asinkron (tidak memblokir UI)
        sukses = await LayananEmail.kirim_otp(email, kode_otp)
        
        if sukses:
            AuthManager.PENYIMPANAN_OTP[email] = {
                "otp": kode_otp,
                "username": username,
                "password": password,
                "role": role,
                "exp": time.time() + 300
            }
            return True, f"Kode OTP telah dikirim ke {email}"
        else:
            return False, "Gagal mengirim email."

    @staticmethod
    async def verifikasi_dan_daftar(email: str, otp_input: str) -> Tuple[bool, str]:
        """Verifikasi OTP secara asinkron."""
        data = AuthManager.PENYIMPANAN_OTP.get(email)
        
        if not data:
            return False, "Sesi habis silakan daftar ulang."
        
        if time.time() > data["exp"]:
            return False, "Kode OTP kedaluwarsa!"
            
        if data["otp"] == otp_input:
            berhasil_disimpan = BasisData.tambah_pengguna(email, data["username"], data["password"], data.get("role", "user"))
            
            if berhasil_disimpan:
                del AuthManager.PENYIMPANAN_OTP[email]
                return True, "Akun berhasil dibuat! Silakan login."
            else:
                return False, "Gagal menyimpan ke database."
        
        return False, "Kode OTP salah!"

    @staticmethod
    def logout() -> None:
        app.storage.user['authenticated'] = False
        app.storage.user['role'] = None

    @staticmethod
    def require_auth():
        from fastapi.responses import RedirectResponse
        if not AuthManager.is_authenticated():
            return RedirectResponse('/login')
        return None

    DATABASE_PENGGUNA = {
        "admin": {"password": "admin123", "role": "admin"},
        "user": {"password": "rahasia", "role": "user"}
    }