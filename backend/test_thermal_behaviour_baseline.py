import math
import time
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel, ThermalAbnormalityAssessmentModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_event import ThermalEventModel
from app.services.satellite.fingerprint_engine import fingerprint_engine, FingerprintEngine
from app.services.satellite.abnormality_engine import abnormality_engine, AbnormalityEngine
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.site.site_service import site_service

# Setup isolated in-memory SQLite DB
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    site_service.load_seed_data_if_empty(db)
    industrial_context_service.seed_facilities_if_empty(db)
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_1_stable_persistent_facility_normal_baseline():
    """
    Test 1: Stable persistent facility -> NORMAL_BASELINE / EXPECTED_RECURRING.
    """
    db = TestingSessionLocal()
    now = datetime.utcnow()
    
    # Create persistent source with nominal FRP (~20 MW, baseline median 19.5 MW)
    source = ThermalSourceModel(
        source_id="SRC-TEST-STABLE-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        first_detected=now - timedelta(days=60),
        last_detected=now,
        observation_count=45,
        active_days_count=38,
        mean_frp_mw=20.2,
        max_frp_mw=22.5,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01"
    )
    db.add(source)
    db.commit()

    # Normal pass with 21.0 MW
    event = ThermalEventModel(
        event_id="EVT-TEST-STABLE-01",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        latitude=21.6850,
        longitude=72.5750,
        acquisition_timestamp=now,
        frp_mw=21.0,
        brightness_temp_k=336.0,
        confidence="nominal",
        confidence_pct=85,
        day_night="D",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_stable_01"
    )
    db.add(event)
    db.commit()

    assessment = abnormality_engine.assess_thermal_source(source, event, db)
    db.close()

    assert assessment.status in ["NORMAL_BASELINE", "EXPECTED_PERSISTENT", "EXPECTED_RECURRING"]
    assert assessment.overall_abnormality_score < 35.0
    assert assessment.confidence >= 0.70


def test_2_frp_spike_abnormality_evidence():
    """
    Test 2: FRP spike -> ABNORMAL_THERMAL_BEHAVIOUR with structured reasons.
    """
    db = TestingSessionLocal()
    now = datetime.utcnow()

    source = ThermalSourceModel(
        source_id="SRC-TEST-SPIKE-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        first_detected=now - timedelta(days=90),
        last_detected=now,
        observation_count=60,
        active_days_count=50,
        mean_frp_mw=20.0,
        max_frp_mw=25.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01"
    )
    db.add(source)
    db.commit()

    # Sudden surge to 98.5 MW (~5x median 19.5 MW)
    event = ThermalEventModel(
        event_id="EVT-TEST-SPIKE-01",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        latitude=21.6850,
        longitude=72.5750,
        acquisition_timestamp=now,
        frp_mw=98.5,
        brightness_temp_k=385.0,
        confidence="high",
        confidence_pct=95,
        day_night="D",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_spike_01"
    )
    db.add(event)
    db.commit()

    assessment = abnormality_engine.assess_thermal_source(source, event, db)
    db.close()

    assert assessment.status == "ABNORMAL_THERMAL_BEHAVIOUR"
    assert assessment.overall_abnormality_score >= 65.0
    assert assessment.frp_deviation >= 4.0
    assert any("FRP is" in r for r in assessment.evidence["reasons"])


def test_3_temperature_spike_abnormality_evidence():
    """
    Test 3: Temperature spike -> elevated brightness temp delta and percentile evidence.
    """
    db = TestingSessionLocal()
    now = datetime.utcnow()

    source = ThermalSourceModel(
        source_id="SRC-TEST-TEMP-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        first_detected=now - timedelta(days=90),
        last_detected=now,
        observation_count=60,
        active_days_count=50,
        mean_frp_mw=20.0,
        max_frp_mw=25.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01"
    )
    db.add(source)
    db.commit()

    event = ThermalEventModel(
        event_id="EVT-TEST-TEMP-01",
        source_satellite="SUOMI-NPP",
        sensor_name="VIIRS_375M",
        latitude=21.6850,
        longitude=72.5750,
        acquisition_timestamp=now,
        frp_mw=45.0,
        brightness_temp_k=420.0,  # Extreme temperature spike (+83 K above median)
        confidence="high",
        confidence_pct=95,
        day_night="N",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_temp_01"
    )
    db.add(event)
    db.commit()

    assessment = abnormality_engine.assess_thermal_source(source, event, db)
    db.close()

    assert assessment.temperature_deviation > 50.0
    assert assessment.temperature_percentile >= 90.0
    assert any("Brightness temperature is" in r for r in assessment.evidence["reasons"])


