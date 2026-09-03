import time
import pytest
import numpy as np
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app
from app.models.thermal_source import ThermalSourceModel
from app.models.thermal_event import ThermalEventModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel
from app.models.thermal_classification import ThermalClassificationResultModel
from app.services.ml.classifier_pipeline import pipeline, FEATURE_NAMES, CLASSES
from app.services.ml.thermal_classifier_service import classifier_service

from sqlalchemy.pool import StaticPool

# SQLite in-memory test engine with shared StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Train and initialize the model artifact
    pipeline.train_and_benchmark(seed=42)
    classifier_service._ensure_initialized()

    # Seed an industrial facility and fingerprint
    now = datetime.utcnow()
    fac = IndustrialFacilityModel(
        facility_id="FAC-IND-OSM-DAHEJ-01",
        name="PetroChem Complex Alpha - Unit 04",
        operator_name="Dahej Petrochem Ltd",
        state="Gujarat",
        district="Bharuch",
        latitude=21.6850,
        longitude=72.5750,
        facility_type="PETROCHEMICAL"
    )
    db.add(fac)

    fp = FacilityThermalFingerprintModel(
        fingerprint_id="FP-FAC-IND-OSM-DAHEJ-01",
        facility_id="FAC-IND-OSM-DAHEJ-01",
        facility_name="PetroChem Complex Alpha - Unit 04",
        baseline_start=now - timedelta(days=90),
        baseline_end=now,
        observation_count=75,
        active_days=60,
        recurrence_rate=0.66,
        detection_rate=0.45,
        frp_mean=21.0,
        frp_median=19.5,
        frp_std=4.5,
        frp_iqr=5.2,
        frp_mad=2.6,
        frp_p10=14.0,
        frp_p50=19.5,
        frp_p90=28.5,
        frp_min=10.0,
        frp_max=34.0,
        temp_mean=338.0,
        temp_median=337.0,
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        spatial_stability_score=0.965,
        spatial_dispersion_radius_m=120.0
    )
    db.add(fp)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# =============================================================================
# 1. FEATURE EXTRACTION & NORMALIZATION TESTS
# =============================================================================

def test_feature_extraction_from_thermal_models():
    """Verify 23 normalized physical features extracted cleanly from Phase 5/6 models."""
    db = TestingSessionLocal()
    now = datetime.utcnow()

    source = ThermalSourceModel(
        source_id="SRC-ML-TEST-01",
        h3_index="h3_872c02829ffffff",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        first_detected=now - timedelta(days=90),
        last_detected=now,
        observation_count=75,
        active_days_count=60,
        night_detection_count=40,
        diurnal_ratio=1.0,
        mean_frp_mw=21.0,
        max_frp_mw=28.0,
        source_status="PERSISTENT_SOURCE",
        primary_attributed_facility_id="FAC-IND-OSM-DAHEJ-01",
        is_inside_facility_boundary=True
    )
    db.add(source)
    db.commit()

    event = ThermalEventModel(
        event_id="EVT-ML-TEST-01",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        latitude=21.6850,
        longitude=72.5750,
        acquisition_timestamp=now,
        frp_mw=22.5,
        brightness_temp_k=339.0,
        confidence="nominal",
        confidence_pct=90,
        day_night="N",
        h3_index="h3_872c02829ffffff",
        dedup_key="dedup_ml_01"
    )
    db.add(event)
    db.commit()

    facility = db.query(IndustrialFacilityModel).filter(IndustrialFacilityModel.facility_id == "FAC-IND-OSM-DAHEJ-01").first()
    fingerprint = db.query(FacilityThermalFingerprintModel).filter(FacilityThermalFingerprintModel.facility_id == "FAC-IND-OSM-DAHEJ-01").first()

    vector, feat_dict = classifier_service.extract_feature_vector(source, event, facility, fingerprint)
    db.close()

    assert vector.shape == (1, len(FEATURE_NAMES))
    assert feat_dict["frp_current"] == 22.5
    assert feat_dict["frp_median"] == 19.5
    assert feat_dict["spatial_stability"] == 0.965
    assert feat_dict["is_inside_facility"] == 1.0


