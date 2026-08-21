"""
database_manager.py
Manages Firestore backend for the biomass supply chain app.

Prereqs:
  pip install firebase-admin
  Place your Firebase service account key as serviceAccountKey.json
  in the same directory as this script.
"""

import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------------------------------------------------------
# 1. Initialize firebase_admin
# ---------------------------------------------------------------------------
def init_firebase():
    """Initializes the Firebase app using a local service account key.
    Safe to call multiple times (guards against re-initialization error)."""
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


db = init_firebase()


# ---------------------------------------------------------------------------
# 2. Push mock industry buyers to the `industries` collection
# ---------------------------------------------------------------------------
def setup_mock_buyers():
    """Pushes 3 mock industry buyers into the 'industries' Firestore collection."""
    mock_buyers = [
        {
            "id": "IND001",
            "facility_type": "Ethanol Plant",
            "remaining_capacity": 500,
            "price_per_ton": 2200,
            "distance_km": 18,
        },
        {
            "id": "IND002",
            "facility_type": "Power Cogeneration",
            "remaining_capacity": 850,
            "price_per_ton": 1950,
            "distance_km": 32,
        },
        {
            "id": "IND003",
            "facility_type": "Paper Mill",
            "remaining_capacity": 300,
            "price_per_ton": 2400,
            "distance_km": 45,
        },
    ]

    collection_ref = db.collection("industries")

    for buyer in mock_buyers:
        # Use the buyer's own id as the Firestore document ID for easy lookup
        collection_ref.document(buyer["id"]).set(buyer)
        print(f"Added buyer: {buyer['id']} ({buyer['facility_type']})")

    print(f"\nSuccessfully pushed {len(mock_buyers)} mock buyers to 'industries'.")


if __name__ == "__main__":
    setup_mock_buyers()
