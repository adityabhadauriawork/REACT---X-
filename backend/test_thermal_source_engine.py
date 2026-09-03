import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.thermal_event import ThermalEventModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel, SourceFacilityCandidateModel
from app.models.facility import IndustrialFacilityModel
from app.services.satellite.clustering_engine import clustering_engine
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.satellite.source_attribution_engine import source_attribution_engine
from app.services.satellite.spatial_index import spatial_index

from sqlalchemy.pool import StaticPool

# In-memory SQLite for high-speed isolated testing
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
# 1. H3 INDEXING & SPATIAL CLUSTERING TESTS
# =============================================================================

def test_h3_neighborhood_generation():
    lat, lon = 21.6850, 72.5750
    h3_center = spatial_index.lat_lng_to_h3(lat, lon)
    assert h3_center is not None
    assert len(h3_center) == 15

    candidates = clustering_engine.get_candidate_h3_indices(lat, lon)
    assert len(candidates) >= 7  # Center cell + 6 ring neighbors
    assert h3_center in candidates


def test_spatial_distance_grouping_and_separation(db_session):
    now = datetime.now(timezone.utc)
    
    # Event 1 at Dahej Unit 04
    ev1 = ThermalEventModel(
        event_id="EVT-01",
        dedup_key="K1",
        source="NASA_FIRMS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now,
        latitude=21.6850,
        longitude=72.5750,
        frp_mw=35.0,
        brightness_temp_k=340.0,
        confidence="HIGH",
        day_night="N",
        is_live_data=True
    )
    db_session.add(ev1)
    db_session.commit()

    src1, is_new1 = clustering_engine.attach_or_create_source(ev1, db_session)
    assert is_new1 is True
    assert src1.observation_count == 1
    assert src1.source_status == "NEW_SOURCE"

    # Event 2 closely situated (120m away) -> should attach to same source
    ev2 = ThermalEventModel(
        event_id="EVT-02",
        dedup_key="K2",
        source="NASA_FIRMS",
        source_satellite="SUOMI-NPP",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now + timedelta(hours=6),
        latitude=21.6858,  # ~90m North
        longitude=72.5755,
        frp_mw=45.0,
        brightness_temp_k=355.0,
        confidence="HIGH",
        day_night="D",
        is_live_data=True
    )
    db_session.add(ev2)
    db_session.commit()

    src2, is_new2 = clustering_engine.attach_or_create_source(ev2, db_session)
    assert is_new2 is False
    assert src2.source_id == src1.source_id
    assert src2.observation_count == 2
    assert src2.unique_satellite_count == 2
    assert src2.mean_frp_mw == 40.0  # (35 + 45)/2

    # Event 3 situated 5 km away in Hazira -> must NOT merge (must create separate source)
    ev3 = ThermalEventModel(
        event_id="EVT-03",
        dedup_key="K3",
        source="NASA_FIRMS",
        source_satellite="NOAA-21",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now + timedelta(hours=12),
        latitude=21.1200,  # ~60km away
        longitude=72.6700,
        frp_mw=60.0,
        brightness_temp_k=365.0,
        confidence="HIGH",
        day_night="N",
        is_live_data=True
    )
    db_session.add(ev3)
    db_session.commit()

    src3, is_new3 = clustering_engine.attach_or_create_source(ev3, db_session)
    assert is_new3 is True
    assert src3.source_id != src1.source_id
    assert src3.observation_count == 1


# =============================================================================
# 2. TEMPORAL CHARACTERIZATION & LIFECYCLE TESTS
# =============================================================================

