"""
CaneCycle — Central Assumptions Registry (Feature 10 foundation)

Every hardcoded constant used anywhere in the CaneCycle pipeline lives
here, and ONLY here. Data-generation scripts (01, 03, and future
pathway/pricing/logistics scripts) import their constants from this
file instead of inlining literals. The Assumptions Panel (Feature 10,
rendered by 05_generate_assumptions_panel.py) reads the ASSUMPTIONS
registry below and displays exactly what's in use — never a stale copy.

Why this matters for a team build: if a teammate's script hardcodes its
own emission factor or price instead of importing from here, the
Assumptions Panel becomes a lie. Treat "import from assumptions.py" as
a hard rule for any new constant added while building Features 2-9.

To add a new assumption:
  1. Define the constant below, grouped under the right section.
  2. Add one entry to ASSUMPTIONS describing it.
  3. Import the constant (not a re-typed literal) wherever it's used.

Run directly (`python assumptions.py`) to sanity-print the registry.
"""

# ---------------------------------------------------------------------------
# NDVI & Harvest Readiness  (used by 03_generate_biomass_supply_map_data.py)
# ---------------------------------------------------------------------------
PEAK_AGE_MONTHS = 9.0
HARVEST_AGE_MIN_MONTHS = 11
NDVI_DECLINE_THRESHOLD_PCT = -2.0

# ---------------------------------------------------------------------------
# Residue Quantification / RPR proxies  (used by 01_generate_mock_data.py)
# Ranges are (low, high) and feed np.random.uniform(*RANGE, N) directly, so
# updating a range here changes both the generated data AND the panel.
# ---------------------------------------------------------------------------
BAGASSE_YIELD_RANGE = (2.8, 3.6)
LEAVES_YIELD_RANGE = (0.9, 1.4)
PRESS_MUD_YIELD_RANGE = (0.3, 0.6)

# ---------------------------------------------------------------------------
# Spatial Clustering  (used by 03_generate_biomass_supply_map_data.py)
# ---------------------------------------------------------------------------
CLUSTER_EPS_DEG = 0.05            # ~5.5 km at this latitude
CLUSTER_MIN_SAMPLES = 2

# ---------------------------------------------------------------------------
# Farm Geo-Scatter  (used by 03_generate_biomass_supply_map_data.py)
# ---------------------------------------------------------------------------
FARM_SCATTER_DEG = 0.15           # ~15 km jitter radius around district center

# ---------------------------------------------------------------------------
# District Crush Capacity (mock)  (used by 03_generate_biomass_supply_map_data.py)
# Placeholder ranges until a real mill registry is wired in.
# ---------------------------------------------------------------------------
ACTIVE_MILLS_RANGE = (3, 9)                       # randint upper bound is exclusive
CRUSH_CAPACITY_TPD_RANGE = (15000, 45000)
SEASON_CRUSH_TONS_RANGE = (400000, 1800000)
AVG_DISTANCE_TO_MILL_KM_RANGE = (4, 28)

