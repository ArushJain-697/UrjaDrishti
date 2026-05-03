import pandas as pd

# Asset registry — 6 plants across 2 clusters
# Cluster 1: Pavagada region (solar-dominant)
# Cluster 2: Gadag region (wind-dominant)
# 2 mixed plants added for generalization

ASSET_REGISTRY = [
    # --- Cluster 1: Pavagada Solar ---
    {
        "plant_id": "PVG_S1",
        "type": "solar",
        "cluster_id": "C1_Pavagada",
        "capacity_mw": 150,
        "latitude": 14.5,
        "longitude": 77.2,
        "altitude_m": 700,
        "tilt_angle_deg": 15,
        "azimuth_deg": 180,           # south-facing
        "technology_class": "crystalline_silicon",
        "hub_height_m": None,
    },
    {
        "plant_id": "PVG_S2",
        "type": "solar",
        "cluster_id": "C1_Pavagada",
        "capacity_mw": 120,
        "latitude": 14.52,
        "longitude": 77.25,
        "altitude_m": 710,
        "tilt_angle_deg": 12,
        "azimuth_deg": 180,
        "technology_class": "crystalline_silicon",
        "hub_height_m": None,
    },
    # --- Cluster 2: Gadag Wind ---
    {
        "plant_id": "GAD_W1",
        "type": "wind",
        "cluster_id": "C2_Gadag",
        "capacity_mw": 100,
        "latitude": 15.4,
        "longitude": 75.6,
        "altitude_m": 650,
        "tilt_angle_deg": None,
        "azimuth_deg": None,
        "technology_class": "HAWT",
        "hub_height_m": 100,
    },
    {
        "plant_id": "GAD_W2",
        "type": "wind",
        "cluster_id": "C2_Gadag",
        "capacity_mw": 80,
        "latitude": 15.43,
        "longitude": 75.63,
        "altitude_m": 660,
        "tilt_angle_deg": None,
        "azimuth_deg": None,
        "technology_class": "HAWT",
        "hub_height_m": 90,
    },
    # --- Mixed plants (for generalization) ---
    {
        "plant_id": "MIX_S1",
        "type": "solar",
        "cluster_id": "C1_Pavagada",
        "capacity_mw": 90,
        "latitude": 14.48,
        "longitude": 77.18,
        "altitude_m": 690,
        "tilt_angle_deg": 18,
        "azimuth_deg": 175,
        "technology_class": "crystalline_silicon",
        "hub_height_m": None,
    },
    {
        "plant_id": "MIX_W1",
        "type": "wind",
        "cluster_id": "C2_Gadag",
        "capacity_mw": 60,
        "latitude": 15.38,
        "longitude": 75.58,
        "altitude_m": 640,
        "tilt_angle_deg": None,
        "azimuth_deg": None,
        "technology_class": "HAWT",
        "hub_height_m": 85,
    },
]

def get_registry_df():
    return pd.DataFrame(ASSET_REGISTRY)

if __name__ == "__main__":
    df = get_registry_df()
    print(df.to_string())
    import os
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/asset_registry.csv", index=False)
    print("\nSaved to data/asset_registry.csv")