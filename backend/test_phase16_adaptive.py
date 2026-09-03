import pytest
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.adaptive import (
    MonitoringLevel, AnalyticalPriority, FacilityCriticalityTier,
    AdaptiveMonitoringDecision, NationalPriorityItem
)
from app.services.adaptive.hysteresis_controller import hysteresis_controller, StateHysteresisController
from app.services.adaptive.priority_queue_manager import priority_queue_manager
from app.services.adaptive.adaptive_orchestrator_service import adaptive_orchestrator_service
from app.services.storage.adaptive_repository import adaptive_repository
from app.core.database import SessionLocal

client = TestClient(app)

# 1. Hysteresis Controller Tests
def test_hysteresis_immediate_escalation_and_cooldown_hold():
    ctrl = StateHysteresisController()
    fac_id = "FAC-TEST-HYSTERESIS"

    # A. Initial baseline
    eff, prev, in_cd, cd_sec = ctrl.process_level_transition(fac_id, MonitoringLevel.LEVEL_0_BASELINE)
    assert eff == MonitoringLevel.LEVEL_0_BASELINE
    assert in_cd is False

    # B. Immediate Upward Escalation (0s delay)
    eff, prev, in_cd, cd_sec = ctrl.process_level_transition(fac_id, MonitoringLevel.LEVEL_4_CRITICAL)
    assert eff == MonitoringLevel.LEVEL_4_CRITICAL
    assert prev == MonitoringLevel.LEVEL_0_BASELINE
    assert in_cd is False

    # C. Downward attempt while in cooldown -> Holds Level 4
    eff, prev, in_cd, cd_sec = ctrl.process_level_transition(fac_id, MonitoringLevel.LEVEL_0_BASELINE)
    assert eff == MonitoringLevel.LEVEL_4_CRITICAL
    assert in_cd is True
    assert cd_sec > 0.0

# 2. Priority Queue Manager Aging & Starvation Guard
def test_priority_queue_aging_and_starvation_prevention():
    snapshots = [
        {
            "facility_id": "FAC-A-CRITICAL",
            "facility_name": "Facility A",
            "hazard_state": "CRITICAL",
            "criticality": FacilityCriticalityTier.TIER_1_CRITICAL,
            "uncertainty_score": 0.05,
            "monitoring_level": MonitoringLevel.LEVEL_4_CRITICAL
        },
        {
            "facility_id": "FAC-B-NOMINAL-AGED",
            "facility_name": "Facility B",
            "hazard_state": "NORMAL",
            "criticality": FacilityCriticalityTier.TIER_1_CRITICAL,
            "uncertainty_score": 0.05,
            "monitoring_level": MonitoringLevel.LEVEL_0_BASELINE
        }
    ]

    # Simulate Facility B having not been observed for 400 seconds
    priority_queue_manager.update_observation_timestamp("FAC-A-CRITICAL", time.time() - 2.0)
    priority_queue_manager.update_observation_timestamp("FAC-B-NOMINAL-AGED", time.time() - 400.0)

    ranked = priority_queue_manager.rank_facilities(snapshots)
    assert len(ranked) == 2
    # Facility B gained +100 aging points, ensuring it rises in priority
    item_b = next(x for x in ranked if x.facility_id == "FAC-B-NOMINAL-AGED")
    assert item_b.priority_score > 100.0

# 3. Scenario A: Nominal Baseline (Level 0)
def test_scenario_a_nominal_baseline_level_0():
    hysteresis_controller.reset_facility("FAC-TEST-A")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-A",
        asset_id="T-04",
        force_hazard_state="NORMAL",
        force_instant_transition=True
    )
    assert dec.monitoring_level == MonitoringLevel.LEVEL_0_BASELINE
    assert dec.priority == AnalyticalPriority.LOW
    assert dec.applied_policy.telemetry_evaluation_window_sec == 60.0

# 4. Scenario B: Watch (Level 1)
def test_scenario_b_watch_level_1():
    hysteresis_controller.reset_facility("FAC-TEST-B")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-B",
        asset_id="T-04",
        force_hazard_state="WATCH",
        force_instant_transition=True
    )
    assert dec.monitoring_level == MonitoringLevel.LEVEL_1_WATCH
    assert dec.applied_policy.telemetry_evaluation_window_sec == 30.0

# 5. Scenario C: Abnormal & Conflict (Level 2)
def test_scenario_c_abnormal_and_conflict_level_2():
    hysteresis_controller.reset_facility("FAC-TEST-C")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-C",
        asset_id="T-04",
        force_hazard_state="CONFLICTING_EVIDENCE",
        force_instant_transition=True
    )
    assert dec.monitoring_level == MonitoringLevel.LEVEL_2_ABNORMAL
    assert dec.applied_policy.thermal_camera_tracking_mode == "CONTINUOUS_CONTOUR"

