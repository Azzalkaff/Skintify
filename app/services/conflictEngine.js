/**
 * conflictEngine.js
 * Skintify – Ingredient Conflict Detection Engine
 *
 * Berisi:
 * 1. CONFLICT_RULES  – database konflik berdasarkan riset dermatologi
 * 2. SYNERGY_RULES   – kombinasi yang justru saling memperkuat
 * 3. analyzeConflicts() – algoritma utama
 * 4. getUsageOrder()    – rekomendasi urutan pemakaian
 */

// ─── SEVERITY LEVELS ─────────────────────────────────────────────────────────
export const SEVERITY = {
  AVOID:   "avoid",   // jangan gunakan bersamaan
  CAUTION: "caution", // bisa, tapi hati-hati / selang waktu
  MILD:    "mild",    // sedikit berpengaruh, tidak berbahaya
};

// ─── CONFLICT RULES DATABASE ─────────────────────────────────────────────────
// Format: { id, a: [keywords], b: [keywords], severity, reason, fix }

export const CONFLICT_RULES = [
  // ── RETINOL conflicts ──────────────────────────────────────────────────────
  {
    id: "retinol-aha",
    a: ["retinol", "retinal", "tretinoin", "retinyl palmitate", "retinaldehyde"],
    b: ["glycolic acid", "lactic acid", "mandelic acid", "aha", "alpha hydroxy"],
    severity: SEVERITY.AVOID,
    reason:
      "Retinol + AHA menyebabkan iritasi parah karena keduanya exfoliant. pH AHA (3–4) menonaktifkan retinol, membuat keduanya tidak efektif sekaligus memprovokasi kulit.",
    fix: "Gunakan AHA di pagi hari, retinol di malam hari. Atau bergantian malam.",
    ref: "Dermatology Times, 2021",
  },
  {
    id: "retinol-bha",
    a: ["retinol", "retinal", "tretinoin", "retinaldehyde"],
    b: ["salicylic acid", "bha", "beta hydroxy"],
    severity: SEVERITY.CAUTION,
    reason:
      "Kombinasi retinol + BHA dapat menyebabkan pengelupasan berlebihan dan kemerahan, terutama untuk kulit sensitif. Untuk kulit berjerawat, dokter kadang meresepkan ini bersama dengan pengawasan.",
    fix: "Gunakan BHA pagi, retinol malam. Jika kulit toleran, bisa digabung tapi mulai dari frekuensi rendah.",
    ref: "JAAD, 2020",
  },
  {
    id: "retinol-benzoyl",
    a: ["retinol", "retinal", "tretinoin"],
    b: ["benzoyl peroxide"],
    severity: SEVERITY.AVOID,
    reason:
      "Benzoyl peroxide mengoksidasi retinol, menonaktifkannya secara kimiawi. Efektivitas keduanya turun drastis jika dipakai bersamaan.",
    fix: "Gunakan benzoyl peroxide pagi, retinol malam.",
    ref: "British Journal of Dermatology",
  },
  {
    id: "retinol-vitamin-c",
    a: ["retinol", "retinal", "tretinoin"],
    b: ["vitamin c", "ascorbic acid", "l-ascorbic acid", "sodium ascorbyl phosphate"],
    severity: SEVERITY.CAUTION,
    reason:
      "Keduanya bekerja pada pH berbeda (Vit C: 2.5–3.5, Retinol: 5–6). Jika dipakai bersamaan, salah satu tidak optimal. Risiko iritasi juga meningkat.",
    fix: "Vitamin C di pagi hari (setelah SPF), retinol di malam hari.",
    ref: "Cosmetic Dermatology, 2019",
  },

  // ── VITAMIN C conflicts ────────────────────────────────────────────────────
  {
    id: "vitaminc-niacinamide",
    a: ["vitamin c", "ascorbic acid", "l-ascorbic acid"],
    b: ["niacinamide", "vitamin b3", "nicotinamide"],
    severity: SEVERITY.MILD,
    reason:
      "Mitos lama: dulu dikira membentuk niacin (flush). Penelitian modern menunjukkan ini tidak terjadi pada suhu ruangan normal. Tapi pH keduanya berbeda sehingga efektivitas bisa menurun jika dipakai langsung bersamaan.",
    fix: "Tunggu 15–20 menit di antara aplikasi, atau pakai di waktu berbeda. Produk dengan formula stabil bisa mengkombinasikannya.",
    ref: "International Journal of Cosmetic Science, 2020",
  },
  {
    id: "vitaminc-aha",
    a: ["vitamin c", "ascorbic acid", "l-ascorbic acid"],
    b: ["glycolic acid", "lactic acid", "aha", "alpha hydroxy"],
    severity: SEVERITY.CAUTION,
    reason:
      "Kedua asam ini dapat menyebabkan iritasi dan kemerahan terutama untuk kulit sensitif. pH terlalu rendah bisa mengganggu skin barrier.",
    fix: "Pilih satu exfoliant per sesi. Vitamin C pagi, AHA malam.",
    ref: "Skin Pharmacology and Physiology",
  },

  // ── AHA/BHA conflicts ──────────────────────────────────────────────────────
  {
    id: "aha-bha",
    a: ["glycolic acid", "lactic acid", "mandelic acid", "aha"],
    b: ["salicylic acid", "bha"],
    severity: SEVERITY.CAUTION,
    reason:
      "Menggunakan dua chemical exfoliant sekaligus bisa over-exfoliate, merusak skin barrier, menyebabkan kulit merah, kering, dan sensitif.",
    fix: "Pilih salah satu: AHA untuk permukaan kulit, BHA untuk pori. Bisa bergantian hari atau pagi/malam.",
    ref: "American Academy of Dermatology",
  },
  {
    id: "aha-peptide",
    a: ["glycolic acid", "lactic acid", "aha"],
    b: ["peptide", "matrixyl", "argireline", "palmitoyl"],
    severity: SEVERITY.CAUTION,
    reason:
      "pH rendah AHA (3–4) mendegradasi struktur peptida, mengurangi efektivitasnya secara signifikan.",
    fix: "Pakai AHA terlebih dahulu, tunggu skin barrier kembali normal (20–30 menit), lalu peptide. Lebih baik di waktu berbeda.",
    ref: "Journal of Cosmetic Dermatology",
  },

  // ── BENZOYL PEROXIDE conflicts ─────────────────────────────────────────────
  {
    id: "benzoyl-aha",
    a: ["benzoyl peroxide"],
    b: ["glycolic acid", "lactic acid", "aha", "salicylic acid"],
    severity: SEVERITY.CAUTION,
    reason:
      "Kombinasi dua agen aktif untuk jerawat bisa menyebabkan iritasi parah, kekeringan ekstrem, dan peeling berlebih.",
    fix: "Benzoyl peroxide pagi, exfoliant malam. Atau fokus ke salah satu saja.",
    ref: "Cutis, 2018",
  },

  // ── SPF / Physical sunscreen ───────────────────────────────────────────────
  {
    id: "spf-vitaminc",
    a: ["zinc oxide", "titanium dioxide"],
    b: ["vitamin c", "ascorbic acid", "l-ascorbic acid"],
    severity: SEVERITY.MILD,
    reason:
      "Zinc oxide dapat mengoksidasi vitamin C, menurunkan efektivitasnya. Efek ini minimal tapi ada pada kontak langsung.",
    fix: "Pakai Vitamin C serum dulu, tunggu meresap, baru sunscreen. Hindari mencampur keduanya di telapak tangan.",
    ref: "Photodermatology, Photoimmunology & Photomedicine",
  },
];

