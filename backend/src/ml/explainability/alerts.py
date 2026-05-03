"""
PERSON 3 — Explainability & Reconciliation
Day 1: SHAP-based alert template system
- Initialize SHAP explainer on toy LightGBM
- Define feature buckets and alert templates
- Generate human-readable alerts based on SHAP feature importance
"""

import shap
import lightgbm as lgb
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# FEATURE BUCKET DEFINITIONS & ALERT TEMPLATES
# ============================================================
FEATURE_BUCKETS = {
    'cloud_modification_factor': {
        'name': 'Cloud Cover',
        'negative_severity': 'warning',
        'positive_severity': 'success',
        'negative_message': 'forecast below expected due to cloud cover',
        'positive_message': 'clear skies support strong output'
    },
    'wind_speed': {
        'name': 'Wind Speed',
        'negative_severity': 'warning',
        'positive_severity': 'success',
        'negative_message': 'weak wind conditions limiting generation',
        'positive_message': 'strong wind conditions boost turbine output'
    },
    'temperature': {
        'name': 'Temperature',
        'negative_severity': 'info',
        'positive_severity': 'info',
        'negative_message': 'high temperature reduces PV efficiency',
        'positive_message': 'moderate temperature supports efficiency'
    },
    'time_of_day': {
        'name': 'Time of Day',
        'negative_severity': 'info',
        'positive_severity': 'success',
        'negative_message': 'early morning or late evening limits solar generation',
        'positive_message': 'peak solar hours drive strong output'
    },
    'irradiance': {
        'name': 'Irradiance',
        'negative_severity': 'warning',
        'positive_severity': 'success',
        'negative_message': 'low irradiance expected',
        'positive_message': 'high irradiance supports peak output'
    },
    'humidity': {
        'name': 'Humidity',
        'negative_severity': 'info',
        'positive_severity': 'info',
        'negative_message': 'high humidity may reduce generation',
        'positive_message': 'moderate humidity supports stable output'
    }
}

# ============================================================
# TOY MODEL FOR DAY 1 DEVELOPMENT
# ============================================================
class ShapExplainer:
    """SHAP explainer initialized once on toy model"""
    
    def __init__(self):
        """Create and train toy LightGBM model for SHAP"""
        np.random.seed(42)
        
        # Generate synthetic training data (24 hours × 30 days = 720 samples)
        n_samples = 720
        feature_names = [
            'cloud_modification_factor', 'wind_speed', 'temperature',
            'irradiance', 'humidity', 'time_of_day'
        ]
        
        # Create realistic-ish correlation structure
        X = pd.DataFrame({
            'cloud_modification_factor': np.random.uniform(0.2, 1.0, n_samples),
            'wind_speed': np.abs(np.random.normal(8, 4, n_samples)),
            'temperature': np.random.uniform(15, 45, n_samples),
            'irradiance': np.random.uniform(0, 850, n_samples),
            'humidity': np.random.uniform(20, 95, n_samples),
            'time_of_day': np.sin(np.linspace(0, 4*np.pi, n_samples))  # Daily cycle
        })
        
        # Target: weighted combination
        y = (
            X['cloud_modification_factor'] * 400 +
            X['wind_speed'] * 20 +
            X['time_of_day'] * 100 +
            X['humidity'] * -2 +
            np.random.normal(0, 50, n_samples)
        ).clip(0, 1000)
        
        # Train simple LightGBM
        self.model = lgb.LGBMRegressor(
            n_estimators=50,
            learning_rate=0.1,
            max_depth=5,
            verbose=-1
        )
        self.model.fit(X, y)
        
        # Initialize SHAP explainer
        self.explainer = shap.TreeExplainer(self.model)
        self.reference_X = X  # For base value computation
        self.feature_names = feature_names
        
        print("✓ SHAP Explainer initialized with toy LightGBM model")
    
    def get_shap_values(self, X: pd.DataFrame) -> np.ndarray:
        """Compute SHAP values for given features"""
        return self.explainer.shap_values(X)


# Initialize globally (once per app startup)
_shap_explainer = None

def _get_explainer():
    """Lazy initialization of SHAP explainer"""
    global _shap_explainer
    if _shap_explainer is None:
        _shap_explainer = ShapExplainer()
    return _shap_explainer


