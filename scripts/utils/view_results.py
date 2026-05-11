"""
view_results.py — Tampilkan hasil scraping multi-platform dari database.
Jalankan: python scripts/view_results.py
"""

import os
import sys
from sqlalchemy import func

# Fix Pathing - Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from app.database.engine import SessionLocal, init_db
from app.database.models import Toko, Produk, HasilPencarian, SociollaReferensi

def tampilkan_ringkasan():
    init_db()
    with SessionLocal() as s:

        # ── Statistik Global ──────────────────────────────────────────────────
        total_toko_tokopedia = (
            s.query(func.count(Toko.id)).filter_by(platform="tokopedia").scalar() or 0
        )
        total_toko_lazada = (
            s.query(func.count(Toko.id)).filter_by(platform="lazada").scalar() or 0
        )
        total_produk_tokopedia = (
            s.query(func.count(Produk.id)).filter_by(platform="tokopedia").scalar() or 0
        )
        total_produk_lazada = (
            s.query(func.count(Produk.id)).filter_by(platform="lazada").scalar() or 0
        )
        total_referensi = s.query(func.count(SociollaReferensi.id)).scalar() or 0
        sudah_scrape    = (
            s.query(func.count(SociollaReferensi.id))
            .filter_by(sudah_di_scrape=True)
            .scalar() or 0
        )

        print("\n" + "=" * 65)
        print("  SKINTIFY — DATABASE STATISTICS DASHBOARD")
        print("=" * 65)

        print(f"\n  📊 Referensi Sociolla : {total_referensi} produk "
              f"({sudah_scrape} sudah di-scrape)")

        print(f"\n  {'Platform':<15} {'Toko':>8} {'Produk':>10}")
        print(f"  {'-'*15} {'-'*8} {'-'*10}")
        print(f"  {'Tokopedia':<15} {total_toko_tokopedia:>8} {total_produk_tokopedia:>10}")
        print(f"  {'Lazada':<15} {total_toko_lazada:>8} {total_produk_lazada:>10}")
        print(f"  {'TOTAL':<15} {total_toko_tokopedia+total_toko_lazada:>8} "
              f"{total_produk_tokopedia+total_produk_lazada:>10}")

        # ── Riwayat Pencarian ─────────────────────────────────────────────────
        sesi_list = (
            s.query(HasilPencarian)
            .order_by(HasilPencarian.dicari_pada.desc())
            .limit(10)
            .all()
        )

        if sesi_list:
            print(f"\n  🕒 Riwayat Scraping Terakhir:")
            print(f"  {'Platform':<12} {'Keyword':<30} {'Produk':>7} {'Toko':>5} {'Waktu'}")
            print(f"  {'-'*12} {'-'*30} {'-'*7} {'-'*5} {'-'*16}")
            for ses in sesi_list:
                kw = ses.keyword[:28] + ".." if len(ses.keyword) > 30 else ses.keyword
                print(
                    f"  {ses.platform:<12} "
                    f"{kw:<30} "
                    f"{ses.jumlah_produk:>7} "
                    f"{ses.jumlah_toko:>5}  "
                    f"{ses.dicari_pada.strftime('%m-%d %H:%M')}"
                )

        # ── Perbandingan Harga Per Keyword ────────────────────────────────────
        # Ambil keyword unik yang punya data di KEDUA platform
        keywords_tokopedia = {
            r[0] for r in s.query(Produk.keyword).filter_by(platform="tokopedia").distinct()
        }
        keywords_lazada = {
            r[0] for r in s.query(Produk.keyword).filter_by(platform="lazada").distinct()
        }
        keywords_berdua = keywords_tokopedia & keywords_lazada

        if keywords_berdua:
            print(f"\n  💰 Perbandingan Harga (Top 5 Keywords):")
            print(f"  {'Keyword':<30} {'Toko':<20} {'Harga':>12} {'Platform'}")
            print(f"  {'-'*30} {'-'*20} {'-'*12} {'-'*12}")

            for kw in sorted(keywords_berdua)[:5]:
                for platform in ["tokopedia", "lazada"]:
                    produk_termurah = (
                        s.query(Produk)
                        .filter(Produk.platform == platform, Produk.keyword == kw)
                        .filter(Produk.harga > 0)
                        .order_by(Produk.harga.asc())
                        .first()
                    )
                    if produk_termurah:
                        kw_display = kw[:28] + ".." if len(kw) > 30 else kw
                        toko_nama  = (produk_termurah.toko.nama[:18]
                                      if produk_termurah.toko else "-")
                        print(
                            f"  {kw_display:<30} "
                            f"{toko_nama:<20} "
                            f"Rp{produk_termurah.harga:>10,.0f} "
                            f"{platform}"
                        )

        # ── Produk Sociolla yang Belum Di-scrape ──────────────────────────────
        belum = (
            s.query(SociollaReferensi)
            .filter_by(sudah_di_scrape=False)
            .all()
        )
        if belum:
            print(f"\n  ⚠️  Produk Belum Di-scrape: {len(belum)} produk lagi")
            for ref in belum[:3]:
                print(f"     - {ref.brand} — {ref.product_name[:50]}")
            if len(belum) > 3:
                print(f"     ... dan {len(belum) - 3} lainnya")

        print("\n" + "=" * 65 + "\n")


if __name__ == "__main__":
    tampilkan_ringkasan()