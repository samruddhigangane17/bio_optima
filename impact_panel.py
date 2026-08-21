"""
impact_panel.py
----------------
BioOptima — Counterfactual Impact Panel.

Shows a sharp, side-by-side comparison between the "do nothing" baseline
(farmers open-burning their residue, as is common practice today) and the
BioOptima-recommended outcome (LP + routing pipeline via matching_service.py).

Reuses existing project data and modules only:
    - sugarcane_data.csv (bagasse_tons / leaves_tons / press_mud_tons columns)
      is aggregated into the biomass_cluster's available_biomass -- this is
      real data already in the project, not invented.
    - optimization_engine.optimize_biomass_match() (Role A Feature 4 LP,
      which already calls routing_engine.py internally for Feature 5) for
      the full multi-buyer BioOptima allocation

No new data model, no UI, no changes to optimization_engine.py, routing_engine.py,
or matching_service.py.

Data gaps in the project (flagged, not invented as if real):
    sugarcane_data.csv has no buyers, prices, collection cost, processing
    emissions, or coordinates -- none of that exists anywhere in the project.
    Those fields keep the same illustrative constants already used in every
    previous example in this project (documented inline below) until real
    buyer/commercial data is supplied.

Baseline assumption (the one number not already in the project's data):
    Open burning of sugarcane residue is well documented to be far dirtier
    than collecting and processing it, largely due to incomplete combustion.
    Since no emissions-per-ton figure for open burning exists anywhere in the
    project's data, OPEN_BURNING_EMISSIONS_PER_TON is introduced here as a
    single, clearly-labeled, overridable constant (default 1500 kg CO2e/ton).
    Revenue and profit from open burning are taken as ₹0, since nothing is
    sold.

Usage:
    result = generate_impact_panel(biomass_cluster, buyers, objective="balanced")
"""

from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Union

from optimization_engine import optimize_biomass_match

BiomassCluster = Union[Dict[str, Any], List[Dict[str, Any]]]

# kg CO2e emitted per ton of residue via uncontrolled open burning.
# Overridable per call via the open_burning_emissions_per_ton argument.
OPEN_BURNING_EMISSIONS_PER_TON = 1500.0

# Path to the project's real farm data, alongside this file.
SUGARCANE_DATA_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sugarcane_data.csv")


def load_real_biomass_cluster(
    csv_path: str = SUGARCANE_DATA_CSV,
    cluster_id: str = "C001",
    location: str = "Aggregated Farm Cluster",
    latitude: float = 16.7050,   # Kolhapur -- same reference point used throughout this project
    longitude: float = 74.2433,
) -> Dict[str, Any]:
    """
    Build a real biomass_cluster by summing bagasse_tons/leaves_tons/press_mud_tons
    across every farm row in the project's actual sugarcane_data.csv.

    Only the tonnage figures come from real project data -- cost_per_ton and
    emissions_per_ton are not present anywhere in the CSV, so they keep the
    same illustrative constants already used in every earlier example in
    this project (Rs 12/8/5 per ton and 40/30/20 kg CO2e/ton for
    bagasse/leaves/press_mud respectively). Replace them once real
    collection-cost / processing-emissions figures are available.
    """
    totals = {"bagasse": 0.0, "leaves": 0.0, "press_mud": 0.0}
    column_map = {
        "bagasse_tons": "bagasse",
        "leaves_tons": "leaves",
        "press_mud_tons": "press_mud",
    }

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for column, biomass_type in column_map.items():
                value = row.get(column, "")
                if value not in ("", None):
                    totals[biomass_type] += float(value)

    return {
        "cluster_id": cluster_id,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "available_biomass": {k: round(v, 2) for k, v in totals.items()},
        "cost_per_ton": {"bagasse": 12.0, "leaves": 8.0, "press_mud": 5.0},
        "emissions_per_ton": {"bagasse": 40.0, "leaves": 30.0, "press_mud": 20.0},
    }


def _total_available_tons(biomass_cluster: BiomassCluster) -> float:
    """Sum available biomass (all types) across one cluster or a list of clusters."""
    clusters = [biomass_cluster] if isinstance(biomass_cluster, dict) else biomass_cluster
    return sum(
        qty
        for c in clusters
        for qty in c.get("available_biomass", {}).values()
    )


