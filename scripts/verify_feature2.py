"""
CaneCycle - Feature 2 verification script
--------------------------------------------
Run this AFTER running 01_generate_mock_data.py and 03_residue_quantification.py.
It checks the outputs against the correctness criteria for Feature 2 and
prints a clear PASS/FAIL summary instead of you having to eyeball the CSVs.

Run: python verify_feature2.py
"""

import sys
import pandas as pd

checks_passed = 0
checks_failed = 0


def check(label, condition):
    global checks_passed, checks_failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if condition:
        checks_passed += 1
    else:
        checks_failed += 1


try:
    src = pd.read_csv("../data/sugarcane_data.csv")
except FileNotFoundError:
    print("Could not find ../data/sugarcane_data.csv -- run 01_generate_mock_data.py first.")
    sys.exit(1)

try:
    res = pd.read_csv("../data/residue_quantities.csv")
except FileNotFoundError:
    print("Could not find ../data/residue_quantities.csv -- run 03_residue_quantification.py first.")
    sys.exit(1)

print("=== Checking sugarcane_data.csv (source data) ===")
check("Has exactly 8 columns", src.shape[1] == 8)
check("No stale residue columns (bagasse_tons/leaves_tons/press_mud_tons)",
      not any(c in src.columns for c in ["bagasse_tons", "leaves_tons", "press_mud_tons"]))
check("Has 100 farms", len(src) == 100)

print("\n=== Checking residue_quantities.csv (Feature 2 output) ===")
expected_cols = {"farm_id", "farm_acreage", "crop_age_months", "cane_tonnes",
                  "trash_tons", "tops_tons", "bagasse_tons", "press_mud_tons",
                  "total_residue_tons"}
check("Has all 9 expected columns", expected_cols.issubset(set(res.columns)))
check("No missing (NaN) values anywhere", not res.isna().any().any())

numeric_cols = res.select_dtypes("number")
check("No negative values anywhere", not (numeric_cols < 0).any().any())

residue_cols = ["trash_tons", "tops_tons", "bagasse_tons", "press_mud_tons"]
recomputed_total = res[residue_cols].sum(axis=1).round(2)
check("total_residue_tons matches sum of the 4 residue columns",
      (res["total_residue_tons"] == recomputed_total).all())

check("total_residue_tons never exceeds cane_tonnes",
      (res["total_residue_tons"] <= res["cane_tonnes"]).all())

not_ready = src["crop_age_months"] < 10
check("Farms below 10 months old have zero cane_tonnes (harvest-ready gate working)",
      (res.loc[not_ready, "cane_tonnes"] == 0).all())

ready = src["crop_age_months"] >= 12
check("Fully mature farms (>=12 months) have positive cane_tonnes",
      (res.loc[ready, "cane_tonnes"] > 0).all())

print(f"\n{checks_passed} passed, {checks_failed} failed.")
if checks_failed == 0:
    print("Feature 2 is verified and ready.")
else:
    print("Feature 2 has issues -- see FAIL lines above.")
