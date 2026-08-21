"""
optimization_engine.py
-----------------------
BioOptima — Role A / Feature 4: Linear Programming biomass-to-buyer matching.

Matches available biomass (aggregated from farm data, e.g. bagasse, leaves,
press_mud — see sugarcane_data.csv) against buyer demand using a linear
program (PuLP / CBC), maximizing profit, minimizing emissions, or balancing
both.

Data model (plain dict/list — JSON friendly, no project-specific classes
existed yet, so this schema is introduced here and documented for reuse):

biomass_cluster:
    Single cluster dict, OR a list of cluster dicts (multiple supply points).
    {
        "cluster_id": "C001",
        "location": "Kolhapur",                       # optional, for reference
        "latitude": 16.7050,                            # optional, enables routing (Feature 5)
        "longitude": 74.2433,                           # optional, enables routing (Feature 5)
        "available_biomass": {                        # tons available, by type
            "bagasse": 500.0,
            "leaves": 150.0,
            "press_mud": 60.0
        },
        "cost_per_ton": {                               # production/collection cost
            "bagasse": 12.0,
            "leaves": 8.0,
            "press_mud": 5.0
        },
        "emissions_per_ton": {                          # kg CO2e per ton (processing)
            "bagasse": 40.0,
            "leaves": 30.0,
            "press_mud": 20.0
        }
    }

buyers:
    List of buyer dicts.
    {
        "buyer_id": "B001",
        "name": "Cogen Plant A",
        "accepted_biomass_types": ["bagasse"],          # optional; default = all types
        "demand_tons": 300.0,                           # max total tons this buyer takes
        "price_per_ton": 35.0,                          # revenue per ton
        "latitude": 18.5204,                            # optional, enables routing (Feature 5)
        "longitude": 73.8567,                           # optional, enables routing (Feature 5)
        "transport_cost_per_ton": 4.0,                  # fallback only, used if no lat/lon on either side
        "emissions_factor_per_ton": 10.0                # fallback only, used if no lat/lon on either side
    }

Transport (Role A / Feature 5, routing_engine.py):
    When both the cluster and the buyer have "latitude"/"longitude", transport
    cost and emissions are computed via routing_engine.calculate_transport()
    using Haversine distance, and are deducted from profit / added to
    emissions automatically. If either side lacks coordinates, this falls
    back to the buyer's flat "transport_cost_per_ton" / "emissions_factor_per_ton".

Usage:
    result = optimize_biomass_match(biomass_cluster, buyers, objective="balanced")
"""

from __future__ import annotations

from typing import Any, Dict, List, Union

import pulp

from routing_engine import calculate_transport

BiomassCluster = Union[Dict[str, Any], List[Dict[str, Any]]]


def _as_cluster_list(biomass_cluster: BiomassCluster) -> List[Dict[str, Any]]:
    """Normalize a single cluster dict or a list of clusters into a list."""
    if isinstance(biomass_cluster, dict):
        return [biomass_cluster]
    if isinstance(biomass_cluster, list):
        return biomass_cluster
    raise TypeError("biomass_cluster must be a dict or a list of dicts")


