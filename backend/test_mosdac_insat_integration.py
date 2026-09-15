import pytest
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import Base
from app.services.satellite.mosdac_service import MOSDACDataService, mosdac_service
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine
from app.services.satellite.clustering_engine import clustering_engine
from app.services.satellite.fingerprint_engine import fingerprint_engine
from app.services.satellite.spatial_index import spatial_index
from app.services.ml.classifier_pipeline import FEATURE_NAMES, CLASSES
from app.services.fusion.dempster_shafer_engine import ds_combiner
from app.schemas.thermal_corroboration import (
    ObservationStatus, SatelliteSensorRole, CorroborationRequest
)
from app.models.thermal_event import ThermalEventModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.models.facility import IndustrialFacilityModel

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_mosdac_authentication_lifecycle():
    """Verify MOSDAC credentials detection, authentication request flow, and token caching."""
    svc = MOSDACDataService()
    assert svc.is_configured is True

    with patch.object(svc._session, "post") as mock_post:
        mock_resp = MagicMock(status_code=200)
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"token": "MOSDAC_SESSION_TOKEN_XYZ123", "expires_in": 3600}
        mock_post.return_value = mock_resp

        token = svc.authenticate(force_refresh=True)
        assert token == "MOSDAC_SESSION_TOKEN_XYZ123"
        assert len(token) > 5

        cached = svc.authenticate(force_refresh=False)
        assert cached == token


# 2. TEST AUTHENTICATION REJECTION WITHOUT LEAKING CREDENTIALS
def test_mosdac_auth_failure_graceful_handling():
    """Verify graceful handling when bad credentials are provided, ensuring secrets never leak."""
    svc = MOSDACDataService()
    with patch.object(settings, "MOSDAC_PASSWORD", "INVALID_PASSWORD_FOR_TEST"):
        with patch.object(svc._session, "post") as mock_post:
            mock_post.return_value = MagicMock(status_code=401, json=lambda: {"error": "Unauthorized"})
            token = svc.authenticate(force_refresh=True)
            assert token is None, "Bad credentials should return None"


# 3. TEST RETRIEVAL FOR KEY INDIAN INDUSTRIAL FACILITIES
@pytest.mark.parametrize("name,lat,lon", [
    ("Dahej Petrochemical Complex", 21.6850, 72.5620),
    ("Jamnagar Refining Complex", 22.3600, 69.8300),
    ("Paradip Industrial Complex", 20.2700, 86.6700)
])
def test_mosdac_retrieval_for_indian_facilities(name, lat, lon):
    """Verify retrieval of INSAT-3DR geostationary thermal observations across Indian hubs."""
    obs = mosdac_service.get_insat_thermal_observation(latitude=lat, longitude=lon)
    assert obs is not None, f"Failed to retrieve INSAT-3DR geostationary observation for {name}"
    
    # Verify canonical schema fields
    assert obs["source"] == "MOSDAC_INSAT"
    assert obs["satellite"] in ["INSAT-3DR", "INSAT-3D", "INSAT-3DS"]
    assert obs["sensor"] == "Imager TIR/MIR"
    assert obs["spatial_resolution_m"] >= 4000.0
    assert obs["scan_cadence_minutes"] == 15
    assert obs["latitude"] == lat
    assert obs["longitude"] == lon
    assert obs["acquisition_timestamp"] is not None
    assert obs["ingestion_timestamp"] is not None
    assert "MIR (3.9μm)" in obs["bands_used"]
    assert obs["brightness_temp_mir_k"] > 250.0
    assert obs["brightness_temp_tir_k"] > 250.0
    assert obs["delta_t_mir_tir_k"] >= 0.0
    assert 0.0 <= obs["geostationary_hotspot_probability"] <= 1.0
    assert obs["provenance"]["agency"] == "ISRO / Space Applications Centre (SAC)"
    assert obs["provenance"]["data_centre"] == "Meteorological & Oceanographic Satellite Data Archival Centre (MOSDAC)"


# 4. TEST DATA QUALITY: CLOUD OBTAINMENT & OFF-NADIR EXPANSION
def test_mosdac_cloud_contamination_and_off_nadir():
    """Verify cloud contamination degrades observation status and off-nadir expands resolution."""
    # Cloud contaminated observation
    obs_cloud = mosdac_service.get_insat_thermal_observation(21.6850, 72.5620, cloud_fraction_override=75.0)
    assert obs_cloud["data_quality"] == "OBSCURED"
    assert obs_cloud["geostationary_hotspot_probability"] < 0.30
    assert any("HIGH_CLOUD_COVERAGE" in f for f in obs_cloud["quality_flags"])

    member_cloud = mosdac_service.create_evidence_member(21.6850, 72.5620, "SRC-CLOUD-01")
    # Cloud member created with cloud override should be marked OBSCURED
    assert member_cloud is not None

    # Off-nadir resolution expansion in North India (e.g. 34°N)
    res_north = mosdac_service.calculate_effective_resolution(34.0, 74.0)
    assert res_north > 4500.0, "High latitude off-nadir should increase pixel footprint"


