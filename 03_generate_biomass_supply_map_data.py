"""
Feature 1 — Biomass Supply Map: data layer.

Builds everything the map needs on top of the existing farm-level dataset:
  1. Geolocates each farm to a district in the Maharashtra sugarcane belt
     (the raw dataset has no coordinates at all, so this is the missing
     foundation every other part of Feature 1 depends on).
  2. Simulates 3 pre-fetched Sentinel-2 NDVI scenes per farm (Sentinel-2
     itself is not wired up yet — see the swap-in note at the bottom).
  3. Derives a harvest-readiness signal from crop age + NDVI trend.
  4. Attaches a district-level crush-data overlay (mill capacity/demand).
  5. Runs DBSCAN over harvest-ready farms to form the "harvest-ready
     clusters" the map draws, and aggregates recoverable tonnage per cluster.

Inputs:  sugarcane_data.csv        (output of 01_generate_mock_data.py, same folder)
Outputs: biomass_supply_map.csv    (farm-level: geo + NDVI + readiness + cluster_id)
         district_crush_data.csv   (district-level crush overlay)
         harvest_clusters.csv      (cluster-level aggregates for map markers)

Run: python 03_generate_biomass_supply_map_data.py
"""
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

np.random.seed(42)

# ---------------------------------------------------------------------------
# 0. Load the base farm dataset produced by 01_generate_mock_data.py
# ---------------------------------------------------------------------------
df = pd.read_csv("sugarcane_data.csv")

# ---------------------------------------------------------------------------
# 1. District geolocation
#    Six districts from Maharashtra's sugarcane belt, each defined by a
#    center point. Farms are scattered within a small radius of their
#    assigned district's center to mimic real dispersion.
# ---------------------------------------------------------------------------
DISTRICTS = {
    "Kolhapur":   {"lat": 16.7050, "lon": 74.2433, "weight": 0.22},
    "Sangli":     {"lat": 16.8524, "lon": 74.5815, "weight": 0.20},
    "Solapur":    {"lat": 17.6599, "lon": 75.9064, "weight": 0.18},
    "Pune":       {"lat": 18.5204, "lon": 73.8567, "weight": 0.16},
    "Ahmednagar": {"lat": 19.0948, "lon": 74.7480, "weight": 0.14},
    "Satara":     {"lat": 17.6805, "lon": 74.0183, "weight": 0.10},
}
district_names = list(DISTRICTS.keys())
district_weights = [DISTRICTS[d]["weight"] for d in district_names]

df["district"] = np.random.choice(district_names, size=len(df), p=district_weights)

# Scatter each farm within ~0.15 deg (~15km) of its district center
SCATTER_DEG = 0.15
df["latitude"] = df["district"].map(lambda d: DISTRICTS[d]["lat"]) + np.random.uniform(
    -SCATTER_DEG, SCATTER_DEG, len(df)
)
df["longitude"] = df["district"].map(lambda d: DISTRICTS[d]["lon"]) + np.random.uniform(
    -SCATTER_DEG, SCATTER_DEG, len(df)
)
df["latitude"] = df["latitude"].round(5)
df["longitude"] = df["longitude"].round(5)

# ---------------------------------------------------------------------------
# 2. Mock Sentinel-2 NDVI scenes (2-3 pre-fetched dates)
#    Sugarcane NDVI rises through the vegetative phase, peaks around
#    ~9 months, then senesces as harvest approaches. We model that curve
#    per farm from crop_age_months, then sample 3 scene dates 15 days
#    apart (today, 15 days ago, 30 days ago) with independent noise so
#    the scenes show a believable trend rather than a straight line.
# ---------------------------------------------------------------------------
PEAK_AGE_MONTHS = 9.0


def ndvi_at_age(age_months):
    """Rough sugarcane NDVI growth curve: rises to a peak near 9 months,
    then declines as the crop matures toward harvest."""
    distance_from_peak = np.abs(age_months - PEAK_AGE_MONTHS)
    base = 0.85 - 0.03 * distance_from_peak
    return np.clip(base, 0.15, 0.90)


scene_dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=3, freq="15D")
scene_cols = []
for i, scene_date in enumerate(scene_dates, start=1):
    # Age "as of" each scene date, in months, walking back from current crop_age_months
    days_before_latest = (scene_dates[-1] - scene_date).days
    age_at_scene = df["crop_age_months"] - (days_before_latest / 30.0)
    col = f"ndvi_scene{i}"
    df[col] = np.round(
        ndvi_at_age(age_at_scene) + np.random.normal(0, 0.02, len(df)), 3
    ).clip(0.05, 0.95)
    scene_cols.append(col)

df["ndvi_scene1_date"] = scene_dates[0].date()
df["ndvi_scene2_date"] = scene_dates[1].date()
df["ndvi_scene3_date"] = scene_dates[2].date()

# ---------------------------------------------------------------------------
# 3. Harvest-readiness signal
#    A farm is "harvest ready" if it's in the typical harvest age window
#    AND its NDVI is trending down across the 3 scenes (senescence signal).
# ---------------------------------------------------------------------------
df["ndvi_trend_pct"] = np.round(
    (df["ndvi_scene3"] - df["ndvi_scene1"]) / df["ndvi_scene1"] * 100, 2
)

