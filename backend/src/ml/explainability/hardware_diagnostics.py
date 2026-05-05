"""
PERSON 3 — Hardware Anomaly Detection via CQR Violations
Detects hardware issues (broken sensors, tripped inverters, panel soiling) by monitoring
CQR prediction interval violations.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime

# ============================================================
# HARDWARE ANOMALY DETECTION
# ============================================================

class HardwareAnomalyDetector:
    """Detect hardware anomalies using CQR bounds violations"""
    
    def __init__(self, violation_threshold_hours: int = 7, verbose: bool = False):
        """
        Args:
            violation_threshold_hours: Consecutive hours below P10 to flag anomaly (default: 7)
            verbose: Print diagnostic messages
        """
        self.violation_threshold = violation_threshold_hours
        self.verbose = verbose
    
    def detect_anomaly(self, actuals: np.ndarray, p10_forecast: np.ndarray, 
                      plant_id: str = "unknown") -> Dict:
        """
        Detect hardware anomalies based on CQR lower bound violations.
        
        Args:
            actuals: Actual generation values (array of floats)
            p10_forecast: P10 (10th percentile) forecast (array of floats)
            plant_id: Plant identifier for reporting
        
        Returns:
            Dictionary with:
            - anomaly: bool (True if anomaly detected)
            - plant_id: str
            - violation_count: int (total hours below P10)
            - max_consecutive: int (longest consecutive violation streak)
            - violation_indices: List[int] (hour indices with violations)
            - consecutive_streaks: List[Dict] (each streak with start, end, duration)
            - severity: str ("none", "moderate", "severe")
            - recommendation: str (operator action)
            - timestamp: str
        """
        
        actuals = np.array(actuals)
        p10_forecast = np.array(p10_forecast)
        
        # Find violations: actual < P10
        violations = actuals < p10_forecast
        violation_indices = np.where(violations)[0].tolist()
        
        # Find consecutive streaks
        consecutive_streaks = self._find_consecutive_streaks(violations)
        
        # Identify max streak
        max_consecutive = max([s['duration'] for s in consecutive_streaks]) if consecutive_streaks else 0
        
        # Determine severity and anomaly flag
        anomaly_detected = max_consecutive >= self.violation_threshold
        severity = self._assess_severity(max_consecutive, len(violation_indices), len(actuals))
        recommendation = self._generate_recommendation(severity, plant_id)
        
        if self.verbose and anomaly_detected:
            print(f"[HARDWARE ANOMALY] {plant_id}: {max_consecutive}h consecutive P10 violations (threshold: {self.violation_threshold}h)")
        
        return {
            "anomaly": anomaly_detected,
            "plant_id": plant_id,
            "violation_count": int(np.sum(violations)),
            "max_consecutive_hours": int(max_consecutive),
            "violation_hours": violation_indices,
            "consecutive_streaks": consecutive_streaks,
            "severity": severity,
            "recommendation": recommendation,
            "timestamp": pd.Timestamp.now().isoformat(),
            "stats": {
                "total_hours": len(actuals),
                "violation_percentage": float(100 * np.sum(violations) / len(actuals)),
                "expected_violation_percentage": 10.0,  # P10 should be violated ~10% of time
                "p10_mean": float(np.mean(p10_forecast)),
                "actual_mean": float(np.mean(actuals)),
                "actual_min": float(np.min(actuals)),
                "p10_min": float(np.min(p10_forecast))
            }
        }
    
    def _find_consecutive_streaks(self, violations: np.ndarray) -> List[Dict]:
        """Find all consecutive streaks of violations"""
        streaks = []
        in_streak = False
        streak_start = None
        
        for i, v in enumerate(violations):
            if v and not in_streak:
                # Start new streak
                streak_start = i
                in_streak = True
            elif not v and in_streak:
                # End streak
                streak_end = i - 1
                duration = streak_end - streak_start + 1
                streaks.append({
                    'start_hour': int(streak_start),
                    'end_hour': int(streak_end),
                    'duration': int(duration),
                    'hours': list(range(streak_start, streak_end + 1))
                })
                in_streak = False
        
        # Handle streak that extends to end
        if in_streak:
            streak_end = len(violations) - 1
            duration = streak_end - streak_start + 1
            streaks.append({
                'start_hour': int(streak_start),
                'end_hour': int(streak_end),
                'duration': int(duration),
                'hours': list(range(streak_start, streak_end + 1))
            })
        
        return streaks
    
    def _assess_severity(self, max_consecutive: int, total_violations: int, 
                         total_hours: int) -> str:
        """Assess severity of anomaly"""
        if max_consecutive < self.violation_threshold:
            return "none"
        elif max_consecutive >= self.violation_threshold and max_consecutive < 2 * self.violation_threshold:
            return "moderate"
        else:
            return "severe"
    
    def _generate_recommendation(self, severity: str, plant_id: str) -> str:
        """Generate operator recommendation based on severity"""
        recommendations = {
            "none": "✓ No action required. Generation within expected variance.",
            "moderate": f"⚠️ {plant_id}: Monitor closely. Possible sensor drift or temporary shading. Check next 24h.",
            "severe": f"🚨 {plant_id}: URGENT. Possible hardware failure (inverter trip, panel soiling, sensor fault). Inspect immediately."
        }
        return recommendations.get(severity, "Unknown")


def detect_hardware_anomalies_batch(plant_data: Dict[str, Dict], 
                                    violation_threshold: int = 7) -> Dict:
    """
    Run anomaly detection for multiple plants.
    
    Args:
        plant_data: {plant_id: {"actuals": [...], "p10": [...]}, ...}
        violation_threshold: Hours threshold for anomaly flag
    
    Returns:
        Dictionary with results for each plant and system summary
    """
    detector = HardwareAnomalyDetector(violation_threshold_hours=violation_threshold)
    
    results = {}
    anomalies_detected = []
    
    for plant_id, data in plant_data.items():
        if 'actuals' not in data or 'p10' not in data:
            continue
        
        result = detector.detect_anomaly(
            data['actuals'],
            data['p10'],
            plant_id
        )
        
        results[plant_id] = result
        if result['anomaly']:
            anomalies_detected.append(plant_id)
    
    # System-level summary
    return {
        "timestamp": pd.Timestamp.now().isoformat(),
        "plants": results,
        "anomalies_detected": anomalies_detected,
        "total_plants": len(plant_data),
        "summary": {
            "healthy_plants": len(plant_data) - len(anomalies_detected),
            "anomalous_plants": len(anomalies_detected),
            "system_status": "✓ HEALTHY" if not anomalies_detected else "⚠️ ANOMALIES DETECTED"
        }
    }


__all__ = ['HardwareAnomalyDetector', 'detect_hardware_anomalies_batch']
