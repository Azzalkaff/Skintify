import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from .core.tokopedia import TokopediaScraper
from .core.lazada import LazadaScraper
from .core.shopee import ShopeeScraper
from .core.config import OUTPUT_DIR, SLEEP_RANGE

class ScraperManager:
    def __init__(self):
        self.scrapers = [
            TokopediaScraper(),
            LazadaScraper(),
            ShopeeScraper()
        ]
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_batch(self, keywords: List[str], top_n: int = 5) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = self.output_dir / f"scrape_{timestamp}.json"

        results_agg = {
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "total_keywords": len(keywords),
                "status": "running"
            },
            "data": []
        }

        for i, kw in enumerate(keywords):
            entry = {"keyword": kw, "marketplaces": {}}
            
            for s in self.scrapers:
                try:
                    prods, shops = s.scrape(kw, top_n=top_n)
                    entry["marketplaces"][s.name.lower()] = {"products": prods, "shops": shops}
                except Exception as exc:
                    print(f"   [!] Gagal scraping '{kw}' [{s.name}]: {exc}")
                    entry["marketplaces"][s.name.lower()] = {"products": [], "shops": []}
                s.random_sleep(*SLEEP_RANGE)
            
            tokped_cnt = len(entry['marketplaces'].get('tokopedia', {}).get('products', []))
            lazada_cnt = len(entry['marketplaces'].get('lazada', {}).get('products', []))
            shopee_cnt = len(entry['marketplaces'].get('shopee', {}).get('products', []))
            print(f"   [OK] Selesai: '{kw}' ({tokped_cnt} Tokped, {lazada_cnt} Lazada, {shopee_cnt} Shopee)")
            print("-" * 30)
            
            results_agg["data"].append(entry)
            
            # Checkpoint every 5
            if (i + 1) % 5 == 0:
                self._save(results_agg, filepath)
                print(f"   [Checkpoint] Saved {i+1}/{len(keywords)} to {filepath.name}")

        results_agg["metadata"]["status"] = "completed"
        results_agg["metadata"]["end_time"] = datetime.now().isoformat()
        self._save(results_agg, filepath)
        
        return filepath

    def _save(self, data: dict, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
