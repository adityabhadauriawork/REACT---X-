import math
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from app.schemas.predictive import TrendDirection, ForecastHorizon

class HazardTrajectoryEngine:
    """
    Layer 3: Hazard Trajectory & Trend Forecasting Engine.
    Computes 1st and 2nd derivatives (slope and acceleration), categorizes trend direction,
    and projects parameter trajectories across supported short horizons (1m, 5m, 10m).
    """

    def __init__(self):
        # Supported forecast horizons
        self.supported_horizons = {
            ForecastHorizon.HORIZON_1M: 60.0,
            ForecastHorizon.HORIZON_5M: 300.0,
            ForecastHorizon.HORIZON_10M: 600.0
        }

    def compute_trajectory(
        self,
        values: List[float],
        timestamps_sec: List[float],
        baseline_critical_limit: float
    ) -> Dict[str, Any]:
        """
        Calculates linear/polynomial regression slope, acceleration, and trend direction.
        """
        if not values or len(values) < 2:
            return {
                "trend": TrendDirection.STABLE,
                "slope_per_min": 0.0,
                "acceleration": 0.0,
                "current_value": values[-1] if values else 0.0,
                "projected_time_to_limit_sec": None
            }

        x = np.array(timestamps_sec) - timestamps_sec[0]
        y = np.array(values)
        n = len(values)

        # 1st order linear slope (per second -> per minute)
        if len(values) >= 2:
            slope_sec, intercept = np.polyfit(x, y, 1)
            slope_min = slope_sec * 60.0
        else:
            slope_min = 0.0

        # 2nd order acceleration if >= 4 points
        if n >= 4:
            poly2 = np.polyfit(x, y, 2)
            accel = poly2[0] * 3600.0 # per min^2
        else:
            accel = 0.0

        curr_val = float(values[-1])

        # Trend classification
        if slope_min > 5.0:
            trend = TrendDirection.RAPIDLY_RISING
        elif slope_min > 0.8:
            trend = TrendDirection.RISING
        elif slope_min < -5.0:
            trend = TrendDirection.RAPIDLY_FALLING
        elif slope_min < -0.8:
            trend = TrendDirection.FALLING
        else:
            trend = TrendDirection.STABLE

        # Time to threshold crossing
        time_to_limit_sec = None
        if slope_sec > 0.001 and curr_val < baseline_critical_limit:
            time_to_limit_sec = max(0.0, (baseline_critical_limit - curr_val) / slope_sec)

        return {
            "trend": trend,
            "slope_per_min": round(float(slope_min), 2),
            "acceleration": round(float(accel), 2),
            "current_value": round(curr_val, 2),
            "projected_time_to_limit_sec": round(time_to_limit_sec, 1) if time_to_limit_sec else None
        }

    def project_horizon(
        self,
        current_val: float,
        slope_per_min: float,
        acceleration: float,
        horizon: ForecastHorizon
    ) -> Dict[str, Any]:
        """
        Projects value into future horizon with uncertainty bounds.
        """
        if horizon not in self.supported_horizons:
            return {
                "horizon": horizon.value,
                "supported": False,
                "projected_value": current_val,
                "uncertainty_margin": 0.0,
                "reason": "Horizon exceeds validated high-frequency process model domain (max 10m)."
            }

        horizon_sec = self.supported_horizons[horizon]
        horizon_min = horizon_sec / 60.0

        # Polynomial projection: V(t + dt) = V + (slope * dt) + (0.5 * accel * dt^2)
        projected = current_val + (slope_per_min * horizon_min) + (0.5 * (acceleration / 60.0) * horizon_min**2)
        
        # Uncertainty widens with square root of time
        uncertainty = 0.4 * math.sqrt(horizon_min) * (1.0 + abs(slope_per_min) * 0.1)

        return {
            "horizon": horizon.value,
            "supported": True,
            "projected_value": round(float(projected), 2),
            "lower_bound_95": round(float(projected - 1.96 * uncertainty), 2),
            "upper_bound_95": round(float(projected + 1.96 * uncertainty), 2),
            "uncertainty_margin": round(float(uncertainty), 2)
        }

hazard_trajectory_engine = HazardTrajectoryEngine()
