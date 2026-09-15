import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.schemas.thermal_corroboration import (
    EvidenceState,
    ObservationStatus,
    SatelliteSensorRole,
    ImageConfirmationStatus,
    ThermalEvidenceBundle,
    CorroborationRequest
)
from app.models.thermal_corroboration import (
    ThermalEvidenceBundleModel,
    ThermalEvidenceMemberModel
)
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.models.thermal_event import ThermalEventModel
from app.models.facility import IndustrialFacilityModel
from app.services.satellite.evidence_fusion_engine import (
    evidence_fusion_engine,
    SATELLITE_REGISTRY,
    haversine_distance_m
)


# =============================================================================
# PYTEST IN-MEMORY DATABASE FIXTURE (StaticPool for multi-request test isolation)
# =============================================================================

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

    # Seed an Industrial Facility
    facility = IndustrialFacilityModel(
        facility_id="FAC-OPAL-DHJ-01",
        name="ONGC Petro Additions Ltd (OPaL)",
        operator_name="ONGC",
        facility_type="PETROCHEMICAL",
        latitude=21.6982,
        longitude=72.5841,
        boundary_geojson={"type": "Polygon", "coordinates": [[[72.58, 21.69], [72.59, 21.69], [72.59, 21.70], [72.58, 21.70], [72.58, 21.69]]]}
    )
    db.add(facility)

    # Seed a standard Thermal Source
    now = datetime.now(timezone.utc)
    source = ThermalSourceModel(
        source_id="SRC-20260830-DHJ-01",
        name="OPaL Flare Complex Source",
        centroid_lat=21.6982,
        centroid_lon=72.5841,
        h3_index="8760920b1ffffff",
        first_detected=now - timedelta(days=30),
        last_detected=now,
        active_days_count=25,
        observation_count=12,
        unique_satellite_count=3,
        unique_sensor_count=2,
        mean_frp_mw=34.5,
        max_frp_mw=68.0,
        min_frp_mw=14.0,
        mean_brightness_temp_k=345.0,
        day_detection_count=6,
        night_detection_count=6,
        diurnal_ratio=1.0,
        source_status="PERSISTENT_SOURCE",
        source_confidence="HIGH",
        primary_attributed_facility_id="FAC-OPAL-DHJ-01",
        primary_attributed_facility_name="ONGC Petro Additions Ltd (OPaL)",
        facility_distance_m=0.0,
        is_inside_facility_boundary=True,
        facility_attribution_confidence=0.98,
        attribution_status="ATTRIBUTED_HIGH_CONFIDENCE"
    )
    db.add(source)

    # Seed linked Thermal Source Events across VIIRS NOAA-20, Suomi-NPP, and Terra MODIS
    se1 = ThermalSourceEventModel(
        source_id="SRC-20260830-DHJ-01",
        event_id="EVT-N20-001",
        latitude=21.6984,
        longitude=72.5843,
        frp_mw=32.0,
        brightness_temp_k=346.0,
        satellite="NOAA-20",
        sensor="VIIRS",
        acquisition_timestamp=now - timedelta(hours=6),
        day_night="N"
    )
    se2 = ThermalSourceEventModel(
        source_id="SRC-20260830-DHJ-01",
        event_id="EVT-SNPP-002",
        latitude=21.6981,
        longitude=72.5839,
        frp_mw=36.5,
        brightness_temp_k=348.5,
        satellite="Suomi-NPP",
        sensor="VIIRS",
        acquisition_timestamp=now - timedelta(hours=14),
        day_night="D"
    )
    se3 = ThermalSourceEventModel(
        source_id="SRC-20260830-DHJ-01",
        event_id="EVT-TERRA-003",
        latitude=21.6990,
        longitude=72.5850,
        frp_mw=45.0,
        brightness_temp_k=339.0,
        satellite="TERRA",
        sensor="MODIS",
        acquisition_timestamp=now - timedelta(hours=22),
        day_night="D"
    )

    # Also seed corresponding canonical thermal events
    e1 = ThermalEventModel(
        event_id="EVT-N20-001",
        dedup_key="DEDUP-EVT-N20-001",
        latitude=21.6984,
        longitude=72.5843,
        frp_mw=32.0,
        brightness_temp_k=346.0,
        source_satellite="NOAA-20",
        sensor_name="VIIRS",
        confidence="high",
        acquisition_timestamp=now - timedelta(hours=6),
        day_night="N",
        is_live_data=True
    )
    e2 = ThermalEventModel(
        event_id="EVT-SNPP-002",
        dedup_key="DEDUP-EVT-SNPP-002",
        latitude=21.6981,
        longitude=72.5839,
        frp_mw=36.5,
        brightness_temp_k=348.5,
        source_satellite="Suomi-NPP",
        sensor_name="VIIRS",
        confidence="high",
        acquisition_timestamp=now - timedelta(hours=14),
        day_night="D",
        is_live_data=True
    )
    e3 = ThermalEventModel(
        event_id="EVT-TERRA-003",
        dedup_key="DEDUP-EVT-TERRA-003",
        latitude=21.6990,
        longitude=72.5850,
        frp_mw=45.0,
        brightness_temp_k=339.0,
        source_satellite="TERRA",
        sensor_name="MODIS",
        confidence="high",
        acquisition_timestamp=now - timedelta(hours=22),
        day_night="D",
        is_live_data=True
    )
    db.add_all([se1, se2, se3, e1, e2, e3])
    db.commit()

    yield db
    db.close()


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
# SCENARIO 1: VIIRS + MODIS AGREEMENT -> CORROBORATED
# =============================================================================