# ---------------------------------------------------------------------------
# Registry consumed by the Assumptions Panel (Feature 10).
# Grouped by category, in display order. Values are read straight from the
# constants above so the panel and the pipeline can never drift apart.
# ---------------------------------------------------------------------------
ASSUMPTIONS = [
    # --- NDVI & Harvest Readiness ---
    {
        "category": "NDVI & Harvest Readiness",
        "label": "Sugarcane NDVI peak age",
        "value": PEAK_AGE_MONTHS,
        "unit": "months",
        "justification": "Canopy NDVI typically peaks around this crop age before senescence begins.",
    },
    {
        "category": "NDVI & Harvest Readiness",
        "label": "Minimum crop age for harvest readiness",
        "value": HARVEST_AGE_MIN_MONTHS,
        "unit": "months",
        "justification": "Below this age the crop is not agronomically ready regardless of NDVI trend.",
    },
    {
        "category": "NDVI & Harvest Readiness",
        "label": "NDVI decline threshold (senescence signal)",
        "value": NDVI_DECLINE_THRESHOLD_PCT,
        "unit": "% change across 3 scenes",
        "justification": "A drop of at least this size across the 3 pre-fetched scenes signals imminent harvest.",
    },
    # --- Residue Quantification (RPR proxies) ---
    {
        "category": "Residue Quantification (RPR)",
        "label": "Bagasse yield factor",
        "value": f"{BAGASSE_YIELD_RANGE[0]} \u2013 {BAGASSE_YIELD_RANGE[1]}",
        "unit": "tons per (acreage \u00d7 age-year factor)",
        "justification": "Mock RPR range standing in for literature-reported bagasse residue-to-product ratios.",
    },
    {
        "category": "Residue Quantification (RPR)",
        "label": "Leaves/tops yield factor",
        "value": f"{LEAVES_YIELD_RANGE[0]} \u2013 {LEAVES_YIELD_RANGE[1]}",
        "unit": "tons per (acreage \u00d7 age-year factor)",
        "justification": "Mock RPR range for trash/tops residue.",
    },
    {
        "category": "Residue Quantification (RPR)",
        "label": "Press mud yield factor",
        "value": f"{PRESS_MUD_YIELD_RANGE[0]} \u2013 {PRESS_MUD_YIELD_RANGE[1]}",
        "unit": "tons per (acreage \u00d7 age-year factor)",
        "justification": "Mock RPR range for press mud residue.",
    },
    # --- Spatial Clustering ---
    {
        "category": "Spatial Clustering",
        "label": "DBSCAN neighborhood radius",
        "value": CLUSTER_EPS_DEG,
        "unit": "degrees (~5.5 km at this latitude)",
        "justification": "Farms within this radius are grouped into the same harvest-ready cluster for routing.",
    },
    {
        "category": "Spatial Clustering",
        "label": "DBSCAN minimum cluster size",
        "value": CLUSTER_MIN_SAMPLES,
        "unit": "farms",
        "justification": "Below this, a farm becomes its own singleton cluster instead of being dropped as noise.",
    },
    # --- District Crush Capacity (mock) ---
    {
        "category": "District Crush Capacity (mock)",
        "label": "Active mills per district",
        "value": f"{ACTIVE_MILLS_RANGE[0]} \u2013 {ACTIVE_MILLS_RANGE[1] - 1}",
        "unit": "mills",
        "justification": "Placeholder range until a real mill registry is wired in.",
    },
    {
        "category": "District Crush Capacity (mock)",
        "label": "Total crush capacity per district",
        "value": f"{CRUSH_CAPACITY_TPD_RANGE[0]:,} \u2013 {CRUSH_CAPACITY_TPD_RANGE[1]:,}",
        "unit": "tons/day",
        "justification": "Placeholder range representing plausible district-level milling capacity.",
    },
    {
        "category": "District Crush Capacity (mock)",
        "label": "Current season crush",
        "value": f"{SEASON_CRUSH_TONS_RANGE[0]:,} \u2013 {SEASON_CRUSH_TONS_RANGE[1]:,}",
        "unit": "tons",
        "justification": "Placeholder for season-to-date crush volume per district.",
    },
    {
        "category": "District Crush Capacity (mock)",
        "label": "Avg. distance to nearest mill",
        "value": f"{AVG_DISTANCE_TO_MILL_KM_RANGE[0]} \u2013 {AVG_DISTANCE_TO_MILL_KM_RANGE[1]}",
        "unit": "km",
        "justification": "Placeholder transport-distance range, to be replaced once the Logistics Layer (Feature 5) is live.",
    },
]


def get_by_category():
    """Group ASSUMPTIONS into an ordered dict keyed by category, preserving
    the display order above. Used by 05_generate_assumptions_panel.py."""
    from collections import OrderedDict
    grouped = OrderedDict()
    for a in ASSUMPTIONS:
        grouped.setdefault(a["category"], []).append(a)
    return grouped


if __name__ == "__main__":
    for category, items in get_by_category().items():
        print(f"\n{category}")
        for a in items:
            print(f"  - {a['label']}: {a['value']} {a['unit']}")
