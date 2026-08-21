"""
Feature 1 — Biomass Supply Map: static visual check.

Renders the three outputs of 03_generate_biomass_supply_map_data.py into a
single interactive-but-static HTML file you can open directly in a browser
(no server, no localhost needed). Three toggleable layers:
  1. District Crush Capacity — a circle per district, sized by total crush
     capacity, from district_crush_data.csv.
  2. Farms — every farm as a point, colored by harvest_ready status.
  3. Harvest-Ready Clusters — one marker per cluster, sized by total
     recoverable tonnage, from harvest_clusters.csv.

Inputs:  biomass_supply_map.csv, district_crush_data.csv, harvest_clusters.csv
         (all in the same folder, output of 03_generate_biomass_supply_map_data.py)
Output:  supply_map.html (same folder) — double-click to open in a browser.

Run: python 04_render_supply_map.py
"""
import numpy as np
import pandas as pd
import folium

# ---------------------------------------------------------------------------
# 0. Load the three outputs from the previous script
# ---------------------------------------------------------------------------
farms = pd.read_csv("biomass_supply_map.csv")
district_crush = pd.read_csv("district_crush_data.csv")
clusters = pd.read_csv("harvest_clusters.csv")

# ---------------------------------------------------------------------------
# 1. District centroids
#    district_crush_data.csv has no coordinates of its own (it's a
#    district-level table), so we derive each district's center as the
#    mean position of the farms assigned to it.
# ---------------------------------------------------------------------------
district_centers = farms.groupby("district")[["latitude", "longitude"]].mean().reset_index()
crush_geo = district_centers.merge(district_crush, on="district", how="left")

# ---------------------------------------------------------------------------
# 2. Base map, centered on the mean farm location
# ---------------------------------------------------------------------------
center_lat = farms["latitude"].mean()
center_lon = farms["longitude"].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles="cartodbpositron")

# ---------------------------------------------------------------------------
# 3. Layer 1 — District crush-data overlay
#    Circle radius (in meters) scales with total crush capacity so bigger
#    processing hubs read as visually bigger on the map.
# ---------------------------------------------------------------------------
crush_layer = folium.FeatureGroup(name="District Crush Capacity", show=True)
for _, row in crush_geo.iterrows():
    radius_m = row["total_crush_capacity_tpd"] * 0.15
    folium.Circle(
        location=[row["latitude"], row["longitude"]],
        radius=radius_m,
        color="#2b6cb0",
        weight=1.5,
        fill=True,
        fill_color="#2b6cb0",
        fill_opacity=0.12,
        popup=folium.Popup(
            f"<b>{row['district']}</b><br>"
            f"Active mills: {row['active_mills']}<br>"
            f"Crush capacity: {row['total_crush_capacity_tpd']:,} tons/day<br>"
            f"Season crush so far: {row['current_season_crush_tons']:,} tons<br>"
            f"Avg. distance to nearest mill: {row['avg_distance_to_nearest_mill_km']} km",
            max_width=260,
        ),
    ).add_to(crush_layer)
crush_layer.add_to(m)

# ---------------------------------------------------------------------------
# 4. Layer 2 — Individual farms, colored by harvest readiness
# ---------------------------------------------------------------------------
farms_layer = folium.FeatureGroup(name="Farms", show=True)
READY_COLOR = "#d1495b"      # harvest ready -> flag it clearly
NOT_READY_COLOR = "#8ab17d"  # still growing -> muted green

for _, row in farms.iterrows():
    is_ready = bool(row["harvest_ready"])
    color = READY_COLOR if is_ready else NOT_READY_COLOR
    total_tons = row["bagasse_tons"] + row["leaves_tons"] + row["press_mud_tons"]
    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=4 if is_ready else 3,
        color=color,
        weight=1,
        fill=True,
        fill_color=color,
        fill_opacity=0.85 if is_ready else 0.5,
        popup=folium.Popup(
            f"<b>{row['farm_id']}</b> — {row['district']}<br>"
            f"Crop age: {row['crop_age_months']} months<br>"
            f"NDVI trend: {row['ndvi_trend_pct']}%<br>"
            f"Harvest ready: {'Yes' if is_ready else 'No'}<br>"
            f"Total residue: {total_tons:.1f} tons",
            max_width=220,
        ),
    ).add_to(farms_layer)
farms_layer.add_to(m)

# ---------------------------------------------------------------------------
# 5. Layer 3 — Harvest-ready clusters
#    Marker radius scales with total_biomass_tons (sqrt scale so a few
#    huge clusters don't visually swamp the rest).
# ---------------------------------------------------------------------------
clusters_layer = folium.FeatureGroup(name="Harvest-Ready Clusters", show=True)
for _, row in clusters.iterrows():
    radius_px = 4 + np.sqrt(row["total_biomass_tons"]) * 1.2
    folium.CircleMarker(
        location=[row["centroid_lat"], row["centroid_lon"]],
        radius=radius_px,
        color="#e07a00",
        weight=2,
        fill=True,
        fill_color="#ffb703",
        fill_opacity=0.35,
        popup=folium.Popup(
            f"<b>Cluster {int(row['cluster_id'])}</b> — {row['primary_district']}<br>"
            f"Farms in cluster: {row['farm_count']}<br>"
            f"Total recoverable biomass: {row['total_biomass_tons']:.1f} tons<br>"
            f"Avg. NDVI trend: {row['avg_ndvi_trend_pct']}%",
            max_width=240,
        ),
    ).add_to(clusters_layer)
clusters_layer.add_to(m)

# ---------------------------------------------------------------------------
# 6. Layer control + a simple legend, then save
# ---------------------------------------------------------------------------
folium.LayerControl(collapsed=False).add_to(m)

legend_html = """
<div style="position: fixed; bottom: 20px; left: 20px; z-index: 9999;
            background: white; padding: 10px 14px; border-radius: 6px;
            box-shadow: 0 1px 6px rgba(0,0,0,0.3); font-size: 13px; line-height: 1.6;">
  <b>Legend</b><br>
  <span style="color:#d1495b;">&#9679;</span> Harvest-ready farm<br>
  <span style="color:#8ab17d;">&#9679;</span> Not yet ready<br>
  <span style="color:#ffb703;">&#9679;</span> Harvest-ready cluster (size = tonnage)<br>
  <span style="color:#2b6cb0;">&#9675;</span> District crush capacity (size = capacity)
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

m.save("supply_map.html")
print("Saved supply_map.html — open it directly in a browser, no server needed.")
