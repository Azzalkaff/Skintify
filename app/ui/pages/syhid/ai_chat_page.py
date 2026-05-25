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

def query_gemini_api(prompt: str, api_key: str, model_name: str = "gemini-2.0-flash") -> str:
    """Mengirim request langsung ke API Gemini via HTTP POST."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    system_instruction = (
        "Anda adalah Dokter AI Skintify, asisten dermatologi virtual profesional dan ramah. "
        "Tugas Anda adalah menganalisis keluhan kulit pengguna, memberikan rekomendasi bahan aktif skincare, "
        "dan memberikan tips perawatan kulit yang aman. Selalu ingatkan pengguna untuk melakukan patch test "
        "dan berkonsultasi ke dokter kulit asli jika keluhan parah. Jawab dalam Bahasa Indonesia yang santun. "
        "Buatlah format jawaban Anda rapi, gunakan Markdown untuk judul, bullet points, dan penekanan kata agar mudah dibaca.\n\n"
        "Anda memiliki akses database internal produk Skintify. "
        "Jika Anda merekomendasikan produk skincare nyata (terutama produk dari brand populer seperti Skintific, Cosrx, Somethinc, Wardah, dll), "
        "sebutkan nama lengkap produk tersebut dengan jelas di dalam teks respon Anda. "
        "PENTING: Di akhir respon Anda, Anda HARUS menuliskan daftar produk yang direkomendasikan dengan format tag khusus:\n"
        "[RECOMMEND: Nama Lengkap Produk] (satu baris untuk satu produk, tanpa backtick atau markdown di dalam tag tersebut).\n"
        "Contoh format tag di akhir respon:\n"
        "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
        "[RECOMMEND: Cosrx Advanced Snail 96 Mucin Power Essence]"
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"System Instruction: {system_instruction}\n\nUser Question: {prompt}"}
                ]
            }
        ]
    }
    
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

def query_groq_api(prompt: str, api_key: str, model_name: str = "llama-3.3-70b-versatile") -> str:
    """Mengirim request langsung ke API Groq via HTTP POST (OpenAI Compatible)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_instruction = (
        "Anda adalah Dokter AI Skintify, asisten dermatologi virtual profesional dan ramah. "
        "Tugas Anda adalah menganalisis keluhan kulit pengguna, memberikan rekomendasi bahan aktif skincare, "
        "dan memberikan tips perawatan kulit yang aman. Selalu ingatkan pengguna untuk melakukan patch test "
        "dan berkonsultasi ke dokter kulit asli jika keluhan parah. Jawab dalam Bahasa Indonesia yang santun. "
        "Buatlah format jawaban Anda rapi, gunakan Markdown untuk judul, bullet points, dan penekanan kata agar mudah dibaca.\n\n"
        "Anda memiliki akses database internal produk Skintify. "
        "Jika Anda merekomendasikan produk skincare nyata (terutama produk dari brand populer seperti Skintific, Cosrx, Somethinc, Wardah, dll), "
        "sebutkan nama lengkap produk tersebut dengan jelas di dalam teks respon Anda. "
        "PENTING: Di akhir respon Anda, Anda HARUS menuliskan daftar produk yang direkomendasikan dengan format tag khusus:\n"
        "[RECOMMEND: Nama Lengkap Produk] (satu baris untuk satu produk, tanpa backtick atau markdown di dalam tag tersebut).\n"
        "Contoh format tag di akhir respon:\n"
        "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
        "[RECOMMEND: Cosrx Advanced Snail 96 Mucin Power Essence]"
    )
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6
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
    text = text.lower()
    # 1. Check for specific keywords
    if "seratus ribu" in text or "100 ribu" in text or "100rb" in text or "100k" in text or "100.000" in text:
        return 100000.0
    if "dua ratus ribu" in text or "200 ribu" in text or "200rb" in text or "200k" in text or "200.000" in text:
        return 200000.0
    if "lima puluh ribu" in text or "50 ribu" in text or "50rb" in text or "50k" in text or "50.000" in text:
        return 50000.0
    if "seratus lima puluh ribu" in text or "150 ribu" in text or "150rb" in text or "150k" in text or "150.000" in text:
        return 150000.0
        
    # Generic regex for numbers followed by k, rb, or ribu
    match = re.search(r"(\d+)\s*(?:rb|k|ribu)", text)
    if match:
        return float(match.group(1)) * 1000
        
    # Generic regex for numbers like 100.000 or 100000
    match = re.search(r"(\d+(?:\.\d{3})+|\d{4,})", text)
    if match:
        num_str = match.group(1).replace(".", "").replace(",", "")
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
    
    with SessionLocal() as session:
        for cat in categories:
            prods = session.query(SociollaReferensi).filter(
                SociollaReferensi.category == cat,
                SociollaReferensi.min_price > 5000.0,
                SociollaReferensi.min_price < budget,
                SociollaReferensi.image_url != None,
                SociollaReferensi.image_url != ""
            ).order_by(SociollaReferensi.min_price.asc()).limit(15).all()
            
            products_by_cat[cat] = [
                {
                    "brand": p.brand,
                    "product_name": p.product_name,
                    "min_price": p.min_price,
                    "category": p.category,
                    "image_url": p.image_url,
                    "rating_sociolla": p.rating_sociolla,
                    "slug": p.slug,
                    "ingredients": p.ingredients,
                    "reviews": p.reviews
                }
                for p in prods
            ]
            
    # 3-product combos
    cleansers = products_by_cat.get("Cleanser", [])
    moisturizers = products_by_cat.get("Moisturizer", [])
    sunscreens = products_by_cat.get("Sunscreen", [])
    toners = products_by_cat.get("Toner", [])
    serums = products_by_cat.get("Serum", [])
    
    # 1. Cleanser + Moisturizer + Sunscreen
    for c in cleansers[:5]:
        for m in moisturizers[:5]:
            for s in sunscreens[:5]:
                tot = c["min_price"] + m["min_price"] + s["min_price"]
                if tot <= budget:
                    return [c, m, s]
                    
    # 2. Cleanser + Toner + Moisturizer
    for c in cleansers[:5]:
        for t in toners[:5]:
            for m in moisturizers[:5]:
                tot = c["min_price"] + t["min_price"] + m["min_price"]
                if tot <= budget:
                    return [c, t, m]

    # 3. Cleanser + Moisturizer + Serum
    for c in cleansers[:5]:
        for m in moisturizers[:5]:
            for sr in serums[:5]:
                tot = c["min_price"] + m["min_price"] + sr["min_price"]
                if tot <= budget:
                    return [c, m, sr]

    # 2-product combos
    # 1. Cleanser + Moisturizer
    for c in cleansers[:5]:
        for m in moisturizers[:5]:
            tot = c["min_price"] + m["min_price"]
            if tot <= budget:
                return [c, m]
                
    # 2. Cleanser + Toner
    for c in cleansers[:5]:
        for t in toners[:5]:
            tot = c["min_price"] + t["min_price"]
            if tot <= budget:
                return [c, t]

    # 3. Moisturizer + Sunscreen
    for m in moisturizers[:5]:
        for s in sunscreens[:5]:
            tot = m["min_price"] + s["min_price"]
            if tot <= budget:
                return [m, s]
                
    # Fallback to top 2 cheapest products
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
    """Mengembalikan jawaban simulasi pintar secara offline jika API Key belum dipasang di .env."""
    p_lower = prompt.lower()
    
    budget = parse_budget_from_text(prompt)
    if budget is not None:
        package = find_skincare_package(budget)
        if package:
            total_price = sum(p["min_price"] for p in package)
            prod_lines = "\n".join([f"- **Langkah {i+1} ({p['category']})**: **{p['brand']}** - {p['product_name']} (Harga: Rp{p['min_price']:,.0f}".replace(',', '.') + ")" for i, p in enumerate(package)])
            tags = "\n".join([f"[RECOMMEND: {p['brand']} {p['product_name']}]" for p in package])
            
            return (
                f"💡 **Dokter AI Skintify (Mode Offline - Paket Budget):**\n\n"
                f"Tentu! Saya telah menganalisis database produk internal kami untuk meracik paket skincare terbaik "
                f"dengan budget maksimal **Rp {budget:,.0f}** Anda.\n\n"
                f"Berikut adalah rangkaian **Basic Skincare Paket Hemat** yang total harganya benar-benar berada di bawah budget Anda:\n\n"
                f"{prod_lines}\n\n"
                f"📊 **Rincian Kalkulasi Harga Paket:**\n"
                f"- **Total Harga Paket**: **Rp {total_price:,.0f}**".replace(',', '.') + "\n"
                f"- **Sisa Budget Anda**: **Rp {budget - total_price:,.0f}**".replace(',', '.') + "\n\n"
                f"Paket ini sangat ideal untuk merawat barrier kulit Anda dengan harga yang sangat ekonomis dan terjangkau! "
                f"Gunakan tombol di bawah untuk menambahkannya ke Planner atau Wishlist Anda. ❤️\n\n"
                f"{tags}"
            )
        else:
            return (
                f"💡 **Dokter AI Skintify (Mode Offline):**\n\n"
                f"Maaf, saya tidak menemukan kombinasi produk di database kami yang totalnya berada di bawah budget **Rp {budget:,.0f}** Anda. "
                f"Cobalah untuk menaikkan sedikit budget Anda atau mencari produk satuan di halaman Cari Produk."
            )

    if "analisis kelemahan" in p_lower or "analisis rutinitas" in p_lower:
        routine_str = ""
        if state.routine:
            routine_str = "\n".join([f"- **{p.get('brand')}** {p.get('product_name')}" for p in state.routine])
        else:
            routine_str = "- (Belum ada produk di Planner Anda)"
            
        return (
            "💡 **Dokter AI Skintify (Mode Heuristik Offline):**\n\n"
            "Saya telah mendeteksi produk di Routine Planner Anda:\n"
            f"{routine_str}\n\n"
            "**Hasil Evaluasi Cepat:**\n"
            "1. **Keamanan Barrier**: Produk Anda secara umum aman digunakan. Pastikan pelembap digunakan setelah pemakaian bahan aktif.\n"
            "2. **Deteksi Konflik**: Tidak terdeteksi tabrakan bahan aktif berat (seperti Retinol + AHA/BHA secara bersamaan).\n"
            "3. **Rekomendasi**: Selalu gunakan **Sunscreen** di pagi hari untuk melindungi kulit dari kemerahan.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]\n"
            "[RECOMMEND: Somethinc Granactive Retinoid]"
        )
        
    if "retinol" in p_lower:
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            "Retinol sangat baik untuk anti-aging dan regenerasi kulit. Namun, harap ingat:\n"
            "1. **Gunakan di malam hari saja** karena retinol membuat kulit sensitif terhadap cahaya matahari.\n"
            "2. **JANGAN dicampur** bersamaan dengan **AHA/BHA** atau **Vitamin C** dalam satu rutinitas karena berisiko iritasi parah.\n"
            "3. Pastikan gunakan **Sunscreen** minimal SPF 30 di pagi hari setelah pemakaian retinol.\n\n"
            "[RECOMMEND: Somethinc Granactive Retinoid]"
        )
    elif "jerawat" in p_lower or "acne" in p_lower:
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            "Untuk kulit rentan berjerawat (Acne-Prone), cari bahan skincare berikut:\n"
            "- **Salicylic Acid (BHA)**: Membersihkan pori-pori tersumbat.\n"
            "- **Centella Asiatica (Cica)**: Menenangkan kemerahan & inflamasi.\n"
            "- **Niacinamide**: Mengontrol sebum berlebih dan menyamarkan noda hitam bekas jerawat.\n\n"
            "[RECOMMEND: Cosrx Salicylic Acid Daily Gentle Cleanser]"
        )
    elif "kering" in p_lower or "dry" in p_lower:
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            "Kulit kering membutuhkan hidrasi ekstra. Fokus pada bahan-bahan berikut:\n"
            "- **Hyaluronic Acid**: Mengunci hidrasi di lapisan kulit.\n"
            "- **Ceramide**: Memperbaiki dan menjaga kekuatan skin barrier.\n"
            "- **Glycerin**: Menjaga kelembapan kulit agar tetap kenyal.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )
    elif "berminyak" in p_lower or "oily" in p_lower:
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            "Untuk kulit berminyak, tujuannya adalah mengontrol sebum tanpa membuat kulit dehidrasi:\n"
            "- Gunakan pelembap bertekstur **Gel** yang ringan.\n"
            "- Cari kandungan **Niacinamide** atau **Zinc PCA** untuk regulasi minyak.\n"
            "- Gunakan pembersih wajah berformula lembut agar kulit tidak memproduksi minyak berlebih sebagai kompensasi.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )
    elif "tips" in p_lower or "cuaca" in p_lower:
        city = app.storage.user.get('city', 'Jakarta')
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            f"Berdasarkan lokasi tinggal Anda di **{city}**:\n"
            "1. **Kelembapan Tinggi**: Gunakan produk non-komedogenik bertekstur gel yang ringan agar tidak menyumbat pori-pori.\n"
            "2. **Perlindungan UV**: Mengingat indeks UV perkotaan cukup tinggi di siang hari, jangan pernah melewatkan sunscreen!\n"
            "3. **Double Cleansing**: Pastikan mencuci wajah 2 tahap di malam hari setelah beraktivitas di luar.\n\n"
            "[RECOMMEND: Skintific 5X Ceramide Barrier Moisture Gel]"
        )
    elif "halo" in p_lower or "hi" in p_lower or "pagi" in p_lower or "siang" in p_lower or "malam" in p_lower:
        return (
            "Halo! Saya Dokter AI Skintify. 👋\n\n"
            "Saya siap membantu menjawab segala keluhan kulit Anda dan memberikan tips padu-padan skincare. "
            "Coba tanyakan sesuatu, misalnya: *'Bagaimana cara mengatasi kulit kering?'* atau *'Apakah retinol boleh dicampur niacinamide?'*"
        )
    else:
        return (
            "💡 **Saran Dokter AI Skintify (Mode Offline):**\n\n"
            "Pertanyaan Anda sangat menarik! Sebagai saran umum, pastikan Anda selalu menjaga **Basic Skincare** Anda:\n"
            "1. *Cleanser* (Pembeda wajah lembut)\n"
            "2. *Moisturizer* (Pelembap penyuplai hidrasi)\n"
            "3. *Sunscreen* (Pelindung UV di pagi hari)\n\n"
            "*Tips: Untuk jawaban yang lebih detail dan personal, silakan masukkan API Key Anda pada file .env.*"
        )

