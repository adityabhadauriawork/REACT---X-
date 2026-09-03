import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.schemas.fusion import (
    FusedHazardAssessment, FusedHazardState, EvidenceItem,
    EvidenceSourceType, EvidenceSupportState, FusionEvaluationRequest
)
from app.services.fusion.dempster_shafer_engine import ds_combiner
from app.services.fusion.evidence_normalizer import evidence_normalizer
from app.services.fusion.multimodal_fusion_service import multimodal_fusion_service
from app.services.fusion.ablation_service import ablation_service
from app.services.storage.fusion_repository import fusion_repository

client = TestClient(app)

# 1. Mathematical Dempster-Shafer Combination
def test_dempster_shafer_orthogonal_combination():
    ev1 = EvidenceItem(
        evidence_id="EV-1", facility_id="FAC-1", asset_id="T-04", zone_id="Z1",
        source_id="S1", source_type=EvidenceSourceType.TELEMETRY,
        evidence_type="temperature", observation_timestamp=datetime.now(timezone.utc),
        raw_value=15.0, unit="°C", normalized_score=0.80, quality="GOOD",
        freshness_status="LIVE", reliability_score=0.95, support_state=EvidenceSupportState.SUPPORTING
    )
    ev2 = EvidenceItem(
        evidence_id="EV-2", facility_id="FAC-1", asset_id="T-04", zone_id="Z1",
        source_id="CAM-1", source_type=EvidenceSourceType.THERMAL_CAMERA,
        evidence_type="thermal_hotspot", observation_timestamp=datetime.now(timezone.utc),
        raw_value=85.0, unit="°C", normalized_score=0.75, quality="GOOD",
        freshness_status="LIVE", reliability_score=0.90, support_state=EvidenceSupportState.SUPPORTING
    )

    res = ds_combiner.combine_evidence_items([ev1, ev2])
    assert res.hypothesis_masses.get("THERMAL_ESCALATION", 0.0) > 0.60
    assert res.conflict_mass_k < 0.10
    assert res.belief.get("THERMAL_ESCALATION", 0.0) > 0.60
    assert res.uncertainty_mass < 0.35

# 2. Dempster-Shafer Conflict Metric K
def test_dempster_shafer_conflict_k():
    # ev_fire supports THERMAL_ESCALATION
    ev_fire = EvidenceItem(
        evidence_id="EV-SAT", facility_id="FAC-1", asset_id="T-04", zone_id="Z1",
        source_id="SAT-1", source_type=EvidenceSourceType.SATELLITE,
        evidence_type="thermal_frp", observation_timestamp=datetime.now(timezone.utc),
        raw_value=35.0, unit="MW", normalized_score=0.90, quality="GOOD",
        freshness_status="FRESH", reliability_score=0.90, support_state=EvidenceSupportState.SUPPORTING
    )
    # ev_norm supports NORMAL
    ev_norm = EvidenceItem(
        evidence_id="EV-TEL", facility_id="FAC-1", asset_id="T-04", zone_id="Z1",
        source_id="S-TEL", source_type=EvidenceSourceType.TELEMETRY,
        evidence_type="temperature", observation_timestamp=datetime.now(timezone.utc),
        raw_value=-33.0, unit="°C", normalized_score=0.05, quality="GOOD",
        freshness_status="LIVE", reliability_score=0.95, support_state=EvidenceSupportState.CONTRADICTING
    )

    res = ds_combiner.combine_evidence_items([ev_fire, ev_norm])
    assert res.conflict_mass_k >= 0.40 # High orthogonal conflict

# 3. Evidence Normalization
def test_evidence_normalization_telemetry_and_vision():
    sat_ev = evidence_normalizer.generate_satellite_evidence("FAC-IN-DAHEJ-001", "T-04", force_anomaly=True)
    assert sat_ev.source_type == EvidenceSourceType.SATELLITE
    assert sat_ev.raw_value == 35.0
    assert sat_ev.unit == "MW"
    assert sat_ev.normalized_score > 0.70
    assert sat_ev.support_state == EvidenceSupportState.SUPPORTING

# 4. Scenario A: All Sources Agree Normal
def test_scenario_a_all_sources_agree_normal():
    from app.services.industrial.telemetry_simulator import telemetry_simulator, SimulationScenario
    from app.services.vision.camera_simulator import camera_simulator
    from app.services.vision.vision_pipeline_service import vision_pipeline_service
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)
    camera_simulator.set_scenario("NORMAL")
    vision_pipeline_service.generate_simulator_tick()
    asm = multimodal_fusion_service.evaluate_facility_fusion(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        force_satellite_anomaly=False
    )
    assert asm.fused_state in [FusedHazardState.NORMAL, FusedHazardState.WATCH]
    assert asm.confidence >= 0.70
    assert asm.conflict_mass_k < 0.40
    assert asm.human_review_required is False

# 5. Scenario E: Satellite Anomaly + Local Normal -> CONFLICTING_EVIDENCE
def test_scenario_e_satellite_anomaly_and_local_normal_conflict():
    asm = multimodal_fusion_service.evaluate_facility_fusion(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        force_satellite_anomaly=True # Satellite reports FRP surge while ground sensors report nominal baseline
    )
    assert asm.fused_state == FusedHazardState.CONFLICTING_EVIDENCE
    assert asm.conflict_mass_k >= 0.40
    assert asm.conflict_explanation is not None
    assert asm.human_review_required is True