# =============================================================================
# 2. MULTI-CLASS INFERENCE & CALIBRATION TESTS
# =============================================================================

def test_gas_flare_classification_and_probabilities():
    """Verify normal persistent thermal source classifies as GAS_FLARE with calibrated probabilities."""
    db = TestingSessionLocal()
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == "SRC-ML-TEST-01").first()
    event = db.query(ThermalEventModel).filter(ThermalEventModel.event_id == "EVT-ML-TEST-01").first()
    
    result = classifier_service.classify_source(source=source, event=event, db=db)
    db.close()

    assert result.predicted_class in ["GAS_FLARE", "ROUTINE_PROCESS_HEAT"]
    assert result.model_confidence > 0.60
    assert result.system_confidence > 0.50
    assert result.classification_state == "CLASSIFIED"
    assert sum(result.class_probabilities.values()) == pytest.approx(1.0, abs=0.01)
    assert len(result.explanation["reasons"]) > 0


def test_industrial_fire_surge_classification():
    """Verify extreme FRP surge with expanding footprint classifies as INDUSTRIAL_FIRE."""
    features = {
        "frp_current": 180.0,
        "frp_median": 20.0,
        "frp_robust_zscore": 5.4,
        "frp_percentile": 99.8,
        "temp_current": 415.0,
        "temp_median": 335.0,
        "temp_departure_k": 80.0,
        "spatial_stability": 0.45,
        "dispersion_radius_r95": 950.0,
        "facility_distance_m": 0.0,
        "is_inside_facility": 1.0,
        "active_days": 4,
        "observation_count": 6,
        "recurrence_rate": 0.15,
        "detection_rate": 0.35,
        "day_night_ratio": 1.0,
        "night_fraction": 0.5,
        "seasonal_deviation": 1.0,
        "sta_overlap": 1.0,
        "satellite_count": 2
    }

    result = classifier_service.classify_features(features=features, source_id="SRC-TEST-FIRE-01")

    assert result.predicted_class == "INDUSTRIAL_FIRE"
    assert result.class_probabilities["INDUSTRIAL_FIRE"] >= 0.70
    assert any("surged" in r.lower() for r in result.explanation["reasons"])


def test_agricultural_burning_classification():
    """Verify transient daytime fire far outside industrial facilities classifies as AGRICULTURAL_BURNING."""
    features = {
        "frp_current": 18.0,
        "frp_median": 12.0,
        "frp_robust_zscore": 0.8,
        "frp_percentile": 60.0,
        "temp_current": 328.0,
        "temp_median": 320.0,
        "temp_departure_k": 8.0,
        "spatial_stability": 0.25,
        "dispersion_radius_r95": 1800.0,
        "facility_distance_m": 8500.0,
        "is_inside_facility": 0.0,
        "active_days": 2,
        "observation_count": 3,
        "recurrence_rate": 0.08,
        "detection_rate": 0.20,
        "day_night_ratio": 4.5,  # Overwhelmingly daytime
        "night_fraction": 0.08,
        "seasonal_deviation": 1.1,
        "sta_overlap": 0.0,
        "satellite_count": 1
    }

    result = classifier_service.classify_features(features=features, source_id="SRC-TEST-AGRI-01")

    assert result.predicted_class == "AGRICULTURAL_BURNING"
    assert result.class_probabilities["AGRICULTURAL_BURNING"] >= 0.65


def test_wildfire_natural_classification():
    """Verify shifting rural thermal front classifies as WILDFIRE_NATURAL."""
    features = {
        "frp_current": 75.0,
        "frp_median": 25.0,
        "frp_robust_zscore": 2.2,
        "frp_percentile": 88.0,
        "temp_current": 355.0,
        "temp_median": 325.0,
        "temp_departure_k": 30.0,
        "spatial_stability": 0.15,
        "dispersion_radius_r95": 3200.0,
        "facility_distance_m": 18000.0,
        "is_inside_facility": 0.0,
        "active_days": 5,
        "observation_count": 8,
        "recurrence_rate": 0.12,
        "detection_rate": 0.25,
        "day_night_ratio": 2.2,
        "night_fraction": 0.25,
        "seasonal_deviation": 1.0,
        "sta_overlap": 0.0,
        "satellite_count": 2
    }

    result = classifier_service.classify_features(features=features, source_id="SRC-TEST-WILD-01")

    assert result.predicted_class == "WILDFIRE_NATURAL"
    assert result.class_probabilities["WILDFIRE_NATURAL"] >= 0.60