// ─── SYNERGY RULES (Kombinasi BAGUS) ─────────────────────────────────────────

export const SYNERGY_RULES = [
  {
    id: "niacinamide-zinc",
    a: ["niacinamide", "vitamin b3"],
    b: ["zinc pca", "zinc gluconate", "zinc"],
    reason: "Niacinamide + Zinc adalah duo ikonik untuk kulit berjerawat dan berminyak. Keduanya saling memperkuat efek anti-inflamasi dan regulasi sebum.",
  },
  {
    id: "retinol-peptide",
    a: ["retinol", "retinal"],
    b: ["peptide", "matrixyl", "palmitoyl"],
    reason: "Retinol mendorong pergantian sel, peptide membantu repair dan produksi kolagen. Jika dipakai terpisah (pagi/malam), efek anti-aging berlipat ganda.",
  },
  {
    id: "vitaminc-spf",
    a: ["vitamin c", "ascorbic acid"],
    b: ["spf", "sunscreen", "uva", "uvb"],
    reason: "Vitamin C meningkatkan perlindungan antioksidan sunscreen terhadap kerusakan UV. Kombinasi terbaik untuk anti-aging.",
  },
  {
    id: "hyaluronic-moisturizer",
    a: ["hyaluronic acid", "sodium hyaluronate"],
    b: ["glycerin", "ceramide", "squalane", "shea butter"],
    reason: "Hyaluronic acid menarik air, moisturizer menyegel. Kombinasi sempurna untuk hidrasi berlapis.",
  },
  {
    id: "aha-hyaluronic",
    a: ["glycolic acid", "lactic acid", "aha"],
    b: ["hyaluronic acid", "sodium hyaluronate"],
    reason: "Setelah AHA mengeksfoliasi, hyaluronic acid masuk lebih dalam untuk hidrasi optimal.",
  },
];