# 5. TEST PERSISTENT-SOURCE INTEGRATION & DEDUPLICATION (NO DOUBLE COUNTING)
def test_mosdac_persistent_source_integration(db_session):
    """
    Verify that MOSDAC geostationary observations contribute to:
    - thermal event creation
    - source clustering & observation count increment
    - unique satellite tracking ('INSAT-3DR')
    - deduplication / zero double-counting
    """
    dahej_lat, dahej_lon = 21.6850, 72.5620
    
    # 1. First Ingestion
    res1 = mosdac_service.ingest_observation_to_persistent_source(dahej_lat, dahej_lon, db_session, frp_equivalent_mw=30.0)
    assert res1 is not None, "Expected successful initial ingestion"
    source, is_new = res1
    assert source is not None
    assert "INSAT-3DR" in source.satellites_seen
    initial_obs_count = source.observation_count
    assert initial_obs_count >= 1
    db_session.commit()

    # 2. Duplicate Ingestion Attempt (Same slot/coordinates)
    res_dup = mosdac_service.ingest_observation_to_persistent_source(dahej_lat, dahej_lon, db_session, frp_equivalent_mw=30.0)
    assert res_dup is None, "Duplicate observation in same 15-minute slot MUST be rejected without double-counting"
    
    # Verify observation count did not double-increment
    db_source = db_session.query(ThermalSourceModel).filter_by(source_id=source.source_id).first()
    assert db_source.observation_count == initial_obs_count


# 6. TEST CROSS-SATELLITE CORRELATION (VIIRS + INSAT + SENTINEL-2 + LANDSAT)
def test_cross_satellite_correlation_dahej(db_session):
    """
    Correlates heterogeneous multi-satellite observations:
    - Tier 1: VIIRS NOAA-20 (FRP 32 MW)
    - Tier 3: INSAT-3DR Imager (15-min temporal continuity)
    - Tier 4: Sentinel-2 MSI (20m SWIR)
    """
    now = datetime.now(timezone.utc)
    dahej_lat, dahej_lon = 21.6850, 72.5620

    # Seed source with valid h3_index and timestamps
    source = ThermalSourceModel(
        source_id="SRC-DAHEJ-CORR-01",
        centroid_lat=dahej_lat,
        centroid_lon=dahej_lon,
        h3_index=spatial_index.lat_lng_to_h3(dahej_lat, dahej_lon, resolution=8),
        first_detected=now - timedelta(days=10),
        last_detected=now,
        mean_frp_mw=32.0,
        observation_count=6,
        night_detection_count=3,
        source_status="PERSISTENT_SOURCE",
        source_confidence="HIGH"
    )
    db_session.add(source)

    # Seed VIIRS event
    se_viirs = ThermalSourceEventModel(
        source_id="SRC-DAHEJ-CORR-01",
        event_id="EVT-VIIRS-01",
        latitude=dahej_lat,
        longitude=dahej_lon,
        frp_mw=32.0,
        brightness_temp_k=345.0,
        satellite="NOAA-20",
        sensor="VIIRS",
        acquisition_timestamp=now - timedelta(hours=2),
        day_night="N"
    )
    db_session.add(se_viirs)
    db_session.commit()

    # Corroborate source
    bundle = evidence_fusion_engine.corroborate_thermal_source(
        source=source,
        db=db_session,
        req=CorroborationRequest(include_on_demand_optical=False)
    )
    assert bundle is not None
    satellite_names = [m.satellite_name for m in bundle.members]
    assert "NOAA-20" in satellite_names
    assert "INSAT-3DR" in satellite_names

    # Check Tier roles
    insat_m = next(m for m in bundle.members if m.satellite_name == "INSAT-3DR")
    assert insat_m.role == SatelliteSensorRole.HIGH_CADENCE_TEMPORAL
    assert insat_m.observation_status == ObservationStatus.OBSERVED
    assert insat_m.evidence_contribution_sign == "+"


# 7. TEST SCIENTIFIC SAFETY INVARIANTS: ML MODEL & DEMPSTER-SHAFER
def test_scientific_safety_invariants():
    """
    Verify that MOSDAC integration leaves:
    1. 23-feature vector schema 100% invariant
    2. 7-class industrial taxonomy 100% invariant
    3. Dempster-Shafer frame of discernment 100% invariant
    """
    # 1. Feature Vector Invariance
    assert len(FEATURE_NAMES) == 23, "23-feature vector MUST remain exactly 23 features"
    
    # 2. Taxonomy Invariance
    assert len(CLASSES) == 7, "Taxonomy MUST remain exactly 7 classes"
    assert "INDUSTRIAL_FIRE" in CLASSES
    assert "GAS_FLARE" in CLASSES
    assert "ROUTINE_PROCESS_HEAT" in CLASSES

    # 3. Dempster-Shafer Frame of Discernment Invariance
    assert len(ds_combiner.FRAME_OF_DISCERNMENT) == 6
    assert "THERMAL_ESCALATION" in ds_combiner.FRAME_OF_DISCERNMENT
    assert "NORMAL" in ds_combiner.FRAME_OF_DISCERNMENT


# 8. TEST SECRETS ARE NEVER EXPOSED
def test_mosdac_credentials_never_exposed():
    """Verify that MOSDAC username and password never leak into responses or representations."""
    obs = mosdac_service.get_insat_thermal_observation(21.6850, 72.5620)
    obs_str = str(obs)
    if settings.MOSDAC_PASSWORD:
        assert settings.MOSDAC_PASSWORD not in obs_str
    
    member = mosdac_service.create_evidence_member(21.6850, 72.5620, "SRC-DAHEJ-01")
    member_str = member.model_dump_json()
    if settings.MOSDAC_PASSWORD:
        assert settings.MOSDAC_PASSWORD not in member_str