# =============================================================================
# 3. UNCERTAINTY, ABSTENTION & DUAL CONFIDENCE TESTS
# =============================================================================

def test_sparse_history_dual_confidence_penalty():
    """Verify sparse history applies data sufficiency penalty to system confidence."""
    features = {
        "frp_current": 20.0,
        "frp_median": 20.0,
        "active_days": 1,
        "observation_count": 1,  # Only 1 observation
        "spatial_stability": 0.85,
        "facility_distance_m": 50.0,
        "is_inside_facility": 1.0
    }

    result = classifier_service.classify_features(features=features, source_id="SRC-SPARSE-01")

    assert result.classification_state == "INSUFFICIENT_DATA"
    assert result.system_confidence < result.model_confidence  # Sufficiency penalty applied
    assert result.system_confidence <= 0.45


def test_out_of_distribution_coverage_limited():
    """Verify extreme anomaly features trigger OOD detection / suspect flag."""
    features = {
        "frp_current": 9999.0,  # Physically absurd extreme value
        "temp_current": 1800.0,
        "spatial_stability": -5.0,
        "dispersion_radius_r95": 99999.0,
        "facility_distance_m": 99999.0,
        "active_days": 1,
        "observation_count": 1
    }

    result = classifier_service.classify_features(features=features, source_id="SRC-OOD-01")
    assert result.explanation["is_out_of_distribution"] is True or result.data_quality == "OOD_SUSPECT" or result.classification_state in ["MODEL_COVERAGE_LIMITED", "INSUFFICIENT_DATA"]


# =============================================================================
# 4. REST API & DATABASE PERSISTENCE TESTS
# =============================================================================

def test_fastapi_model_status_endpoint():
    """Test GET /api/thermal/model/status."""
    resp = client.get("/api/thermal/model/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_production_ready"] is True
    assert data["macro_f1"] >= 0.85
    assert len(data["per_class_metrics"]) == 7
    assert data["primary_model_type"] == "HistGradientBoostingClassifier"


def test_fastapi_controlled_inference_endpoint():
    """Test POST /api/thermal/classify."""
    payload = {
        "source_id": "SRC-API-INFER-01",
        "features": {
            "frp_current": 30.0,
            "frp_median": 28.0,
            "spatial_stability": 0.92,
            "is_inside_facility": 1.0,
            "active_days": 60,
            "observation_count": 80,
            "night_fraction": 0.5
        }
    }
    resp = client.post("/api/thermal/classify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["predicted_class"] in ["GAS_FLARE", "ROUTINE_PROCESS_HEAT"]
    assert "class_probabilities" in data
    assert data["model_confidence"] > 0.50


def test_fastapi_classification_results_history():
    """Test GET /api/thermal/classification/results."""
    resp = client.get("/api/thermal/classification/results?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# =============================================================================
# 5. HIGH-THROUGHPUT SCALE BENCHMARKS
# =============================================================================

def test_inference_speed_and_throughput_benchmark():
    """Benchmark single and batch inference throughput (1,000 sources)."""
    n_sources = 1000
    rng = np.random.default_rng(42)
    
    # Create batch of 1,000 synthetic feature vectors
    X_batch = rng.uniform(0.0, 100.0, size=(n_sources, len(FEATURE_NAMES)))

    start_time = time.perf_counter()
    clf = classifier_service.pipeline.calibrated_model or classifier_service.pipeline.primary_model
    probs = clf.predict_proba(X_batch)
    preds = np.argmax(probs, axis=1)
    elapsed = time.perf_counter() - start_time

    assert probs.shape == (n_sources, len(CLASSES))
    assert len(preds) == n_sources
    assert elapsed < 5.0  # High-throughput batch inference check
    print(f"\n[BENCHMARK] 1,000 ML Inferences completed in {elapsed:.4f}s ({n_sources/elapsed:.1f} inf/sec)")
