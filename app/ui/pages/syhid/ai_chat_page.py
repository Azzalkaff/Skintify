import os
import requests
import asyncio
import re
from dotenv import load_dotenv
from nicegui import ui, app
from app.context import data_mgr, state
from app.ui.components import UIComponents
from app.auth.auth import AuthManager
from app.database.engine import SessionLocal
from app.services.routine_service import RoutineService

# Muat file .env secara global
load_dotenv()

def query_gemini_api(prompt: str, api_key: str, model_name: str = "gemini-3.1-flash-lite", chat_history: list = None) -> str:
    """Mengirim request langsung ke API Gemini via HTTP POST dengan support chat history."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    system_instruction = (
        "Anda adalah Skintif AI, asisten dermatologi virtual profesional dan ramah. Jawablah dengan sangat singkat, padat, secukupnya saja, dan tidak bertele-tele. "
        "Tugas Anda adalah menganalisis keluhan kulit pengguna, memberikan rekomendasi bahan aktif skincare, "
        "dan memberikan tips perawatan kulit yang aman. Selalu ingatkan pengguna untuk melakukan patch test "
        "dan berkonsultasi ke dokter kulit asli jika keluhan parah. Jawab dalam Bahasa Indonesia yang santun. "
        "Buatlah format jawaban Anda rapi, gunakan Markdown untuk judul, bullet points, dan penekanan kata agar mudah dibaca.\n\n"
        "Anda memiliki akses database internal produk Skintify. "
        "Jika Anda merekomendasikan produk skincare nyata (terutama produk dari brand populer seperti Skintific, Cosrx, Somethinc, Wardah, dll), "
        "sebutkan nama lengkap produk tersebut dengan jelas di dalam teks respon Anda. "
        "PENTING: Di akhir respon Anda, Anda HARUS menuliskan daftar produk yang direkomendasikan dengan format tag khusus:\n"
        "[RECOMMEND: Nama Lengkap Produk] (satu baris untuk satu produk, tanpa backtick atau markdown di dalam tag tersebut).\n"
        "Jika Anda membutuhkan klarifikasi dari pengguna, Anda dapat memberikan opsi pilihan ganda dengan format tag khusus di akhir respon:\n"
        "[ACTION: Pilihan 1 | Pilihan 2 | Pilihan 3]\n"
        "Contoh format tag di akhir respon:\n"
        "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
        "[ACTION: Kulit Berminyak | Kulit Kering | Kombinasi]"
    )
    
    contents = []
    if chat_history:
        for msg in chat_history[-8:]:
            if msg.get('name') in ['user', 'bot']:
                role = "user" if msg.get('name') == 'user' else "model"
                text = msg.get('text', '')
                if text.strip():
                    contents.append({"role": role, "parts": [{"text": text}]})
    
    contents.append({
        "role": "user",
        "parts": [{"text": f"System Instruction: {system_instruction}\n\nUser Question: {prompt}"}]
    })
    
    payload = {"contents": contents}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data['candidates'][0]['content']['parts'][0]['text']
            return text
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown Error')
            return f"❌ Terjadi kesalahan API Gemini: {error_msg}. Pastikan API Key Anda di .env valid dan aktif."
    except Exception as e:
        return f"❌ Gagal terhubung ke Gemini: {str(e)}. Periksa koneksi internet Anda."

def query_groq_api(prompt: str, api_key: str, model_name: str = "llama-3.3-70b-versatile", chat_history: list = None) -> str:
    """Mengirim request langsung ke API Groq via HTTP POST dengan support chat history."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_instruction = (
        "Anda adalah Skintif AI, asisten dermatologi virtual profesional dan ramah. Jawablah dengan sangat singkat, padat, secukupnya saja, dan tidak bertele-tele. "
        "Tugas Anda adalah menganalisis keluhan kulit pengguna, memberikan rekomendasi bahan aktif skincare, "
        "dan memberikan tips perawatan kulit yang aman. Selalu ingatkan pengguna untuk melakukan patch test "
        "dan berkonsultasi ke dokter kulit asli jika keluhan parah. Jawab dalam Bahasa Indonesia yang santun. "
        "Buatlah format jawaban Anda rapi, gunakan Markdown untuk judul, bullet points, dan penekanan kata agar mudah dibaca.\n\n"
        "Anda memiliki akses database internal produk Skintify. "
        "Jika Anda merekomendasikan produk skincare nyata (terutama produk dari brand populer seperti Skintific, Cosrx, Somethinc, Wardah, dll), "
        "sebutkan nama lengkap produk tersebut dengan jelas di dalam teks respon Anda. "
        "PENTING: Di akhir respon Anda, Anda HARUS menuliskan daftar produk yang direkomendasikan dengan format tag khusus:\n"
        "[RECOMMEND: Nama Lengkap Produk] (satu baris untuk satu produk, tanpa backtick atau markdown di dalam tag tersebut).\n"
        "Jika Anda membutuhkan klarifikasi dari pengguna, Anda dapat memberikan opsi pilihan ganda dengan format tag khusus di akhir respon:\n"
        "[ACTION: Pilihan 1 | Pilihan 2 | Pilihan 3]\n"
        "Contoh format tag di akhir respon:\n"
        "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
        "[ACTION: Kulit Berminyak | Kulit Kering | Kombinasi]"
    )
    
    messages = [{"role": "system", "content": system_instruction}]
    if chat_history:
        for msg in chat_history[-8:]:
            if msg.get('name') in ['user', 'bot']:
                role = "user" if msg.get('name') == 'user' else "assistant"
                text = msg.get('text', '')
                if text.strip():
                    messages.append({"role": role, "content": text})
    
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            res_data = response.json()
            text = res_data['choices'][0]['message']['content']
            return text
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown Error')
            return f"❌ Terjadi kesalahan API Groq: {error_msg}. Pastikan API Key Groq Anda di .env valid."
    except Exception as e:
        return f"❌ Gagal terhubung ke Groq: {str(e)}. Periksa koneksi internet Anda."

def parse_budget_from_text(text: str) -> float | None:
    text = text.lower().replace(",", "").replace("rebu", "ribu")
    
    # Pemetaan istilah finansial kasual Indonesia ke angka asli
    konversi_slang = {
        "gocap": 50000, "cepek": 100000, "nopek": 200000,
        "lima puluh ribu": 50000, "seratus ribu": 100000, 
        "seratus lima puluh ribu": 150000, "dua ratus ribu": 200000,
        "tiga ratus ribu": 300000, "empat ratus ribu": 400000, "lima ratus ribu": 500000
    }
    for kata, angka in konversi_slang.items():
        if kata in text:
            return float(angka)

    # Deteksi format ringkas e-commerce (contoh: 100k, 50rb, 150 ribu, 85k, 120.5k)
    match_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:rb|k|ribu)", text)
    if match_k:
        val = match_k.group(1).replace(".", "")
        return float(val) * 1000

    # Deteksi angka nominal bulat utuh (contoh: 150000 atau 150.000)
    match_num = re.search(r"(\d+(?:\.\d{3})+|\d{4,})", text)
    if match_num:
        num_str = match_num.group(1).replace(".", "")
        try:
            return float(num_str)
        except ValueError:
            pass
            
    return None

