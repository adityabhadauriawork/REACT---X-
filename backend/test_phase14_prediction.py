import pytest
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.schemas.predictive import (
    HazardPrediction, HazardState, HazardFamily, TrendDirection,
    ForecastHorizon, UncertaintyState, PredictionEvaluationRequest
)
from app.services.predictive.change_point_detector import CUSUMChangePointDetector
from app.services.predictive.facility_anomaly_engine import FacilityAnomalyEngine
from app.services.predictive.hazard_trajectory_engine import HazardTrajectoryEngine
from app.services.predictive.hazard_prediction_service import HazardPredictionService
from app.services.predictive.backtesting_framework import TemporalBacktestEngine
from app.services.storage.predictive_repository import predictive_repository

client = TestClient(app)

# 1. CUSUM Change-Point Detector
def test_cusum_change_point_detector():
    detector = CUSUMChangePointDetector(slack_k_factor=0.5, threshold_h_factor=4.0)
    
    # Case A: Steady nominal values (mean 25.0, std 1.0)
    normal_series = [25.0, 25.2, 24.8, 25.1, 24.9, 25.3]
    res_norm = detector.evaluate_series(normal_series, baseline_mean=25.0, baseline_std=1.0)
    assert res_norm["change_detected"] is False
    assert res_norm["change_strength"] == 0.0

    # Case B: Significant upward shift (25 -> 32)
    drift_series = [25.0, 25.2, 27.5, 29.8, 32.4, 35.0]
    res_drift = detector.evaluate_series(drift_series, baseline_mean=25.0, baseline_std=1.0)
    assert res_drift["change_detected"] is True
    assert res_drift["change_direction"] == "UPWARD"
    assert res_drift["change_strength"] > 0.3

# 2. Facility-Specific Anomaly Engine
def test_facility_anomaly_engine():
    engine = FacilityAnomalyEngine()
    
    # T-04 Nominal: Temp -33C, Press 4.2 bar, Gas 0.5 ppm, Flow 120
    norm_res = engine.score_observations("T-04", -33.0, 4.2, 0.5, 120.0)
    assert norm_res["is_anomaly"] is False
    assert norm_res["anomaly_score"] < 0.35

    # T-04 Severe Excursion: Temp -10C (+23C warmup), Press 5.8 bar, Gas 8.0 ppm
    anom_res = engine.score_observations("T-04", -10.0, 5.8, 8.0, 120.0)
    assert anom_res["is_anomaly"] is True
    assert anom_res["anomaly_score"] > 0.60
    assert anom_res["max_z_score"] > 4.0

# 3. Hazard Trajectory & Trend Classification
def test_hazard_trajectory_engine_trend():
    engine = HazardTrajectoryEngine()
    
    # A. High Value but STABLE (Temp 80°C flat)
    vals_stable = [80.0, 80.1, 79.9, 80.0]
    t_sec = [0.0, 30.0, 60.0, 90.0]
    res_stable = engine.compute_trajectory(vals_stable, t_sec, baseline_critical_limit=95.0)
    assert res_stable["trend"] == TrendDirection.STABLE
    assert abs(res_stable["slope_per_min"]) < 0.8

    # B. High Value and RAPIDLY RISING (Temp 50 -> 75°C in 90s)
    vals_rising = [50.0, 58.0, 67.0, 75.0]
    res_rising = engine.compute_trajectory(vals_rising, t_sec, baseline_critical_limit=95.0)
    assert res_rising["trend"] == TrendDirection.RAPIDLY_RISING
    assert res_rising["slope_per_min"] > 10.0

# 4. Multi-Horizon Forecast Projection & Horizon Validation
def test_hazard_trajectory_horizon_projection():
    engine = HazardTrajectoryEngine()
    
    # 5m horizon valid
    proj_5m = engine.project_horizon(current_val=50.0, slope_per_min=2.0, acceleration=0.0, horizon=ForecastHorizon.HORIZON_5M)
    assert proj_5m["supported"] is True
    assert proj_5m["projected_value"] == 60.0 # 50 + 2*5
    assert proj_5m["upper_bound_95"] > 60.0

    # 30m horizon unsupported -> INSUFFICIENT_EVIDENCE
    proj_30m = engine.project_horizon(current_val=50.0, slope_per_min=2.0, acceleration=0.0, horizon=ForecastHorizon.HORIZON_30M)
    assert proj_30m["supported"] is False

# 5. Layer 4 Central Hazard Prediction Service
def test_hazard_prediction_service_evaluation():
    service = HazardPredictionService()
    pred = service.evaluate_facility_hazard(facility_id="FAC-IN-DAHEJ-001", asset_id="T-04")
    
    assert pred.facility_id == "FAC-IN-DAHEJ-001"
    assert pred.asset_id == "T-04"
    assert pred.hazard_family in HazardFamily
    assert pred.current_state in HazardState
    assert 0.0 <= pred.escalation_probability <= 1.0
    assert 0.0 <= pred.calibrated_confidence <= 1.0

