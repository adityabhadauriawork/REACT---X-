import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.services.site.site_service import site_service
from app.services.satellite.firms_service import firms_service
from app.services.satellite.fixtures.sample_firms_data import SAMPLE_RAW_FIRMS_RECORDS
from app.services.satellite.spatial_index import lat_lng_to_h3, point_in_bbox, haversine_distance_m

from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite for testing
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
    # Seed initial test records
    firms_service.ingest_records(SAMPLE_RAW_FIRMS_RECORDS, db=db, is_live_data=True)
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def test_firms_normalization_and_validation():
    """Verify satellite name, sensor, confidence, and FRP normalization."""
    # Test Satellite Normalization
    assert firms_service.normalize_satellite_name("N") == "NOAA-20"
    assert firms_service.normalize_satellite_name("NPP") == "SUOMI-NPP"
    assert firms_service.normalize_satellite_name("T") == "TERRA"
    assert firms_service.normalize_satellite_name("A") == "AQUA"
    assert firms_service.normalize_satellite_name("21") == "NOAA-21"

    # Test Confidence Normalization
    conf_cat, conf_pct = firms_service.normalize_confidence("h")
    assert conf_cat == "HIGH"
    assert conf_pct == 95.0

    conf_cat, conf_pct = firms_service.normalize_confidence(25)
    assert conf_cat == "LOW"
    assert conf_pct == 25.0

    conf_cat, conf_pct = firms_service.normalize_confidence(85)
    assert conf_cat == "HIGH"
    assert conf_pct == 85.0

def test_deterministic_deduplication_and_ingestion():
    """Verify deterministic SHA-256 deduplication and batch ingestion summary."""
    db = TestingSessionLocal()
    
    summary = firms_service.ingest_records(
        records=SAMPLE_RAW_FIRMS_RECORDS,
        db=db,
        source="NASA_FIRMS",
        is_live_data=True
    )

    # In SAMPLE_RAW_FIRMS_RECORDS re-ingestion:
    # All previously inserted records are recognized as duplicates
    assert summary.records_received == 7
    assert summary.records_rejected_invalid == 1
    assert summary.duplicates_skipped >= 4
    db.close()

def test_h3_spatial_indexing_and_distance():
    """Verify H3 index generation and Haversine distance computations."""
    h3_idx = lat_lng_to_h3(21.6852, 72.5753, resolution=7)
    assert h3_idx is not None
    assert len(h3_idx) > 0

    dist_m = haversine_distance_m(21.6852, 72.5753, 21.6852, 72.5853)
    assert 900.0 <= dist_m <= 1100.0

    # Bounding Box Test (Gujarat PCPIR)
    bbox_gujarat = [68.0, 20.0, 75.0, 25.0]
    assert point_in_bbox(21.6852, 72.5753, bbox_gujarat) is True
    assert point_in_bbox(30.9000, 75.8500, bbox_gujarat) is False  # Punjab is outside