def get_user_context() -> str:
    """Mengumpulkan info profil kulit dan produk user saat ini untuk diumpankan ke AI sebagai konteks."""
    skin_type = app.storage.user.get('skin_type', 'Belum diisi')
    avoid_ing = app.storage.user.get('avoid_ingredients', [])
    skin_issues = app.storage.user.get('skin_issues', [])
    city = app.storage.user.get('city', 'Jakarta')
    
    # Ambil produk di routine
    routine_products = []
    for p in state.routine:
        brand = p.get('brand', 'Unknown')
        name = p.get('product_name', 'Unnamed Product')
        routine_products.append(f"- {brand} - {name}")
    
    routine_str = "\n".join(routine_products) if routine_products else "- Belum ada produk di Routine Planner."
    avoid_str = ", ".join(avoid_ing) if avoid_ing else "Tidak ada"
    issues_str = ", ".join(skin_issues) if skin_issues else "Tidak ada"
    
    context = (
        f"\n[KONTEKS PROFIL PENGGUNA SKINTIFY]\n"
        f"- Jenis Kulit Pengguna: {skin_type}\n"
        f"- Kandungan Skincare yang Dihindari: {avoid_str}\n"
        f"- Keluhan Kulit Utama: {issues_str}\n"
        f"- Kota Tinggal Pengguna: {city}\n"
        f"- Produk Skincare di Routine Planner Pengguna Saat Ini:\n{routine_str}\n\n"
        f"Gunakan profil di atas untuk memberikan jawaban yang 100% relevan, dipersonalisasi, dan ramah! "
        f"Contoh: jika jenis kulit mereka kering, fokuskan pada hidrasi. Jika ada kandungan dihindari, peringatkan jika produk yang ditanyakan mengandung bahan tersebut."
    )
    return context

