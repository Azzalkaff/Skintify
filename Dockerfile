# Gunakan image Python resmi yang ringan
FROM python:3.11-slim

# Set environment variables agar output langsung dicetak ke terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# Set working directory di dalam kontainer
WORKDIR /app

# Install sistem dependensi yang dibutuhkan
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Salin requirements file dan instal dependensi python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek ke dalam kontainer
COPY . .

# Buat folder penyimpanan database agar aman
RUN mkdir -p data/db

# Ekspos port yang digunakan
EXPOSE 8081

# Jalankan aplikasi web NiceGUI
CMD ["python", "main.py"]
