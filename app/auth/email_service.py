import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Memuat variabel lingkungan dari file .env
load_dotenv()

class LayananEmail:
    """Modul khusus untuk menangani pengiriman email (SMTP)."""
    
    # KONFIGURASI: Ganti dengan Email dan App Password Anda di file .env
    # Cara buat App Password: Google Account -> Security -> 2-Step Verification -> App Passwords
    EMAIL_PENGIRIM = os.getenv("EMAIL_PENGIRIM", "email-anda@gmail.com") 
    PASSWORD_APLIKASI = os.getenv("PASSWORD_APLIKASI", "xxxx xxxx xxxx xxxx") 

    @staticmethod
    def kirim_otp(email_tujuan: str, kode_otp: str) -> bool:
        """Mengirimkan kode OTP ke email tujuan menggunakan protokol SSL."""
        subjek = f"Kode OTP Skintify Anda: {kode_otp}"
        isi_pesan = f"""
        <html>
            <body style="font-family: sans-serif; line-height: 1.6;">
                <h2 style="color: #A84A62;">Halo, Pecinta Skincare!</h2>
                <p>Terima kasih telah mendaftar di <b>Skintify</b>.</p>
                <p>Gunakan kode OTP di bawah ini untuk memverifikasi akun Anda:</p>
                <div style="background: #F9F5F6; padding: 20px; text-align: center; border-radius: 10px;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #C8607A;">{kode_otp}</span>
                </div>
                <p>Kode ini hanya berlaku selama 5 menit. Jangan bagikan kode ini kepada siapapun.</p>
                <br>
                <p>Salam hangat,<br>Tim Skintify</p>
            </body>
        </html>
        """

        pesan = MIMEMultipart()
        pesan["From"] = LayananEmail.EMAIL_PENGIRIM
        pesan["To"] = email_tujuan
        pesan["Subject"] = subjek
        pesan.attach(MIMEText(isi_pesan, "html"))

        konteks_ssl = ssl.create_default_context()

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=konteks_ssl) as server:
                server.login(LayananEmail.EMAIL_PENGIRIM, LayananEmail.PASSWORD_APLIKASI)
                server.sendmail(LayananEmail.EMAIL_PENGIRIM, email_tujuan, pesan.as_string())
            return True
        except Exception as e:
            print(f"Gagal mengirim email: {e}")
            return False