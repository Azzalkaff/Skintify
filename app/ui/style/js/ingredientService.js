/**
 * ingredientService.js
 * Skintify – INCIDecoder Integration Service
 *
 * Cara kerja:
 * 1. Scrape INCIDecoder lewat backend proxy (untuk hindari CORS)
 * 2. Cache hasil di localStorage supaya tidak spam request
 * 3. Fallback ke database lokal jika offline
 */

const INCIDECODER_BASE = "https://incidecoder.com";
const CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 hari

// ─── CACHE HELPER ────────────────────────────────────────────────────────────

function cacheSet(key, value) {
  try {
    localStorage.setItem(
      `inci_${key}`,
      JSON.stringify({ ts: Date.now(), data: value })
    );
  } catch (_) {}
}

function cacheGet(key) {
  try {
    const raw = localStorage.getItem(`inci_${key}`);
    if (!raw) return null;
    const { ts, data } = JSON.parse(raw);
    if (Date.now() - ts > CACHE_TTL_MS) {
      localStorage.removeItem(`inci_${key}`);
      return null;
    }
    return data;
  } catch (_) {
    return null;
  }
}

// ─── SLUG HELPER ─────────────────────────────────────────────────────────────

function toSlug(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

// ─── HTML PARSER (berjalan di browser) ───────────────────────────────────────

function parseIngredientPage(html, slug) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");

  const getName = () =>
    doc.querySelector(".inciname")?.textContent?.trim() ||
    doc.querySelector("h1")?.textContent?.trim() ||
    slug;

  const getDescription = () =>
    doc.querySelector(".description")?.textContent?.trim() ||
    doc.querySelector('[class*="desc"]')?.textContent?.trim() ||
    "";

  const getFunctions = () => {
    const functionEls = doc.querySelectorAll(".function-badge, .ingredient-function");
    if (functionEls.length > 0) {
      return Array.from(functionEls).map((el) => el.textContent.trim());
    }
    // fallback: cari teks "Also-called" atau "Functions"
    const labels = doc.querySelectorAll(".also-called-label ~ *, .ingredient-prop");
    return Array.from(labels)
      .map((el) => el.textContent.trim())
      .filter(Boolean)
      .slice(0, 5);
  };

  const getRating = () => {
    const ratingEl = doc.querySelector(".rating-circle, [class*='rating']");
    if (!ratingEl) return null;
    const text = ratingEl.textContent.trim();
    const match = text.match(/(\d+(\.\d+)?)/);
    return match ? parseFloat(match[1]) : null;
  };

  const getIrritancy = () => {
    const irritEl = doc.querySelector('[data-irritancy], .irritancy-badge');
    return irritEl ? irritEl.textContent.trim() : "Unknown";
  };

  const getComedogenicity = () => {
    const el = doc.querySelector('[data-comedogenic], .comedogenic-badge');
    return el ? el.textContent.trim() : "Unknown";
  };

  return {
    slug,
    name: getName(),
    description: getDescription(),
    functions: getFunctions(),
    rating: getRating(),
    irritancy: getIrritancy(),
    comedogenicity: getComedogenicity(),
    sourceUrl: `${INCIDECODER_BASE}/ingredients/${slug}`,
  };
}

// ─── FETCH VIA BACKEND PROXY ──────────────────────────────────────────────────
// Backend Express contoh ada di proxyServer.js
// GET /api/inci?url=https://incidecoder.com/ingredients/niacinamide

async function fetchViaProxy(url) {
  const proxyUrl = `/api/inci?url=${encodeURIComponent(url)}`;
  const res = await fetch(proxyUrl);
  if (!res.ok) throw new Error(`Proxy error: ${res.status}`);
  return res.text();
}

// ─── SEARCH INCIDECODER ───────────────────────────────────────────────────────

export async function searchIngredient(name) {
  const cacheKey = `search_${toSlug(name)}`;
  const cached = cacheGet(cacheKey);
  if (cached) return cached;

  try {
    const searchUrl = `${INCIDECODER_BASE}/search?query=${encodeURIComponent(name)}`;
    const html = await fetchViaProxy(searchUrl);

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");

    const results = Array.from(
      doc.querySelectorAll(".search-result-item, .ingredient-item")
    ).map((el) => {
      const link = el.querySelector("a");
      const href = link?.getAttribute("href") || "";
      const slug = href.replace("/ingredients/", "").replace("/", "");
      return {
        name: link?.textContent?.trim() || el.textContent?.trim(),
        slug,
        url: `${INCIDECODER_BASE}${href}`,
      };
    });

    cacheSet(cacheKey, results);
    return results;
  } catch (err) {
    console.error("INCIDecoder search failed:", err);
    return [];
  }
}

// ─── GET INGREDIENT DETAIL ────────────────────────────────────────────────────

export async function getIngredientDetail(nameOrSlug) {
  const slug = toSlug(nameOrSlug);
  const cacheKey = `detail_${slug}`;
  const cached = cacheGet(cacheKey);
  if (cached) return cached;

  try {
    const url = `${INCIDECODER_BASE}/ingredients/${slug}`;
    const html = await fetchViaProxy(url);
    const detail = parseIngredientPage(html, slug);
    cacheSet(cacheKey, detail);
    return detail;
  } catch (err) {
    console.error(`INCIDecoder detail failed for ${slug}:`, err);
    return null;
  }
}

// ─── BATCH FETCH ──────────────────────────────────────────────────────────────
// Ambil detail beberapa ingredient sekaligus (dengan rate-limit)

export async function batchFetchIngredients(names, delayMs = 300) {
  const results = {};
  for (const name of names) {
    results[name] = await getIngredientDetail(name);
    if (delayMs > 0) {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  return results;
}

// ─── PARSE INGREDIENT LIST STRING ────────────────────────────────────────────
// Input: "Water, Niacinamide, Zinc PCA, Hyaluronic Acid, ..."
// Output: string[]

export function parseIngredientList(rawText) {
  return rawText
    .split(/[,\n]/)
    .map((s) => s.trim())
    .filter((s) => s.length > 1)
    .map((s) => s.replace(/^\d+\.\s*/, "")); // hapus nomor "1. Water"
}
