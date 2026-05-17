import requests
from urllib.parse import quote
from typing import List, Dict, Any, Tuple
from .base import BaseScraper
from .config import TOKOPEDIA_ENDPOINT, TOKOPEDIA_GQL_QUERY, get_tokopedia_headers, get_tokopedia_cookies

class TokopediaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Tokopedia")

    def scrape(self, keyword: str, top_n: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        print(f"[{self.name}] Processing: '{keyword}'")
        try:
            raw = self._fetch(keyword)
            products, shops = self._parse(raw)
            
            top_shop_ids = {s["shop_id"] for s in shops[:top_n]}
            filtered_products = [p for p in products if p["shop_id"] in top_shop_ids]
            
            # Detil Data untuk Transparansi (Anti-Blackbox)
            if filtered_products:
                print(f"   --- Data {self.name} yang Diambil (Sample) ---")
                for p in filtered_products[:3]: # Tampilkan 3 saja
                    print(f"   * {p['name'][:60]}...")
                    print(f"      Harga: Rp{p['price']:,} | Rating: {p['rating']} | Shop: {p['shop_id']}")
            else:
                print(f"   ⚠️ Tidak ada produk {self.name} yang sesuai kriteria.")

            return filtered_products, shops[:top_n]
        except Exception as e:
            print(f"   [!] {self.name} Error: {e}")
            return [], []

    def _fetch(self, keyword: str) -> Any:
        params = f"device=mobile&ob=23&q={quote(keyword)}&rows=40&source=search"
        payload = [{
            "operationName": "SearchProductV5Query",
            "variables": {"searchProductV5Param": params},
            "query": TOKOPEDIA_GQL_QUERY
        }]
        resp = requests.post(
            TOKOPEDIA_ENDPOINT,
            json=payload,
            headers=get_tokopedia_headers(),
            cookies=get_tokopedia_cookies(),
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    def _parse(self, raw_response: list) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        if not raw_response or "data" not in raw_response[0]:
            return [], []
            
        data = raw_response[0]["data"]["searchProductV5"]["data"]
        raw_products = data.get("products", [])

        shops_map = {}
        products_list = []

        for p in raw_products:
            shop = p.get("shop") or {}
            shop_id = str(shop.get("id", ""))
            
            if shop_id and shop_id not in shops_map:
                shops_map[shop_id] = {
                    "shop_id": shop_id,
                    "name": shop.get("name", ""),
                    "city": shop.get("city", ""),
                    "tier": shop.get("tier", 0),
                    "url": shop.get("url", ""),
                }

            price_info = p.get("price") or {}
            media = p.get("mediaURL") or {}

            products_list.append({
                "source": "tokopedia",
                "product_id": str(p.get("id", "")),
                "name": p.get("name", ""),
                "url": p.get("url", ""),
                "image": media.get("image300") or media.get("image", ""),
                "price": self._clean_price(price_info.get("number") or 0),
                "price_original": self._clean_price(price_info.get("original") or 0),
                "discount": int(price_info.get("discountPercentage") or 0),
                "rating": float(p.get("rating") or 0),
                "sold": self._parse_sold(p.get("labelGroups") or []),
                "shop_id": shop_id,
            })

        return products_list, list(shops_map.values())

    def _parse_sold(self, labels: list) -> int:
        if not labels:
            return 0
        sold_text = ""
        for lb in labels:
            title = lb.get("title", "").lower()
            if "terjual" in title or "sold" in title:
                sold_text = title
                break
        if not sold_text:
            return 0
        cleaned = sold_text.replace("terjual", "").replace("sold", "").replace("+", "").replace(",", ".").strip()
        multiplier = 1
        if "rb" in cleaned or "k" in cleaned:
            multiplier = 1000
            cleaned = cleaned.replace("rb", "").replace("k", "")
        elif "jt" in cleaned or "m" in cleaned:
            multiplier = 1000000
            cleaned = cleaned.replace("jt", "").replace("m", "")
        try:
            import re
            match = re.search(r"(\d+\.?\d*)", cleaned)
            if match:
                return int(float(match.group(1)) * multiplier)
            return 0
        except:
            return 0

    def _clean_price(self, val: Any) -> float:
        if isinstance(val, (int, float)):
            return float(val)
        if not val:
            return 0.0
        try:
            # Handle "Rp632.000" or "632.000"
            s = str(val).replace("Rp", "").replace(".", "").replace(",", "").strip()
            return float(s)
        except:
            return 0.0
