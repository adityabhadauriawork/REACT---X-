import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.thermal_event import ThermalEventModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel, SourceFacilityCandidateModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel, ThermalAbnormalityAssessmentModel
from app.services.satellite.fingerprint_engine import fingerprint_engine
from app.services.satellite.abnormality_engine import abnormality_engine
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.satellite.clustering_engine import clustering_engine
from app.services.satellite.source_attribution_engine import source_attribution_engine

# In-memory SQLite with StaticPool for fast isolated tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        industrial_context_service.seed_facilities_if_empty(db)
        fingerprint_engine.seed_initial_fingerprints_if_empty(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# 1. ROBUST STATISTICS & LEVEL 2 METRICS
# =============================================================================

def test_robust_statistics_calculation():
    # Symmetric distribution
    symmetric_data = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0]
    stats_sym = fingerprint_engine.compute_robust_statistics(symmetric_data)
    assert stats_sym["median"] == 16.0
    assert stats_sym["iqr"] > 0
    assert stats_sym["mad"] > 0

    # Highly skewed distribution with extreme outlier
    skewed_data = [15.0, 16.0, 16.5, 17.0, 17.5, 18.0, 19.0, 200.0]
    stats_skewed = fingerprint_engine.compute_robust_statistics(skewed_data)
    # Median and MAD should be resistant to the single extreme 200.0 outlier
    assert stats_skewed["median"] < 20.0
    assert stats_skewed["mad"] < 5.0
    assert stats_skewed["mean"] > stats_skewed["median"]  # Mean pulled by outlier


# =============================================================================
# 2. DATA SUFFICIENCY & MULTI-MONTH HISTORICAL BASELINES
# =============================================================================

def test_data_sufficiency_tiers():
    assert fingerprint_engine.determine_data_sufficiency(2, 1) == "INSUFFICIENT_HISTORY"
    assert fingerprint_engine.determine_data_sufficiency(8, 4) == "LIMITED_HISTORY"
    assert fingerprint_engine.determine_data_sufficiency(45, 20) == "ESTABLISHED_BASELINE"
    assert fingerprint_engine.determine_data_sufficiency(150, 60) == "STRONG_BASELINE"


# =============================================================================
# 3. TEST 1 & TEST 2: STABLE FACILITY & RECURRENT NORMAL OPERATION
# =============================================================================

def test_normal_baseline_and_expected_persistent(db_session):
    now = datetime.utcnow()
    
    # Create persistent source at Dahej PetroChem Unit 04 with normal FRP (20.5 MW vs 19.5 median)
    src_normal = ThermalSourceModel(
        source_id="SRC-TEST-NORM-01",
        name="Dahej Flare Stack Alpha",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        h3_index="872c02829ffffff",
        first_detected=now - timedelta(days=90),
        last_detected=now,
        active_days_count=60,
        observation_count=75,
        unique_satellite_count=3,
        mean_frp_mw=21.0,
        max_frp_mw=28.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01",
        primary_attributed_facility_name="PetroChem Complex Alpha - Unit 04",
        is_inside_facility_boundary=True
    )
    db_session.add(src_normal)
    db_session.commit()

    ev_normal = ThermalEventModel(
        event_id="EVT-NORM-01",
        dedup_key="K-NORM-01",
        source="NASA_FIRMS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now,
        latitude=21.6850,
        longitude=72.5750,
        frp_mw=20.5,  # Within normal baseline
        brightness_temp_k=338.0,
        day_night="N",
        is_live_data=True
    )

    assessment = abnormality_engine.assess_thermal_source(src_normal, ev_normal, db_session)
    assert assessment.status in ["NORMAL_BASELINE", "EXPECTED_PERSISTENT"]
    assert assessment.overall_abnormality_score < 35.0
    assert assessment.confidence >= 0.75  # High confidence due to established baseline
    assert "within normal" in assessment.evidence["reasons"][0].lower()


# =============================================================================
# 4. TEST 3 & TEST 4: SUDDEN FRP SPIKE & TEMPERATURE SPIKE
# =============================================================================

def test_sudden_frp_and_temperature_spike_abnormality(db_session):
    now = datetime.utcnow()
    
    # Source at Dahej PetroChem (normally 19.5 MW median) experiencing severe surge (92.0 MW)
    src_spike = ThermalSourceModel(
        source_id="SRC-TEST-SPIKE-01",
        name="Dahej Flare Stack Alpha",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        h3_index="872c02829ffffff",
        first_detected=now - timedelta(days=90),
        last_detected=now,
        active_days_count=60,
        observation_count=75,
        unique_satellite_count=3,
        mean_frp_mw=21.0,
        max_frp_mw=92.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01",
        primary_attributed_facility_name="PetroChem Complex Alpha - Unit 04",
        is_inside_facility_boundary=True
    )
    db_session.add(src_spike)
    db_session.commit()

    ev_spike = ThermalEventModel(
        event_id="EVT-SPIKE-01",
        dedup_key="K-SPIKE-01",
        source="NASA_FIRMS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now,
        latitude=21.6850,
        longitude=72.5750,
        frp_mw=92.0,  # 4.7x baseline median!
        brightness_temp_k=395.0,  # Elevated temperature (+58 K above median)
        day_night="N",
        is_live_data=True
    )

    assessment = abnormality_engine.assess_thermal_source(src_spike, ev_spike, db_session)
    assert assessment.status == "ABNORMAL_THERMAL_BEHAVIOUR"
    assert assessment.overall_abnormality_score >= 65.0
    assert assessment.frp_deviation >= 4.0
    assert assessment.frp_robust_zscore >= 5.0
    assert assessment.temperature_deviation >= 40.0
    assert assessment.confidence >= 0.80

    # Verify explainable reasons payload
    reasons = assessment.evidence["reasons"]
    assert any("FRP is" in r and "baseline" in r for r in reasons)
    assert any("temperature is" in r.lower() for r in reasons)