# 6. Signal Gate & Stale Telemetry Degradation
def test_signal_gate_stale_telemetry_degradation():
    service = HazardPredictionService()
    # Force stale telemetry
    pred = service.evaluate_facility_hazard(facility_id="FAC-IN-DAHEJ-001", asset_id="T-04", force_stale=True)
    
    assert pred.uncertainty_state == UncertaintyState.DEGRADED
    assert pred.telemetry_freshness == "STALE"
    assert "[DEGRADED]" in pred.recommendation_reason

# 7. Signal Gate & Missing Sensors Abstention
def test_signal_gate_missing_sensors_abstention():
    service = HazardPredictionService()
    # Simulate missing critical temperature and pressure transmitters
    pred = service.evaluate_facility_hazard(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        simulate_missing_sensors=["TEMP", "PRESS"]
    )
    assert pred.uncertainty_state == UncertaintyState.INSUFFICIENT_EVIDENCE
    assert pred.data_sufficiency == "INSUFFICIENT"
    assert "[ABSTENTION]" in pred.recommendation_reason

# 8. Feature Explanation Percentage Sum
def test_feature_explanation_decomposition():
    service = HazardPredictionService()
    pred = service.evaluate_facility_hazard(facility_id="FAC-IN-DAHEJ-001", asset_id="T-04")
    
    assert len(pred.top_contributing_features) >= 3
    total_pct = sum(f.contribution_pct for f in pred.top_contributing_features)
    # Total percentage sum should be close to 100%
    assert 98.0 <= total_pct <= 102.0

# 9. Predictive Timeline Points
def test_predictive_timeline_generation():
    service = HazardPredictionService()
    tl = service.get_predictive_timeline("FAC-IN-DAHEJ-001", "T-04")
    
    assert len(tl.timeline_points) == 5
    labels = [p.relative_time_label for p in tl.timeline_points]
    assert labels == ["t-10m", "t-5m", "NOW", "t+5m", "t+10m"]

# 10. Temporal Backtesting Engine
def test_temporal_backtesting_engine():
    engine = TemporalBacktestEngine()
    res = engine.run_walk_forward_backtest(scenario_name="THERMAL_ESCALATION", duration_minutes=15)
    
    assert res["no_future_leakage_verified"] is True
    assert res["precision_at_alert"] >= 0.70
    assert res["recall_at_alert"] >= 0.70
    assert res["brier_calibration_score"] < 0.15
    assert res["median_warning_lead_time_min"] > 0.0

# 11. Database Persistence & Querying
def test_predictive_repository_persistence():
    db = SessionLocal()
    try:
        service = HazardPredictionService()
        pred = service.evaluate_facility_hazard("FAC-IN-DAHEJ-001", "T-04")
        rec = predictive_repository.persist_prediction(db, pred)
        assert rec.prediction_id == pred.prediction_id

        latest = predictive_repository.get_latest_prediction(db, "FAC-IN-DAHEJ-001", "T-04")
        assert latest is not None
        assert latest.prediction_id == pred.prediction_id
    finally:
        db.close()

# 12. REST APIs
def test_prediction_api_endpoints():
    # A. Current
    res = client.get("/api/prediction/facilities/FAC-IN-DAHEJ-001/current?asset_id=T-04")
    assert res.status_code == 200
    assert res.json()["facility_id"] == "FAC-IN-DAHEJ-001"

    # B. Timeline
    res = client.get("/api/prediction/facilities/FAC-IN-DAHEJ-001/timeline?asset_id=T-04")
    assert res.status_code == 200
    assert len(res.json()["timeline_points"]) == 5

    # C. Explanation
    res = client.get("/api/prediction/facilities/FAC-IN-DAHEJ-001/explanation?asset_id=T-04")
    assert res.status_code == 200
    assert "feature_contributions" in res.json()

    # D. Deterministic evaluate POST
    res = client.post("/api/prediction/facilities/FAC-IN-DAHEJ-001/evaluate", json={
        "facility_id": "FAC-IN-DAHEJ-001",
        "asset_id": "T-04",
        "forecast_horizon": "10m",
        "force_stale_telemetry": False,
        "simulate_missing_sensors": []
    })
    assert res.status_code == 200
    assert res.json()["facility_id"] == "FAC-IN-DAHEJ-001"

    # E. Backtest endpoint
    res = client.post("/api/prediction/backtest", json={
        "scenario_name": "THERMAL_ESCALATION",
        "duration_minutes": 15
    })
    assert res.status_code == 200
    assert res.json()["no_future_leakage_verified"] is True

# 13. Performance Benchmarks
def test_prediction_performance_benchmarks():
    service = HazardPredictionService()
    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        service.evaluate_facility_hazard("FAC-IN-DAHEJ-001", "T-04")
        times.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(times) / len(times)
    p95_ms = sorted(times)[int(len(times) * 0.95)]
    
    # Layered prediction should execute in sub-50ms under CI/system load
    assert avg_ms < 50.0
    assert p95_ms < 100.0