# ============================================================
# ALERT GENERATION LOGIC
# ============================================================
def _get_top_drivers(shap_values: np.ndarray, 
                     feature_names: List[str], 
                     top_k: int = 3) -> List[Dict]:
    """
    Extract top K most important features based on SHAP values
    Returns list of {feature: str, impact: float, is_positive: bool}
    """
    abs_shap = np.abs(shap_values)
    top_indices = np.argsort(abs_shap)[-top_k:][::-1]
    
    drivers = []
    for idx in top_indices:
        drivers.append({
            'feature': feature_names[idx],
            'impact': float(shap_values[idx]),
            'is_positive': shap_values[idx] > 0
        })
    return drivers


def _build_alert_message(driver: Dict, forecast_value: float) -> str:
    """
    Convert a SHAP driver into a plain-English alert message
    """
    feature = driver['feature']
    is_positive = driver['is_positive']
    
    # Check if feature exists in buckets
    if feature not in FEATURE_BUCKETS:
        return f"Feature '{feature}' affecting output"
    
    bucket = FEATURE_BUCKETS[feature]
    message_key = 'positive_message' if is_positive else 'negative_message'
    
    return bucket[message_key]


def generate_alerts(plant_id: str, p50: List[float], hours: List[int],
                   shap_values: Optional[np.ndarray] = None,
                   features: Optional[pd.DataFrame] = None) -> Dict:
    """
    Generate alert messages based on SHAP feature importance
    
    Args:
        plant_id: Plant identifier
        p50: List of P50 (median) forecast values
        hours: List of hour indices (0-23)
        shap_values: Optional pre-computed SHAP values
        features: Optional feature dataframe for computing SHAP on-demand
    
    Returns:
        {"alerts": [{"hour": int, "message": str, "type": str}, ...]}
    """
    try:
        explainer = _get_explainer()
        alerts = []
        
        # For Day 1: mock features if not provided
        if features is None:
            features = pd.DataFrame({
                'cloud_modification_factor': np.random.uniform(0.3, 0.9, len(hours)),
                'wind_speed': np.abs(np.random.normal(8, 3, len(hours))),
                'temperature': np.random.uniform(20, 40, len(hours)),
                'irradiance': p50,  # Use forecast as proxy for irradiance
                'humidity': np.random.uniform(40, 80, len(hours)),
                'time_of_day': np.sin(np.array(hours) / 12 * np.pi)
            })
        
        # Compute SHAP values if not provided
        if shap_values is None:
            shap_values = explainer.get_shap_values(features)
        
        # Generate alerts for each hour
        for hour_idx, (hour, p50_val) in enumerate(zip(hours, p50)):
            hour_shap = shap_values[hour_idx]
            
            # Get top 3 drivers for this hour
            drivers = _get_top_drivers(hour_shap, explainer.feature_names, top_k=3)
            
            # Primary alert from strongest driver
            if drivers:
                primary_driver = drivers[0]
                message = _build_alert_message(primary_driver, p50_val)
                
                # Determine alert severity
                if p50_val < 50:  # Low output
                    alert_type = 'warning'
                elif p50_val > 400:  # High output
                    alert_type = 'success'
                else:
                    alert_type = 'info'
                
                # Special case: peak hour
                if p50_val == max(p50):
                    message = f"Peak generation expected at {hour:02d}:00 — conditions favourable, high confidence interval"
                    alert_type = 'success'
                
                alerts.append({
                    'hour': hour,
                    'message': message,
                    'type': alert_type,
                    'top_drivers': [d['feature'] for d in drivers]
                })
        
        # Add atmospheric uncertainty alert
        if max(hours) >= 17:
            alerts.append({
                'hour': 17,
                'message': f"Atmospheric uncertainty rising for {plant_id} after 17:00 — intraday update recommended before evening scheduling",
                'type': 'info'
            })
        
        return {'alerts': alerts}
    
    except Exception as e:
        print(f"[ERROR] Alert generation failed: {e}")
        # Graceful fallback
        return {
            'alerts': [{
                'hour': hours[0] if hours else 0,
                'message': 'Forecast available — check dashboard for details',
                'type': 'info'
            }]
        }


# ============================================================
# EXPORT FOR SERVICE LAYER
# ============================================================
__all__ = ['generate_alerts', 'FEATURE_BUCKETS']