# =============================================================================
# 5. TEST 5 & TEST 7: SPARSE HISTORY & LOW SATELLITE COVERAGE
# =============================================================================

def test_sparse_history_and_low_coverage_separation(db_session):
    now = datetime.utcnow()
    
    # Solitary new observation in an unmonitored location
    src_sparse = ThermalSourceModel(
        source_id="SRC-TEST-SPARSE-01",
        name="Remote Solitary Hotspot",
        centroid_lat=25.4500,
        centroid_lon=81.8500,
        h3_index="872cb4049ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=1,
        unique_satellite_count=1,
        mean_frp_mw=65.0,
        max_frp_mw=65.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id=None
    )
    db_session.add(src_sparse)
    db_session.commit()

    ev_sparse = ThermalEventModel(
        event_id="EVT-SPARSE-01",
        dedup_key="K-SPARSE-01",
        source="NASA_FIRMS",
        source_satellite="SUOMI-NPP",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now,
        latitude=25.4500,
        longitude=81.8500,
        frp_mw=65.0,
        day_night="D",
        is_live_data=True
    )

    assessment = abnormality_engine.assess_thermal_source(src_sparse, ev_sparse, db_session)
    assert assessment.status == "INSUFFICIENT_HISTORY"
    # Strict separation: Confidence MUST be low (0.30) due to lack of historical baseline
    assert assessment.confidence <= 0.35


# =============================================================================
# 6. TEST 9 & TEST 11: SPATIAL STABILITY & MULTI-FACILITY ISOLATION
# =============================================================================

def test_spatial_stability_and_multi_facility_isolation(db_session):
    # Facility 1: Dahej (Baseline median ~19.5 MW)
    fp_dahej = db_session.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-OSM-DAHEJ-01"
    ).first()
    assert fp_dahej is not None
    assert fp_dahej.frp_median < 25.0
    assert fp_dahej.spatial_stability_score >= 0.90

    # Facility 2: Jamnagar Mega Refinery (Baseline median ~145 MW)
    fp_jam = db_session.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-GEM-JAMNAGAR-01"
    ).first()
    assert fp_jam is not None
    assert fp_jam.frp_median >= 140.0
    assert fp_jam.spatial_stability_score >= 0.95

    # 145 MW is completely NORMAL for Jamnagar, but would be highly ABNORMAL for Dahej!
    assert fp_jam.frp_median > (fp_dahej.frp_median * 5.0)


# =============================================================================
# 7. FASTAPI REST ENDPOINTS INTEGRATION TESTS
# =============================================================================

def test_fastapi_thermal_fingerprint_endpoints(client, db_session):
    # 1. Query fingerprints list
    res_fps = client.get("/api/thermal/fingerprints")
    assert res_fps.status_code == 200
    fps_data = res_fps.json()
    assert len(fps_data) >= 6
    first_fp = fps_data[0]
    assert "frp_median" in first_fp
    assert "frp_iqr" in first_fp
    assert "frp_mad" in first_fp
    assert "data_sufficiency" in first_fp

    # 2. Query single fingerprint deep-dive
    fp_id = first_fp["fingerprint_id"]
    res_detail = client.get(f"/api/thermal/fingerprints/{fp_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "frp_statistics" in detail_data
    assert "hourly_distribution" in detail_data
    assert "sensor_statistics" in detail_data

    # 3. Query Facility Thermal Health for UI
    res_health = client.get("/api/thermal/facilities/FAC-IND-OSM-DAHEJ-01/thermal-health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert "thermal_health_status" in health_data
    assert "historical_median_frp_mw" in health_data
    assert "historical_iqr_frp_mw" in health_data
    assert "historical_range_mw" in health_data
    assert len(health_data["evidence_reasons"]) >= 1

    # 4. Query Abnormalities List and GeoJSON Map Layer
    res_abn = client.get("/api/thermal/abnormalities")
    assert res_abn.status_code == 200

    res_geojson = client.get("/api/thermal/abnormalities/geojson")
    assert res_geojson.status_code == 200
    geojson_data = res_geojson.json()
    assert geojson_data["type"] == "FeatureCollection"

    # 5. Query Phase 7 Prepared ML Features
    res_ml = client.get("/api/thermal/ml-features")
    assert res_ml.status_code == 200


# =============================================================================
# 8. SCALE & PERFORMANCE BENCHMARK (500,000 SYNTHETIC OBSERVATIONS)
# =============================================================================

def test_scale_performance_500k_fingerprints():
    # Benchmark the mathematical Layer 1-5 statistical computation on 500,000 raw floating point values
    import random
    random.seed(42)
    
    # 500,000 synthetic observations representing multi-year VIIRS/MODIS archive
    raw_frps = [random.gauss(25.0, 6.0) for _ in range(500000)]
    
    start_time = time.time()
    stats = fingerprint_engine.compute_robust_statistics(raw_frps)
    duration = time.time() - start_time
    
    print(f"\n[BENCHMARK] 500,000 observations processed in {duration:.3f}s ({len(raw_frps)/duration:.0f} obs/sec)")
    assert duration < 2.5  # Sub-2.5 second throughput for 500,000 observations
    assert 24.5 <= stats["median"] <= 25.5
    assert 24.5 <= stats["mean"] <= 25.5