// ─── NORMALIZE INGREDIENT NAME ────────────────────────────────────────────────

function normalizeIngredient(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// ─── MATCH RULE ───────────────────────────────────────────────────────────────
// Cek apakah ingredient list mengandung salah satu keyword dari grup

function matchesGroup(ingredientList, keywords) {
  const normalized = ingredientList.map(normalizeIngredient);
  return keywords.some((kw) =>
    normalized.some((ing) => ing.includes(kw.toLowerCase()))
  );
}

function findMatchedIngredient(ingredientList, keywords) {
  const normalized = ingredientList.map((n, i) => ({ n: normalizeIngredient(n), orig: ingredientList[i] }));
  for (const kw of keywords) {
    const found = normalized.find(({ n }) => n.includes(kw.toLowerCase()));
    if (found) return found.orig;
  }
  return null;
}

// ─── MAIN: ANALYZE SINGLE PRODUCT ─────────────────────────────────────────────

export function analyzeProduct(ingredientList) {
  const conflicts = [];
  const synergies = [];

  // Check konflik internal dalam satu produk
  for (const rule of CONFLICT_RULES) {
    const hasA = matchesGroup(ingredientList, rule.a);
    const hasB = matchesGroup(ingredientList, rule.b);
    if (hasA && hasB) {
      conflicts.push({
        ...rule,
        matchedA: findMatchedIngredient(ingredientList, rule.a),
        matchedB: findMatchedIngredient(ingredientList, rule.b),
        scope: "internal",
      });
    }
  }

  for (const rule of SYNERGY_RULES) {
    const hasA = matchesGroup(ingredientList, rule.a);
    const hasB = matchesGroup(ingredientList, rule.b);
    if (hasA && hasB) {
      synergies.push({
        ...rule,
        matchedA: findMatchedIngredient(ingredientList, rule.a),
        matchedB: findMatchedIngredient(ingredientList, rule.b),
      });
    }
  }

  return { conflicts, synergies };
}

// ─── MAIN: ANALYZE MULTI-PRODUCT ROUTINE ─────────────────────────────────────

/**
 * @param {Array<{ name: string, ingredients: string[] }>} products
 * @returns {Object} analisis lengkap
 */
export function analyzeRoutine(products) {
  const results = {
    productAnalyses: [],
    crossProductConflicts: [],
    crossProductSynergies: [],
    overallSeverity: null,
    summary: "",
    recommendations: [],
  };

  // 1. Analisis tiap produk secara individual
  for (const product of products) {
    const analysis = analyzeProduct(product.ingredients);
    results.productAnalyses.push({
      productName: product.name,
      ...analysis,
    });
  }

  // 2. Cross-product conflicts (kombinasi antar produk)
  for (let i = 0; i < products.length; i++) {
    for (let j = i + 1; j < products.length; j++) {
      const pA = products[i];
      const pB = products[j];

      for (const rule of CONFLICT_RULES) {
        const aInPA = matchesGroup(pA.ingredients, rule.a);
        const bInPB = matchesGroup(pB.ingredients, rule.b);
        const bInPA = matchesGroup(pA.ingredients, rule.b);
        const aInPB = matchesGroup(pB.ingredients, rule.a);

        if ((aInPA && bInPB) || (bInPA && aInPB)) {
          const [prodA, prodB, grpA, grpB] =
            aInPA && bInPB
              ? [pA, pB, rule.a, rule.b]
              : [pB, pA, rule.a, rule.b];

          results.crossProductConflicts.push({
            ...rule,
            productA: prodA.name,
            productB: prodB.name,
            matchedA: findMatchedIngredient(prodA.ingredients, grpA),
            matchedB: findMatchedIngredient(prodB.ingredients, grpB),
            scope: "cross-product",
          });
        }
      }

      for (const rule of SYNERGY_RULES) {
        const aInPA = matchesGroup(pA.ingredients, rule.a);
        const bInPB = matchesGroup(pB.ingredients, rule.b);
        const bInPA = matchesGroup(pA.ingredients, rule.b);
        const aInPB = matchesGroup(pB.ingredients, rule.a);

        if ((aInPA && bInPB) || (bInPA && aInPB)) {
          results.crossProductSynergies.push({
            ...rule,
            productA: pA.name,
            productB: pB.name,
          });
        }
      }
    }
  }

  // 3. Hitung overall severity
  const allConflicts = [
    ...results.productAnalyses.flatMap((p) => p.conflicts),
    ...results.crossProductConflicts,
  ];

  if (allConflicts.some((c) => c.severity === SEVERITY.AVOID)) {
    results.overallSeverity = SEVERITY.AVOID;
  } else if (allConflicts.some((c) => c.severity === SEVERITY.CAUTION)) {
    results.overallSeverity = SEVERITY.CAUTION;
  } else if (allConflicts.length > 0) {
    results.overallSeverity = SEVERITY.MILD;
  } else {
    results.overallSeverity = null;
  }

  // 4. Build recommendations
  const uniqueFixes = new Set(allConflicts.map((c) => c.fix).filter(Boolean));
  results.recommendations = [...uniqueFixes];

  // 5. Summary teks
  const totalConflicts = allConflicts.length;
  const totalSynergies = results.crossProductSynergies.length;
  if (totalConflicts === 0) {
    results.summary = `✅ Semua ${products.length} produk aman digunakan bersamaan. Ditemukan ${totalSynergies} kombinasi sinergis.`;
  } else {
    results.summary = `⚠️ Ditemukan ${totalConflicts} konflik di antara ${products.length} produk kamu. ${totalSynergies} kombinasi sinergis juga terdeteksi.`;
  }

  return results;
}

// ─── GET USAGE ORDER ─────────────────────────────────────────────────────────
// Urutkan produk: thinnest → thickest (standard layering rule)

const STEP_KEYWORDS = {
  0: ["micellar", "cleansing water", "first cleanser"],
  1: ["cleanser", "face wash", "foaming", "gel cleanser"],
  2: ["toner", "essence", "mist"],
  3: ["serum", "ampoule", "concentrate"],
  4: ["eye cream"],
  5: ["moisturizer", "lotion", "emulsion", "gel cream", "cream"],
  6: ["face oil", "facial oil", "rosehip", "squalane"],
  7: ["sunscreen", "spf", "uv protection", "sun cream"],
};

export function getUsageOrder(products) {
  const scored = products.map((p) => {
    const nameLower = p.name.toLowerCase();
    let step = 4; // default: serum step
    for (const [s, keywords] of Object.entries(STEP_KEYWORDS)) {
      if (keywords.some((kw) => nameLower.includes(kw))) {
        step = parseInt(s);
        break;
      }
    }
    return { ...p, step };
  });

  return scored.sort((a, b) => a.step - b.step);
}
