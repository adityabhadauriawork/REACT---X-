import pytest
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.discrimination import (
    LandCoverClass, ObservationQualityState, SourcePersistenceState,
    EOStructuralMatchStatus, DiscriminationAssessment
)
from app.services.satellite.land_cover_service import land_cover_service
from app.services.satellite.observation_quality_engine import observation_quality_engine
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.satellite.source_discrimination_service import source_discrimination_service
from app.services.storage.discrimination_repository import discrimination_repository
from app.core.database import SessionLocal

client = TestClient(app)

# 1. Land-Cover Service Resolution
def test_land_cover_resolution_and_consistency():
    # Dahej PCPIR industrial zone
    res_dahej = land_cover_service.resolve_land_cover(21.6850, 72.5620, facility_id="FAC-IN-DAHEJ-001")
    assert res_dahej.land_cover_class == LandCoverClass.INDUSTRIAL_BUILT_UP
    assert res_dahej.consistency_with_industrial >= 0.90

    # Punjab intensive cropland
    res_punjab = land_cover_service.resolve_land_cover(30.5000, 75.5000)
    assert res_punjab.land_cover_class == LandCoverClass.AGRICULTURE_CROPLAND
    assert res_punjab.consistency_with_industrial < 0.30

    # Gir forest region
    res_gir = land_cover_service.resolve_land_cover(21.1500, 70.8000)
    assert res_gir.land_cover_class == LandCoverClass.FOREST

# 2. Observation Quality & Reflection Flag
def test_observation_quality_and_specular_reflection_flag():
    # High solar elevation (zenith 15 deg), low FRP (2 MW), daytime, zero night detections -> Reflection Confound
    q_state, q_expl, is_refl = observation_quality_engine.evaluate_observation_quality(
        solar_zenith_deg=15.0,
        sensor_scan_angle_deg=20.0,
        cloud_cover_fraction=0.02,
        day_night="D",
        frp_mw=2.0,
        has_night_recurrence=False
    )
    assert q_state == ObservationQualityState.POTENTIAL_REFLECTION
    assert is_refl is True
    assert "specular solar glint" in q_expl

# 3. Observation Quality: Edge-of-Scan & Cloud Cover
def test_observation_quality_edge_of_scan_and_clouds():
    # Extreme scan angle
    q_state, _, _ = observation_quality_engine.evaluate_observation_quality(
        sensor_scan_angle_deg=58.0
    )
    assert q_state == ObservationQualityState.DEGRADED

    # Heavy cloud cover
    q_state, _, _ = observation_quality_engine.evaluate_observation_quality(
        cloud_cover_fraction=0.75
    )
    assert q_state == ObservationQualityState.POOR

# 4. EO Verification Selective Triggers
def test_eo_verification_selective_triggers():
    # Inside industrial facility -> Triggered
    assert eo_verification_service.is_verification_warranted(facility_id="FAC-IN-DAHEJ-001") is True
    # Near facility (<300m) -> Triggered
    assert eo_verification_service.is_verification_warranted(facility_distance_m=120.0) is True
    # High uncertainty -> Triggered
    assert eo_verification_service.is_verification_warranted(uncertainty_score=0.45) is True
    # Far wilderness, low FRP, low uncertainty -> Not triggered
    assert eo_verification_service.is_verification_warranted(facility_distance_m=2500.0, uncertainty_score=0.05, frp_mw=8.0) is False

# 5. EO Verification Structural Matching
def test_eo_verification_structural_matching():
    eo_res = eo_verification_service.verify_thermal_source(
        source_id="SRC-TEST-EO-01",
        latitude=21.6850,
        longitude=72.5620,
        facility_id="FAC-IN-DAHEJ-001",
        facility_distance_m=30.0
    )
    assert eo_res.structural_match_status == EOStructuralMatchStatus.STRONG_SPATIAL_MATCH
    assert len(eo_res.detected_structures) >= 2
    feature_types = [s.feature_type for s in eo_res.detected_structures]
    assert "FLARE_STACK" in feature_types or "PROCESS_UNIT" in feature_types

# 6. EO Verification Unavailable Handling
def test_eo_verification_unavailable_handling():
    eo_res = eo_verification_service.verify_thermal_source(
        source_id="SRC-TEST-EO-UNAVAIL",
        latitude=21.6850,
        longitude=72.5620,
        force_unavailable=True
    )
    assert eo_res.structural_match_status == EOStructuralMatchStatus.IMAGERY_UNAVAILABLE
    assert eo_res.cloud_cover_percent >= 80.0

# 7. Scenario: Gas Flare Discrimination
def test_scenario_gas_flare_discrimination():
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-FLARE-DAHEJ",
        latitude=21.6850,
        longitude=72.5620,
        mean_frp_mw=32.0,
        observation_count=50,
        active_days_count=35,
        diurnal_night_fraction=0.70,
        facility_id="FAC-IN-DAHEJ-001",
        is_inside_facility=True
    )
    assert asm.predicted_class == "GAS_FLARE"
    assert asm.classification_state == "CLASSIFIED"
    assert asm.persistence_state == SourcePersistenceState.PERSISTENT
    assert asm.eo_verification is not None
    assert len(asm.top_supporting_evidence) >= 2