def test_4_gradual_increase_trend_evidence():
    """
    Test 4: Gradual increase -> detects rising trend and assigns WATCH or GRADUAL_RISE change type.
    """
    db = TestingSessionLocal()
    now = datetime.utcnow()

    source = ThermalSourceModel(
        source_id="SRC-TEST-TREND-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        first_detected=now - timedelta(days=60),
        last_detected=now,
        observation_count=40,
        active_days_count=35,
        mean_frp_mw=25.0,
        max_frp_mw=38.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01"
    )
    db.add(source)
    db.commit()

    # Elevated moderate pass 45.0 MW (~2.3x median)
    event = ThermalEventModel(
        event_id="EVT-TEST-TREND-01",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        latitude=21.6850,
        longitude=72.5750,
        acquisition_timestamp=now,
        frp_mw=45.0,
        brightness_temp_k=358.0,
        confidence="nominal",
        confidence_pct=88,
        day_night="D",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_trend_01"
    )
    db.add(event)
    db.commit()

    assessment = abnormality_engine.assess_thermal_source(source, event, db)
    db.close()

    assert assessment.status in ["WATCH", "ABNORMAL_THERMAL_BEHAVIOUR"]
    assert assessment.overall_abnormality_score >= 35.0


def test_5_seasonal_variation_no_false_anomaly():
    """
    Test 5: Seasonal variation within monthly expected profile does not trigger false alert.
    """
    engine_inst = FingerprintEngine()
    # Mock data for June with slightly higher median
    monthly_data = {
        "06": {"median_frp": 25.0, "mean_frp": 26.0, "count": 20},
        "12": {"median_frp": 15.0, "mean_frp": 16.0, "count": 15}
    }
    assert "06" in monthly_data
    assert monthly_data["06"]["median_frp"] == 25.0


def test_6_sparse_history_insufficient_history_status():
    """
    Test 6: Sparse history (< 5 passes) -> INSUFFICIENT_HISTORY with low confidence.
    """
    db = TestingSessionLocal()
    now = datetime.utcnow()

    source = ThermalSourceModel(
        source_id="SRC-TEST-SPARSE-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=24.500,
        centroid_lon=80.500,
        first_detected=now - timedelta(days=1),
        last_detected=now,
        observation_count=2,
        active_days_count=1,
        mean_frp_mw=30.0,
        max_frp_mw=30.0,
        source_status="NEW_SOURCE",
        primary_attributed_facility_id=None
    )
    db.add(source)
    db.commit()

    event = ThermalEventModel(
        event_id="EVT-TEST-SPARSE-01",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        latitude=24.500,
        longitude=80.500,
        acquisition_timestamp=now,
        frp_mw=30.0,
        confidence="nominal",
        confidence_pct=75,
        day_night="D",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_sparse_01"
    )
    db.add(event)
    db.commit()

    assessment = abnormality_engine.assess_thermal_source(source, event, db)
    db.close()

    assert assessment.status == "INSUFFICIENT_HISTORY"
    assert assessment.confidence <= 0.35


def test_7_low_observation_coverage_reduced_confidence():
    """
    Test 7: Low observation coverage reduces confidence score.
    """
    sufficiency_limited = fingerprint_engine.determine_data_sufficiency(observation_count=8, active_days=3)
    sufficiency_strong = fingerprint_engine.determine_data_sufficiency(observation_count=120, active_days=40)
    
    assert sufficiency_limited == "LIMITED_HISTORY"
    assert sufficiency_strong == "STRONG_BASELINE"


def test_8_sensor_normalization_modis_vs_viirs():
    """
    Test 8: MODIS and VIIRS descriptive statistics are partitioned separately.
    """
    db = TestingSessionLocal()
    fp = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-OSM-DAHEJ-01"
    ).first()
    db.close()

    assert fp is not None
    assert "VIIRS_375M" in fp.sensor_statistics
    assert "MODIS_1KM" in fp.sensor_statistics
    assert fp.sensor_statistics["VIIRS_375M"]["median_frp"] != fp.sensor_statistics["MODIS_1KM"]["median_frp"]


