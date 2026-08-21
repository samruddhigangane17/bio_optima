/**
 * pathwayData.js
 * ---------------------------------------------------------------------------
 * Dataset + calculation engine for the "Pathway Comparison" feature.
 *
 * WHY THIS SHAPE:
 * Every pathway is stored as a rate PER TONNE (₹/t and tCO2e/t), not as a
 * pre-computed total. The UI multiplies by the selected quantity at render
 * time. This means:
 *   1. Changing quantity never touches this file — it's a pure function call.
 *   2. Swapping mock data for real optimizer/API output later means
 *      replacing PATHWAYS below (or the source it's read from) — the
 *      calculation + component code does not change.
 *
 * TO CONNECT REAL DATA LATER:
 * Replace the hardcoded PATHWAYS array with a fetch to your
 * optimizer/recommendation endpoint, e.g.:
 *
 *   export async function fetchPathwaysForCluster(clusterId) {
 *     const res = await fetch(`/api/clusters/${clusterId}/pathways`);
 *     return res.json(); // must match the PATHWAYS shape below
 *   }
 *
 * The `isRecommended` flag should then come from your LP optimizer's
 * Pareto-optimal pick for that cluster, rather than being hardcoded.
 * ---------------------------------------------------------------------------
 */

// All monetary values in ₹ per tonne. All emissions in tCO2e per tonne.
// These are DEMO / ILLUSTRATIVE values only.
export const PATHWAYS = [
  {
    id: "recommended",
    name: "2G Ethanol (Recommended)",
    shortLabel: "Recommended",
    isRecommended: true,
    category: "financial", // primary pathway type, used for icon/detail copy
    ratesPerTonne: {
      revenue: 4200,
      transportCost: 350,
      processingCost: 1980,
    },
    emissionsPerTonne: 0.12,
    whyRecommended:
      "Highest net margin of all viable pathways for this cluster, with the lowest processing emissions among revenue-generating options — the optimizer's Pareto-optimal pick balancing margin and emissions avoided.",
    details: {
      revenueNote:
        "Sale price to nearest 2G ethanol offtaker, based on current procurement rate per tonne of feedstock.",
      transportNote:
        "Trucking cost to the assigned buyer, calculated from routing distance and per-km haulage rate.",
      processingNote:
        "Feedstock handling, pre-treatment and enzymatic conversion cost charged by the offtaker, netted back to the supplier price.",
      marginFormula: "Net Margin = Revenue − Transport Cost − Processing Cost",
      emissionsNote:
        "Lifecycle processing emissions per tonne of feedstock converted to ethanol, including transport.",
    },
  },
  {
    id: "bioenergy",
    name: "Bioenergy / Biomass Plant",
    shortLabel: "Bioenergy",
    isRecommended: false,
    category: "financial",
    ratesPerTonne: {
      revenue: 3600,
      transportCost: 380,
      processingCost: 1620,
    },
    emissionsPerTonne: 0.31,
    details: {
      revenueNote:
        "Sale price to biomass power plant, based on calorific-value-linked procurement rate.",
      transportNote:
        "Trucking cost to the nearest plant with available intake capacity.",
      processingNote:
        "Combustion feedstock prep (chipping/baling) and handling cost netted back to supplier price.",
      marginFormula: "Net Margin = Revenue − Transport Cost − Processing Cost",
      emissionsNote:
        "Combustion emissions per tonne of feedstock, including transport.",
    },
  },
  {
    id: "biochar",
    name: "Biochar",
    shortLabel: "Biochar",
    isRecommended: false,
    category: "environmental",
    ratesPerTonne: {
      revenue: 3300,
      transportCost: 400,
      processingCost: 1480,
    },
    emissionsPerTonne: 0.45,
    details: {
      revenueNote:
        "Sale price for pyrolysis-derived biochar into the soil-amendment / carbon-credit market.",
      transportNote:
        "Trucking cost to the nearest pyrolysis unit.",
      processingNote:
        "Pyrolysis energy and equipment cost netted back to supplier price.",
      marginFormula: "Net Margin = Revenue − Transport Cost − Processing Cost",
      emissionsNote:
        "Pyrolysis process emissions per tonne of feedstock, including transport.",
    },
  },
  {
    id: "composting",
    name: "Composting",
    shortLabel: "Composting",
    isRecommended: false,
    category: "environmental",
    ratesPerTonne: {
      revenue: 2800,
      transportCost: 420,
      processingCost: 1130,
    },
    emissionsPerTonne: 0.6,
    details: {
      revenueNote:
        "Sale price for finished compost into the local agri-input market.",
      transportNote:
        "Trucking cost to the nearest composting/windrow facility.",
      processingNote:
        "Windrow turning, water and labour cost over the composting cycle, netted back to supplier price.",
      marginFormula: "Net Margin = Revenue − Transport Cost − Processing Cost",
      emissionsNote:
        "Methane/N2O emissions from the composting process per tonne of feedstock, including transport.",
    },
  },
  {
    id: "open-burning",
    name: "Open Burning",
    shortLabel: "Open Burning",
    isRecommended: false,
    category: "baseline",
    isBaseline: true,
    ratesPerTonne: {
      revenue: 0,
      transportCost: 0,
      processingCost: 0,
    },
    emissionsPerTonne: 2.84,
    details: {
      revenueNote: "No revenue — residue is burned in-field, not sold.",
      transportNote: "No transport — residue is burned where it lies.",
      processingNote: "No processing cost incurred.",
      marginFormula: "Net Margin = ₹0 (status quo, no transaction)",
      emissionsNote:
        "Direct field-burning emission factor per tonne of residue — the baseline every other pathway avoids.",
    },
  },
];

const QUANTITY_PRESETS = [50, 100, 250, 500];

/**
 * Given a quantity (tonnes), compute totals for every pathway.
 * Returns a new array — never mutates PATHWAYS.
 */
function calculateForQuantity(quantity, pathways = PATHWAYS) {
  const qty = Number(quantity) > 0 ? Number(quantity) : 0;
  const baseline = pathways.find((p) => p.isBaseline);
  const baselineEmissions = baseline ? baseline.emissionsPerTonne * qty : 0;

  const rows = pathways.map((p) => {
    const revenue = p.ratesPerTonne.revenue * qty;
    const transportCost = p.ratesPerTonne.transportCost * qty;
    const processingCost = p.ratesPerTonne.processingCost * qty;
    const netMargin = revenue - transportCost - processingCost;
    const emissions = p.emissionsPerTonne * qty;
    const co2Avoided = p.isBaseline
      ? 0
      : Math.max(0, baselineEmissions - emissions);

    return {
      ...p,
      quantity: qty,
      revenue,
      transportCost,
      processingCost,
      netMargin,
      emissions,
      co2Avoided,
    };
  });

  // Flag best-in-class for badges (baseline excluded automatically since
  // it never wins margin, and never has lowest emissions).
  const highestMarginId = rows.reduce((best, r) =>
    r.netMargin > best.netMargin ? r : best
  ).id;
  const lowestEmissionsId = rows.reduce((best, r) =>
    r.emissions < best.emissions ? r : best
  ).id;

  return rows.map((r) => ({
    ...r,
    isHighestMargin: r.id === highestMarginId,
    isLowestEmissions: r.id === lowestEmissionsId,
  }));
}

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const formatCurrency = (value) => currencyFormatter.format(value);
const formatTonnes = (value) => `${value.toFixed(2)} t`;

export { QUANTITY_PRESETS, calculateForQuantity, formatCurrency, formatTonnes };