def test_source_lifecycle_transitions(db_session):
    now = datetime.now(timezone.utc)
    base_lat, base_lon = 22.3600, 69.8300  # Jamnagar Refinery
    
    # 1. First detection -> NEW_SOURCE
    ev_first = ThermalEventModel(
        event_id="JAM-01",
        dedup_key="JK1",
        source="NASA_FIRMS",
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=now - timedelta(days=10),
        latitude=base_lat,
        longitude=base_lon,
        frp_mw=100.0,
        day_night="N",
        is_live_data=True
    )
    db_session.add(ev_first)
    db_session.commit()
    src, is_new = clustering_engine.attach_or_create_source(ev_first, db_session)
    assert src.source_status == "NEW_SOURCE"

    # 2. Add 3 detections across 3 distinct days -> transitions to RECURRING_SOURCE
    for i in range(2, 5):
        ev = ThermalEventModel(
            event_id=f"JAM-{i:02d}",
            dedup_key=f"JK{i}",
            source="NASA_FIRMS",
            source_satellite="SUOMI-NPP",
            sensor_name="VIIRS_375M",
            acquisition_timestamp=now - timedelta(days=10 - i),
            latitude=base_lat + 0.0005,
            longitude=base_lon - 0.0005,
            frp_mw=110.0 + i,
            day_night="D" if i % 2 == 0 else "N",
            is_live_data=True
        )
        db_session.add(ev)
        db_session.commit()
        clustering_engine.attach_or_create_source(ev, db_session)

    src_updated = db_session.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == src.source_id).first()
    assert src_updated.observation_count == 4
    assert src_updated.source_status == "RECURRING_SOURCE"

    # 3. Add 7 more detections across 6 active days -> transitions to PERSISTENT_SOURCE
    for i in range(5, 12):
        ev = ThermalEventModel(
            event_id=f"JAM-{i:02d}",
            dedup_key=f"JK{i}",
            source="NASA_FIRMS",
            source_satellite="TERRA",
            sensor_name="MODIS_1KM",
            acquisition_timestamp=now - timedelta(days=12 - i),
            latitude=base_lat - 0.0003,
            longitude=base_lon + 0.0003,
            frp_mw=120.0,
            day_night="N",
            is_live_data=True
        )
        db_session.add(ev)
        db_session.commit()
        clustering_engine.attach_or_create_source(ev, db_session)

    src_persistent = db_session.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == src.source_id).first()
    assert src_persistent.observation_count == 11
    assert src_persistent.active_days_count >= 5
    assert src_persistent.source_status == "PERSISTENT_SOURCE"
    assert src_persistent.unique_satellite_count >= 3


# =============================================================================
# 3. OSM & GEM NORMALIZATION AND MULTI-SIGNAL RECONCILIATION
# =============================================================================

def test_facility_reconciliation_engine(db_session):
    initial_count = db_session.query(IndustrialFacilityModel).count()
    assert initial_count >= 7

    # Ingest a GEM facility that overlaps with existing Dahej PetroChem complex (400m away, similar name)
    gem_feed = [
        {
            "facility_id": "GEM-NEW-DAHEJ-PCH",
            "source": "GEM",
            "source_id": "GEM-PETRO-999",
            "name": "PetroChem Complex Alpha - Chemical Unit 4",
            "operator_name": "Bharat Petrochemical Industrial Corp.",
            "facility_type": "PETROCHEMICAL",
            "latitude": 21.6860,
            "longitude": 72.5760,
            "state": "Gujarat",
            "district": "Bharuch",
            "fence_radius_m": 1200.0,
            "source_metadata": {"capacity_mt": 2.5}
        }
    ]

    res = industrial_context_service.reconcile_facilities(gem_feed, db_session)
    assert res["reconciled_matches"] == 1
    assert res["new_facilities_inserted"] == 0

    # Verify reconciliation status updated to RECONCILED_MATCH
    reconciled = db_session.query(IndustrialFacilityModel).filter(
        IndustrialFacilityModel.facility_id == "FAC-IND-OSM-DAHEJ-01"
    ).first()
    assert reconciled.reconciliation_status == "RECONCILED_MATCH"
    assert reconciled.source_metadata["reconciled_with"] == "GEM-PETRO-999"


# =============================================================================
# 4. THERMAL SOURCE -> FACILITY ATTRIBUTION & MULTI-CANDIDATE RANKING
# =============================================================================

def test_polygon_containment_and_candidate_ranking(db_session):
    now = datetime.now(timezone.utc)
    
    # 1. Hotspot inside Dahej Polygon perimeter
    source_inside = ThermalSourceModel(
        source_id="SRC-TEST-INSIDE",
        name="Dahej Flare Stack Source",
        centroid_lat=21.6850,
        centroid_lon=72.5750,
        h3_index="872c02829ffffff",
        first_detected=now,
        last_detected=now,
        observation_count=5,
        mean_frp_mw=45.0,
        max_frp_mw=60.0
    )
    db_session.add(source_inside)
    db_session.commit()

    candidates = source_attribution_engine.attribute_source(source_inside, db_session)
    assert len(candidates) >= 1
    top_cand = candidates[0]
    assert top_cand.facility_id == "FAC-IND-OSM-DAHEJ-01"
    assert top_cand.is_inside_boundary is True
    assert top_cand.attribution_confidence >= 0.90
    assert source_inside.attribution_status == "ATTRIBUTED_HIGH_CONFIDENCE"

    # 2. Hotspot located in remote agricultural zone (Punjab, far from all plants)
    source_remote = ThermalSourceModel(
        source_id="SRC-TEST-REMOTE",
        name="Punjab Crop Residue Burn",
        centroid_lat=30.9000,
        centroid_lon=75.8500,
        h3_index="872cb4049ffffff",
        first_detected=now,
        last_detected=now,
        observation_count=1,
        mean_frp_mw=12.0
    )
    db_session.add(source_remote)
    db_session.commit()

    remote_candidates = source_attribution_engine.attribute_source(source_remote, db_session)
    assert len(remote_candidates) == 0  # Outside 10km search radius
    assert source_remote.attribution_status == "UNATTRIBUTED"
    assert source_remote.primary_attributed_facility_id is None


