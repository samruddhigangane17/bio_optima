"""
Generates mock sugarcane residue dataset -> data/sugarcane_data.csv
Run: python 01_generate_mock_data.py
"""
import numpy as np
import pandas as pd
from assumptions import BAGASSE_YIELD_RANGE, LEAVES_YIELD_RANGE, PRESS_MUD_YIELD_RANGE


np.random.seed(42)
N = 100

varieties = ["Co-0238", "Co-86032", "CoM-0265", "Co-94012"]
soil_types = ["Clay", "Loam", "Sandy", "Black Cotton"]
irrigation_types = ["Drip", "Flood", "Rainfed"]

df = pd.DataFrame({
    "farm_id": [f"F{i:04d}" for i in range(1, N + 1)],
    "crop_age_months": np.random.randint(8, 18, N),
    "farm_acreage": np.round(np.random.uniform(1.0, 25.0, N), 2),
    "sugarcane_variety": np.random.choice(varieties, N),
    "soil_type": np.random.choice(soil_types, N),
    "rainfall_mm": np.round(np.random.normal(950, 200, N).clip(300, 1600), 1),
    "irrigation_type": np.random.choice(irrigation_types, N),
    "fertilizer_kg_per_acre": np.round(np.random.uniform(80, 220, N), 1),
})

# Inject a few missing values to simulate real-world messiness
for col in ["rainfall_mm", "soil_type", "fertilizer_kg_per_acre"]:
    df.loc[df.sample(frac=0.05, random_state=1).index, col] = np.nan

# --- Target variables (tons), loosely correlated with acreage/age/fertilizer ---
base = df["farm_acreage"] * (df["crop_age_months"] / 12)
df["bagasse_tons"] = np.round(base * np.random.uniform(*BAGASSE_YIELD_RANGE, N), 2)
df["leaves_tons"] = np.round(base * np.random.uniform(*LEAVES_YIELD_RANGE, N), 2)
df["press_mud_tons"] = np.round(base * np.random.uniform(*PRESS_MUD_YIELD_RANGE, N), 2)

df.to_csv("../data/sugarcane_data.csv", index=False)
print("Saved sugarcane_data.csv with shape:", df.shape)