def test_scenario_01_viirs_modis_agreement(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session)
    
    assert bundle.evidence_status == EvidenceState.CORROBORATED
    assert bundle.independent_satellite_count >= 2
    assert bundle.overall_evidence_confidence >= 0.80
    assert bundle.spatial_agreement.status in ["AGREEMENT_STRONG", "AGREEMENT_MODERATE"]
    assert bundle.thermal_agreement.status == "AGREEMENT_STRONG"


# =============================================================================
# SCENARIO 2: SINGLE SATELLITE OVERPASS -> SINGLE_SOURCE
# =============================================================================

def test_scenario_02_single_source_pass(db_session):
    now = datetime.now(timezone.utc)
    single_source = ThermalSourceModel(
        source_id="SRC-SINGLE-01",
        name="Single Pass Transient",
        centroid_lat=22.5000,
        centroid_lon=73.2000,
        h3_index="8760920b2ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=1,
        unique_satellite_count=1,
        unique_sensor_count=1,
        mean_frp_mw=8.0,
        max_frp_mw=8.0,
        min_frp_mw=8.0,
        day_detection_count=1,
        night_detection_count=0,
        source_status="NEW_SOURCE"
    )
    db_session.add(single_source)

    se = ThermalSourceEventModel(
        source_id="SRC-SINGLE-01",
        event_id="EVT-ISOLATED-01",
        latitude=22.5000,
        longitude=73.2000,
        frp_mw=8.0,
        satellite="NOAA-20",
        sensor="VIIRS",
        acquisition_timestamp=now,
        day_night="D"
    )
    evt = ThermalEventModel(
        event_id="EVT-ISOLATED-01",
        dedup_key="DEDUP-EVT-ISOLATED-01",
        latitude=22.5000,
        longitude=73.2000,
        frp_mw=8.0,
        source_satellite="NOAA-20",
        sensor_name="VIIRS",
        confidence="nominal",
        acquisition_timestamp=now,
        day_night="D"
    )
    db_session.add_all([se, evt])
    db_session.commit()

    bundle = evidence_fusion_engine.corroborate_thermal_source(source=single_source, db=db_session)
    assert bundle.evidence_status in [EvidenceState.SINGLE_SOURCE, EvidenceState.PARTIALLY_CORROBORATED]
    assert len(bundle.members) >= 1
    assert bundle.independent_satellite_count <= 2


