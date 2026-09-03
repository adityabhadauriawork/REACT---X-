import numpy as np
from typing import Dict, Any, List, Optional, Tuple

class CUSUMChangePointDetector:
    """
    Layer 1: Two-Sided Tabular Cumulative Sum (CUSUM) Sequential Change-Point Detector.
    Detects material shifts in process parameters (temperature, pressure, gas concentration)
    relative to facility baseline mean and standard deviation.
    """

    def __init__(self, slack_k_factor: float = 0.5, threshold_h_factor: float = 4.5):
        self.k_factor = slack_k_factor
        self.h_factor = threshold_h_factor

    def evaluate_series(
        self,
        values: List[float],
        baseline_mean: float,
        baseline_std: float
    ) -> Dict[str, Any]:
        """
        Runs CUSUM sequential accumulation over time-series values.
        """
        if not values or len(values) < 3:
            return {
                "change_detected": False,
                "change_strength": 0.0,
                "change_direction": "NONE",
                "cusum_high": 0.0,
                "cusum_low": 0.0,
                "sample_count": len(values)
            }

        std = max(0.01, baseline_std)
        k = self.k_factor * std
        h = self.h_factor * std

        s_high = 0.0
        s_low = 0.0
        change_detected = False
        change_direction = "NONE"
        max_deviation_ratio = 0.0

        for x in values:
            s_high = max(0.0, s_high + (x - baseline_mean - k))
            s_low = max(0.0, s_low - (x - baseline_mean + k))

            if s_high >= h:
                change_detected = True
                change_direction = "UPWARD"
                ratio = s_high / h
                if ratio > max_deviation_ratio:
                    max_deviation_ratio = ratio

            elif s_low >= h:
                change_detected = True
                change_direction = "DOWNWARD"
                ratio = s_low / h
                if ratio > max_deviation_ratio:
                    max_deviation_ratio = ratio

        strength = min(1.0, max_deviation_ratio / 3.0) if change_detected else 0.0

        return {
            "change_detected": change_detected,
            "change_strength": round(strength, 3),
            "change_direction": change_direction,
            "cusum_high": round(s_high, 2),
            "cusum_low": round(s_low, 2),
            "threshold_h": round(h, 2),
            "sample_count": len(values)
        }

cusum_detector = CUSUMChangePointDetector()
