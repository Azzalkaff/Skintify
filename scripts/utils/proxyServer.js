/**
 * proxyServer.js
 * Skintify – Backend Proxy untuk INCIDecoder
 *
 * Kenapa perlu proxy?
 * Browser tidak bisa langsung fetch incidecoder.com karena CORS.
 * Server ini bertindak sebagai "perantara" yang mengambil data dari INCIDecoder
 * dan mengembalikannya ke frontend.
 *
 * Setup:
 *   npm install express axios node-cache cors express-rate-limit
 *   node proxyServer.js
 *
 * Endpoint:
 *   GET /api/inci?url=https://incidecoder.com/ingredients/niacinamide
 *   GET /api/search?q=niacinamide
 *   GET /api/health
 */

const express = require("express");
const axios = require("axios");
const NodeCache = require("node-cache");
const cors = require("cors");
const rateLimit = require("express-rate-limit");

const app = express();
const cache = new NodeCache({ stdTTL: 60 * 60 * 24 * 7 }); // 7 hari cache
const PORT = process.env.PORT || 3001;

// ─── MIDDLEWARE ───────────────────────────────────────────────────────────────

app.use(cors({ origin: process.env.FRONTEND_URL || "http://localhost:3000" }));
app.use(express.json());

// Rate limiting supaya tidak diblok INCIDecoder
const limiter = rateLimit({
  windowMs: 60 * 1000, // 1 menit
  max: 30,             // max 30 request/menit dari satu IP
  message: { error: "Terlalu banyak request, coba lagi sebentar." },
});
app.use("/api/", limiter);

// ─── HELPER ───────────────────────────────────────────────────────────────────

const INCIDECODER_BASE = "https://incidecoder.com";
const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
  Accept: "text/html,application/xhtml+xml",
  "Accept-Language": "en-US,en;q=0.9",
  Referer: "https://incidecoder.com",
};

async function fetchInciDecoder(path) {
  const cacheKey = `page_${path}`;
  const hit = cache.get(cacheKey);
  if (hit) return hit;

  const url = path.startsWith("http") ? path : `${INCIDECODER_BASE}${path}`;
  const res = await axios.get(url, {
    headers: HEADERS,
    timeout: 10000,
    maxRedirects: 3,
  });

  cache.set(cacheKey, res.data);
  return res.data;
}

// ─── ROUTES ───────────────────────────────────────────────────────────────────

// Health check
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", cacheKeys: cache.keys().length });
});

// Proxy HTML halaman INCIDecoder
app.get("/api/inci", async (req, res) => {
  const { url } = req.query;
  if (!url) return res.status(400).json({ error: "Parameter 'url' diperlukan" });

  // Validasi: hanya izinkan URL incidecoder.com
  if (!url.includes("incidecoder.com")) {
    return res.status(403).json({ error: "Hanya URL incidecoder.com yang diizinkan" });
  }

  try {
    const html = await fetchInciDecoder(url);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader("X-Cache-Status", "miss");
    res.send(html);
  } catch (err) {
    console.error("Fetch error:", err.message);
    res.status(502).json({ error: "Gagal mengambil data dari INCIDecoder", detail: err.message });
  }
});

// Search ingredient
app.get("/api/search", async (req, res) => {
  const { q } = req.query;
  if (!q) return res.status(400).json({ error: "Parameter 'q' diperlukan" });

  try {
    const html = await fetchInciDecoder(`/search?query=${encodeURIComponent(q)}`);

    // Parse hasil search
    // INCIDecoder mengembalikan HTML, kita perlu parse di server
    const cheerio = require("cheerio");
    const $ = cheerio.load(html);

    const results = [];
    $(".search-result-item, .ingredient-row").each((_, el) => {
      const $el = $(el);
      const link = $el.find("a").first();
      const href = link.attr("href") || "";
      const slug = href.replace("/ingredients/", "").replace(/\/$/, "");
      const name = link.text().trim() || $el.text().trim();

      if (slug && name) {
        results.push({
          name,
          slug,
          url: `${INCIDECODER_BASE}/ingredients/${slug}`,
        });
      }
    });

    res.json({ query: q, results, total: results.length });
  } catch (err) {
    // Jika cheerio tidak ada, kembalikan HTML mentah
    if (err.code === "MODULE_NOT_FOUND") {
      const html = await fetchInciDecoder(`/search?query=${encodeURIComponent(q)}`);
      res.setHeader("Content-Type", "text/html");
      return res.send(html);
    }
    res.status(502).json({ error: err.message });
  }
});

// Get ingredient detail (parsed JSON)
app.get("/api/ingredient/:slug", async (req, res) => {
  const { slug } = req.params;

  try {
    const cheerio = require("cheerio");
    const html = await fetchInciDecoder(`/ingredients/${slug}`);
    const $ = cheerio.load(html);

    const detail = {
      slug,
      name: $(".inciname, h1").first().text().trim(),
      alsoCalled: $(".also-called")
        .text()
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      description: $(".description").text().trim(),
      functions: [],
      rating: null,
      irritancy: null,
      comedogenicity: null,
      sourceUrl: `${INCIDECODER_BASE}/ingredients/${slug}`,
    };

    // Functions / roles
    $(".function-badge, .ingredient-function").each((_, el) => {
      detail.functions.push($(el).text().trim());
    });

    // Rating
    const ratingText = $(".rating-circle").text().trim();
    const ratingMatch = ratingText.match(/(\d+(\.\d+)?)/);
    if (ratingMatch) detail.rating = parseFloat(ratingMatch[1]);

    res.json(detail);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// Clear cache (admin only)
app.delete("/api/cache", (req, res) => {
  const { secret } = req.query;
  if (secret !== process.env.ADMIN_SECRET) {
    return res.status(401).json({ error: "Unauthorized" });
  }
  cache.flushAll();
  res.json({ message: "Cache cleared" });
});

// ─── START ────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`✅ Skintify Proxy Server berjalan di http://localhost:${PORT}`);
  console.log(`   INCIDecoder proxy: GET /api/inci?url=https://incidecoder.com/...`);
  console.log(`   Search:            GET /api/search?q=niacinamide`);
  console.log(`   Ingredient detail: GET /api/ingredient/niacinamide`);
});

module.exports = app;
