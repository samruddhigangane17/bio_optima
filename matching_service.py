"""
matching_service.py
--------------------
BioOptima — integration layer for Role A Feature 4 (LP) + Feature 5 (Routing).

Pipeline: Biomass -> Transport -> LP -> Best Buyer

Does not reimplement LP or routing logic. It calls optimize_biomass_match()
(optimization_engine.py), which already calls calculate_transport()
(routing_engine.py) internally for every cluster-buyer pair, then reduces
the resulting multi-buyer allocation down to a single recommended "best
buyer" match.

"Best buyer" = the buyer with the highest aggregated profit in the LP's
solution (summed across every cluster/biomass-type leg routed to that
buyer). If a buyer receives biomass from more than one leg (e.g. more than
one cluster, or more than one biomass type), figures are summed, and
distance is reported as the tons-weighted average distance across those legs.

Usage:
    result = find_best_match(biomass_cluster, buyers, objective="balanced")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from optimization_engine import optimize_biomass_match, BiomassCluster


def _empty_result(status: str, message: str) -> Dict[str, Any]:
    return {
        "optimization_status": status,
        "selected_buyer": None,
        "allocated_biomass_tons": 0.0,
        "biomass_breakdown": [],
        "distance_km": None,
        "transport_cost": 0.0,
        "revenue": 0.0,
        "final_profit": 0.0,
        "emissions_kg": 0.0,
        "message": message,
    }


def find_best_match(
    biomass_cluster: BiomassCluster,
    buyers: List[Dict[str, Any]],
    objective: str = "balanced",
    **lp_kwargs: Any,
) -> Dict[str, Any]:
    """
    Run the full Biomass -> Transport -> LP -> Best Buyer pipeline and
    return the single best-matched buyer.

    Args:
        biomass_cluster: one cluster dict or list of cluster dicts (see
            optimization_engine.py docstring for schema, including optional
            "latitude"/"longitude" used for routing).
        buyers: list of buyer dicts (see optimization_engine.py docstring).
        objective: "profit" | "emissions" | "balanced" (passed through to
            optimize_biomass_match).
        **lp_kwargs: extra keyword args forwarded to optimize_biomass_match
            (e.g. carbon_price_per_kg, min_utilization).

    Returns:
        JSON-serializable dict:
        {
            "optimization_status": str,
            "selected_buyer": {"buyer_id": str, "name": str} | None,
            "allocated_biomass_tons": float,
            "biomass_breakdown": [{"cluster_id", "biomass_type", "tons", "distance_km"}],
            "distance_km": float | None,     # tons-weighted average across legs
            "transport_cost": float,
            "revenue": float,
            "final_profit": float,
            "emissions_kg": float,
            "message": str (only present when no match was found),
        }
    """
    lp_result = optimize_biomass_match(
        biomass_cluster, buyers, objective=objective, **lp_kwargs
    )
    status = lp_result["status"]
    matches = lp_result["matches"]

    if status != "Optimal":
        return _empty_result(status, f"LP did not reach an optimal solution (status: {status}).")

    if not matches:
        return _empty_result(status, "No feasible or profitable biomass-buyer match found.")

    # Aggregate LP legs per buyer.
    by_buyer: Dict[str, Dict[str, Any]] = {}
    for m in matches:
        bid = m["buyer_id"]
        agg = by_buyer.setdefault(bid, {
            "buyer_id": bid,
            "buyer_name": m["buyer_name"],
            "tons": 0.0,
            "transport_cost": 0.0,
            "revenue": 0.0,
            "profit": 0.0,
            "emissions_kg": 0.0,
            "legs": [],
        })
        agg["tons"] += m["tons"]
        agg["transport_cost"] += m["transport_cost"]
        agg["revenue"] += m["revenue"]
        agg["profit"] += m["profit"]
        agg["emissions_kg"] += m["emissions_kg"]
        agg["legs"].append({
            "cluster_id": m["cluster_id"],
            "biomass_type": m["biomass_type"],
            "tons": m["tons"],
            "distance_km": m["distance_km"],
        })

    # Best buyer = highest aggregated profit.
    best = max(by_buyer.values(), key=lambda a: a["profit"])

    total_tons = sum(leg["tons"] for leg in best["legs"])
    distance_km: Optional[float] = None
    if total_tons > 0:
        known_distance_legs = [leg for leg in best["legs"] if leg["distance_km"] is not None]
        if known_distance_legs:
            weighted = sum(leg["distance_km"] * leg["tons"] for leg in known_distance_legs)
            weighted_tons = sum(leg["tons"] for leg in known_distance_legs)
            distance_km = round(weighted / weighted_tons, 2) if weighted_tons else None

    return {
        "optimization_status": status,
        "selected_buyer": {"buyer_id": best["buyer_id"], "name": best["buyer_name"]},
        "allocated_biomass_tons": round(best["tons"], 3),
        "biomass_breakdown": best["legs"],
        "distance_km": distance_km,
        "transport_cost": round(best["transport_cost"], 2),
        "revenue": round(best["revenue"], 2),
        "final_profit": round(best["profit"], 2),
        "emissions_kg": round(best["emissions_kg"], 2),
    }


if __name__ == "__main__":
    import json

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

    for obj in ("profit", "emissions", "balanced"):
        print(f"\n=== find_best_match objective: {obj} ===")
        result = find_best_match(example_cluster, example_buyers, objective=obj)
        print(json.dumps(result, indent=2))
