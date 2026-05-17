import os
import time
import random
import requests
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# ── Endpoint & GraphQL Query (diambil langsung dari browser) ──────────────────
ENDPOINT = "https://gql.tokopedia.com/graphql/SearchProductV5Query"

GQL_QUERY = """query SearchProductV5Query($searchProductV5Param: String!) {
  searchProductV5(params: $searchProductV5Param) {
    header {
      totalData
      responseCode
      keywordProcess
      keywordIntention
      componentID
      isQuerySafe
      additionalParams
      backendFilters
      backendFiltersToggle
      meta {
        dynamicFields
        __typename
      }
      __typename
    }
    data {
      totalDataText
      banner {
        position
        text
        url
        imageURL
        componentID
        trackingOption
        __typename
      }
      redirection {
        url
        applink
        __typename
      }
      related {
        relatedKeyword
        position
        trackingOption
        otherRelated {
          keyword
          url
          applink
          componentID
          products {
            oldId: id
            id: id_str_auto_
            name
            url
            applink
            mediaURL {
              image
              __typename
            }
            shop {
              oldId: id
              id: id_str_auto_
              name
              city
              tier
              __typename
            }
            badge {
              id
              title
              url
              __typename
            }
            price {
              text
              number
              __typename
            }
            freeShipping {
              url
              __typename
            }
            labelGroups {
              id
              position
              title
              type
              url
              styles {
                key
                value
                __typename
              }
              __typename
            }
            rating
            wishlist
            ads {
              id
              productClickURL
              productViewURL
              productWishlistURL
              tag
              __typename
            }
            meta {
              oldWarehouseID: warehouseID
              warehouseID: warehouseID_str_auto_
              componentID
              oldParentID: parentID
              parentID: parentID_str_auto_
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      suggestion {
        currentKeyword
        suggestion
        query
        text
        componentID
        trackingOption
        __typename
      }
      shopWidget {
        headline {
          badge {
            id
            title
            url
            __typename
          }
          shop {
            id
            ttsSellerID
            location
            City
            name
            ratingScore
            imageShop {
              sURL
              __typename
            }
            products {
              id
              id_str_auto_
              ttsProductID
              name
              url
              rating
              mediaURL {
                image
                image300
                videoCustom
                __typename
              }
              shop {
                oldId: id
                id: id_str_auto_
                ttsSellerID
                name
                city
                __typename
              }
              price {
                text
                number
                range
                discountPercentage
                original
                __typename
              }
              labelGroups {
                id
                position
                title
                type
                url
                styles {
                  key
                  value
                  __typename
                }
                __typename
              }
              meta {
                oldParentID: parentID
                parentID: parentID_str_auto_
                isPortrait
                oldWarehouseID: warehouseID
                warehouseID: warehouseID_str_auto_
                __typename
              }
              stock {
                ttsSKUID
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        meta {
          redirect
          __typename
        }
        __typename
      }
      ticker {
        id
        text
        query
        applink
        componentID
        trackingOption
        __typename
      }
      violation {
        headerText
        descriptionText
        imageURL
        ctaURL
        ctaApplink
        buttonText
        buttonType
        __typename
      }
      products {
        oldId: id
        id: id_str_auto_
        ttsProductID
        name
        url
        applink
        mediaURL {
          image
          image300
          videoCustom
          __typename
        }
        shop {
          oldId: id
          id: id_str_auto_
          ttsSellerID
          name
          url
          city
          tier
          __typename
        }
        stock {
          ttsSKUID
          __typename
        }
        badge {
          id
          title
          url
          __typename
        }
        price {
          text
          number
          range
          original
          discountPercentage
          __typename
        }
        freeShipping {
          url
          __typename
        }
        labelGroups {
          id
          position
          title
          type
          url
          styles {
            key
            value
            __typename
          }
          __typename
        }
        labelGroupsVariant {
          title
          type
          typeVariant
          hexColor
          __typename
        }
        category {
          oldId: id
          id: id_str_auto_
          name
          breadcrumb
          gaKey
          __typename
        }
        rating
        wishlist
        ads {
          id
          productClickURL
          productViewURL
          productWishlistURL
          tag
          __typename
        }
        meta {
          oldParentID: parentID
          parentID: parentID_str_auto_
          oldWarehouseID: warehouseID
          warehouseID: warehouseID_str_auto_
          isImageBlurred
          isPortrait
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}"""


