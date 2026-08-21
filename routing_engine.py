"""
routing_engine.py
------------------
BioOptima — Role A / Feature 5: Routing.

Computes straight-line (Haversine) distance between a biomass cluster and a
buyer, and the resulting transport cost and transport emissions for a given
tonnage. Designed to plug into optimization_engine.py so transport cost is
deducted from profit and transport emissions are added to total emissions.

Expected inputs (extends the schema used in optimization_engine.py):

cluster / buyer dicts must each include:
    "latitude": float
    "longitude": float

Optional overrides (checked on buyer first, then cluster, else defaults):
    "transport_cost_per_ton_km": float   # $ per ton per km, default 0.08
    "transport_emissions_per_ton_km": float  # kg CO2e per ton per km, default 0.12
"""

from __future__ import annotations

import math
from typing import Any, Dict

EARTH_RADIUS_KM = 6371.0
DEFAULT_COST_PER_TON_KM = 0.08       # $ per ton per km
DEFAULT_EMISSIONS_PER_TON_KM = 0.12  # kg CO2e per ton per km


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def calculate_transport(
    cluster: Dict[str, Any],
    buyer: Dict[str, Any],
    biomass_tons: float,
) -> Dict[str, Any]:
    """
    Calculate transport distance, cost, and emissions for moving
    `biomass_tons` of biomass from `cluster` to `buyer`.

    Args:
        cluster: dict with "latitude" and "longitude".
        buyer: dict with "latitude" and "longitude". May optionally override
            "transport_cost_per_ton_km" / "transport_emissions_per_ton_km".
        biomass_tons: tons being shipped.

    Returns:
        JSON-serializable dict:
        {
            "distance_km": float,
            "cost_per_ton_km": float,
            "emissions_per_ton_km": float,
            "transport_cost": float,          # total $ for biomass_tons
            "transport_emissions_kg": float,  # total kg CO2e for biomass_tons
        }
    """
    for entity, label in ((cluster, "cluster"), (buyer, "buyer")):
        if "latitude" not in entity or "longitude" not in entity:
            raise ValueError(
                f"{label} dict must include 'latitude' and 'longitude' for routing"
            )

    distance_km = haversine_distance(
        cluster["latitude"], cluster["longitude"],
        buyer["latitude"], buyer["longitude"],
    )

    cost_rate = buyer.get(
        "transport_cost_per_ton_km",
        cluster.get("transport_cost_per_ton_km", DEFAULT_COST_PER_TON_KM),
    )
    emissions_rate = buyer.get(
        "transport_emissions_per_ton_km",
        cluster.get("transport_emissions_per_ton_km", DEFAULT_EMISSIONS_PER_TON_KM),
    )

    transport_cost = distance_km * cost_rate * biomass_tons
    transport_emissions_kg = distance_km * emissions_rate * biomass_tons

    return {
        "distance_km": round(distance_km, 2),
        "cost_per_ton_km": cost_rate,
        "emissions_per_ton_km": emissions_rate,
        "transport_cost": round(transport_cost, 2),
        "transport_emissions_kg": round(transport_emissions_kg, 2),
    }


if __name__ == "__main__":
    import json

    example_cluster = {"cluster_id": "C001", "latitude": 16.7050, "longitude": 74.2433}  # Kolhapur
    example_buyer = {"buyer_id": "B001", "latitude": 18.5204, "longitude": 73.8567}       # Pune

    result = calculate_transport(example_cluster, example_buyer, biomass_tons=50.0)
    print(json.dumps(result, indent=2))