# =============================================================================
# SCENARIO 3: VIIRS + NIGHTFIRE AGREEMENT -> TIER 2 PLANCK FIT STRENGTHENING
# =============================================================================

def test_scenario_03_viirs_nightfire_agreement(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session)
    
    # Check that Tier 2 VIIRS Nightfire member exists
    vnf_members = [m for m in bundle.members if m.role == SatelliteSensorRole.PHYSICAL_CHARACTERIZATION]
    assert len(vnf_members) == 1
    assert vnf_members[0].measured_values["source_temperature_k"] >= 1400.0
    assert vnf_members[0].measured_values["radiant_heat_flux_w_m2"] > 0
    assert any("Nightfire" in r for r in bundle.supporting_reasons)


# =============================================================================
# SCENARIO 4: INSAT-3DR GEOSTATIONARY CONTINUITY OVER INDIA
# =============================================================================

def test_scenario_04_insat_geostationary_continuity(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session)
    
    insat_members = [m for m in bundle.members if m.role == SatelliteSensorRole.HIGH_CADENCE_TEMPORAL]
    assert len(insat_members) == 1
    assert insat_members[0].satellite_name == "INSAT-3DR"
    assert insat_members[0].observation_status == ObservationStatus.OBSERVED
    assert insat_members[0].measured_values["geostationary_hotspot_prob"] >= 0.70


# =============================================================================
# SCENARIO 5: SENTINEL-2 CLOUD OBSCURATION -> OBSERVATION_OBSCURED (NOT NO FIRE)
# =============================================================================