# ── Headers (diambil dari cURL browser) ──────────────────────────────────────
def _build_headers() -> dict:
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8",
        "content-type": "application/json",
        "bd-device-id": os.getenv("BD_DEVICE_ID", "7460514796468209159"),
        "bd-web-id":    os.getenv("BD_WEB_ID",    "7460514796468209159"),
        "tkpd-userid":  os.getenv("TKPD_USER_ID", "0"),
        "x-source":              "tokopedia-lite",
        "x-device":              "mobile",
        "x-tkpd-lite-service":   "phoenix",
        "x-dark-mode":           "false",
        "x-price-center":        "true",
        "x-version":             os.getenv("X_VERSION", "efdad60"),
        "user-agent": (
            "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Mobile Safari/537.36"
        ),
        "origin":  "https://www.tokopedia.com",
        "referer": "https://www.tokopedia.com/search",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }


def _build_cookies() -> dict:
    """Parse cookie string dari .env ke dict."""
    raw = os.getenv("COOKIE", "")
    cookies = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


# ── Fungsi pencarian utama ────────────────────────────────────────────────────
def cari_produk(keyword: str, rows: int = 40, page: int = 1) -> dict:
    """
    Kirim request ke Tokopedia GraphQL dan kembalikan response mentah.
    ob=23 = sort terlaris (best seller)
    """
    params = (
        f"device=mobile"
        f"&ob=23"
        f"&page={page}"
        f"&q={quote(keyword)}"
        f"&rows={rows}"
        f"&source=search"
        f"&navsource=home"
    )

    payload = [{
        "operationName": "SearchProductV5Query",
        "variables": {
            "searchProductV5Param": params
        },
        "query": GQL_QUERY
    }]

    resp = requests.post(
        ENDPOINT,
        json=payload,
        headers=_build_headers(),
        cookies=_build_cookies(),
        timeout=15
    )
    resp.raise_for_status()
    try:
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        preview = resp.text[:200].replace("\n", " ")
        raise ValueError(
            f"Tokopedia tidak return JSON (kemungkinan captcha/block). "
            f"HTTP {resp.status_code}. Preview: {preview!r}"
        )

