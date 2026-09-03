from typing import Dict, Any, Tuple, Optional
from app.schemas.discrimination import ObservationQualityState

class ObservationQualityEngine:
    """
    Evaluates observation geometry, solar zenith angles, and edge-of-scan distortions.
    Detects potential specular reflection confounds without silently deleting records.
    """

    def evaluate_observation_quality(
        self,
        solar_zenith_deg: float = 45.0,
        sensor_scan_angle_deg: float = 20.0,
        cloud_cover_fraction: float = 0.05,
        day_night: str = "D",
        frp_mw: float = 15.0,
        has_night_recurrence: bool = True
    ) -> Tuple[ObservationQualityState, str, bool]:
        """
        Returns (quality_state, quality_explanation, is_potential_reflection)
        """
        # Case 1: Potential Daytime Specular Glint / Reflection Confound
        # Daytime, high sun (zenith < 25 deg), low FRP (< 3.5 MW), and zero nighttime detections
        if day_night == "D" and solar_zenith_deg < 25.0 and frp_mw < 3.5 and not has_night_recurrence:
            return (
                ObservationQualityState.POTENTIAL_REFLECTION,
                f"Observation geometry warning: High solar elevation (zenith {solar_zenith_deg:.1f}°) and low FRP ({frp_mw:.1f} MW) with zero nighttime recurrence indicates potential specular solar glint.",
                True
            )

        # Case 2: Extreme Edge-of-Scan Distortion
        if sensor_scan_angle_deg > 55.0:
            return (
                ObservationQualityState.DEGRADED,
                f"Observation quality degraded: Extreme scan angle ({sensor_scan_angle_deg:.1f}°) introduces pixel footprint elongation and parallax error.",
                False
            )

        # Case 3: Heavy Cloud Obscuration
        if cloud_cover_fraction > 0.60:
            return (
                ObservationQualityState.POOR,
                f"Observation quality poor: Cloud cover fraction ({cloud_cover_fraction*100:.0f}%) significantly attenuates mid-wave infrared radiance.",
                False
            )

        # Case 4: Nominal High-Quality Observation
        return (
            ObservationQualityState.GOOD,
            f"Observation geometry nominal: Scan angle {sensor_scan_angle_deg:.1f}°, solar zenith {solar_zenith_deg:.1f}°, clear atmospheric transmittance.",
            False
        )

observation_quality_engine = ObservationQualityEngine()