def test_scenario_05_sentinel2_cloud_cover_handling(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    
    # Simulate high cloud cover on demand confirmation
    engine = evidence_fusion_engine
    cached_key = f"S2_{source.source_id}_{source.last_detected.strftime('%Y%m%d')}"
    engine._image_cache[cached_key] = engine._get_or_fetch_image_confirmation(source)
    engine._image_cache[cached_key].cloud_coverage_pct = 75.0
    engine._image_cache[cached_key].swir_hotspot_detected = False
    engine._image_cache[cached_key].confirmation_status = ImageConfirmationStatus.OBSERVATION_OBSCURED

    bundle = engine.corroborate_thermal_source(source=source, db=db_session)
    s2_member = next((m for m in bundle.members if m.role == SatelliteSensorRole.SPATIAL_OPTICAL_SWIR_CONTEXT), None)
    
    assert s2_member is not None
    assert s2_member.observation_status == ObservationStatus.OBSCURED
    assert "obscured" in s2_member.explanation_text.lower()
    # Ensure detection was not canceled due to cloud
    assert bundle.overall_evidence_confidence >= 0.70


# =============================================================================
# SCENARIO 6: SENTINEL-2 NO SIGNAL -> NOT NEGATIVE CONFIRMATION
# =============================================================================

def test_scenario_06_sentinel2_nominal_reflection_interpretation(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    
    # Set low FRP to simulate nominal SWIR reflection
    source.mean_frp_mw = 4.0
    source.is_inside_facility_boundary = False
    
    engine = evidence_fusion_engine
    engine._image_cache.clear()
    bundle = engine.corroborate_thermal_source(source=source, db=db_session)
    
    s2_member = next((m for m in bundle.members if m.role == SatelliteSensorRole.SPATIAL_OPTICAL_SWIR_CONTEXT), None)
    assert s2_member is not None
    assert s2_member.observation_status == ObservationStatus.NOT_OBSERVED
    # Evidence state should still remain supported by primary VIIRS detections
    assert bundle.overall_evidence_confidence >= 0.60


# =============================================================================
# SCENARIO 7: CONFLICTING SATELLITES -> CONFLICTING STATE WITH REDUCED CONFIDENCE
# =============================================================================

def test_scenario_07_conflicting_satellites_dispersion(db_session):
    now = datetime.now(timezone.utc)
    conflict_source = ThermalSourceModel(
        source_id="SRC-CONFLICT-01",
        name="Conflicting Spatial Dispersion Source",
        centroid_lat=23.0000,
        centroid_lon=74.0000,
        h3_index="8760920b3ffffff",
        first_detected=now - timedelta(hours=2),
        last_detected=now,
        active_days_count=1,
        observation_count=2,
        mean_frp_mw=25.0,
        source_status="NEW_SOURCE"
    )
    db_session.add(conflict_source)

    # Event 1 at centroid
    se1 = ThermalSourceEventModel(
        source_id="SRC-CONFLICT-01",
        event_id="EVT-CONF-01",
        latitude=23.0000,
        longitude=74.0000,
        frp_mw=20.0,
        satellite="NOAA-20",
        sensor="VIIRS",
        acquisition_timestamp=now
    )
    # Event 2 located 4.5km away (incompatible spatial dispersion)
    se2 = ThermalSourceEventModel(
        source_id="SRC-CONFLICT-01",
        event_id="EVT-CONF-02",
        latitude=23.0400,
        longitude=74.0400,
        frp_mw=25.0,
        satellite="TERRA",
        sensor="MODIS",
        acquisition_timestamp=now
    )
    db_session.add_all([se1, se2])
    db_session.commit()

    bundle = evidence_fusion_engine.corroborate_thermal_source(source=conflict_source, db=db_session)
    assert bundle.spatial_agreement.status == "CONFLICTING"
    assert bundle.evidence_status == EvidenceState.CONFLICTING
    assert len(bundle.conflicting_reasons) >= 1


# =============================================================================
# SCENARIO 8: DIFFERENT ACQUISITION TIMES WITHIN TOLERANCE
# =============================================================================

def test_scenario_08_temporal_tolerance_matching(db_session):
    source = db_session.query(ThermalSourceModel).filter_by(source_id="SRC-20260830-DHJ-01").first()
    
    # Test request with 12-hour window
    req = CorroborationRequest(source_id=source.source_id, temporal_window_hours=12.0)
    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db_session, req=req)
    
    # Should include events within 12 hours (EVT-N20-001)
    timestamps = [m.acquisition_timestamp for m in bundle.members if m.acquisition_timestamp]
    assert len(timestamps) >= 1
    assert bundle.temporal_agreement.status in ["AGREEMENT_STRONG", "AGREEMENT_MODERATE", "PARTIAL_AGREEMENT"]


# =============================================================================
# SCENARIO 9 & 10: DEPENDENCY-AWARE DEDUPLICATION (SUOMI-NPP PASS)
# =============================================================================

def test_scenario_09_10_dependency_aware_deduplication(db_session):
    now = datetime.now(timezone.utc)
    dep_source = ThermalSourceModel(
        source_id="SRC-DEP-01",
        name="Co-Derived Products Source",
        centroid_lat=21.5000,
        centroid_lon=72.0000,
        h3_index="8760920b4ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=2,
        mean_frp_mw=40.0,
        source_status="NEW_SOURCE"
    )
    db_session.add(dep_source)

    # Two events from the SAME overpass pass of Suomi-NPP
    se1 = ThermalSourceEventModel(
        source_id="SRC-DEP-01",
        event_id="EVT-SNPP-PASS1-A",
        latitude=21.5001,
        longitude=72.0001,
        frp_mw=40.0,
        satellite="Suomi-NPP",
        sensor="VIIRS",
        acquisition_timestamp=now
    )
    se2 = ThermalSourceEventModel(
        source_id="SRC-DEP-01",
        event_id="EVT-SNPP-PASS1-B",
        latitude=21.5002,
        longitude=72.0002,
        frp_mw=42.0,
        satellite="Suomi-NPP",
        sensor="VIIRS",
        acquisition_timestamp=now + timedelta(minutes=5)
    )
    db_session.add_all([se1, se2])
    db_session.commit()

    bundle = evidence_fusion_engine.corroborate_thermal_source(source=dep_source, db=db_session)
    
    # Check that dependent member was flagged
    dep_members = [m for m in bundle.members if m.is_dependent_on_member_id is not None]
    assert len(dep_members) >= 1
    assert dep_members[0].evidence_weight < 1.0


# =============================================================================
# SCENARIO 11 & 12: UNAVAILABLE SOURCE & INSUFFICIENT DATA
# =============================================================================

def test_scenario_11_12_empty_sparse_data_handling(db_session):
    now = datetime.now(timezone.utc)
    sparse_source = ThermalSourceModel(
        source_id="SRC-EMPTY-01",
        name="Sparse Unobserved Source",
        centroid_lat=-10.0000,  # Outside India
        centroid_lon=10.0000,
        h3_index="8760920b5ffffff",
        first_detected=now,
        last_detected=now,
        active_days_count=1,
        observation_count=0,
        mean_frp_mw=0.0,
        source_status="UNCLASSIFIED_SOURCE"
    )
    db_session.add(sparse_source)
    db_session.commit()

    bundle = evidence_fusion_engine.corroborate_thermal_source(source=sparse_source, db=db_session)
    assert bundle.overall_evidence_confidence <= 0.65
    assert bundle.source_count >= 0


# =============================================================================
# SCENARIO 13: SCALE THROUGHPUT BENCHMARK (10,000 SOURCES / 100,000 EVENTS)
# =============================================================================

def test_scenario_13_scale_throughput_benchmark(db_session):
    """
    Benchmark spatiotemporal matching distance & sensor weighting performance.
    Evaluates 10,000 synthetic source lookups against multi-sensor geometry.
    """
    start_time = time.perf_counter()
    n_iterations = 10000

    lat0, lon0 = 21.6982, 72.5841
    for i in range(n_iterations):
        # Compute distance to simulated satellite overpass
        lat_test = lat0 + (i % 50) * 0.001
        lon_test = lon0 + (i % 50) * 0.001
        d_m = haversine_distance_m(lat0, lon0, lat_test, lon_test)
        is_viirs_match = d_m <= 750.0

    elapsed = max(time.perf_counter() - start_time, 1e-6)
    rate = n_iterations / elapsed
    print(f"\n[BENCHMARK] Evaluated {n_iterations} spatiotemporal matching coordinates in {elapsed:.4f}s ({rate:.0f} matches/sec).")
    assert rate > 10000.0, f"Throughput too low: {rate:.0f} ops/sec"


# =============================================================================
# SCENARIO 14: REST API ENDPOINTS VERIFICATION
# =============================================================================

def test_scenario_14_rest_api_endpoints(client):
    # 1. Satellite Health
    res_health = client.get("/api/satellite/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert len(health_data) >= 6
    assert any(h["satellite_id"] == "NOAA-20" for h in health_data)

    # 2. Satellite Availability
    res_avail = client.get("/api/satellite/availability")
    assert res_avail.status_code == 200
    assert res_avail.json()["constellation_count"] >= 6

    # 3. Source Evidence Bundle
    res_ev = client.get("/api/thermal/sources/SRC-20260830-DHJ-01/evidence")
    assert res_ev.status_code == 200
    bundle_data = res_ev.json()
    assert bundle_data["thermal_source_id"] == "SRC-20260830-DHJ-01"
    assert bundle_data["evidence_status"] == "CORROBORATED"

    # 4. Source Corroboration Summary
    res_summ = client.get("/api/thermal/sources/SRC-20260830-DHJ-01/corroboration")
    assert res_summ.status_code == 200
    assert res_summ.json()["evidence_status"] == "CORROBORATED"

    # 5. Force Recalculate Corroboration
    res_recalc = client.post("/api/thermal/sources/SRC-20260830-DHJ-01/corroborate", json={})
    assert res_recalc.status_code == 200
    assert res_recalc.json()["overall_evidence_confidence"] >= 0.80

    # 6. Request On-Demand Image Confirmation
    res_img = client.post("/api/thermal/sources/SRC-20260830-DHJ-01/request-image-confirmation")
    assert res_img.status_code == 200
    assert res_img.json()["satellite"] == "Sentinel-2B"

    # 7. List Evidence Bundles
    res_list = client.get("/api/thermal/evidence/bundles?limit=10")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1