# 8. Scenario: Routine Process Heat Discrimination
def test_scenario_routine_process_heat_discrimination():
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-HEAT-HAZIRA",
        latitude=21.1200,
        longitude=72.6800,
        mean_frp_mw=8.5,
        observation_count=20,
        active_days_count=12,
        diurnal_night_fraction=0.35,
        facility_id="FAC-IN-HAZIRA-002",
        is_inside_facility=True
    )
    assert asm.predicted_class == "ROUTINE_PROCESS_HEAT"
    assert asm.classification_state == "CLASSIFIED"

# 9. Scenario: Agricultural Burning Discrimination
def test_scenario_agricultural_burn_discrimination():
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-STUBBLE-PUNJAB",
        latitude=30.8000,
        longitude=75.8000,
        mean_frp_mw=12.0,
        observation_count=2,
        active_days_count=1,
        diurnal_night_fraction=0.05,
        facility_id=None,
        facility_name=None,
        facility_distance_m=12000.0,
        is_inside_facility=False
    )
    assert asm.predicted_class == "AGRICULTURAL_BURNING"
    assert asm.land_cover.land_cover_class == LandCoverClass.AGRICULTURE_CROPLAND

# 10. Scenario: Wildfire / Natural Discrimination
def test_scenario_wildfire_natural_discrimination():
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-WILDFIRE-GIR",
        latitude=21.1500,
        longitude=70.8000,
        mean_frp_mw=45.0,
        observation_count=3,
        active_days_count=2,
        diurnal_night_fraction=0.30,
        facility_id=None,
        facility_name=None,
        facility_distance_m=35000.0,
        is_inside_facility=False
    )
    assert asm.predicted_class == "WILDFIRE_NATURAL"
    assert asm.land_cover.land_cover_class == LandCoverClass.FOREST

# 11. Scenario: Potential Reflection Confound Abstention
def test_scenario_potential_reflection_abstention():
    asm = source_discrimination_service.discriminate_source(
        source_id="SRC-GLINT-DAY",
        latitude=21.6850,
        longitude=72.5620,
        mean_frp_mw=1.8,
        observation_count=1,
        active_days_count=1,
        diurnal_night_fraction=0.0,
        facility_id=None,
        facility_distance_m=2000.0,
        is_inside_facility=False,
        solar_zenith_deg=12.0 # High sun angle
    )
    assert asm.classification_state == "NEEDS_REVIEW"
    assert asm.is_potential_reflection is True
    assert asm.abstention_reason is not None

# 12. Database Persistence DAO
def test_discrimination_repository_persistence():
    db = SessionLocal()
    try:
        asm = source_discrimination_service.discriminate_source(
            source_id="SRC-PERSIST-001",
            latitude=21.6850,
            longitude=72.5620,
            facility_id="FAC-IN-DAHEJ-001",
            db=db
        )
        rec = discrimination_repository.get_latest_assessment(db, "SRC-PERSIST-001")
        assert rec is not None
        assert rec.source_id == "SRC-PERSIST-001"
        assert rec.land_cover.land_cover_class == LandCoverClass.INDUSTRIAL_BUILT_UP
    finally:
        db.close()

# 13. REST APIs & Verification Endpoint
def test_discrimination_api_endpoints():
    # A. Source detailed discrimination
    res = client.get("/api/discrimination/sources/SRC-API-01?lat=21.685&lon=72.562&facility_id=FAC-IN-DAHEJ-001")
    assert res.status_code == 200
    data = res.json()
    assert "predicted_class" in data
    assert "land_cover" in data

    # B. Land Cover lookup
    res = client.get("/api/discrimination/sources/SRC-API-01/land-cover?lat=21.685&lon=72.562")
    assert res.status_code == 200
    assert "land_cover_class" in res.json()

    # C. EO Verification
    res = client.get("/api/discrimination/sources/SRC-API-01/eo-verification?lat=21.685&lon=72.562&facility_id=FAC-IN-DAHEJ-001")
    assert res.status_code == 200
    assert "structural_match_status" in res.json()

    # D. Explanation
    res = client.get("/api/discrimination/sources/SRC-API-01/explanation?lat=21.685&lon=72.562&facility_id=FAC-IN-DAHEJ-001")
    assert res.status_code == 200
    assert "top_supporting_evidence" in res.json()

    # E. Trigger EO Verification POST
    res = client.post("/api/discrimination/sources/SRC-API-01/verify-eo", json={
        "latitude": 21.685,
        "longitude": 72.562,
        "facility_id": "FAC-IN-DAHEJ-001"
    })
    assert res.status_code == 200
    assert res.json()["structural_match_status"] == "STRONG_SPATIAL_MATCH"

# 14. Performance & Latency Benchmarks
def test_discrimination_performance_latency_benchmarks():
    times = []
    for _ in range(50):
        t0 = time.perf_counter()
        source_discrimination_service.discriminate_source(
            source_id="SRC-BENCH",
            latitude=21.6850,
            longitude=72.5620,
            facility_id="FAC-IN-DAHEJ-001"
        )
        times.append((time.perf_counter() - t0) * 1000.0)

    avg_ms = sum(times) / len(times)
    assert avg_ms < 5.0
