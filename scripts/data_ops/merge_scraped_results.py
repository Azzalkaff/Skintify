import json
import os
import sys
from pathlib import Path
from datetime import datetime

def merge_json_files(input_dir: Path, output_file: Path):
    if not input_dir.exists():
        print(f"[Error] Direktori {input_dir} tidak ditemukan.")
        return

    json_files = list(input_dir.glob("scrape_*.json"))
    if not json_files:
        print(f"[Info] Tidak ada file scrape_*.json untuk digabungkan di {input_dir}.")
        return

    print(f"[Info] Ditemukan {len(json_files)} file. Memulai penggabungan...")

    merged_data = []
    total_keywords = 0
    
    # Sort files by name (usually timestamped)
    json_files.sort()

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                data_list = content.get("data", [])
                merged_data.extend(data_list)
                total_keywords += len(data_list)
                print(f"   [+] {file_path.name}: {len(data_list)} item ditambahkan.")
        except Exception as e:
            print(f"   [!] Gagal membaca {file_path.name}: {e}")

    # Final structure
    result = {
        "metadata": {
            "merged_at": datetime.now().isoformat(),
            "source_files_count": len(json_files),
            "total_items": len(merged_data),
            "description": "Hasil penggabungan dari semua file scraping marketplace"
        },
        "data": merged_data
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n[Selesai] {len(merged_data)} item berhasil digabung ke: {output_file}")
    except Exception as e:
        print(f"\n[Error] Gagal menyimpan file gabungan: {e}")

def main():
    # Fix Pathing (three parents needed because we are in scripts/data_ops/)
    BASE_DIR = Path(__file__).parent.parent.parent.absolute()
    SCRAPED_DIR = BASE_DIR / "data" / "scraped_results"
    OUTPUT_FILE = BASE_DIR / "data" / "merged_scraped_results.json"

    print("\n" + "="*40)
    print("   SKINTIFY DATA MERGER (MARKETPLACE)")
    print("="*40)
    
    merge_json_files(SCRAPED_DIR, OUTPUT_FILE)

if __name__ == "__main__":
    main()