# =============================================================================
# 5. FASTAPI REST & GEOJSON API INTEGRATION TESTS
# =============================================================================

def test_fastapi_thermal_source_endpoints(client, db_session):
    now = datetime.now(timezone.utc)
    
    # Create sample thermal events and trigger clustering endpoint
    for i in range(1, 4):
        ev = ThermalEventModel(
            event_id=f"EVT-API-{i}",
            dedup_key=f"DEDUP-API-{i}",
            source="NASA_FIRMS",
            source_satellite="NOAA-20",
            sensor_name="VIIRS_375M",
            acquisition_timestamp=now - timedelta(hours=i),
            latitude=21.6850 + (i * 0.0002),
            longitude=72.5750 + (i * 0.0002),
            frp_mw=25.0 + i,
            brightness_temp_k=335.0,
            confidence="HIGH",
            day_night="N",
            is_live_data=True
        )
        db_session.add(ev)
    db_session.commit()

    # 1. Trigger batch clustering
    res_cluster = client.post("/api/thermal/sources/cluster")
    assert res_cluster.status_code == 200
    cluster_json = res_cluster.json()
    assert cluster_json["total_active_sources"] >= 1

    # 2. Query thermal sources list
    res_sources = client.get("/api/thermal/sources")
    assert res_sources.status_code == 200
    sources_data = res_sources.json()
    assert len(sources_data) >= 1
    top_src = sources_data[0]
    assert "source_id" in top_src
    assert "centroid_lat" in top_src
    assert "mean_frp_mw" in top_src
    assert "primary_attributed_facility_name" in top_src

    # 3. Query GeoJSON FeatureCollection
    res_geojson = client.get("/api/thermal/sources/geojson")
    assert res_geojson.status_code == 200
    geojson_data = res_geojson.json()
    assert geojson_data["type"] == "FeatureCollection"
    assert len(geojson_data["features"]) >= 1
    first_feat = geojson_data["features"][0]
    assert first_feat["type"] == "Feature"
    assert first_feat["geometry"]["type"] == "Point"
    assert "source_id" in first_feat["properties"]

    # 4. Query Facilities list & GeoJSON
    res_facs = client.get("/api/facilities")
    assert res_facs.status_code == 200
    facs_data = res_facs.json()
    assert len(facs_data) >= 7

    res_facs_geojson = client.get("/api/facilities/geojson")
    assert res_facs_geojson.status_code == 200
    facs_geojson = res_facs_geojson.json()
    assert facs_geojson["type"] == "FeatureCollection"


# =============================================================================
# 6. SCALE & PERFORMANCE BENCHMARK (10,000 SYNTHETIC DETECTIONS)
# =============================================================================

def test_scale_performance_10k_events(db_session):
    now = datetime.now(timezone.utc)
    base_lat, base_lon = 21.6850, 72.5750

    # Generate 10,000 synthetic observations across 20 distinct industrial clusters
    events_batch = []
    for i in range(10000):
        cluster_idx = i % 20
        c_lat = base_lat + (cluster_idx * 0.05) + ((i % 10) * 0.0004)
        c_lon = base_lon + (cluster_idx * 0.05) + ((i % 10) * 0.0004)
        
        events_batch.append(
            ThermalEventModel(
                event_id=f"SCALE-EVT-{i:05d}",
                dedup_key=f"SCALE-KEY-{i:05d}",
                source="NASA_FIRMS",
                source_satellite="NOAA-20" if i % 2 == 0 else "SUOMI-NPP",
                sensor_name="VIIRS_375M",
                acquisition_timestamp=now - timedelta(minutes=i % 1440),
                latitude=c_lat,
                longitude=c_lon,
                frp_mw=15.0 + (i % 80),
                brightness_temp_k=330.0 + (i % 50),
                confidence="HIGH" if i % 3 == 0 else "NOMINAL",
                day_night="D" if i % 2 == 0 else "N",
                is_live_data=True
            )
        )

    # Ingest batch into DB
    start_insert = time.time()
    db_session.add_all(events_batch)
    db_session.commit()
    insert_dur = time.time() - start_insert
    print(f"\n[BENCHMARK] 10,000 events inserted into DB in {insert_dur:.2f}s ({len(events_batch)/insert_dur:.0f} recs/sec)")

    # Run batch clustering
    start_cluster = time.time()
    cluster_res = clustering_engine.run_batch_clustering(db_session)
    cluster_dur = time.time() - start_cluster
    print(f"[BENCHMARK] 10,000 events clustered in {cluster_dur:.2f}s ({cluster_res['total_active_sources']} sources generated)")

    assert cluster_dur < 15.0  # Must complete 10,000 observations clustering under 15 seconds
    assert cluster_res["total_active_sources"] >= 20