def generate_impact_panel(
    biomass_cluster: BiomassCluster,
    buyers: List[Dict[str, Any]],
    objective: str = "balanced",
    open_burning_emissions_per_ton: float = OPEN_BURNING_EMISSIONS_PER_TON,
    **lp_kwargs: Any,
) -> Dict[str, Any]:
    """
    Build the counterfactual comparison: Open Burning vs BioOptima.

    Args:
        biomass_cluster: one cluster dict or list of cluster dicts (existing schema).
        buyers: list of buyer dicts (existing schema).
        objective: "profit" | "emissions" | "balanced", passed to optimize_biomass_match.
        open_burning_emissions_per_ton: kg CO2e/ton assumed for open burning.
        **lp_kwargs: forwarded to optimize_biomass_match (e.g. carbon_price_per_kg).

    Returns:
        JSON-serializable dict:
        {
            "optimization_status": str,
            "open_burning": {revenue, profit, biomass_utilized_tons,
                              biomass_wasted_tons, emissions_kg},
            "biooptima": {buyers_matched, top_buyer, revenue, transport_cost,
                          final_profit, biomass_utilized_tons,
                          biomass_wasted_tons, emissions_kg},
            "comparison": {revenue_gained, profit_gained,
                           biomass_utilized_tons, emissions_avoided_kg}
        }
    """
    total_tons = round(_total_available_tons(biomass_cluster), 3)

    lp_result = optimize_biomass_match(biomass_cluster, buyers, objective=objective, **lp_kwargs)
    matches = lp_result["matches"]

    # Aggregate the FULL multi-buyer LP allocation (every buyer/leg the LP
    # routed biomass to), not just a single top buyer.
    utilized_tons = round(sum(m["tons"] for m in matches), 3)
    total_revenue = round(sum(m["revenue"] for m in matches), 2)
    total_transport_cost = round(sum(m["transport_cost"] for m in matches), 2)
    total_profit = round(sum(m["profit"] for m in matches), 2)
    total_emissions = round(sum(m["emissions_kg"] for m in matches), 2)
    wasted_tons_biooptima = round(max(total_tons - utilized_tons, 0.0), 3)

    # Per-buyer breakdown, so the panel can show every buyer the LP matched,
    # not just the single largest one.
    by_buyer: Dict[str, Dict[str, Any]] = {}
    for m in matches:
        bid = m["buyer_id"]
        agg = by_buyer.setdefault(bid, {
            "buyer_id": bid,
            "buyer_name": m["buyer_name"],
            "tons": 0.0,
            "revenue": 0.0,
            "profit": 0.0,
        })
        agg["tons"] += m["tons"]
        agg["revenue"] += m["revenue"]
        agg["profit"] += m["profit"]
    buyers_matched = sorted(
        (
            {
                "buyer_id": a["buyer_id"],
                "buyer_name": a["buyer_name"],
                "tons": round(a["tons"], 3),
                "revenue": round(a["revenue"], 2),
                "profit": round(a["profit"], 2),
            }
            for a in by_buyer.values()
        ),
        key=lambda a: a["profit"],
        reverse=True,
    )
    top_buyer = {"buyer_id": buyers_matched[0]["buyer_id"], "name": buyers_matched[0]["buyer_name"]} \
        if buyers_matched else None

    open_burning = {
        "revenue": 0.0,
        "profit": 0.0,
        "biomass_utilized_tons": 0.0,
        "biomass_wasted_tons": total_tons,
        "emissions_kg": round(total_tons * open_burning_emissions_per_ton, 2),
    }

    biooptima = {
        "buyers_matched": buyers_matched,
        "top_buyer": top_buyer,
        "revenue": total_revenue,
        "transport_cost": total_transport_cost,
        "final_profit": total_profit,
        "biomass_utilized_tons": utilized_tons,
        "biomass_wasted_tons": wasted_tons_biooptima,
        "emissions_kg": total_emissions,
    }

    # Emissions avoided: only for the tons actually utilized, comparing what
    # burning *those* tons would have emitted vs what BioOptima actually emitted
    # moving/processing them (apples-to-apples on the same tonnage).
    would_be_burn_emissions = round(utilized_tons * open_burning_emissions_per_ton, 2)
    emissions_avoided = round(would_be_burn_emissions - biooptima["emissions_kg"], 2)

    comparison = {
        "revenue_gained": round(biooptima["revenue"] - open_burning["revenue"], 2),
        "profit_gained": round(biooptima["final_profit"] - open_burning["profit"], 2),
        "biomass_utilized_tons": utilized_tons,
        "emissions_avoided_kg": emissions_avoided,
    }

    return {
        "optimization_status": lp_result["status"],
        "open_burning": open_burning,
        "biooptima": biooptima,
        "comparison": comparison,
    }