# 6. Scenario D: Hazard Developing (Level 3)
def test_scenario_d_hazard_developing_level_3():
    hysteresis_controller.reset_facility("FAC-TEST-D")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-D",
        asset_id="T-04",
        force_hazard_state="HAZARD_DEVELOPING",
        force_instant_transition=True
    )
    assert dec.monitoring_level == MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING
    assert dec.applied_policy.telemetry_sampling_interval_sec == 1.0

# 7. Scenario E: Acute Critical (Level 4)
def test_scenario_e_acute_critical_level_4():
    hysteresis_controller.reset_facility("FAC-TEST-E")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-E",
        asset_id="T-04",
        force_hazard_state="CRITICAL",
        force_instant_transition=True
    )
    assert dec.monitoring_level == MonitoringLevel.LEVEL_4_CRITICAL
    assert dec.priority == AnalyticalPriority.URGENT
    assert dec.applied_policy.telemetry_sampling_interval_sec == 0.5
    assert len(dec.value_of_information) > 0

# 8. Scenario F: Recovery Cooldown Holding
def test_scenario_f_recovery_cooldown_holding():
    fac_id = "FAC-TEST-F"
    hysteresis_controller.reset_facility(fac_id)
    # Escalate to Critical
    dec1 = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id=fac_id, asset_id="T-04", force_hazard_state="CRITICAL", force_instant_transition=False
    )
    assert dec1.monitoring_level == MonitoringLevel.LEVEL_4_CRITICAL

    # Immediate drop to Normal -> Hysteresis holds Critical
    dec2 = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id=fac_id, asset_id="T-04", force_hazard_state="NORMAL", force_instant_transition=False
    )
    assert dec2.monitoring_level == MonitoringLevel.LEVEL_4_CRITICAL
    assert dec2.is_in_cooldown is True
    assert dec2.cooldown_remaining_sec > 0.0

# 9. Scenario G: High Uncertainty & Value of Information
def test_scenario_g_high_uncertainty_and_missing_sensors():
    hysteresis_controller.reset_facility("FAC-TEST-G")
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id="FAC-TEST-G",
        asset_id="T-04",
        force_hazard_state="WATCH",
        force_uncertainty=0.65,
        force_missing_sources=["THERMAL_CAMERA"],
        force_instant_transition=True
    )
    assert dec.uncertainty_score == 0.65
    assert "THERMAL_CAMERA" in dec.requested_evidence or len(dec.value_of_information) > 0

# 10. Scenario H: National Priority Queue Ranking
def test_scenario_h_national_queue_ranking():
    db = SessionLocal()
    try:
        queue = adaptive_orchestrator_service.get_national_priority_queue(db=db)
        assert len(queue) >= 3
        # Ensure items are ordered descending by priority score
        scores = [item.priority_score for item in queue]
        assert scores == sorted(scores, reverse=True)
    finally:
        db.close()

# 11. Database Persistence DAO
def test_adaptive_repository_persistence():
    db = SessionLocal()
    try:
        dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
            facility_id="FAC-PERSIST-001",
            asset_id="T-04",
            force_hazard_state="ABNORMAL",
            force_instant_transition=True,
            db=db
        )
        rec = adaptive_repository.get_latest_decision(db, "FAC-PERSIST-001")
        assert rec is not None
        assert rec.monitoring_level == MonitoringLevel.LEVEL_2_ABNORMAL
    finally:
        db.close()

# 12. REST APIs & Human Acknowledgement
def test_adaptive_api_endpoints_and_acknowledgement():
    # A. Current
    res = client.get("/api/adaptive/facilities/FAC-IN-DAHEJ-001/current")
    assert res.status_code == 200
    data = res.json()
    assert "monitoring_level" in data
    assert "applied_policy" in data

    # B. History
    res = client.get("/api/adaptive/facilities/FAC-IN-DAHEJ-001/history")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # C. Explanation
    res = client.get("/api/adaptive/facilities/FAC-IN-DAHEJ-001/explanation")
    assert res.status_code == 200
    assert "reason" in res.json()

    # D. Priority Queue
    res = client.get("/api/adaptive/priority")
    assert res.status_code == 200
    assert len(res.json()) >= 3

    # E. Evaluate
    res = client.post("/api/adaptive/facilities/FAC-IN-DAHEJ-001/evaluate", json={
        "facility_id": "FAC-IN-DAHEJ-001",
        "asset_id": "T-04",
        "force_hazard_state": "CRITICAL"
    })
    assert res.status_code == 200
    assert res.json()["monitoring_level"] == "LEVEL_4_CRITICAL"

    # F. Acknowledge
    res = client.post("/api/adaptive/facilities/FAC-IN-DAHEJ-001/acknowledge", json={
        "operator_name": "Chief Safety Inspector",
        "notes": "Field team mobilized."
    })
    assert res.status_code == 200
    assert res.json()["acknowledged"] is True

# 13. Latency Benchmarks
def test_adaptive_latency_benchmarks():
    # Pure adaptive decision engine latency
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        hysteresis_controller.process_level_transition("FAC-BENCH", MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING)
        times.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(times) / len(times)
    assert avg_ms < 1.0