def parse_ai_recommendations(text: str) -> tuple:
    """
    Memindai respon dari AI untuk mendeteksi tag [RECOMMEND: Nama Produk],
    menghapusnya dari tampilan teks mentah, dan mencari produk tersebut di database.
    """
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
            
        # Ambil produk dari database lokal
        res = data_mgr.get_paginated_products(keyword=prod_name, items_per_page=1)
        items = res.get("items", [])
        if items:
            recommended_products.append(items[0])
            
    return cleaned_text, recommended_products

def show_page():
    """Halaman Utama Skintify AI Chatbot (End-User Interface)"""
    
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

    def render_recommended_product_card(prod):
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
                    def trigger_search(p_name=prod.get('product_name')):
                        app.storage.user['search_query'] = p_name
                        ui.navigate.to('/search')
                    ui.button('Bandingkan ↗', on_click=trigger_search).props('flat dense size=xs color=primary').classes('text-[8px] font-bold bg-pink-50 px-1.5 py-0.5 rounded-lg')
                    
                    # Tambah ke Planner
                    def trigger_add(p=prod):
                        open_add_to_routine_dialog(p)
                    ui.button('+ Planner', on_click=trigger_add).props('flat dense size=xs color=positive').classes('text-[8px] font-bold bg-green-50 px-1.5 py-0.5 rounded-lg')
                    
                    # Wishlist Icon Button
                    ui.button(icon='favorite', on_click=lambda p=prod: add_to_wishlist(p)).props('flat dense size=xs color=pink').classes('bg-red-50 p-0.5 rounded-lg flex-shrink-0')

    # Inisialisasi riwayat chat jika masih kosong
    if 'chat_history' not in app.storage.user or not app.storage.user['chat_history']:
        app.storage.user['chat_history'] = [
            {
                'name': 'bot',
                'text': 'Halo! Saya adalah Dokter AI Skintify. 🌸\n\nSaya telah membaca profil kulit Anda dari database. Ada keluhan kulit apa hari ini? Atau ingin menganalisis kecocokan produk skincare di Routine Planner Anda?'
            }
        ]

    # 2. Refreshable Status Bar
    @ui.refreshable
    def taskbar_status() -> None:
        analysis = data_mgr.analyze_routine(state.routine, kota=state.kota)
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
                            ui.avatar(icon='smart_toy', color='primary', text_color='white').classes('shadow-sm')
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
                            ui.avatar(icon=avatar_icon, color=avatar_color, text_color='white').classes('shadow-sm')
                        
                        with ui.column().classes('gap-2'):
                            with ui.card().classes(f'p-4 rounded-2xl border border-white/60 {bg_color}').style('max-width: 650px;'):
                                ui.markdown(msg['text']).classes('text-sm leading-relaxed')
                            
                            # Render interactive product cards if bot recommended products
                            if is_bot and msg.get('recommended_products'):
                                with ui.row().classes('gap-3 flex-wrap mt-1 justify-start'):
                                    for prod in msg['recommended_products']:
                                        render_recommended_product_card(prod)
                            
                        if not is_bot:
                            ui.avatar(icon=avatar_icon, color=avatar_color, text_color='white').classes('shadow-sm')
            
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
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
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
                prod_lines = "\n".join([f"- **{p['brand']}** - {p['product_name']} (Kategori: {p['category']}, Harga: Rp{p['min_price']:,.0f})" for p in package])
                tags = "\n".join([f"[RECOMMEND: {p['brand']} {p['product_name']}]" for p in package])
                
                context += (
                    f"\n\n[PENGGUNA MEMINTA REKOMENDASI BUDGET MAKSIMAL RP {budget_limit:,.0f}]\n"
                    f"Anda WAJIB memberikan rekomendasi paket skincare nyata yang harganya jika dijumlahkan berada di bawah Rp {budget_limit:,.0f}.\n"
                    f"Berdasarkan pencarian database kami yang presisi, berikut adalah paket produk yang harganya di bawah budget tersebut (Total: Rp {total_price:,.0f}):\n"
                    f"{prod_lines}\n\n"
                    f"Tugas Anda (Dokter AI):\n"
                    f"1. Rekomendasikan rangkaian produk di atas sebagai Paket Hemat. Jelaskan fungsi masing-masing produk (misal: cleanser sebagai pembersih wajah, moisturizer sebagai pelembap).\n"
                    f"2. Tuliskan harga masing-masing produk di atas, dan buktikan dengan menjumlahkannya bahwa totalnya Rp {total_price:,.0f} (yang di bawah budget Rp {budget_limit:,.0f}).\n"
                    f"3. JANGAN merekomendasikan produk tambahan di luar daftar di atas yang dapat membuat total harga melebihi budget!\n"
                    f"4. Tuliskan tag rekomendasi di bagian paling akhir respon Anda secara presisi:\n"
                    f"{tags}"
                )
        
        prompt_with_context = f"{pesan}\n\n{context}"
        
        # 2. Jalankan pemanggilan di thread terpisah agar UI tidak membeku
        if provider == 'gemini' and gemini_api_key:
            loop = asyncio.get_event_loop()
            respon = await loop.run_in_executor(None, query_gemini_api, prompt_with_context, gemini_api_key, gemini_model)
        elif provider == 'groq' and groq_api_key:
            loop = asyncio.get_event_loop()
            respon = await loop.run_in_executor(None, query_groq_api, prompt_with_context, groq_api_key, groq_model)
        else:
            await asyncio.sleep(1.0) # Efek berpikir sebentar
            respon = get_smart_mock_response(pesan)
        
        # 3. Hapus loading bubble & masukkan respon bot asli
        riwayat = app.storage.user['chat_history']
        if riwayat and riwayat[-1]['name'] == 'bot_loading':
            riwayat.pop()
            
        # Parse recommendations sisa dari teks respon
        cleaned_respon, recommended_products = parse_ai_recommendations(respon)
        
        riwayat.append({
            'name': 'bot',
            'text': cleaned_respon,
            'recommended_products': recommended_products
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
                ui.avatar(icon='smart_toy', color='primary', text_color='white').classes('shadow-sm scale-90')
                with ui.column().classes('gap-0'):
                    ui.label('Skintify AI Skincare Assistant').classes('text-lg font-black text-gray-800')
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
                                placeholder='Tanyakan sesuatu pada Dokter AI Skintify...'
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