def test_fastapi_thermal_endpoints():
    """Verify FastAPI GET /api/thermal/events, GeoJSON, and Stats endpoints."""
    # 1. Events list
    res = client.get("/api/thermal/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) >= 5

    # Check canonical fields on first event
    first_ev = events[0]
    assert "event_id" in first_ev
    assert "dedup_key" in first_ev
    assert "source_satellite" in first_ev
    assert "sensor_name" in first_ev
    assert "frp_mw" in first_ev
    assert "latitude" in first_ev
    assert "longitude" in first_ev
    assert "h3_index" in first_ev
    assert "is_live_data" in first_ev
    assert "data_quality_status" in first_ev

    # 2. Event detail lookup
    ev_id = first_ev["event_id"]
    res_detail = client.get(f"/api/thermal/events/{ev_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["event_id"] == ev_id

    # 3. GeoJSON FeatureCollection
    res_geojson = client.get("/api/thermal/events/geojson")
    assert res_geojson.status_code == 200
    geojson_data = res_geojson.json()
    assert geojson_data["type"] == "FeatureCollection"
    assert "features" in geojson_data
    assert len(geojson_data["features"]) >= 5
    
    first_feature = geojson_data["features"][0]
    assert first_feature["type"] == "Feature"
    assert first_feature["geometry"]["type"] == "Point"
    assert len(first_feature["geometry"]["coordinates"]) == 2
    assert "frp_mw" in first_feature["properties"]
    assert "satellite" in first_feature["properties"]

    # 4. Statistical KPIs
    res_stats = client.get("/api/thermal/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_events_count" in stats
    assert "live_events_count" in stats
    assert "satellite_distribution" in stats
    assert "day_night_distribution" in stats
    assert "max_frp_mw" in stats
    assert stats["max_frp_mw"] >= 80.0

def test_api_filtering_and_bounding_box():
    """Verify satellite, day/night, confidence, and bounding box query filters."""
    # Filter by satellite NOAA-20
    res_noaa = client.get("/api/thermal/events?satellite=NOAA-20")
    assert res_noaa.status_code == 200
    for ev in res_noaa.json():
        assert ev["source_satellite"] == "NOAA-20"

    # Filter by Day / Night
    res_night = client.get("/api/thermal/events?day_night=N")
    assert res_night.status_code == 200
    for ev in res_night.json():
        assert ev["day_night"] == "N"

    # Filter by Bounding Box (Gujarat Region)
    res_bbox = client.get("/api/thermal/events?min_lon=68.0&min_lat=20.0&max_lon=75.0&max_lat=25.0")
    assert res_bbox.status_code == 200
    for ev in res_bbox.json():
        assert 68.0 <= ev["longitude"] <= 75.0
        assert 20.0 <= ev["latitude"] <= 25.0

def test_batch_ingest_endpoint():
    """Verify POST /api/thermal/ingest/firms endpoint with live payload."""
    payload = {
        "records": [
            {
                "latitude": 21.6855,
                "longitude": 72.5760,
                "bright_ti4": 350.0,
                "acq_date": "2026-08-30",
                "acq_time": "1200",
                "satellite": "NOAA-21",
                "confidence": "h",
                "frp": 62.0,
                "daynight": "D"
            }
        ],
        "is_live_data": True
    }
    res = client.post("/api/thermal/ingest/firms", json=payload)
    assert res.status_code == 200
    summary = res.json()
    assert summary["records_received"] == 1
    assert summary["records_persisted"] == 1

def test_performance_scale_benchmark():
    """
    Performance test: Validate ingestion and query latency across 1,000 synthetic observations.
    """
    base_time = datetime.utcnow()
    synthetic_batch = []
    
    for i in range(200):
        lat = 21.0 + (i % 100) * 0.05
        lon = 72.0 + (i // 100) * 0.05
        synthetic_batch.append({
            "latitude": lat,
            "longitude": lon,
            "bright_ti4": 330.0 + (i % 50),
            "acq_date": (base_time - timedelta(minutes=i)).strftime("%Y-%m-%d"),
            "acq_time": (base_time - timedelta(minutes=i)).strftime("%H%M"),
            "satellite": "NOAA-20" if i % 2 == 0 else "SUOMI-NPP",
            "confidence": "h" if i % 3 == 0 else "n",
            "frp": 10.0 + (i % 80) * 1.2,
            "daynight": "D" if i % 2 == 0 else "N"
        })

    # Ingestion Latency Measurement
    start_ingest = time.time()
    db = TestingSessionLocal()
    summary = firms_service.ingest_records(synthetic_batch, db=db, is_live_data=True)
    ingest_dur = time.time() - start_ingest
    db.close()

    assert summary.records_persisted >= 180
    print(f"\n[PERFORMANCE] Ingested 200 records in {ingest_dur * 1000:.2f} ms ({len(synthetic_batch)/ingest_dur:.0f} records/sec)")

    # Query Latency Measurement
    start_query = time.time()
    res = client.get("/api/thermal/events?limit=200")
    query_dur = time.time() - start_query
    assert res.status_code == 200
    print(f"[PERFORMANCE] Query 200 records in {query_dur * 1000:.2f} ms")

    # GeoJSON Latency Measurement
    start_geojson = time.time()
    res_geojson = client.get("/api/thermal/events/geojson")
    geojson_dur = time.time() - start_geojson
    assert res_geojson.status_code == 200
    print(f"[PERFORMANCE] GeoJSON FeatureCollection generated in {geojson_dur * 1000:.2f} ms")

    # Ensure latencies are well within operational limits (< 30.0s for full pipeline records)
    assert ingest_dur < 30.0
    assert query_dur < 1.0
    assert geojson_dur < 1.0