HARVEST_AGE_MIN_MONTHS = 11
NDVI_DECLINE_THRESHOLD_PCT = -2.0  # at least a 2% drop across the 3 scenes

df["harvest_ready"] = (
    (df["crop_age_months"] >= HARVEST_AGE_MIN_MONTHS)
    & (df["ndvi_trend_pct"] <= NDVI_DECLINE_THRESHOLD_PCT)
)

# ---------------------------------------------------------------------------
# 4. District crush-data overlay (mock mill capacity / current demand)
# ---------------------------------------------------------------------------
np.random.seed(7)  # separate stream so district table changes independently
district_crush = pd.DataFrame({
    "district": district_names,
    "active_mills": np.random.randint(3, 9, len(district_names)),
    "total_crush_capacity_tpd": np.random.randint(15000, 45000, len(district_names)),
    "current_season_crush_tons": np.random.randint(400000, 1800000, len(district_names)),
    "avg_distance_to_nearest_mill_km": np.round(np.random.uniform(4, 28, len(district_names)), 1),
})

# ---------------------------------------------------------------------------
# 5. Spatial clustering of harvest-ready farms -> "harvest-ready clusters"
#    DBSCAN groups nearby harvest-ready farms; eps is in degrees (~0.05
#    deg ~= 5.5 km at this latitude), min_samples=2 so isolated single
#    farms are flagged as noise and re-labeled as their own singleton
#    cluster below (every harvest-ready farm should still show up on the
#    map as a deliverable node, even if it has no neighbors).
# ---------------------------------------------------------------------------
df["cluster_id"] = np.nan  # not harvest-ready -> no cluster

ready_mask = df["harvest_ready"]
ready_df = df.loc[ready_mask, ["latitude", "longitude"]]

if len(ready_df) > 0:
    dbscan = DBSCAN(eps=0.05, min_samples=2)
    labels = dbscan.fit_predict(ready_df.values)

    # Re-label noise points (-1) as their own unique singleton clusters,
    # continuing the id sequence after the last real (multi-farm) cluster.
    next_id = labels.max() + 1 if labels.max() >= 0 else 0
    final_labels = labels.astype(float)
    for idx in np.where(labels == -1)[0]:
        final_labels[idx] = next_id
        next_id += 1

    df.loc[ready_mask, "cluster_id"] = final_labels

df["cluster_id"] = df["cluster_id"].astype("Int64")  # nullable int (NaN for non-ready farms)

# ---------------------------------------------------------------------------
# 6. Cluster-level aggregation for map markers
# ---------------------------------------------------------------------------
clustered = df.loc[df["cluster_id"].notna()].copy()
harvest_clusters = (
    clustered.groupby("cluster_id")
    .agg(
        farm_count=("farm_id", "count"),
        centroid_lat=("latitude", "mean"),
        centroid_lon=("longitude", "mean"),
        primary_district=("district", lambda s: s.mode().iloc[0]),
        total_bagasse_tons=("bagasse_tons", "sum"),
        total_leaves_tons=("leaves_tons", "sum"),
        total_press_mud_tons=("press_mud_tons", "sum"),
        avg_ndvi_trend_pct=("ndvi_trend_pct", "mean"),
    )
    .reset_index()
)
harvest_clusters["total_biomass_tons"] = np.round(
    harvest_clusters["total_bagasse_tons"]
    + harvest_clusters["total_leaves_tons"]
    + harvest_clusters["total_press_mud_tons"],
    2,
)
harvest_clusters[["centroid_lat", "centroid_lon", "avg_ndvi_trend_pct"]] = harvest_clusters[
    ["centroid_lat", "centroid_lon", "avg_ndvi_trend_pct"]
].round(5)

# ---------------------------------------------------------------------------
# 7. Persist outputs
# ---------------------------------------------------------------------------
df.to_csv("biomass_supply_map.csv", index=False)
district_crush.to_csv("district_crush_data.csv", index=False)
harvest_clusters.to_csv("harvest_clusters.csv", index=False)

print("Saved biomass_supply_map.csv with shape:", df.shape)
print("Saved district_crush_data.csv with shape:", district_crush.shape)
print("Saved harvest_clusters.csv with shape:", harvest_clusters.shape)
print(f"Harvest-ready farms: {int(df['harvest_ready'].sum())} / {len(df)}")
print(f"Harvest-ready clusters formed: {harvest_clusters['cluster_id'].nunique()}")

# ---------------------------------------------------------------------------
# Swap-in note: to replace mock NDVI with real Sentinel-2 data later,
# only the block in section 2 needs to change. Keep the output contract
# the same (ndvi_scene1..3 columns + their dates) and everything
# downstream (readiness, clustering, the map renderer) keeps working
# unmodified. A library like `sentinelhub-py` or Google Earth Engine's
# Python API, queried per farm's (latitude, longitude) with a small buffer
# polygon, is the natural drop-in replacement for ndvi_at_age().
# ---------------------------------------------------------------------------