def optimize_biomass_match(
    biomass_cluster: BiomassCluster,
    buyers: List[Dict[str, Any]],
    objective: str = "balanced",
    carbon_price_per_kg: float = 0.05,
    min_utilization: float = 0.95,
) -> Dict[str, Any]:
    """
    Match biomass supply to buyers using linear programming.

    Args:
        biomass_cluster: One cluster dict or a list of cluster dicts (see module docstring).
        buyers: List of buyer dicts (see module docstring).
        objective: "profit" | "emissions" | "balanced" (default).
            - "profit": maximize total profit (revenue - cost).
            - "emissions": minimize total emissions. To avoid the trivial
              zero-shipment solution, this mode requires at least
              `min_utilization` fraction of the maximum matchable volume
              (min of total supply, total demand, per biomass type) to be
              shipped, then finds the lowest-emission way to do it.
            - "balanced": maximize (profit - carbon_price_per_kg * emissions),
              i.e. profit net of a carbon cost. Tune with carbon_price_per_kg.
        carbon_price_per_kg: $ cost per kg CO2e, used only for "balanced".
        min_utilization: fraction (0-1) of max matchable volume required for
            "emissions" mode. Ignored for other objectives.

    Returns:
        JSON-serializable dict with status, objective, matches, and totals.
    """
    if objective not in ("profit", "emissions", "balanced"):
        raise ValueError('objective must be "profit", "emissions", or "balanced"')

    clusters = _as_cluster_list(biomass_cluster)
    if not clusters:
        raise ValueError("biomass_cluster must contain at least one cluster")
    if not buyers:
        raise ValueError("buyers must be a non-empty list")

    all_types = sorted({t for c in clusters for t in c.get("available_biomass", {})})

    prob = pulp.LpProblem("biomass_matching", pulp.LpMaximize)

    # Decision variables: tons shipped from cluster c to buyer b of type t.
    x: Dict[tuple, pulp.LpVariable] = {}
    for c in clusters:
        cid = c["cluster_id"]
        available = c.get("available_biomass", {})
        for b in buyers:
            bid = b["buyer_id"]
            accepted = b.get("accepted_biomass_types", all_types)
            for t in accepted:
                if available.get(t, 0) > 0:
                    x[(cid, bid, t)] = pulp.LpVariable(
                        f"x_{cid}_{bid}_{t}", lowBound=0
                    )

    if not x:
        raise ValueError("No valid (cluster, buyer, biomass_type) combinations found")

    # --- Expressions -----------------------------------------------------
    def buyer_of(bid):
        return next(b for b in buyers if b["buyer_id"] == bid)

    def cluster_of(cid):
        return next(c for c in clusters if c["cluster_id"] == cid)

    # Per-(cluster, buyer) transport rate cache. Transport cost/emissions
    # depend only on the cluster-buyer pair (distance), not on biomass type,
    # so the per-ton rate is a constant LP coefficient -- computed once via
    # routing_engine.calculate_transport(..., biomass_tons=1.0).
    _route_cache: Dict[tuple, Dict[str, float]] = {}

    def route_rate(cid: str, bid: str) -> Dict[str, float]:
        key = (cid, bid)
        if key in _route_cache:
            return _route_cache[key]
        c, b = cluster_of(cid), buyer_of(bid)
        if "latitude" in c and "longitude" in c and "latitude" in b and "longitude" in b:
            route = calculate_transport(c, b, biomass_tons=1.0)
            rate = {
                "distance_km": route["distance_km"],
                "transport_cost_per_ton": route["transport_cost"],
                "transport_emissions_per_ton": route["transport_emissions_kg"],
            }
        else:
            # Fallback: no coordinates available, use flat per-ton fields if given.
            rate = {
                "distance_km": None,
                "transport_cost_per_ton": b.get("transport_cost_per_ton", 0.0),
                "transport_emissions_per_ton": b.get("emissions_factor_per_ton", 0.0),
            }
        _route_cache[key] = rate
        return rate

    revenue_terms, cost_terms, emissions_terms = [], [], []
    for (cid, bid, t), var in x.items():
        c = cluster_of(cid)
        b = buyer_of(bid)
        price = b.get("price_per_ton", 0.0)
        supply_cost = c.get("cost_per_ton", {}).get(t, 0.0)
        supply_emissions = c.get("emissions_per_ton", {}).get(t, 0.0)
        rate = route_rate(cid, bid)
        transport_cost = rate["transport_cost_per_ton"]
        transport_emissions = rate["transport_emissions_per_ton"]

        revenue_terms.append(price * var)
        cost_terms.append((supply_cost + transport_cost) * var)
        emissions_terms.append((supply_emissions + transport_emissions) * var)

    total_revenue = pulp.lpSum(revenue_terms)
    total_cost = pulp.lpSum(cost_terms)
    total_profit = total_revenue - total_cost
    total_emissions = pulp.lpSum(emissions_terms)

    # --- Constraints -------------------------------------------------------
    # Biomass availability: per cluster, per type.
    for c in clusters:
        cid = c["cluster_id"]
        for t, avail in c.get("available_biomass", {}).items():
            vars_ct = [var for (cc, bb, tt), var in x.items() if cc == cid and tt == t]
            if vars_ct:
                prob += pulp.lpSum(vars_ct) <= avail, f"avail_{cid}_{t}"

    # Buyer demand/capacity: total tons taken by a buyer across all types.
    for b in buyers:
        bid = b["buyer_id"]
        vars_b = [var for (cc, bb, tt), var in x.items() if bb == bid]
        if vars_b:
            prob += pulp.lpSum(vars_b) <= b.get("demand_tons", 0.0), f"demand_{bid}"

    # --- Objective -----------------------------------------------------
    if objective == "profit":
        prob += total_profit

    elif objective == "emissions":
        # Force meaningful utilization, then minimize emissions.
        total_supply = sum(c.get("available_biomass", {}).get(t, 0.0)
                            for c in clusters for t in all_types)
        total_demand = sum(b.get("demand_tons", 0.0) for b in buyers)
        max_matchable = min(total_supply, total_demand)
        prob += -total_emissions  # maximize negative emissions == minimize emissions
        if max_matchable > 0:
            prob += pulp.lpSum(x.values()) >= min_utilization * max_matchable, "min_utilization"

    else:  # balanced
        prob += total_profit - carbon_price_per_kg * total_emissions

    # --- Solve -----------------------------------------------------
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]

    matches = []
    for (cid, bid, t), var in x.items():
        qty = var.value() or 0.0
        if qty > 1e-6:
            c = cluster_of(cid)
            b = buyer_of(bid)
            price = b.get("price_per_ton", 0.0)
            supply_cost = c.get("cost_per_ton", {}).get(t, 0.0)
            supply_emissions = c.get("emissions_per_ton", {}).get(t, 0.0)
            rate = route_rate(cid, bid)
            transport_cost_per_ton = rate["transport_cost_per_ton"]
            transport_emissions_per_ton = rate["transport_emissions_per_ton"]

            revenue = round(qty * price, 2)
            cost = round(qty * (supply_cost + transport_cost_per_ton), 2)
            matches.append({
                "cluster_id": cid,
                "buyer_id": bid,
                "buyer_name": b.get("name"),
                "biomass_type": t,
                "tons": round(qty, 3),
                "distance_km": rate["distance_km"],
                "transport_cost": round(qty * transport_cost_per_ton, 2),
                "revenue": revenue,
                "cost": cost,
                "profit": round(revenue - cost, 2),
                "emissions_kg": round(qty * (supply_emissions + transport_emissions_per_ton), 2),
            })

    total_revenue_val = round(sum(m["revenue"] for m in matches), 2)
    total_cost_val = round(sum(m["cost"] for m in matches), 2)
    total_profit_val = round(total_revenue_val - total_cost_val, 2)
    total_emissions_val = round(sum(m["emissions_kg"] for m in matches), 2)
    total_tons_val = round(sum(m["tons"] for m in matches), 3)

    return {
        "status": status,
        "objective": objective,
        "matches": matches,
        "totals": {
            "tons_matched": total_tons_val,
            "revenue": total_revenue_val,
            "cost": total_cost_val,
            "profit": total_profit_val,
            "emissions_kg": total_emissions_val,
        },
    }


if __name__ == "__main__":
    example_cluster = {
        "cluster_id": "C001",
        "location": "Kolhapur",
        "latitude": 16.7050,
        "longitude": 74.2433,
        "available_biomass": {"bagasse": 500.0, "leaves": 150.0, "press_mud": 60.0},
        "cost_per_ton": {"bagasse": 12.0, "leaves": 8.0, "press_mud": 5.0},
        "emissions_per_ton": {"bagasse": 40.0, "leaves": 30.0, "press_mud": 20.0},
    }

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

    import json

    for obj in ("profit", "emissions", "balanced"):
        print(f"\n=== objective: {obj} ===")
        result = optimize_biomass_match(example_cluster, example_buyers, objective=obj)
        print(json.dumps(result, indent=2))
