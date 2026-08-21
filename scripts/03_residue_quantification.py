"""
CaneCycle - Feature 2: Residue Quantification
------------------------------------------------
Converts harvested area into residue tonnage, split by residue type
(trash, tops, bagasse, press mud), using Residue-to-Product Ratios (RPR).

This is DELIBERATELY a deterministic formula, not a trained ML model --
every number traces back to a constant listed in RPR / YIELD below, which
is exactly what Feature 10 (Assumptions Panel) is meant to expose.

Formula:
    cane_tonnes           = harvested_area_acres * yield_per_acre(crop_age_months)
    residue_tonnes[type]  = cane_tonnes * RPR[type]

Run: python 03_residue_quantification.py
Input:  ../data/sugarcane_data.csv
Output: ../data/residue_quantities.csv
"""

import pandas as pd

# ----------------------------------------------------------------------
# ASSUMPTIONS -- surface these verbatim in the Assumptions Panel (Feature 10)
# Sources: sugarcane residue reviews (Kaur & Phutela 2011; Yadav & Solomon
# 2006; Hofsetz & Silva 2012; FAO Sugarcane as feed, s8850e17)
# ----------------------------------------------------------------------

RPR = {
    "trash_tons":     0.10,  # dry leaves left in field   -- t residue / t cane  (lit. range 0.09-0.11)
    "tops_tons":      0.10,  # cane tops removed at harvest -- t residue / t cane (lit. range 0.05-0.15)
    "bagasse_tons":   0.30,  # wet-basis mill residue      -- t residue / t cane (industry std ~30%)
    "press_mud_tons": 0.03,  # filter/press mud at mill    -- t residue / t cane
}

BASE_YIELD_TONNES_PER_ACRE = 30.0  # India avg cane yield at full maturity (~70-80 t/ha). Tune per district if you have real crush-season data.
MATURITY_MONTHS = 12               # age at which cane reaches ~full yield potential
HARVEST_READY_MIN_MONTHS = 10      # below this age, cane is not yet harvestable -> contributes 0 this cycle


def estimate_cane_yield(crop_age_months: pd.Series, farm_acreage: pd.Series) -> pd.Series:
    """
    Maturity-gated yield estimate.
    - Below HARVEST_READY_MIN_MONTHS: not harvestable yet -> 0 tonnes.
    - Between min-age and MATURITY_MONTHS: yield scales linearly with maturity.
    - At/after MATURITY_MONTHS: full yield (ratio capped at 1.0).
    """
    maturity_ratio = (crop_age_months / MATURITY_MONTHS).clip(upper=1.0)
    not_ready = crop_age_months < HARVEST_READY_MIN_MONTHS
    maturity_ratio = maturity_ratio.where(~not_ready, 0.0)
    yield_per_acre = BASE_YIELD_TONNES_PER_ACRE * maturity_ratio
    return yield_per_acre * farm_acreage  # tonnes of cane


def quantify_residue(df: pd.DataFrame,
                      area_col: str = "farm_acreage",
                      age_col: str = "crop_age_months") -> pd.DataFrame:
    out = df.copy()
    out["cane_tonnes"] = estimate_cane_yield(out[age_col], out[area_col]).round(2)

    for residue_type, ratio in RPR.items():
        out[residue_type] = (out["cane_tonnes"] * ratio).round(2)

    out["total_residue_tons"] = out[list(RPR.keys())].sum(axis=1).round(2)
    return out


if __name__ == "__main__":
    df = pd.read_csv("../data/sugarcane_data.csv")
    result = quantify_residue(df)

    output_cols = ["farm_id", "farm_acreage", "crop_age_months", "cane_tonnes"] \
        + list(RPR.keys()) + ["total_residue_tons"]

    result[output_cols].to_csv("../data/residue_quantities.csv", index=False)
    print(result[output_cols].head(10).to_string(index=False))
    print("\nSaved residue_quantities.csv with shape:", result[output_cols].shape)
    print(f"Farms not yet harvest-ready (<{HARVEST_READY_MIN_MONTHS} months): "
          f"{(df['crop_age_months'] < HARVEST_READY_MIN_MONTHS).sum()} / {len(df)}")
