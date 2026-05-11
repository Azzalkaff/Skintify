import json
from pathlib import Path
from typing import List
from .config import SOCIOLLA_FILES

class KeywordService:
    @staticmethod
    def get_keywords_from_sociolla() -> List[str]:
        """Extract keywords from available Sociolla JSON files."""
        filepath = None
        for p in SOCIOLLA_FILES:
            if p.exists():
                filepath = p
                break
        
        if not filepath:
            return []
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            products = data.get("products", [])
            keywords = []
            for p in products:
                brand = p.get("brand", "")
                name = p.get("product_name", "")
                keyword = f"{brand} {name}".strip()
                if keyword:
                    keywords.append(keyword)
            return keywords
        except Exception as e:
            print(f"[!] Error loading Sociolla file: {e}")
            return []