def find_skincare_package(budget: float) -> list:
    from app.database.engine import SessionLocal
    from app.database.models import SociollaReferensi
    
    categories = ["Cleanser", "Moisturizer", "Sunscreen", "Toner", "Serum"]
    products_by_cat = {}
    
    avoid_ingredients = [ing.lower().strip() for ing in app.storage.user.get('avoid_ingredients', [])]
    
    with SessionLocal() as session:
        for cat in categories:
            # 1. Ambil SEMUA produk dalam batas budget (MCKP Rule: Himpun kandidat valid)
            prods = session.query(SociollaReferensi).filter(
                SociollaReferensi.category == cat,
                SociollaReferensi.min_price > 5000.0,
                SociollaReferensi.min_price <= budget,
                SociollaReferensi.image_url != None,
                SociollaReferensi.image_url != ""
            ).all()
            
            cat_list = []
            for p in prods:
                ingredients_text = (p.ingredients or "").lower()
                if any(forbidden in ingredients_text for forbidden in avoid_ingredients if forbidden):
                    continue
                
                # 2. Multi-Criteria Decision Analysis (MCDA) Scoring
                rating = p.rating_sociolla or 0.0
                reviews_count = p.total_reviews or 0
                
                # Normalisasi skor sederhana: Rating (70% bobot) + Popularitas (30% bobot)
                # Asumsi review_count 1000 adalah populasi maksimum yang optimal
                pop_score = min(reviews_count / 1000.0, 1.0) * 5.0 
                weighted_score = (rating * 0.7) + (pop_score * 0.3)
                
                cat_list.append({
                    "brand": p.brand,
                    "product_name": p.product_name,
                    "min_price": p.min_price,
                    "category": p.category,
                    "image_url": p.image_url,
                    "rating_sociolla": p.rating_sociolla,
                    "slug": p.slug,
                    "ingredients": p.ingredients,
                    "reviews": p.reviews,
                    "quality_score": weighted_score # Simpan skor kualitas
                })
            
            # 3. Urutkan berdasarkan Kualitas (Tertinggi ke Terendah), bukan Harga Termurah!
            cat_list.sort(key=lambda x: x["quality_score"], reverse=True)
            products_by_cat[cat] = cat_list
            
    # Skenario Kategori Hirarkis (Prioritas CTMP)
    scenarios = [
        ["Cleanser", "Moisturizer", "Sunscreen"], # Prioritas 1: Basic Skincare Siang
        ["Cleanser", "Toner", "Moisturizer"],     # Prioritas 2: Basic Skincare Malam
        ["Cleanser", "Moisturizer", "Serum"],     # Prioritas 3: Basic + Treatment
        ["Cleanser", "Moisturizer"],              # Prioritas 4: Minimalis
        ["Cleanser", "Sunscreen"],                # Prioritas 5: Minimalis Pagi
        ["Moisturizer", "Sunscreen"],             # Prioritas 6: Hidrasi & Proteksi
        ["Cleanser"]                              # Prioritas 7: Super Hemat
    ]

    for scenario in scenarios:
        current_budget = budget
        temp_combo = []
        
        # Asumsi minimum harga produk (Rp 20.000) untuk sisa kategori 
        # agar budget tidak dihabiskan seluruhnya oleh produk pertama
        min_price_assumption = 20000.0 
        
        for i, cat in enumerate(scenario):
            remaining_cats_count = len(scenario) - (i + 1)
            min_reserved_budget = remaining_cats_count * min_price_assumption
            max_price_for_this_item = current_budget - min_reserved_budget
            
            selected = None
            for p in products_by_cat.get(cat, []):
                # Cari produk dengan harga masuk akal (karena sudah diurutkan berdasar Quality Score)
                if p["min_price"] <= max_price_for_this_item:
                    selected = p
                    break # Langsung ambil yang pertama (Kualitas Tertinggi di budget ini)
                    
            if selected:
                temp_combo.append(selected)
                current_budget -= selected["min_price"]
            else:
                break # Gagal menemukan produk yang pas untuk kategori ini di dalam budget
                
        # Jika berhasil menemukan produk untuk SEMUA kategori di skenario ini
        if len(temp_combo) == len(scenario):
            return temp_combo

    # Fallback to top 2 cheapest products (Jika gagal semua skenario)
    all_flat = []
    for cat, list_p in products_by_cat.items():
        if list_p:
            all_flat.append(list_p[0])
            
    all_flat = sorted(all_flat, key=lambda x: x["min_price"])
    if len(all_flat) >= 2:
        if all_flat[0]["min_price"] + all_flat[1]["min_price"] <= budget:
            return [all_flat[0], all_flat[1]]
            
    if all_flat:
        return [all_flat[0]]
        
    return []

