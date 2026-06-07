import os
import sys
import argparse
from getpass import getpass

# Pastikan sys.path memiliki root directory project untuk bisa import 'app'
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.database.database_manager import BasisData

def main():
    parser = argparse.ArgumentParser(description="Buat akun Super Admin secara aman via CLI")
    parser.add_argument("--username", type=str, help="Username untuk Admin")
    parser.add_argument("--email", type=str, help="Alamat email untuk Admin")
    parser.add_argument("--password", type=str, help="Password (opsional, akan ditanya interaktif jika dikosongkan)")
    args = parser.parse_args()

    print("=== Skintify-C4 | Super Admin Creator ===")
    
    username = args.username
    if not username:
        username = input("Masukkan Username Admin: ").strip()
    
    email = args.email
    if not email:
        email = input("Masukkan Email Admin: ").strip()
    
    password = args.password
    if not password:
        password = getpass("Masukkan Password Admin: ")
    
    # Validasi
    if not username or not email or not password:
        print("[!] Semua data wajib diisi.")
        sys.exit(1)
        
    if BasisData.cek_identifier_terdaftar(email):
        print(f"[!] Email '{email}' sudah terdaftar. Gagal membuat admin.")
        sys.exit(1)
        
    if BasisData.cek_identifier_terdaftar(username):
        print(f"[!] Username '{username}' sudah terdaftar. Gagal membuat admin.")
        sys.exit(1)
        
    # Proses simpan ke database dengan role 'admin'
    berhasil = BasisData.tambah_pengguna(email=email, username=username, password=password, role="admin")
    
    if berhasil:
        print("\n✅ BERHASIL: Akun Super Admin telah dibuat!")
        print(f"Username : {username}")
        print(f"Email    : {email}")
        print(f"Role     : admin")
        print("Silakan buka aplikasi dan login menggunakan kredensial di atas.")
    else:
        print("\n❌ GAGAL: Terjadi kesalahan saat menyimpan ke database.")

if __name__ == "__main__":
    main()
