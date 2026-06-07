import requests
from typing import List, Dict, Any, Tuple
from .base import BaseScraper
from .config import LAZADA_ENDPOINT, get_lazada_headers, get_lazada_cookies

class LazadaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Lazada")

    def scrape(self, keyword: str, top_n: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        print(f"[{self.name}] Processing: '{keyword}'")
        try:
            raw = self._fetch(keyword)
            products, shops = self._parse(raw)

            # Hitung total penjualan per toko dari semua produknya
            from collections import defaultdict
            toko_total_terjual: dict = defaultdict(int)
            for p in products:
                if not p.get("is_sponsored"):
                    toko_total_terjual[p["shop_id"]] += p.get("terjual", 0) or 0

            # Rank toko berdasarkan total terjual (bukan urutan kemunculan)
            shops_ranked = sorted(
                shops,
                key=lambda s: toko_total_terjual.get(s["shop_id"], 0),
                reverse=True
            )
            top_shop_ids = {s["shop_id"] for s in shops_ranked[:top_n]}
            filtered_products = [p for p in products if p["shop_id"] in top_shop_ids and not p.get("is_sponsored")]
            top_shops = shops_ranked[:top_n]

            # Detil Data untuk Transparansi (Anti-Blackbox)
            if filtered_products:
                print(f"   --- Data {self.name} yang Diambil (Sample) ---")
                for p in filtered_products[:3]:
                    print(f"   * {p['name'][:60]}...")
                    print(f"      Harga: Rp{p['price']:,} | Rating: {p['rating']} | Terjual: {p.get('terjual',0)} | Seller: {p['shop_id']}")
            else:
                print(f"   ⚠️ Tidak ada produk {self.name} yang sesuai kriteria (Sponsored dibuang).")

            return filtered_products, top_shops
        except Exception as e:
            print(f"   [!] {self.name} Error: {e}")
            return [], []

    def _fetch(self, keyword: str) -> Any:
        params = {"ajax": "true", "isFirstRequest": "true", "page": "1", "q": keyword, "sort": "sales"}
        resp = requests.get(
            LAZADA_ENDPOINT,
            params=params,
            headers=get_lazada_headers(),
            cookies=get_lazada_cookies(),
            timeout=15,
        )
        if "application/json" not in resp.headers.get("Content-Type", "").lower():
            # Likely a captcha or redirect
            if "<title>Robot Check</title>" in resp.text or "security-check" in resp.url:
                raise ValueError("Lazada blocked the request (Captcha/Security Check detected)")
            raise ValueError(f"Lazada returned non-JSON response ({resp.status_code})")

        try:
            return resp.json()
        except Exception:
            raise ValueError(f"Failed to decode Lazada JSON. Length: {len(resp.text)}")

    def _parse(self, raw: dict) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        mods = raw.get("mods", {})
        main_info = raw.get("mainInfo", {})

        if main_info.get("bizCode", -1) != 0:
            raise ValueError(f"Lazada API error: {main_info.get('errorMsg')}")

        raw_items = mods.get("listItems", [])
        raw_products = [i for i in raw_items if i.get("tItemType") == "nt_product"]

        shops_map = {}
        products_list = []

        for p in raw_products:
            shop_id = str(p.get("sellerId", ""))
            if shop_id and shop_id not in shops_map:
                shops_map[shop_id] = {
                    "shop_id": shop_id,
                    "name": p.get("sellerName", ""),
                    "city": p.get("location", ""),
                    "is_lazmall": any(ic.get("bizType") == "lazMall" for ic in (p.get("icons") or [])),
                }

            # Parse sold/sales count robustly
            terjual_val = 0
            for key in ["sales", "sold", "itemSoldCnt", "itemSoldCntShow", "salesText", "cumulativeSales"]:
                val = p.get(key)
                if val:
                    if isinstance(val, (int, float)):
                        terjual_val = int(val)
                        break
                    val_str = str(val).lower().strip()
                    try:
                        # Clean common suffixes/characters
                        val_str = val_str.replace("sold", "").replace("terjual", "").replace("+", "").replace(" ", "").strip()
                        multiplier = 1
                        if 'k' in val_str:
                            multiplier = 1000
                            val_str = val_str.replace('k', '')
                        elif 'rb' in val_str:
                            multiplier = 1000
                            val_str = val_str.replace('rb', '')
                        val_str = val_str.replace(',', '.')
                        terjual_val = int(float(val_str) * multiplier)
                        break
                    except Exception:
                        pass

            # Cek indikator COD (Lazada biasanya menyematkannya di clickTrace, icons, atau badges)
            click_trace = str(p.get("clickTrace", "")).upper()
            is_cod = "COD" in click_trace or "CASH ON DELIVERY" in click_trace
            
            if not is_cod:
                # Cek dari icons atau atribut lain
                for ic in (p.get("icons") or []):
                    ic_str = str(ic).upper()
                    if "COD" in ic_str or "CASH ON DELIVERY" in ic_str:
                        is_cod = True
                        break
            
            products_list.append({
                "source": "lazada",
                "product_id": str(p.get("itemId", "")),
                "name": p.get("name", ""),
                "url": self._fix_url(p.get("itemUrl", "")),
                "image": p.get("image", ""),
                "price": float(p.get("price") or 0),
                "price_original": float(p.get("originalPrice") or 0),
                "discount": self._parse_diskon(p.get("discount", "")),
                "rating": float(p.get("ratingScore") or 0),
                "terjual": terjual_val,
                "shop_id": shop_id,
                "is_sponsored": bool(p.get("isSponsored", False)),
                "is_cod": is_cod,
            })

        return products_list, list(shops_map.values())

    def _fix_url(self, url: str) -> str:
        if not url: return ""
        if url.startswith("//"): return "https:" + url
        return url

    def _parse_diskon(self, teks: str) -> int:
        if not teks: return 0
        try:
            return int(teks.replace("%", "").replace("Off", "").strip())
        except:
            return 0
