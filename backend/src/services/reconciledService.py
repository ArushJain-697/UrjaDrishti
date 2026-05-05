# Wire Day 4 MinT reconciliation from Person 3
from src.ml.explainability.reconciliation import get_reconciled as ml_reconciled

MOCK_RECONCILED = {
    "cluster_a": {
        "pre_mint":  {"plant_sum": 142.3, "cluster_forecast": 156.7, "consistent": False},
        "post_mint": {"plant_sum": 149.1, "cluster_forecast": 149.1, "consistent": True}
    },
    "cluster_b": {
        "pre_mint":  {"plant_sum": 87.4,  "cluster_forecast": 94.2,  "consistent": False},
        "post_mint": {"plant_sum": 90.8,  "cluster_forecast": 90.8,  "consistent": True}
    }
}

def get_reconciled():
    try:
        return ml_reconciled()
    except Exception as e:
        print(f"Reconciled error: {e} — falling back to mock")
        return MOCK_RECONCILED