// CaneCycle backend — starter Express server
// Run with: npm run dev  (after npm install)

const express = require("express");
const cors = require("cors");
require("dotenv").config();

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

// ---- Health check ----
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", message: "CaneCycle API is running" });
});

// ---- Feature 1: Biomass Supply Map ----
// Replace this mock with real Sentinel-2 / NDVI-derived cluster output.
app.get("/api/clusters", (req, res) => {
  res.json([
    { cluster_id: "C1", area_ha: 42.5, centroid: [26.85, 80.95], residue_type: "trash" },
    { cluster_id: "C2", area_ha: 30.1, centroid: [26.87, 80.99], residue_type: "tops" },
    { cluster_id: "C3", area_ha: 55.8, centroid: [26.90, 81.02], residue_type: "bagasse" },
  ]);
});

// ---- Feature 4/6: Multi-Objective Optimizer ----
// `weight` (0 = max margin, 1 = max emissions avoided) drives the objective-weight slider.
app.post("/api/optimize", (req, res) => {
  const { cluster_id, weight = 0.5 } = req.body;

  // Mock pathway scores — replace with real LP (PuLP-equivalent) output.
  const pathways = [
    { pathway: "2G Ethanol", margin: 3200, co2e_avoided: 1.8 },
    { pathway: "Pelletization", margin: 2600, co2e_avoided: 2.4 },
    { pathway: "Bio-CNG", margin: 2100, co2e_avoided: 3.1 },
    { pathway: "Biochar", margin: 1800, co2e_avoided: 3.6 },
    { pathway: "Cogeneration/Compost", margin: 1500, co2e_avoided: 2.0 },
  ];

  const scored = pathways.map((p) => ({
    ...p,
    score: (1 - weight) * p.margin + weight * (p.co2e_avoided * 1000),
  }));

  const best = scored.reduce((a, b) => (b.score > a.score ? b : a));
  res.json({ cluster_id, weight, recommendation: best, all_pathways: scored });
});

// ---- Feature 8: Buyer Directory ----
app.get("/api/buyers", (req, res) => {
  res.json([
    { buyer_id: "B1", name: "Riverside 2G Ethanol Plant", pathway: "2G Ethanol", capacity_tonnes: 500, remaining_tonnes: 500 },
    { buyer_id: "B2", name: "GreenPellet Co.", pathway: "Pelletization", capacity_tonnes: 350, remaining_tonnes: 350 },
    { buyer_id: "B3", name: "District Bio-CNG Facility", pathway: "Bio-CNG", capacity_tonnes: 400, remaining_tonnes: 400 },
  ]);
});

// ---- Feature 10: Assumptions Panel ----
app.get("/api/assumptions", (req, res) => {
  res.json({
    rpr_bagasse: 0.3,
    rpr_tops: 0.2,
    rpr_trash: 0.15,
    emission_factor_open_burning_tCO2e_per_tonne: 1.5,
    emission_factor_2g_ethanol: 0.4,
    price_per_tonne_2g_ethanol_inr: 3200,
    note: "All values are placeholders for the demo — replace with sourced constants before final submission.",
  });
});

app.listen(PORT, () => {
  console.log(`CaneCycle API running on http://localhost:${PORT}`);
});
