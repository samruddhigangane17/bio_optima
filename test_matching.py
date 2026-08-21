"""
test_matching.py
-----------------
BioOptima — sanity tests for matching_service.find_best_match(), which
integrates optimization_engine.py (LP) and routing_engine.py (Haversine
transport) end to end.

Run:
    python3 test_matching.py
"""

from matching_service import find_best_match

cluster = {
    "cluster_id": "C001",
    "location": "Kolhapur",
    "latitude": 16.7050,
    "longitude": 74.2433,
    "available_biomass": {"bagasse": 500.0, "leaves": 150.0, "press_mud": 60.0},
    "cost_per_ton": {"bagasse": 12.0, "leaves": 8.0, "press_mud": 5.0},
    "emissions_per_ton": {"bagasse": 40.0, "leaves": 30.0, "press_mud": 20.0},
}

buyers = [
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


def test_profit_objective_selects_a_buyer():
    result = find_best_match(cluster, buyers, objective="profit")
    assert result["optimization_status"] == "Optimal", result
    assert result["selected_buyer"] is not None, "Expected a buyer to be selected"
    assert result["allocated_biomass_tons"] > 0
    assert result["distance_km"] is not None and result["distance_km"] > 0
    assert result["transport_cost"] >= 0
    assert result["revenue"] >= 0
    assert result["emissions_kg"] >= 0
    print("test_profit_objective_selects_a_buyer: PASS ->", result["selected_buyer"])


def test_balanced_objective_runs_end_to_end():
    result = find_best_match(cluster, buyers, objective="balanced")
    assert result["optimization_status"] == "Optimal", result
    assert result["selected_buyer"] is not None
    # revenue - transport_cost - supply_cost should reconcile with final_profit
    # (supply cost isn't broken out separately here, so just sanity-check ordering)
    assert result["revenue"] >= result["final_profit"]
    print("test_balanced_objective_runs_end_to_end: PASS ->", result["selected_buyer"])


def test_emissions_objective_runs_end_to_end():
    result = find_best_match(cluster, buyers, objective="emissions")
    assert result["optimization_status"] == "Optimal", result
    assert result["selected_buyer"] is not None
    print("test_emissions_objective_runs_end_to_end: PASS ->", result["selected_buyer"])


def test_no_feasible_match_returns_empty_result():
    # Buyer with zero demand -> nothing can be allocated to it, and it's the
    # only buyer, so the LP should return no matches.
    zero_demand_buyers = [
        {
            "buyer_id": "B999",
            "name": "Zero Demand Buyer",
            "accepted_biomass_types": ["bagasse"],
            "demand_tons": 0.0,
            "price_per_ton": 35.0,
            "latitude": 18.5204,
            "longitude": 73.8567,
        }
    ]
    result = find_best_match(cluster, zero_demand_buyers, objective="profit")
    assert result["selected_buyer"] is None
    assert result["allocated_biomass_tons"] == 0.0
    assert "message" in result
    print("test_no_feasible_match_returns_empty_result: PASS ->", result["message"])


def test_invalid_objective_raises():
    try:
        find_best_match(cluster, buyers, objective="not_a_real_objective")
    except ValueError:
        print("test_invalid_objective_raises: PASS")
        return
    raise AssertionError("Expected ValueError for an invalid objective")


if __name__ == "__main__":
    test_profit_objective_selects_a_buyer()
    test_balanced_objective_runs_end_to_end()
    test_emissions_objective_runs_end_to_end()
    test_no_feasible_match_returns_empty_result()
    test_invalid_objective_raises()
    print("\nAll tests passed.")