def _parse_harga(val) -> float:
    """Konversi nilai harga dari API ke float, handle string 'Rp55.500' dll."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    # Bersihkan: hapus "Rp", hapus titik (pemisah ribuan), ganti koma → titik
    cleaned = str(val).replace("Rp", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


import re

def _parse_terjual(labels: list) -> int:
    """
    Ekstrak jumlah terjual dari labelGroups Tokopedia.
    Contoh: 'Terjual 1rb+', 'Terjual 500+', '100+ terjual'
    """
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
        
    # Bersihkan teks: 'terjual 1,2rb+' -> '1.2rb'
    # Ambil angka + suffix sekaligus, hindari false-positive dari kata "terjual"/"sold"
    match = re.search(r"([\d,\.]+)\s*(rb|jt|k|m)?", sold_text)
    if not match:
        return 0

    angka_str = match.group(1).replace(",", ".")
    suffix    = (match.group(2) or "").lower()

    multiplier = {"rb": 1_000, "k": 1_000, "jt": 1_000_000, "m": 1_000_000}.get(suffix, 1)

    try:
        return int(float(angka_str) * multiplier)
    except (ValueError, TypeError):
        return 0


# ── Parser response ───────────────────────────────────────────────────────────
def parse_produk(raw_response: list, keyword: str) -> tuple[list, list, int]:
    """
    Parsing response GraphQL → list produk & toko.
    Return: (list_produk, list_toko_unik, total_data)
    """
    # Cek error dari Tokopedia dulu
    if isinstance(raw_response, list) and raw_response:
        errors = raw_response[0].get("errors")
        if errors:
            pesan = errors[0].get("message", "Unknown error")
            raise ValueError(f"Tokopedia API error: {pesan}")
    try:
        root = raw_response[0]["data"]["searchProductV5"]
    except (IndexError, KeyError, TypeError) as e:
        raise ValueError(f"Struktur response tidak dikenali: {e}")

    total_data = root.get("header", {}).get("totalData", 0)
    raw_products = root.get("data", {}).get("products") or []

    toko_map = {}    # shop_id -> dict toko
    produk_list = []

    for p in raw_products:
        shop = p.get("shop") or {}
        shop_id = str(shop.get("id", ""))

        # Kumpulkan toko unik
        if shop_id and shop_id not in toko_map:
            toko_map[shop_id] = {
                "shop_id": shop_id,
                "nama":    shop.get("name", ""),
                "kota":    shop.get("city", ""),
                "tier":    shop.get("tier", 0),
                "url":     shop.get("url", ""),
            }

        # Ambil badge pertama jika ada
        badges = p.get("badge") or []
        # SESUDAH
        badge_label = badges[0].get("title", "") if isinstance(badges, list) and badges else ""

        harga_info = p.get("price") or {}
        media      = p.get("mediaURL") or {}
        kategori   = p.get("category") or {}

        produk_list.append({
            "product_id":      str(p.get("id", "")),
            "keyword":         keyword,
            "nama":            p.get("name", ""),
            "url":             p.get("url", ""),
            "gambar":          media.get("image300") or media.get("image", ""),
            "harga":      _parse_harga(harga_info.get("number")),
            "harga_teks": harga_info.get("text", ""), 
            "harga_asli": _parse_harga(harga_info.get("original")),
            "diskon_persen":   int(harga_info.get("discountPercentage") or 0),
            "rating":          float(p.get("rating") or 0),
            "terjual":         _parse_terjual(p.get("labelGroups") or []),
            "kategori":        kategori.get("name", ""),
            "label_badge":     badge_label,
            "free_ongkir":     1 if p.get("freeShipping", {}).get("url") else 0,
            "shop_id":         shop_id,
        })

    return produk_list, list(toko_map.values()), total_data


# ── Retry helper ─────────────────────────────────────────────────────────────
def _dengan_retry(fn, maks_coba: int = 3, backoff_awal: float = 2.0):
    """Jalankan fn(), ulangi hingga maks_coba kali dengan exponential backoff."""
    for percobaan in range(1, maks_coba + 1):
        try:
            return fn()
        except (requests.exceptions.RequestException, ValueError) as e:
            if percobaan == maks_coba:
                raise
            tunggu = backoff_awal * (2 ** (percobaan - 1))
            print(f"   ! Percobaan {percobaan} gagal: {e}. Retry dalam {tunggu:.1f}s...")
            time.sleep(tunggu)


# ── Ambil top-N toko terbaik ──────────────────────────────────────────────────
def ambil_top_toko(keyword: str, top_n: int = 5) -> tuple[list, list]:
    """
    Cari produk untuk keyword, lalu kembalikan produk dari top_n toko pertama
    (terlaris berdasarkan posisi pencarian, ob=23).
    """
    print(f"\n[Tokopedia] Mencari: '{keyword}'")

    raw = _dengan_retry(lambda: cari_produk(keyword, rows=50))
    produk_list, semua_toko, total_data = parse_produk(raw, keyword)

    print(f"   Total data Tokopedia : {total_data:,}")
    print(f"   Produk diambil       : {len(produk_list)}")
    print(f"   Toko unik ditemukan  : {len(semua_toko)}")

    # Ambil top_n toko pertama (urutan = relevansi + penjualan dari API)
    top_toko_ids = {t["shop_id"] for t in semua_toko[:top_n]}
    top_toko     = semua_toko[:top_n]

    # Filter produk hanya dari top toko
    produk_top   = [p for p in produk_list if p["shop_id"] in top_toko_ids]

    print(f"   Top {top_n} toko terpilih  : {[t['nama'] for t in top_toko]}")
    print(f"   Produk dari top toko : {len(produk_top)}")

    # Detil Data untuk Transparansi (Anti-Blackbox)
    if produk_top:
        print("   --- Data yang Diambil (Sample) ---")
        for p in produk_top[:5]: # Tampilkan 5 produk teratas
            print(f"   * [Tokped] {p['nama'][:60]}...")
            print(f"      Harga: Rp{p['harga']:,} | Rating: {p['rating']} | Terjual: {p['terjual']} | Shop: {p['shop_id']}")
    else:
        print("   ! Tidak ada produk yang sesuai kriteria dari top toko.")

    # Jaga sopan santun — delay acak
    delay = random.uniform(2.0, 4.0)
    print(f"   . Tunggu {delay:.1f}s sebelum request berikutnya...")
    time.sleep(delay)

    return produk_top, top_toko