# 6. Scenario F: Local Anomaly + Satellite Stale
def test_scenario_f_local_anomaly_satellite_stale():
    asm = multimodal_fusion_service.evaluate_facility_fusion(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        force_satellite_stale=True
    )
    assert any(s.freshness_status == "STALE" for s in asm.agreement_matrix.stale_signals)

# 7. Scenario I: Critical Modalities Missing -> INSUFFICIENT_EVIDENCE
def test_scenario_i_critical_modalities_missing():
    asm = multimodal_fusion_service.evaluate_facility_fusion(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        simulate_missing_sources=["TELEMETRY", "THERMAL_CAMERA"]
    )
    assert asm.fused_state == FusedHazardState.INSUFFICIENT_EVIDENCE
    assert asm.uncertainty_score >= 0.70
    assert asm.human_review_required is True

# 8. Scenario J: All Sources Unavailable -> UNAVAILABLE
def test_scenario_j_all_sources_unavailable():
    asm = multimodal_fusion_service.evaluate_facility_fusion(
        facility_id="FAC-IN-DAHEJ-001",
        asset_id="T-04",
        simulate_missing_sources=["TELEMETRY", "THERMAL_CAMERA", "CCTV", "PREDICTION", "SATELLITE"]
    )
    assert asm.fused_state == FusedHazardState.UNAVAILABLE
    assert asm.uncertainty_score == 1.0

# 9. Systematic Multimodal Ablation
def test_multimodal_ablation_benchmarks():
    results = ablation_service.run_ablation_suite()
    assert len(results) == 6

    # Full Multimodal Fusion must outperform single modality baselines
    sat_only = next(r for r in results if "Satellite Only" in r.modality_combination)
    full_fusion = next(r for r in results if "Full Multimodal" in r.modality_combination)

    assert full_fusion.precision > sat_only.precision
    assert full_fusion.recall > sat_only.recall
    assert full_fusion.false_alarm_rate < sat_only.false_alarm_rate
    assert full_fusion.warning_lead_time_min > sat_only.warning_lead_time_min

# 10. Database Persistence & Querying
def test_fusion_repository_persistence():
    db = SessionLocal()
    try:
        asm = multimodal_fusion_service.evaluate_facility_fusion("FAC-IN-DAHEJ-001", "T-04")
        rec = fusion_repository.persist_assessment(db, asm)
        assert rec.assessment_id == asm.assessment_id

        latest = fusion_repository.get_latest_assessment(db, "FAC-IN-DAHEJ-001", "T-04")
        assert latest is not None
        assert latest.assessment_id == asm.assessment_id
    finally:
        db.close()

# 11. REST API Endpoints
def test_fusion_api_endpoints():
    # A. Current
    res = client.get("/api/fusion/facilities/FAC-IN-DAHEJ-001/current?asset_id=T-04")
    assert res.status_code == 200
    assert res.json()["facility_id"] == "FAC-IN-DAHEJ-001"
    assert "dempster_shafer" in res.json()
    assert "agreement_matrix" in res.json()

    # B. Evidence
    res = client.get("/api/fusion/facilities/FAC-IN-DAHEJ-001/evidence?asset_id=T-04")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # C. Explanation
    res = client.get("/api/fusion/facilities/FAC-IN-DAHEJ-001/explanation?asset_id=T-04")
    assert res.status_code == 200
    assert "fused_state" in res.json()
    assert "recommended_action" in res.json()

    # D. Sources
    res = client.get("/api/fusion/facilities/FAC-IN-DAHEJ-001/sources")
    assert res.status_code == 200
    assert "calibrated_source_reliabilities" in res.json()

    # E. Deterministic POST evaluate
    res = client.post("/api/fusion/facilities/FAC-IN-DAHEJ-001/evaluate", json={
        "facility_id": "FAC-IN-DAHEJ-001",
        "asset_id": "T-04",
        "force_satellite_anomaly": True
    })
    assert res.status_code == 200
    assert res.json()["fused_state"] == "CONFLICTING_EVIDENCE"

    # F. Ablation POST
    res = client.post("/api/fusion/ablation")
    assert res.status_code == 200
    assert len(res.json()) == 6

# 12. Performance Benchmarks
def test_fusion_performance_latency_benchmarks():
    # A. End-to-end full multimodal pipeline latency
    times = []
    for _ in range(30):
        t0 = time.perf_counter()
        multimodal_fusion_service.evaluate_facility_fusion("FAC-IN-DAHEJ-001", "T-04")
        times.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(times) / len(times)
    p95_ms = sorted(times)[int(len(times) * 0.95)]
    
    assert avg_ms < 300.0
    assert p95_ms < 600.0

    # B. Pure Dempster-Shafer mathematical combination latency
    from app.schemas.fusion import EvidenceItem, EvidenceSourceType, EvidenceSupportState
    test_items = [
        EvidenceItem(
            evidence_id=f"EV-{i}", facility_id="FAC-1", asset_id="T-04", zone_id="Z1",
            source_id=f"S-{i}", source_type=EvidenceSourceType.TELEMETRY,
            evidence_type="temperature", observation_timestamp=datetime.now(timezone.utc),
            raw_value=25.0, unit="°C", normalized_score=0.8, quality="GOOD",
            freshness_status="LIVE", reliability_score=0.95, support_state=EvidenceSupportState.SUPPORTING
        ) for i in range(10)
    ]
    ds_times = []
    for _ in range(100):
        t0 = time.perf_counter()
        ds_combiner.combine_evidence_items(test_items)
        ds_times.append((time.perf_counter() - t0) * 1000.0)

    avg_ds_ms = sum(ds_times) / len(ds_times)
    assert avg_ds_ms < 20.0
