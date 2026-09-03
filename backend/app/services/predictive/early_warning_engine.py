import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.services.predictive.anomaly_detector import anomaly_detector

class EarlyWarningEngine:
    """
    Industrial Pre-Incident Early Warning & Multi-Signal Fusion Engine:
    Fuses physical sensor excursions, ML isolation forest anomaly probabilities,
    acoustic ultrasonic detections, and maintenance turnaround state into an explainable safety score.
    """
    def evaluate_asset_pre_incident_state(
        self,
        asset_id: str,
        asset_name: str,
        chemical_name: str,
        pressure_bar: float,
        temperature_c: float,
        vibration_mm_s: float,
        acoustic_db: float,
        maintenance_age_days: int = 180,
        operating_mode: str = "NORMAL",
        vision_thermal_anomaly: bool = False
    ) -> Dict[str, Any]:
        
        # 1. Run Machine Learning Multivariate Anomaly Model
        ml_res = anomaly_detector.detect_multivariate_anomaly(
            asset_id, pressure_bar, temperature_c, vibration_mm_s, acoustic_db
        )

        # 2. Transparent Multi-Signal Evidence Scoring
        # A. Pressure excursion (0 - 25 pts)
        if asset_id == "T-04": # Ammonia nominal ~ 4.5 bar, High > 5.5 bar
            p_score = min(25.0, max(0.0, (pressure_bar - 4.2) * 12.0))
        elif asset_id == "T-03": # LPG nominal ~ 11.0 bar, High > 14.0 bar
            p_score = min(25.0, max(0.0, (pressure_bar - 11.0) * 5.0))
        else:
            p_score = min(25.0, max(0.0, (pressure_bar - 3.0) * 6.0))

        # B. Mechanical Vibration (0 - 25 pts) - Baseline < 2.0 mm/s, Warning > 4.5 mm/s, Alarm > 6.0 mm/s
        v_score = min(25.0, max(0.0, (vibration_mm_s - 1.5) * 5.5))

        # C. Thermal / Skin Temperature (0 - 20 pts)
        if asset_id == "T-04": # Cryogenic Ammonia (-33C baseline), warmup indicates insulation failure
            t_score = min(20.0, max(0.0, (temperature_c - (-33.0)) * 0.8))
        else:
            t_score = min(20.0, max(0.0, (temperature_c - 30.0) * 0.5))

        # D. Acoustic Micro-Leak (0 - 15 pts) - Baseline < 20 dB, Leak > 35 dB
        ac_score = min(15.0, max(0.0, (acoustic_db - 16.0) * 0.75))

        # E. Maintenance Turnaround Aging (0 - 15 pts)
        m_score = min(15.0, (maintenance_age_days / 365.0) * 15.0)

        # Base composite sum (0 - 100)
        raw_composite = p_score + v_score + t_score + ac_score + m_score

        # ML Anomaly probability boost / calibration
        ml_multiplier = 1.0 + (ml_res["anomaly_score"] * 0.25)
        if vision_thermal_anomaly:
            raw_composite += 12.0 # Optical/thermal hotspot confirmation

        total_risk_score = round(min(100.0, raw_composite * ml_multiplier), 1)

        # 3. State Classification & Urgent Interventions
        if total_risk_score >= 75.0:
            state = "CRITICAL"
            action = f"MANDATORY IMMEDIATE ACTION: Initiate emergency isolation and cooling protocol on {asset_id}; dispatch Hazmat inspection squad."
        elif total_risk_score >= 50.0:
            state = "PREVENTIVE"
            action = f"PREVENTIVE INTERVENTION REQUIRED: Perform seal retorquing, reduce process throughput, and pre-position water curtain."
        elif total_risk_score >= 30.0:
            state = "WATCH"
            action = f"OPERATIONAL WATCH: Increase telemetry sampling frequency and review thermal trends on next shift."
        else:
            state = "NORMAL"
            action = f"NOMINAL: Asset operating within design safety envelope."

        # Dominant drivers ranking
        drivers = [
            {"driver": "Operating Pressure Excursion", "score": round(p_score, 1), "weight": "HIGH" if p_score > 12 else "LOW"},
            {"driver": "Mechanical Bearing / Shaft Vibration", "score": round(v_score, 1), "weight": "HIGH" if v_score > 12 else "LOW"},
            {"driver": "Thermal Skin / Insulation Drift", "score": round(t_score, 1), "weight": "HIGH" if t_score > 10 else "LOW"},
            {"driver": "Acoustic Ultrasonic Leak Indicator", "score": round(ac_score, 1), "weight": "HIGH" if ac_score > 8 else "LOW"},
            {"driver": "Overdue Turnaround Maintenance", "score": round(m_score, 1), "weight": "HIGH" if m_score > 8 else "LOW"},
        ]
        drivers.sort(key=lambda x: x["score"], reverse=True)

        # Calibrated confidence based on multi-signal agreement
        signals_in_agreement = sum(1 for d in drivers if d["score"] > 5.0)
        confidence_pct = round(min(98.5, max(65.0, 50.0 + (signals_in_agreement * 11.5))), 1)

        return {
            "asset_id": asset_id,
            "asset_name": asset_name,
            "chemical_name": chemical_name,
            "early_warning_score": total_risk_score,
            "state": state,
            "confidence_pct": confidence_pct,
            "top_driver": drivers[0]["driver"],
            "drivers_breakdown": drivers,
            "recommended_preventive_action": action,
            "ml_anomaly_metadata": ml_res,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "safety_disclaimer": "NON-CERTIFIED DECISION SUPPORT MODEL. Validate with plant process safety engineer."
        }

early_warning_engine = EarlyWarningEngine()