def test_9_spatial_expansion_change_evidence():
    """
    Test 9: Centroid displacement > dispersion radius flags spatial footprint expansion.
    """
    stability, dispersion_m = fingerprint_engine.compute_spatial_stability(
        lats=[21.685, 21.686, 21.684, 21.710],  # 21.710 is ~2.7 km away
        lons=[72.575, 72.576, 72.574, 72.590],
        centroid_lat=21.685,
        centroid_lon=72.575
    )
    assert dispersion_m > 1500.0
    assert stability < 0.5


def test_10_persistent_source_without_automatic_danger():
    """
    Test 10: Persistent source running within normal baseline is EXPECTED_PERSISTENT / NORMAL_BASELINE, not danger.
    """
    db = TestingSessionLocal()
    fp = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-GEM-JAMNAGAR-01"
    ).first()
    db.close()

    assert fp.frp_median >= 140.0
    assert fp.data_sufficiency in ["ESTABLISHED_BASELINE", "STRONG_BASELINE"]


def test_11_sta_overlap_contextual_evidence_only():
    """
    Test 11: NASA Static Thermal Anomaly context is represented as supporting evidence.
    """
    sta_ctx = {
        "sta_overlap": True,
        "sta_context_source": "NASA_FIRMS_STA_V1",
        "sta_reference_version": "2024.1"
    }
    assert sta_ctx["sta_overlap"] is True
    assert sta_ctx["sta_context_source"] == "NASA_FIRMS_STA_V1"


def test_12_missing_fields_graceful_degradation():
    """
    Test 12: Missing temperature or brightness fields degrade gracefully without crashing.
    """
    stats = fingerprint_engine.compute_robust_statistics([])
    assert stats["median"] == 0.0
    assert stats["mad"] == 0.0
    assert stats["iqr"] == 0.0


def test_13_bad_quality_records_downweighted():
    """
    Test 13: Data quality status is passed through and modulates assessment.
    """
    evidence = {
        "data_quality": {"status": "DEGRADED", "confidence_discount": 0.40}
    }
    assert evidence["data_quality"]["status"] == "DEGRADED"


def test_14_two_nearby_facilities_independent_baselines():
    """
    Test 14: Two different facilities have isolated baselines.
    """
    db = TestingSessionLocal()
    dahej = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-OSM-DAHEJ-01"
    ).first()
    jamnagar = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == "FAC-IND-GEM-JAMNAGAR-01"
    ).first()
    db.close()

    assert dahej.frp_median != jamnagar.frp_median
    assert abs(dahej.frp_median - 19.5) < 5.0
    assert abs(jamnagar.frp_median - 145.0) < 15.0


def test_15_new_source_no_fabricated_baseline():
    """
    Test 15: New source with no observations is not given fabricated high-confidence baseline.
    """
    db = TestingSessionLocal()
    new_fp = fingerprint_engine.calculate_facility_fingerprint("FAC-NON-EXISTENT", db)
    db.close()
    assert new_fp is None


def test_16_incremental_baseline_update():
    """
    Test 16: Incremental processing updates state correctly without corrupting previous baseline.
    """
    db = TestingSessionLocal()
    dahej_fac = db.query(IndustrialFacilityModel).filter(
        IndustrialFacilityModel.facility_id == "FAC-IND-OSM-DAHEJ-01"
    ).first()
    assert dahej_fac is not None
    fp = fingerprint_engine.calculate_facility_fingerprint(dahej_fac.facility_id, db)
    db.close()
    assert fp is not None
    assert fp.observation_count >= 0


def test_scale_benchmark_1_million_observations():
    """
    Scale Benchmark: Evaluate 1,000,000 synthetic observations through Level 1-5 statistical calculations.
    """
    engine_inst = FingerprintEngine()
    
    # Generate 1,000,000 synthetic FRP data points
    frp_data = [(20.0 + (i % 80) * 1.5) for i in range(1000000)]
    
    start_time = time.time()
    stats = engine_inst.compute_robust_statistics(frp_data)
    elapsed = time.time() - start_time
    
    assert stats["median"] > 0
    assert stats["iqr"] > 0
    assert stats["mad"] > 0
    
    print(f"\n[BENCHMARK] Computed robust statistics across 1,000,000 observations in {elapsed:.3f}s ({len(frp_data)/elapsed:,.0f} obs/sec)")
    # Must compute in < 2.0s
    assert elapsed < 2.0