def print_impact_panel(result: Dict[str, Any]) -> None:
    """Render the comparison as a sharp, readable console panel."""
    ob = result["open_burning"]
    bo = result["biooptima"]
    cmp_ = result["comparison"]
    top_buyer = bo["top_buyer"]["name"] if bo["top_buyer"] else "None"
    n_buyers = len(bo["buyers_matched"])

    print("=" * 56)
    print(" COUNTERFACTUAL IMPACT PANEL")
    print("=" * 56)
    print(f"{'':22}{'Open Burning':>16}{'BioOptima':>16}")
    print(f"{'Revenue (Rs)':22}{ob['revenue']:>16,.2f}{bo['revenue']:>16,.2f}")
    print(f"{'Transport cost (Rs)':22}{'-':>16}{bo['transport_cost']:>16,.2f}")
    print(f"{'Profit (Rs)':22}{ob['profit']:>16,.2f}{bo['final_profit']:>16,.2f}")
    print(f"{'Biomass utilized (t)':22}{ob['biomass_utilized_tons']:>16,.2f}{bo['biomass_utilized_tons']:>16,.2f}")
    print(f"{'Biomass wasted (t)':22}{ob['biomass_wasted_tons']:>16,.2f}{bo['biomass_wasted_tons']:>16,.2f}")
    print(f"{'Emissions (kg CO2e)':22}{ob['emissions_kg']:>16,.2f}{bo['emissions_kg']:>16,.2f}")
    print("-" * 56)
    print(f"Buyers matched          : {n_buyers} (top: {top_buyer})")
    for b in bo["buyers_matched"]:
        print(f"    - {b['buyer_name']:<20} {b['tons']:>8,.2f} t   profit Rs {b['profit']:,.2f}")
    print(f"Revenue gained          : Rs {cmp_['revenue_gained']:,.2f}")
    print(f"Profit gained           : Rs {cmp_['profit_gained']:,.2f}")
    print(f"Emissions avoided       : {cmp_['emissions_avoided_kg']:,.2f} kg CO2e")
    print("=" * 56)


if __name__ == "__main__":
    import json

    # Real biomass supply, aggregated from the project's actual sugarcane_data.csv.
    real_cluster = load_real_biomass_cluster()

    # No buyer/commercial data exists anywhere in the project, so these stay
    # as the same illustrative buyers used in every earlier example here.
    example_buyers = [
        {
            "buyer_id": "B001",
            "name": "Cogen Plant A",
            "accepted_biomass_types": ["bagasse"],
            "demand_tons": 300.0,
            "price_per_ton": 35.0,
            "latitude": 18.5204,   # Pune
            "longitude": 73.8567,
        },
        {
            "buyer_id": "B002",
            "name": "Paper Mill B",
            "accepted_biomass_types": ["bagasse", "leaves"],
            "demand_tons": 250.0,
            "price_per_ton": 28.0,
            "latitude": 19.0760,   # Mumbai
            "longitude": 72.8777,
        },
        {
            "buyer_id": "B003",
            "name": "Biofertilizer Unit C",
            "accepted_biomass_types": ["press_mud"],
            "demand_tons": 80.0,
            "price_per_ton": 15.0,
            "latitude": 15.8497,   # Belgaum
            "longitude": 74.4977,
        },
    ]

    print(f"Loaded real biomass supply from {SUGARCANE_DATA_CSV}:")
    print(json.dumps(real_cluster["available_biomass"], indent=2))

    result = generate_impact_panel(real_cluster, example_buyers, objective="balanced")
    print_impact_panel(result)
    print("\nJSON:")
    print(json.dumps(result, indent=2))
