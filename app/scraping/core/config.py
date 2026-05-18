import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Directories ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "scraped_results"

# --- Sociolla Config ---
SOCIOLLA_FILES = [
    DATA_DIR / "products_sociolla.json",
    DATA_DIR / "products_sociolla.ALL.json"
]

# --- Scraping Settings ---
DEFAULT_TOP_N = 5
SLEEP_RANGE = (1.5, 3.5)

# --- Tokopedia Constants ---
TOKOPEDIA_ENDPOINT = "https://gql.tokopedia.com/graphql/SearchProductV5Query"
TOKOPEDIA_GQL_QUERY = """query SearchProductV5Query($searchProductV5Param: String!) {
  searchProductV5(params: $searchProductV5Param) {
    header { totalData responseCode }
    data {
      products {
        id name url rating wishlist
        mediaURL { image image300 }
        shop { id name city tier url }
        price { number original discountPercentage text }
        category { name }
      }
    }
  }
}"""

def get_tokopedia_headers():
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8",
        "content-type": "application/json",
        "x-source": "tokopedia-lite",
        "x-device": "mobile",
        "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36",
        "origin": "https://www.tokopedia.com",
        "referer": "https://www.tokopedia.com/search",
    }

def get_tokopedia_cookies():
    raw = os.getenv("COOKIE", "")
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}

# --- Lazada Constants ---
LAZADA_ENDPOINT = "https://www.lazada.co.id/catalog/"

def get_lazada_headers():
    return {
        "accept": "application/json, text/plain, */*",
        "referer": "https://www.lazada.co.id/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }

def get_lazada_cookies():
    raw = os.getenv("LAZADA_COOKIE", "")
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}

# --- Shopee Constants ---
SHOPEE_ENDPOINT = "https://shopee.co.id/api/v4/search/search_items"

def get_shopee_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://shopee.co.id/",
        "X-Requested-With": "XMLHttpRequest",
        "X-Api-Source": "pc",
        "X-Shopee-Language": "id",
        "Connection": "keep-alive",
    }

def get_shopee_cookies():
    raw = os.getenv("SHOPEE_COOKIE", "")
    if raw:
        try:
            return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in raw.split(";") if "=" in p)}
        except Exception:
            pass
    return {
        "SPC_F": "skintifyc4anonymoussession00000",
        "language": "id",
        "currency": "IDR",
    }