def get_smart_mock_response(prompt: str) -> str:
    """Mengembalikan jawaban simulasi pintar secara offline dengan cakupan skenario berpikir (Scenario Thinking) yang komprehensif."""
    p_lower = prompt.lower()
    
    # 1. SKENARIO: FINANCIAL PLAN & BUDGETING (Slang & Nominal)
    budget = parse_budget_from_text(prompt)
    if budget is not None:
        package = find_skincare_package(budget)
        if package:
            total_price = sum(p["min_price"] for p in package)
            prod_lines = "\n".join([f"- **Langkah {i+1} ({p['category']})**: **{p['brand']}** - {p['product_name']} (Harga: Rp{p['min_price']:,.0f}".replace(',', '.') + ")" for i, p in enumerate(package)])
            tags = "\n".join([f"[RECOMMEND: {p['brand']} {p['product_name']}]" for p in package])
            
            return (
                f"💡 **Skintif AI (Mode Offline - Skincare Financial Plan):**\n\n"
                f"Tentu! Saya telah menyaring ratusan produk di database kami menggunakan *Multi-Criteria Decision Analysis*. "
                f"Hasilnya, saya berhasil meracik paket skincare berkualitas tinggi yang **100% sesuai dengan alokasi kantong Anda** (Budget: **Rp {budget:,.0f}**).\n\n"
                f"Berikut adalah **Paket Perawatan Optimal** yang terpilih khusus untuk Anda:\n\n"
                f"{prod_lines}\n\n"
                f"📊 **Transparansi Kalkulasi Investasi:**\n"
                f"- **Total Biaya Paket**: **Rp {total_price:,.0f}**\n"
                f"- **Sisa Saldo Anda**: **Rp {budget - total_price:,.0f}**\n\n"
                f"Saya memprioritaskan produk-produk ini bukan hanya dari segi harga, tetapi karena memiliki skor ulasan klinis yang tinggi dari pengguna nyata. "
                f"Silakan klik tombol '+ Planner' pada kartu di bawah untuk memulai rutinitas Anda dengan aman! 💖\n\n"
                f"{tags}"
            ).replace(',', '.')
        else:
            return (
                f"💡 **Skintif AI (Mode Offline):**\n\n"
                f"Maaf, saya tidak menemukan kombinasi produk di database kami yang totalnya berada di bawah budget **Rp {budget:,.0f}** Anda. "
                f"Cobalah untuk menaikkan sedikit budget Anda atau mencari produk satuan di halaman Cari Produk."
            )

    # 2. SKENARIO: CHEMICAL CONFLICT ANALYSIS (Gabungan / Tabrakan Bahan Aktif)
    if any(x in p_lower for x in ["campur", "gabung", "bareng", "pake setelah", "ditimpa"]):
        if "retinol" in p_lower and any(x in p_lower for x in ["aha", "bha", "salicylic", "glycolic", "eksfoliasi"]):
            return (
                "🚨 **PERINGATAN BAHAN AKTIF (CHEMICAL CONFLICT):**\n\n"
                "Penggabungan **Retinol** dan **AHA/BHA (Glycolic/Salicylic Acid)** secara bersamaan sangat dilarang!\n"
                "- **Bahaya**: Risiko tinggi memicu eksfoliasi berlebih (*over-exfoliation*), kemerahan, pengelupasan parah, dan iritasi kulit.\n"
                "- **Solusi Aman**: Gunakan secara terpisah di malam yang berbeda (selang-seling), dan selalu kunci dengan pelembap penyuplai hidrasi.\n\n"
                "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
            )
        if "vitamin c" in p_lower and "niacinamide" in p_lower:
            return (
                "💡 **Evaluasi Kombinasi Bahan Aktif:**\n\n"
                "Menggabungkan **Vitamin C** dan **Niacinamide** sebenarnya aman untuk kulit yang sudah toleran. Namun, bagi sebagian kulit sensitif, kombinasi ini dapat memicu kemerahan ringan.\n\n"
                "**Saran Penggunaan (Sirkadian):** Gunakan Vitamin C di pagi hari bersama Sunscreen (untuk proteksi radikal bebas), dan gunakan Niacinamide di malam hari untuk regulasi barrier.\n\n"
                "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
            )

    # 3. SKENARIO: ANALISIS RUTINITAS USER (Heuristik)
    if "analisis kelemahan" in p_lower or "analisis rutinitas" in p_lower:
        routine_str = ""
        if state.routine:
            routine_str = "\n".join([f"- **{p.get('brand')}** {p.get('product_name')}" for p in state.routine])
        else:
            routine_str = "- (Belum ada produk di Planner Anda)"
            
        return (
            "💡 **Skintif AI (Mode Heuristik Offline):**\n\n"
            "Saya telah mendeteksi produk di Routine Planner Anda:\n"
            f"{routine_str}\n\n"
            "**Hasil Evaluasi Cepat:**\n"
            "1. **Keamanan Barrier**: Produk Anda secara umum aman digunakan. Pastikan pelembap digunakan setelah pemakaian bahan aktif.\n"
            "2. **Deteksi Konflik**: Tidak terdeteksi tabrakan bahan aktif berat (seperti Retinol + AHA/BHA secara bersamaan).\n"
            "3. **Rekomendasi**: Selalu gunakan **Sunscreen** di pagi hari untuk melindungi kulit dari kemerahan.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
            "[RECOMMEND: Somethinc Granactive Retinoid]"
        )

    # 4. SKENARIO: GEJALA FISIK KULIT (Symptom-Based Detection & Sinonim)
    if any(x in p_lower for x in ["jerawat", "acne", "beruntus", "komedo", "buntilan", "radang", "nanah"]):
        return (
            "💡 **Saran Skintif AI (Mode Offline):**\n\n"
            "Untuk kulit rentan berjerawat dan beruntusan (*Acne-Prone*), cari bahan skincare berikut:\n"
            "- **Salicylic Acid (BHA) / Sulfur**: Mengikis sel kulit mati dan mengontrol minyak berlebih di pori-pori.\n"
            "- **Centella Asiatica (Cica) / Allantoin**: Menurunkan kadar kemerahan (*erythema*) dan menenangkan inflamasi.\n"
            "- **Niacinamide**: Mengontrol sebum berlebih dan menyamarkan noda bekas jerawat.\n\n"
            "[RECOMMEND: Cosrx Salicylic Acid Daily Gentle Cleanser]"
        )
        
    if any(x in p_lower for x in ["kering", "dry", "kupas", "perih", "ketarik", "barrier", "scaly"]):
        return (
            "💡 **Saran Skintif AI (Mode Offline):**\n\n"
            "Kulit kering, perih, atau mengelupas membutuhkan hidrasi ekstra dan perbaikan lapisan lipid pelindung. Fokus pada bahan berikut:\n"
            "- **Hyaluronic Acid / Glycerin**: Menarik hidrasi air dan mengunci kelembapan di dalam kulit.\n"
            "- **Ceramide / Shea Butter**: Memperbaiki, memperkuat, dan menjaga kekuatan *skin barrier*.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )
        
    if any(x in p_lower for x in ["berminyak", "oily", "kilang", "sebum", "lengket"]):
        return (
            "💡 **Saran Skintif AI (Mode Offline):**\n\n"
            "Untuk kulit berminyak, tujuannya adalah meregulasi sebum tanpa membuat kulit mengalami dehidrasi:\n"
            "- Gunakan pembersih wajah berformula lembut dan pelembap bertekstur **Gel** yang ringan agar tidak menyumbat pori.\n"
            "- Cari kandungan **Sebum Regulator** seperti BHA, Tea Tree, Clay, atau Niacinamide.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )
        
    if "retinol" in p_lower or "retinoid" in p_lower or "aging" in p_lower:
        return (
            "💡 **Saran Skintif AI (Mode Offline):**\n\n"
            "Retinol sangat baik untuk anti-aging dan regenerasi kulit. Namun, harap ingat:\n"
            "1. **Gunakan di malam hari saja** karena retinol membuat kulit sensitif terhadap cahaya matahari.\n"
            "2. **JANGAN dicampur** bersamaan dengan **AHA/BHA** dalam satu rutinitas karena berisiko iritasi parah.\n"
            "3. Pastikan gunakan **Sunscreen** minimal SPF 30 di pagi hari setelah pemakaian retinol.\n\n"
            "[RECOMMEND: Somethinc Granactive Retinoid]"
        )

    # 5. SKENARIO: PROTEKSI EXPOSOME & CUACA (Mendung, Panas, Terik, Dingin)
    if any(x in p_lower for x in ["tips", "cuaca", "panas", "terik", "uv", "dingin", "mendung", "hujan"]):
        city = app.storage.user.get('city', 'Jakarta')
        return (
            "💡 **Saran Skintif AI (Mode Real-Time Weather Guardian):**\n\n"
            f"Berdasarkan adaptasi kondisi cuaca dan lingkungan di kota **{city}**:\n"
            "1. **Indeks UV Tinggi / Terik**: Wajib gunakan perlindungan ekstra. Re-apply Sunscreen setiap 2 jam untuk mencegah eritema.\n"
            "2. **Kelembapan Rendah / Dingin**: Udara kering menyerap kelembapan alami kulit, tambahkan pelembab oklusif untuk mengunci hidrasi.\n"
            "3. **Kelembapan Tinggi / Mendung**: Gunakan produk non-komedogenik bertekstur gel ringan agar pori tidak tersumbat.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )

    # 6. SKENARIO: BATTLE BRAND & COMPOSITE COMPARISON (Adu Mekanik)
    if any(x in p_lower for x in ["bagusan", "mending", "vs", "battle", "banding", "bagus mana"]):
        return (
            "⚔️ **Arena Duel Skintify-C4 (Mode Offline):**\n\n"
            "Untuk melakukan komparasi spesifikasi zat aktif dan fluktuasi harga lintas e-commerce secara presisi, "
            "Skintify menyediakan fitur **Arena Duel Battle Grid**!\n\n"
            "**Cara Penggunaan:**\n"
            "1. Pergi ke halaman **Wishlist**.\n"
            "2. Klik tombol **'Bandingkan ⚔️'** pada produk-produk penantang yang ingin Anda adu.\n"
            "3. **Centered Floating Compare Dock** bergaya iOS akan meluncur di bawah layar Anda. Klik **'Bandingkan!'** untuk membuka matriks komparasi siap tempur!\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )

    # 7. SKENARIO: CHRONODERMATOLOGY & ROUTINE SEQUENCING (Sirkadian Kulit)
    if any(x in p_lower for x in ["urutan", "kapan", "pagi atau malam", "tahapan", "pake setelah"]):
        return (
            "⏰ **Panduan Sirkadian Kulit (Chronodermatology):**\n\n"
            "Sistem metabolisme kulit berubah mengikuti siklus sirkadian waktu lokal. Berikut adalah penyesuaian urutannya:\n"
            "1. ☀️ **Rutinitas Pagi (Fokus Proteksi)**:\n"
            "   - *Cleanser* -> *Hydrating Toner* -> *Moisturizer* -> **Sunscreen** (Wajib dilindungi dari indeks UV).\n"
            "2. 🌙 **Rutinitas Malam (Fokus Pemulihan)**:\n"
            "   - *Double Cleansing* -> *Toner* -> *Active Treatment (Retinol/Eksfoliasi)* -> **Moisturizer / Occlusive** (Untuk mengunci hidrasi trans-epidermal).\n\n"
            "*Catatan Klinis: Agen agresif seperti Retinol eksklusif hanya untuk malam hari!*"
        )

    # 8. SKENARIO: INVESTIGASI DERMATOLOGICAL ACTIVE-INGREDIENT
    if any(x in p_lower for x in ["fungsi", "gunanya", "manfaat", "kandungan", "khasiat"]):
        if "bha" in p_lower or "salicylic" in p_lower or "sulfur" in p_lower:
            return "🧬 **Ingredient Profiling:** Kandungan ini diklasifikasikan sebagai *Sebum Regulator & Keratolytic*. Berfungsi menembus lipid pori-pori untuk mengikis sel kulit mati dan mengontrol minyak berlebih."
        if "ceramide" in p_lower or "hyaluronic" in p_lower or "squalane" in p_lower:
            return "🧬 **Ingredient Profiling:** Kandungan ini diklasifikasikan sebagai *Humectant & Occlusive*. Berfungsi menarik molekul air dan memperkuat pengikatan lipid pelindung kulit (*skin barrier*)."
        if "cica" in p_lower or "centella" in p_lower or "allantoin" in p_lower:
            return "🧬 **Ingredient Profiling:** Kandungan ini diklasifikasikan sebagai *Anti-Inflammatory & Soothing*. Sangat optimal ditargetkan untuk menurunkan kadar kemerahan (*erythema*) akibat iritasi."

    # 9. SKENARIO: GREETINGS (Sapaan Formal & Kasual)
    if any(x in p_lower for x in ["halo", "hi", "pagi", "siang", "malam", "assalamualaikum", "permisi", "hey"]):
        return (
            "Halo! Saya Skintif AI. 👋\n\n"
            "Saya siap membantu menjawab segala keluhan kulit Anda, mendeteksi konflik bahan kimia aktif, hingga meracik rencana finansial skincare. "
            "Coba tanyakan sesuatu, misalnya: *'Muka gua lagi beruntusan dan perih nih'*, *'Bagusan Skintific atau Somethinc?'*, atau *'Gua punya budget gocap dapet paket apa?'*"
        )
        
    # FALLBACK APABILA DI LUAR SELURUH SKENARIO DI ATAS
    return (
        "💡 **Saran Skintif AI (Mode Offline):**\n\n"
        "Pertanyaan Anda sangat menarik! Sebagai saran umum, pastikan Anda selalu menjaga pola **Basic Skincare** Anda:\n"
        "1. *Cleanser* (Pembersih wajah lembut)\n"
        "2. *Moisturizer* (Pelembap penyuplai hidrasi)\n"
        "3. *Sunscreen* (Pelindung UV di pagi hari)\n\n"
        "*Tips: Untuk mendapatkan jawaban yang berbasis data klinis (Evidence-Based Q&A) secara real-time dan personal, silakan masukkan API Key Anda pada file .env.*"
    )

def get_user_context() -> str:
    """Mengumpulkan info profil kulit dan produk user saat ini untuk diumpankan ke AI sebagai konteks (Termasuk Exposome & Sirkadian)."""
    import datetime
    skin_type = app.storage.user.get('skin_type', 'Belum diisi')
    avoid_ing = app.storage.user.get('avoid_ingredients', [])
    skin_issues = app.storage.user.get('skin_issues', [])
    city = app.storage.user.get('city', 'Jakarta')
    
    # 1. Chronodermatology (Sirkadian Kulit)
    current_hour = datetime.datetime.now().hour
    if 5 <= current_hour < 15:
        waktu = "Pagi/Siang"
        fokus_sirkadian = "Fokus pada Proteksi (Sunscreen) dan Antioksidan (contoh: Vitamin C)."
    elif 15 <= current_hour < 19:
        waktu = "Sore"
        fokus_sirkadian = "Fokus pada Pembersihan (Double Cleansing) pasca aktivitas luar ruangan."
    else:
        waktu = "Malam"
        fokus_sirkadian = "Fokus pada Pemulihan Barrier (Ceramide) dan Active Treatment (Retinol/Eksfoliasi)."

    # 2. Skin Exposome (Data Cuaca & Lingkungan Real-Time)
    weather_info = "Data cuaca tidak tersedia."
    instruksi_cuaca = ""
    try:
        # Meminjam modul data_mgr untuk fetch cuaca tanpa mengirim list ingredients penuh
        analysis = data_mgr.analyze_routine([], kota=city)
        if analysis and analysis.get("weather") and analysis["weather"].get("status") == "success":
            w = analysis["weather"]
            weather_info = f"Suhu: {w.get('temp')}°C, Kelembapan: {w.get('humidity')}%, UV Index: {w.get('uv_index')}, Kondisi: {w.get('desc')}"
            
            if int(w.get('uv_index', 0)) >= 6:
                instruksi_cuaca += "UV Index Ekstrem. Wajib tekan pentingnya Re-apply Sunscreen. "
            if int(w.get('humidity', 50)) < 40:
                instruksi_cuaca += "Udara sangat kering. Wajib rekomendasikan humectant (Hyaluronic Acid/Glycerin). "
            elif int(w.get('humidity', 50)) > 75:
                instruksi_cuaca += "Kelembapan tinggi. Sarankan pelembap tekstur gel ringan agar pori tidak tersumbat. "
    except Exception:
        pass
    
    # 3. Identifikasi Rutinitas (RAG Fallback)
    routine_products = []
    has_retinol = False
    for p in state.routine:
        brand = p.get('brand', 'Unknown')
        name = p.get('product_name', 'Unnamed Product')
        routine_products.append(f"- {brand} - {name}")
        
        # Simple deteksi bahan rawan konflik
        if "retinol" in name.lower() or "retinoid" in name.lower():
            has_retinol = True
    
    routine_str = "\n".join(routine_products) if routine_products else "- Belum ada produk di Routine Planner."
    avoid_str = ", ".join(avoid_ing) if avoid_ing else "Tidak ada"
    issues_str = ", ".join(skin_issues) if skin_issues else "Tidak ada"
    
    # Proteksi Konflik Absolut (Mencegah Halusinasi LLM)
    clinical_warning = ""
    if has_retinol:
        clinical_warning = "\n[⚠️ PERINGATAN MEDIS ABSOLUT]\nPengguna ini SEDANG MENGGUNAKAN RETINOL di rutinitasnya. ANDA DILARANG KERAS merekomendasikan penambahan AHA/BHA atau Vitamin C dalam satu waktu bersamaan untuk menghindari kerusakan Skin Barrier!"
    
    context = (
        f"\n[KONTEKS MEDIS PENGGUNA SKINTIFY]\n"
        f"- Jenis Kulit Pengguna: {skin_type}\n"
        f"- Keluhan Kulit Utama: {issues_str}\n"
        f"- Kandungan Skincare Dihindari: {avoid_str}\n"
        f"- Waktu Lokal Saat Ini: {waktu} ({fokus_sirkadian})\n"
        f"- Kondisi Cuaca & Exposome di {city}: {weather_info}\n"
        f"- Instruksi Tambahan Berdasar Cuaca: {instruksi_cuaca}\n"
        f"- Produk di Routine Planner Saat Ini:\n{routine_str}\n"
        f"{clinical_warning}\n\n"
        f"PENTING: Gunakan data medis, sirkadian, dan lingkungan di atas untuk memberikan jawaban Evidence-Based yang sangat akurat, personal, dan aman!"
    )
    return context

def parse_ai_recommendations(text: str) -> tuple:
    """
    Memindai respon dari AI untuk mendeteksi tag [RECOMMEND: Nama Produk],
    menghapusnya dari tampilan teks mentah, dan mencari produk tersebut di database.
    """
    from app.database.engine import SessionLocal
    from app.database.models import SociollaReferensi
    from sqlalchemy import or_
    
    recommended_products = []
    
    # Mencari pola [RECOMMEND: Nama Produk]
    pattern = r"\[RECOMMEND:\s*(.*?)\]"
    matches = re.findall(pattern, text)
    
    # Hapus tag rekomendasi dari teks agar tidak mengotori balon obrolan
    cleaned_text = re.sub(pattern, "", text).strip()
    
    # Hapus baris sisa di bagian akhir respon
    cleaned_text = re.sub(r"\n\s*\n\s*$", "", cleaned_text).strip()
    
    for prod_name in matches:
        prod_name = prod_name.strip()
        if not prod_name:
            continue
            
        # ALGORITMA TERBAIK: Token-based AND Query
        # Memecah string menjadi token kata, dan mewajibkan SEMUA token (AND) muncul.
        # Ini 100x lebih presisi daripada fuzzy paginated search yang menggunakan OR dan limit.
        words = [w.strip().lower() for w in prod_name.split() if len(w.strip()) >= 2]
        if not words:
            continue
            
        with SessionLocal() as session:
            query = session.query(SociollaReferensi)
            for w in words:
                query = query.filter(
                    or_(
                        SociollaReferensi.product_name.ilike(f"%{w}%"),
                        SociollaReferensi.brand.ilike(f"%{w}%")
                    )
                )
            
            first_match = query.first()
            
            # Fallback 1: Jika LLM halusinasi atau menambahkan kata ekstra (misal "Cleanser Skintific 100ml"),
            # abaikan token terakhir dan coba cari lagi.
            if not first_match and len(words) > 2:
                query_fallback = session.query(SociollaReferensi)
                for w in words[:-1]: 
                    query_fallback = query_fallback.filter(
                        or_(
                            SociollaReferensi.product_name.ilike(f"%{w}%"),
                            SociollaReferensi.brand.ilike(f"%{w}%")
                        )
                    )
                first_match = query_fallback.first()
                
            if first_match:
                recommended_products.append({
                    "id": first_match.id,
                    "brand": first_match.brand,
                    "product_name": first_match.product_name,
                    "min_price": first_match.min_price,
                    "image_url": first_match.image_url,
                    "slug": first_match.slug
                })
            
    return cleaned_text, recommended_products

def parse_ai_actions(text: str) -> tuple:
    """
    Memindai respon dari AI untuk mendeteksi tag [ACTION: Opsi 1 | Opsi 2]
    dan mengembalikannya sebagai list of string.
    """
    pattern = r"\[ACTION:\s*(.*?)\]"
    matches = re.findall(pattern, text)
    
    cleaned_text = re.sub(pattern, "", text).strip()
    actions = []
    
    if matches:
        # Ambil tag action terakhir jika AI memberikan lebih dari satu
        actions = [opt.strip() for opt in matches[-1].split("|") if opt.strip()]
        
    return cleaned_text, actions

def show_page():
    """Halaman Utama Skintify AI Chatbot (End-User Interface)"""
    import time
    print(f"[TRACE-BOTTLENECK] {time.time()} - ai_chat_page: show_page started")
    
    # 1. Proteksi Login
    auth_redirect = AuthManager.require_auth()
    if auth_redirect:
        return auth_redirect

    # Mengunci body halaman agar tidak memiliki scrollbar global (Bebas Scrollbar!)
    ui.query('body').style('height: 100vh; overflow: hidden;')

    add_to_routine_data = {'product': None}

    # Modal Dialog untuk Tambah ke Routine Planner
    with ui.dialog() as add_to_routine_modal, ui.card().classes('p-6 w-[450px] rounded-2xl bg-white shadow-2xl') as add_to_routine_card:
        @ui.refreshable
        def add_to_routine_content():
            prod = add_to_routine_data['product']
            if not prod:
                return
            
            ui.label('Tambah ke Routine Planner').classes('text-lg font-black text-gray-800 mb-1')
            ui.label(f"Tambahkan **{prod.get('brand')} {prod.get('product_name')}** ke rutinitas Anda.").classes('text-xs text-gray-500 mb-4')
            
            user_email = app.storage.user.get('email')
            with SessionLocal() as session:
                user = RoutineService.get_or_create_user(session, user_email)
                routines = RoutineService.get_user_routines(session, user.id)
                
                if not routines:
                    ui.label('Anda belum memiliki rutinitas skincare.').classes('text-xs text-amber-600 font-bold mb-2')
                    new_routine_name = ui.input('Nama Rutinitas Baru', placeholder='Contoh: Rutin Pagi Hari').classes('w-full mb-3')
                    
                    async def create_and_add():
                        if not new_routine_name.value:
                            ui.notify('Nama rutinitas wajib diisi!', color='warning')
                            return
                        with SessionLocal() as session_write:
                            db_user = RoutineService.get_or_create_user(session_write, user_email)
                            new_r = RoutineService.create_routine(session_write, db_user.id, new_routine_name.value, "Dibuat dari Asisten AI")
                            from app.database.models import Produk
                            matched_produk = session_write.query(Produk).filter_by(referensi_id=prod['id']).first()
                            if matched_produk:
                                RoutineService.add_item_to_routine(session_write, new_r.id, product_id=matched_produk.id)
                            else:
                                prod_name = f"{prod['brand']} {prod['product_name']}".strip()
                                notes = f"IMAGE:{prod.get('image_url', '')}"
                                RoutineService.add_item_to_routine(session_write, new_r.id, custom_name=prod_name, notes=notes)
                        
                        ui.notify(f"Rutin '{new_routine_name.value}' dibuat & {prod.get('product_name')} ditambahkan!", color='positive')
                        add_to_routine_modal.close()
                    
                    ui.button('Buat Rutin & Tambahkan', on_click=create_and_add, color='pink-500').classes('w-full font-bold text-white')
                else:
                    with ui.column().classes('w-full gap-2 mb-4 max-h-48 overflow-y-auto'):
                        for r in routines:
                            # We create a click handler for each routine
                            async def add_item_to_r(r_id=r.id, r_name=r.name):
                                with SessionLocal() as session_write:
                                    from app.database.models import Produk
                                    matched_produk = session_write.query(Produk).filter_by(referensi_id=prod['id']).first()
                                    if matched_produk:
                                        RoutineService.add_item_to_routine(session_write, r_id, product_id=matched_produk.id)
                                    else:
                                        prod_name = f"{prod['brand']} {prod['product_name']}".strip()
                                        notes = f"IMAGE:{prod.get('image_url', '')}"
                                        RoutineService.add_item_to_routine(session_write, r_id, custom_name=prod_name, notes=notes)
                                ui.notify(f"{prod.get('product_name')} ditambahkan ke '{r_name}'! 🧴", color='positive')
                                add_to_routine_modal.close()
                                
                            ui.button(f"Tambah ke '{r.name}'", on_click=add_item_to_r, color='blue-500').props('outline').classes('w-full text-xs font-bold')
                    
                    # Quick Create Rutinitas Baru
                    ui.separator().classes('my-2')
                    ui.label('Atau buat rutinitas baru:').classes('text-[10px] text-gray-400 font-bold mb-1')
                    with ui.row().classes('w-full gap-2 items-center no-wrap'):
                        quick_name = ui.input(placeholder='Rutin Baru...').classes('flex-grow')
                        async def quick_create():
                            if not quick_name.value:
                                ui.notify('Ketik nama rutin dulu!', color='warning')
                                return
                            with SessionLocal() as session_write:
                                db_user = RoutineService.get_or_create_user(session_write, user_email)
                                new_r = RoutineService.create_routine(session_write, db_user.id, quick_name.value, "Dibuat dari Asisten AI")
                                from app.database.models import Produk
                                matched_produk = session_write.query(Produk).filter_by(referensi_id=prod['id']).first()
                                if matched_produk:
                                    RoutineService.add_item_to_routine(session_write, new_r.id, product_id=matched_produk.id)
                                else:
                                    prod_name = f"{prod['brand']} {prod['product_name']}".strip()
                                    notes = f"IMAGE:{prod.get('image_url', '')}"
                                    RoutineService.add_item_to_routine(session_write, new_r.id, custom_name=prod_name, notes=notes)
                            ui.notify(f"Rutin '{quick_name.value}' dibuat & {prod.get('product_name')} ditambahkan!", color='positive')
                            add_to_routine_modal.close()
                            
                        ui.button('Buat', on_click=quick_create, color='pink-500').classes('font-bold text-white text-xs')
                        
            ui.button('Tutup', on_click=add_to_routine_modal.close).props('flat').classes('w-full text-gray-400 text-xs font-bold mt-2 bg-gray-50')

    def open_add_to_routine_dialog(prod):
        add_to_routine_data['product'] = prod
        add_to_routine_content.refresh()
        add_to_routine_modal.open()

    def add_to_wishlist(prod):
        wishlist = state.wishlist or []
        # Cek jika produk sudah terdaftar di wishlist
        if any(p.get('slug') == prod.get('slug') for p in wishlist):
            ui.notify('Produk sudah ada di Wishlist Anda! ❤️', color='warning', icon='favorite')
            return
            
        wishlist.append(prod)
        state.wishlist = wishlist
        ui.notify('Berhasil ditambahkan ke Wishlist! ❤️', color='pink', icon='favorite')

    def render_recommended_product_card(prod, all_products=None):
        img_url = prod.get('image_url', '')
        with ui.card().classes(
            'p-3 border border-white/80 bg-white/70 backdrop-blur-md rounded-2xl flex-row items-center gap-3 hover:scale-[1.02] transition-all hover:bg-pink-50/40'
        ).style('width: 295px; box-shadow: 0 8px 32px 0 rgba(244, 114, 182, 0.05);'):
            with ui.element('div').classes('w-14 h-14 bg-white rounded-xl overflow-hidden flex items-center justify-center border border-gray-100 flex-shrink-0'):
                if img_url and str(img_url).startswith('http'):
                    ui.image(img_url).classes('w-full h-full object-contain')
                else:
                    ui.label('🧴').classes('text-2xl')
            
            with ui.column().classes('flex-grow min-w-0 gap-0.5'):
                ui.label(prod.get('brand', 'Skintific').upper()).classes('text-[8px] font-black text-pink-500 uppercase tracking-wider')
                ui.label(prod.get('product_name', 'Product')).classes('text-[10px] font-bold text-gray-800 line-clamp-1 leading-tight')
                
                price = prod.get('min_price', 0)
                format_price = f"Rp{price:,.0f}".replace(',', '.') if price else '-'
                ui.label(format_price).classes('text-[10px] font-black text-pink-500')
                
                with ui.row().classes('w-full gap-1 items-center mt-1 no-wrap'):
                    # Bandingkan Harga
                    def trigger_compare(p=prod):
                        state.__dict__['selected_compare_category'] = p.get('category', 'Lainnya')
                        state.__dict__['compare_slots'] = [p, None, None]
                        ui.navigate.to('/compare')
                    ui.button('Bandingkan ↗', on_click=trigger_compare).props('flat dense size=xs color=primary').classes('text-[8px] font-bold bg-pink-50 px-1.5 py-0.5 rounded-lg')
                    
                    # Tambah ke Planner
                    async def auto_add_to_routine(p=prod):
                        user_email = app.storage.user.get('email')
                        with SessionLocal() as session_write:
                            db_user = RoutineService.get_or_create_user(session_write, user_email)
                            routines = RoutineService.get_user_routines(session_write, db_user.id)
                            r_id = None
                            if not routines:
                                new_r = RoutineService.create_routine(session_write, db_user.id, "AI Recommended Routine", "Dibuat dari Asisten AI")
                                r_id = new_r.id
                            else:
                                r_id = routines[0].id
                                
                            from app.database.models import Produk
                            matched_produk = session_write.query(Produk).filter_by(referensi_id=p['id']).first()
                            if matched_produk:
                                RoutineService.add_item_to_routine(session_write, r_id, product_id=matched_produk.id)
                            else:
                                prod_name = f"{p['brand']} {p['product_name']}".strip()
                                notes = f"IMAGE:{p.get('image_url', '')}"
                                RoutineService.add_item_to_routine(session_write, r_id, custom_name=prod_name, notes=notes)
                        ui.notify(f"{p.get('product_name')} otomatis ditambahkan ke planner!", color='positive')
                        ui.navigate.to('/routine')

                    ui.button('+ Planner', on_click=auto_add_to_routine).props('flat dense size=xs color=positive').classes('text-[8px] font-bold bg-green-50 px-1.5 py-0.5 rounded-lg')
                    
                    # Tambah Paket ke Planner (Menggantikan fungsi Wishlist satuan sesuai permintaan)
                    async def auto_add_package(products_list):
                        if not products_list:
                            return
                        user_email = app.storage.user.get('email')
                        with SessionLocal() as session_write:
                            db_user = RoutineService.get_or_create_user(session_write, user_email)
                            new_r = RoutineService.create_routine(session_write, db_user.id, "Paket Rekomendasi Skintif AI", "Dibuat otomatis dari satu paket rekomendasi")
                            r_id = new_r.id
                            from app.database.models import Produk
                            for p in products_list:
                                matched_produk = session_write.query(Produk).filter_by(referensi_id=p.get('id')).first()
                                if matched_produk:
                                    RoutineService.add_item_to_routine(session_write, r_id, product_id=matched_produk.id)
                                else:
                                    prod_name = f"{p.get('brand', '')} {p.get('product_name', '')}".strip()
                                    notes = f"IMAGE:{p.get('image_url', '')}"
                                    RoutineService.add_item_to_routine(session_write, r_id, custom_name=prod_name, notes=notes)
                        ui.notify(f"{len(products_list)} produk ditambahkan sebagai 1 Paket Planner!", color='positive')
                        ui.navigate.to('/routine')

                    ui.button('Wishlist Paket', icon='library_add', on_click=lambda p_list=all_products or [prod]: auto_add_package(p_list)).props('flat dense size=xs color=pink').classes('text-[8px] font-bold bg-pink-50 px-1.5 py-0.5 rounded-lg flex-shrink-0')

    # Inisialisasi riwayat chat jika masih kosong
    if 'chat_history' not in app.storage.user or not app.storage.user['chat_history']:
        app.storage.user['chat_history'] = [
            {
                'name': 'bot',
                'text': 'Halo! Saya adalah Skintif AI. 🌸\n\nSaya telah membaca profil kulit Anda dari database. Ada keluhan kulit apa hari ini? Atau ingin menganalisis kecocokan produk skincare di Routine Planner Anda?'
            }
        ]

    # 2. Refreshable Status Bar
    @ui.refreshable
    def taskbar_status() -> None:
        analysis = data_mgr.analyze_routine(state.routine, kota=state.kota, skip_weather=True)
        UIComponents.routine_status_badge(analysis)

    # 3. Layout Komponen Navbar & Sidebar
    UIComponents.navbar(status_widget=taskbar_status)
    UIComponents.sidebar()

    # Kontainer Chat Refreshable agar pesan baru langsung muncul
    @ui.refreshable
    def chat_messages_container():
        with ui.column().classes('w-full gap-3 p-4'):
            for msg in app.storage.user['chat_history']:
                # Penanganan loading bubble
                if msg['name'] == 'bot_loading':
                    with ui.column().classes('w-full items-start'):
                        with ui.row().classes('items-start gap-2'):
                            ui.image('/static/profile_ai.png').classes('w-14 h-14 rounded-full shadow-sm object-cover border-2 border-white')
                            with ui.card().classes('p-4 rounded-2xl border border-white/60 bg-white/70 shadow-sm'):
                                ui.html(
                                    '<div class="flex items-center gap-1.5 py-1 px-1">'
                                    '  <span class="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style="animation-delay: 0.1s;"></span>'
                                    '  <span class="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style="animation-delay: 0.2s;"></span>'
                                    '  <span class="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style="animation-delay: 0.3s;"></span>'
                                    '</div>'
                                )
                    continue
                
                is_bot = msg['name'] == 'bot'
                align_class = 'items-start' if is_bot else 'items-end'
                bg_color = 'bg-white/75 backdrop-blur-sm' if is_bot else 'bg-pink-100/90 text-pink-900 shadow-sm'
                avatar_icon = 'smart_toy' if is_bot else 'person'
                avatar_color = 'primary' if is_bot else 'grey-7'
                
                with ui.column().classes(f'w-full {align_class}'):
                    with ui.row().classes('items-start gap-2 max-w-[85%]'):
                        if is_bot:
                            ui.image('/static/profile_ai.png').classes('w-14 h-14 rounded-full shadow-sm object-cover border-2 border-white')
                        
                        with ui.column().classes('gap-2'):
                            with ui.card().classes(f'p-4 rounded-2xl border border-white/60 {bg_color}').style('max-width: 650px;'):
                                ui.markdown(msg['text']).classes('text-sm leading-relaxed')
                            
                            # Render interactive product cards if bot recommended products
                            if is_bot and msg.get('recommended_products'):
                                with ui.row().classes('gap-3 flex-wrap mt-1 justify-start'):
                                    for prod in msg['recommended_products']:
                                        render_recommended_product_card(prod, msg['recommended_products'])
                                        
                            # Render interactive action buttons
                            if is_bot and msg.get('actions'):
                                # Hanya aktifkan tombol jika ini adalah pesan bot terbaru
                                is_latest_msg = (msg == app.storage.user['chat_history'][-1] or 
                                                 msg == app.storage.user['chat_history'][-2])
                                                 
                                with ui.row().classes('gap-2 mt-1 flex-wrap'):
                                    for action_text in msg['actions']:
                                        ui.button(
                                            action_text, 
                                            on_click=lambda a=action_text: kirim_pesan_cepat(a)
                                        ).props(f'rounded outline {"disable" if not is_latest_msg else ""} size=sm').classes(
                                            'text-xs text-pink-500 border-pink-500 bg-white font-bold tracking-wide shadow-sm hover:bg-pink-50'
                                        )
                            
                        if not is_bot:
                            ui.avatar(icon=avatar_icon, color=avatar_color, text_color='white').classes('shadow-sm').props('size=56px')
            
            # Jika chat masih bersih/hanya sambutan, tampilkan Quick Suggestion Chips (ChatGPT-Style)
            if len(app.storage.user['chat_history']) <= 1:
                with ui.column().classes('w-full items-center my-6 gap-3'):
                    ui.label('Pilih panduan cepat jika Anda bingung mulai dari mana:').classes('text-[10px] font-black text-gray-400 uppercase tracking-widest')
                    with ui.grid(columns=2).classes('w-full max-w-2xl gap-3 p-2'):
                        prompts = [
                            ("💰 Punya Budget Rp100k, pilih produk apa?", "Saya memiliki budget maksimal Rp 100.000. Tolong carikan produk skincare terbaik dari database Anda yang harganya di bawah Rp 100.000 dan berikan rekomendasi rutinitasnya!", "Rekomendasi skincare lokal terbaik & murah di bawah Rp100.000."),
                            ("🔴 Kulit Kemerahan & Jerawat, baiknya gimana?", "Kulit wajah saya sedang berjerawat, kemerahan, dan sensitif. Kandungan skincare apa saja yang wajib saya cari di database, dan produk apa yang paling direkomendasikan?", "Solusi & kandungan aktif untuk mengatasi jerawat meradang."),
                            ("✨ Rekomendasi Serum Mencerahkan Kulit Kusam", "Tolong berikan rekomendasi produk serum mencerahkan untuk kulit kusam yang ada di database beserta harganya. Apa bahan aktif utama di dalamnya?", "Saran serum mencerahkan yang aman & cepat memudarkan noda hitam."),
                            ("🛡️ Cara Memperbaiki Skin Barrier yang Rusak", "Skin barrier saya sedang rusak, terasa perih dan sangat kering mengelupas. Apa langkah pertolongan pertama yang harus saya lakukan, dan produk pelembap apa di database yang paling cocok?", "Panduan memulihkan skin barrier yang perih, kering, & mengelupas.")
                        ]
                        for title, text, subtitle in prompts:
                            with ui.card().classes('p-4 border border-white/60 bg-white/40 hover:bg-pink-50/60 cursor-pointer rounded-2xl transition-all hover:scale-[1.02] shadow-sm flex flex-col justify-center min-h-[75px]') \
                                .on('click', lambda t=text: kirim_pesan_cepat(t)):
                                ui.label(title).classes('text-xs font-black text-gray-800')
                                ui.label(subtitle).classes('text-[9px] text-gray-400 font-medium')

    # Fungsi untuk mengirim pesan
    async def kirim_pesan(input_el):
        pesan = input_el.value.strip()
        if not pesan:
            return
        
        # Kosongkan input box secepatnya agar user feel responsive
        input_el.value = ''
        
        # 1. Tambahkan pesan user ke riwayat
        riwayat = app.storage.user['chat_history']
        riwayat.append({'name': 'user', 'text': pesan})
        
        # Tambahkan loading bubble sementara
        riwayat.append({'name': 'bot_loading', 'text': 'typing'})
        
        # Batasi memori: simpan pesan penyambutan pertama (index 0) + 30 pesan terakhir
        if len(riwayat) > 31:
            riwayat = [riwayat[0]] + riwayat[-30:]
            
        app.storage.user['chat_history'] = riwayat
        chat_messages_container.refresh()
        
        # Scroll otomatis ke bagian bawah area chat
        ui.run_javascript('const el = document.getElementById("chat_scroll_area"); if(el) el.scrollTo({top: 999999, behavior: "smooth"});')
        
        # Reload env secara dinamis (sehingga jika pengembang mengganti keys di .env, sistem langsung mendeteksinya secara live!)
        load_dotenv()
        
        provider = os.getenv("API_PROVIDER", "groq").strip().lower()
        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
        groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        
        # Dapatkan context profil pengguna secara dinamis!
        context = get_user_context()
        
        # Jika ada request budget, tambahkan rekomendasi paket asli dari DB ke dalam prompt instruksi AI
        budget_limit = parse_budget_from_text(pesan)
        if budget_limit is not None:
            package = find_skincare_package(budget_limit)
            if package:
                total_price = sum(p["min_price"] for p in package)
                sisa_budget = budget_limit - total_price
                
                # Mengirimkan data kaya (termasuk rating) ke LLM agar output lebih meyakinkan (Evidence-Based Q&A)
                prod_lines = "\n".join([
                    f"- **{p['brand']}** - {p['product_name']} | Kategori: {p['category']} | Harga: Rp{p['min_price']:,.0f} | Rating: ★{p.get('rating_sociolla', 0)} ({p.get('reviews', [])} ulasan)" 
                    for p in package
                ])
                tags = "\n".join([f"[RECOMMEND: {p['brand']} {p['product_name']}]" for p in package])
                
                context += (
                    f"\n\n[PENGGUNA MEMINTA REKOMENDASI BUDGET MAKSIMAL RP {budget_limit:,.0f}]\n"
                    f"Database Skintify telah berhasil meracik 'Paket Skincare Optimal' di bawah budget tersebut. Total harga paket ini adalah Rp {total_price:,.0f} (Sisa budget pengguna: Rp {sisa_budget:,.0f}).\n\n"
                    f"DAFTAR PRODUK TERPILIH:\n{prod_lines}\n\n"
                    f"Tugas Anda (Dokter AI):\n"
                    f"1. Berikan apresiasi pada pengguna karena peduli pada perawatan kulit meski dengan budget terbatas.\n"
                    f"2. Sajikan rincian produk di atas dengan format 'Skincare Financial Plan' (Daftar yang rapi, berikan *bullet points*). Jelaskan secara ringkas fungsi dermatologisnya.\n"
                    f"3. Bangun kepercayaan pengguna dengan menyebutkan Skor Rating produk tersebut, tunjukkan bahwa produk yang direkomendasikan bukan murahan melainkan berkualitas tinggi.\n"
                    f"4. Buktikan secara transparan perhitungan biayanya: (Total Harga vs Budget Pengguna), dan sebutkan sisa saldonya.\n"
                    f"5. SANGAT PENTING: DILARANG KERAS menambah rekomendasi produk skincare lain di luar daftar di atas! Menambahkan produk lain akan merusak kalkulasi budget matematis.\n"
                    f"6. Akhiri respon Anda tepat dengan tag berikut ini agar sistem UI dapat merender kartu visual produk:\n"
                    f"{tags}"
                )
            else:
                context += (
                    f"\n\n[PENGGUNA MEMINTA REKOMENDASI BUDGET MAKSIMAL RP {budget_limit:,.0f}]\n"
                    f"Tugas Anda (Dokter AI):\n"
                    f"Beritahu pengguna dengan sangat sopan bahwa budget Rp {budget_limit:,.0f} saat ini belum cukup untuk meracik satu paket skincare dasar yang aman dan memiliki sertifikasi (BPOM) di database kami. "
                    f"Berikan edukasi medis ringan bahwa investasi minimal untuk kebutuhan dasar (Pembersih Wajah + Sunscreen) setidaknya membutuhkan alokasi sekitar Rp 50.000 hingga Rp 100.000 demi keamanan skin barrier."
                )
        
        prompt_with_context = f"{pesan}\n\n{context}"
        
        # Ambil chat history untuk context-aware AI
        riwayat = app.storage.user.get('chat_history', [])
        
        # 2. Jalankan pemanggilan di thread terpisah agar UI tidak membeku
        if provider == 'gemini' and gemini_api_key:
            loop = asyncio.get_event_loop()
            respon = await loop.run_in_executor(None, query_gemini_api, prompt_with_context, gemini_api_key, gemini_model, riwayat)
        elif provider == 'groq' and groq_api_key:
            loop = asyncio.get_event_loop()
            respon = await loop.run_in_executor(None, query_groq_api, prompt_with_context, groq_api_key, groq_model, riwayat)
        else:
            await asyncio.sleep(1.0) # Efek berpikir sebentar
            respon = get_smart_mock_response(pesan)
        
        # 3. Hapus loading bubble & masukkan respon bot asli
        riwayat = app.storage.user.get('chat_history', [])
        if riwayat and riwayat[-1]['name'] == 'bot_loading':
            riwayat.pop()
            
        # Parse recommendations sisa dari teks respon
        cleaned_respon, recommended_products = parse_ai_recommendations(respon)
        cleaned_respon, actions = parse_ai_actions(cleaned_respon)
        
        riwayat.append({
            'name': 'bot',
            'text': cleaned_respon,
            'recommended_products': recommended_products,
            'actions': actions
        })
        
        # Batasi memori: simpan pesan penyambutan pertama (index 0) + 30 pesan terakhir
        if len(riwayat) > 31:
            riwayat = [riwayat[0]] + riwayat[-30:]
            
        app.storage.user['chat_history'] = riwayat
        chat_messages_container.refresh()
        
        # Scroll ke bawah lagi setelah respon selesai digambar
        ui.run_javascript('const el = document.getElementById("chat_scroll_area"); if(el) el.scrollTo({top: 999999, behavior: "smooth"});')

    # Handler untuk Klik Prompt Instan
    async def kirim_pesan_cepat(text_prompt: str):
        class TempInput:
            def __init__(self, val):
                self.value = val
        temp_input = TempInput(text_prompt)
        await kirim_pesan(temp_input)

    # Fungsi untuk menghapus riwayat obrolan
    def bersihkan_chat():
        app.storage.user['chat_history'] = [
            {
                'name': 'bot',
                'text': 'Riwayat chat telah dibersihkan. 🌸 Ada hal lain yang ingin Anda konsultasikan?'
            }
        ]
        chat_messages_container.refresh()
        ui.notify('Riwayat chat berhasil dibersihkan!', color='info', icon='delete')

    # --- TAMPILAN HALAMAN UTAMA (Zero-Scrollbar & Full-Screen Layout) ---
    with ui.column().classes('w-full p-4 lg:p-6 gap-4 no-wrap').style('max-width: 1280px; margin: 0 auto; height: calc(100vh - 100px); overflow: hidden;'):
        
        # Header Bersih Skintify AI (Premium & Minimalist - Super Compact)
        with ui.row().classes('w-full justify-between items-center bg-white/40 border border-white/60 p-3 px-5 rounded-2xl shadow-sm flex-wrap gap-4 no-wrap'):
            with ui.row().classes('items-center gap-3 no-wrap'):
                ui.image('/static/profile_ai.png').classes('w-14 h-14 rounded-full shadow-sm object-cover border-2 border-white')
                with ui.column().classes('gap-0'):
                    ui.label('SkintifAI').classes('text-lg font-black text-gray-800')
                    ui.label('Konsultasi keluhan kulit secara personal dengan AI Dermatologis cerdas.').classes('text-[10px] text-gray-500 font-medium')
            
            # Tombol Bersihkan Obrolan (Clean & Minimalist)
            ui.button('Bersihkan Obrolan', icon='delete_sweep', on_click=bersihkan_chat).props('outline color=red size=sm').classes('rounded-xl px-3 text-xs font-bold')

        # Tata Letak Dua Kolom: Chat Utama (Kiri/Tengah) & Sidebar Profil (Kanan)
        # set h-full & overflow: hidden agar fit 100% dan tidak memicu scrollbar browser
        with ui.row().classes('w-full gap-4 items-stretch no-wrap flex-grow overflow-hidden'):
            
            # 1. KOLOM UTAMA: Kotak Chat
            with ui.column().classes('flex-grow h-full no-wrap').style('flex: 3; min-width: 320px;'):
                with ui.card().classes('glass-card w-full flex flex-col p-0 overflow-hidden h-full'):
                    # Panel Pesan (Scrollable Area) - Menggunakan flex: 1 & height: 100% agar menempati sisa tinggi secara dinamis
                    with ui.scroll_area().classes('w-full bg-white/10 p-4').style('flex: 1; height: 100%;') as scroll_area:
                        scroll_area.props('id="chat_scroll_area"')
                        
                        chat_messages_container()
                    
                    # Panel Input Bawah & Disclaimer medis kecil di bawah input box
                    ui.separator().classes('opacity-20')
                    with ui.column().classes('w-full p-3 bg-white/40 gap-2 no-wrap'):
                        with ui.row().classes('w-full items-center gap-3 no-wrap'):
                            pesan_input = ui.input(
                                placeholder='Tanyakan sesuatu pada Skintif AI...'
                            ).classes('flex-grow bg-white/80 rounded-xl px-2').props('outlined autofocus')
                            
                            # Kirim jika tekan Enter
                            pesan_input.on('keydown.enter', lambda: kirim_pesan(pesan_input))
                            
                            # Kirim jika klik tombol
                            ui.button(icon='send', on_click=lambda: kirim_pesan(pesan_input)).classes('btn-primary').props('unelevated rounded size=md')
                        
                        # Disclaimer Medis Mini ala ChatGPT
                        ui.label(
                            '⚠️ Disclaimer: AI memberikan saran edukatif kecantikan berdasarkan kecocokan umum bahan aktif skincare dan bukan pengganti diagnosis dokter kulit.'
                        ).classes('text-[9px] text-gray-400 italic text-center w-full leading-tight')
            
            # 2. KOLOM KANAN: Ringkasan Profil Kulit Pengguna (Hidden on Mobile)
            with ui.column().classes('hidden lg:flex w-72 h-full no-wrap'):
                with ui.card().classes('glass-card w-full p-4 flex flex-col gap-3 bg-white/30 backdrop-blur-sm h-full overflow-y-auto'):
                    ui.label('DATABASE PROFIL KULIT').classes('text-[10px] font-black text-gray-500 tracking-widest text-center border-b border-gray-200/50 pb-2 w-full')
                    
                    user_skin = app.storage.user.get('skin_type', 'Belum diisi')
                    avoid_ing = app.storage.user.get('avoid_ingredients', [])
                    skin_issues = app.storage.user.get('skin_issues', [])
                    city = app.storage.user.get('city', 'Jakarta')
                    
                    # Tipe Kulit
                    with ui.row().classes('justify-between w-full items-center'):
                        ui.label('Jenis Kulit').classes('text-[11px] font-bold text-gray-600')
                        ui.badge(user_skin, color='pink-400').classes('text-[8px] font-extrabold uppercase px-2 py-0.5 rounded-full')
                    
                    # Keluhan
                    with ui.column().classes('w-full gap-0.5'):
                        ui.label('Keluhan Kulit').classes('text-[11px] font-bold text-gray-600')
                        if skin_issues:
                            with ui.row().classes('gap-1 flex-wrap'):
                                for issue in skin_issues:
                                    ui.badge(issue, color='blue-300').classes('text-[8px] font-bold px-2 py-0.5 rounded-full')
                        else:
                            ui.label('Tidak ada').classes('text-[11px] text-gray-400 italic')
                    
                    # Dihindari
                    with ui.column().classes('w-full gap-0.5'):
                        ui.label('Bahan Dihindari').classes('text-[11px] font-bold text-gray-600')
                        if avoid_ing:
                            with ui.row().classes('gap-1 flex-wrap'):
                                for ing in avoid_ing:
                                    ui.badge(ing, color='red-300').classes('text-[8px] font-bold px-2 py-0.5 rounded-full')
                        else:
                            ui.label('Tidak ada').classes('text-[11px] text-gray-400 italic')
                    
                    # Lokasi Kota
                    with ui.row().classes('justify-between w-full items-center'):
                        ui.label('Lokasi Cuaca').classes('text-[11px] font-bold text-gray-600')
                        ui.label(city).classes('text-[11px] font-black text-gray-700')
                        
                    ui.separator().classes('my-1 opacity-50')
                    
                    # Daftar Rutinitas
                    ui.label('RUTINITAS SAAT INI').classes('text-[10px] font-black text-gray-500 tracking-widest text-center border-b border-gray-200/50 pb-2 w-full')
                    if state.routine:
                        with ui.column().classes('w-full gap-0.5 max-h-24 overflow-y-auto'):
                            for p in state.routine:
                                brand = p.get('brand', 'Unknown')
                                name = p.get('product_name', 'Unnamed')
                                ui.label(f"• {brand} {name}").classes('text-[9px] text-gray-600 line-clamp-1')
                    else:
                        ui.label('Routine Planner Kosong').classes('text-[9px] text-gray-400 italic text-center w-full')
                        
                    # Tombol pintas edit profil kulit
                    ui.button('Edit Profil Kulit', on_click=lambda: (app.storage.user.__setitem__('onboarding_mode', 'edit'), ui.navigate.to('/onboarding')))\
                        .props('flat dense size=xs color=primary').classes('w-full font-bold text-[9px] mt-1')

    # Auto-trigger query from other pages
    initial_query = app.storage.user.pop('ai_initial_query', None)
    if initial_query:
        async def trigger_initial():
            class TempInput:
                def __init__(self, val):
                    self.value = val
            temp_input = TempInput(initial_query)
            await kirim_pesan(temp_input)
        ui.timer(0.1, trigger_initial, once=True)
        
    print(f"[TRACE-BOTTLENECK] {time.time()} - ai_chat_page: show_page ENDED")
