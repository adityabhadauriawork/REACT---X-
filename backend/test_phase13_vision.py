import pytest
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.schemas.vision import (
    CameraMetadata, CameraType, CameraStatus, ThermalFrameEvidence,
    CCTVFrameEvidence, ThermalHotspot, VisionQualityStatus, VisionFreshnessStatus,
    VisualEvidence, VisualEvidenceType, VisionEventsQuery
)
from app.services.vision.thermal_camera_adapter import ThermalCameraAdapter
from app.services.vision.cctv_adapter import CCTVAdapter
from app.services.vision.camera_simulator import CameraSimulator, VisionSimulationScenario
from app.services.vision.thermal_hotspot_tracker import ThermalHotspotTracker
from app.services.vision.vision_quality_engine import VisionQualityEngine
from app.services.vision.vision_pipeline_service import VisionPipelineService
from app.services.storage.vision_repository import vision_repository

client = TestClient(app)

# 1. Camera Adapter Interface & Read-Only Safety
def test_camera_source_adapter_interface():
    adapter = ThermalCameraAdapter()
    assert adapter.connect() is True
    health = adapter.health()
    assert health["read_only"] is True
    assert health["is_radiometric"] is True
    assert adapter.disconnect() is True
    assert adapter.health()["connected"] is False

# 2. Radiometric Thermal Extraction & dT/dt
def test_radiometric_thermal_extraction():
    adapter = ThermalCameraAdapter()
    adapter.connect()
    
    # Create 640x480 matrix with background 25°C and hot patch at 85°C
    matrix = np.full((480, 640), 25.0, dtype=np.float32)
    matrix[100:150, 200:260] = 85.0

    evidence = adapter.process_radiometric_frame(matrix)
    assert evidence.is_radiometric is True
    assert evidence.min_temperature == 25.0
    assert evidence.max_temperature == 85.0
    assert evidence.hotspot_count == 1
    assert len(evidence.hotspot_regions) == 1
    hs = evidence.hotspot_regions[0]
    assert hs.max_temperature_c == 85.0
    assert hs.severity in ["ABNORMAL", "CRITICAL"]

# 3. Spatial Hotspot Tracking Across Frames
def test_spatial_hotspot_tracking():
    tracker = ThermalHotspotTracker()
    tracker.clear()
    t0 = datetime.now(timezone.utc)

    # Frame 1: Hotspot at (0.30, 0.40) temp 50°C
    hs1 = ThermalHotspot(
        hotspot_id="HS-RAW-01",
        camera_id="CAM-TH-01",
        zone_id="Zone-A",
        asset_id="T-04",
        centroid_x_pct=0.30,
        centroid_y_pct=0.40,
        bbox_xywh=[0.25, 0.35, 0.10, 0.10],
        area_pixels=100,
        max_temperature_c=50.0,
        mean_temperature_c=48.0
    )
    tracked_f1 = tracker.update_hotspots("CAM-TH-01", [hs1], t0)
    assert len(tracked_f1) == 1
    persistent_id = tracked_f1[0].hotspot_id

    # Frame 2: Same hotspot 5 seconds later getting hotter (70°C) with slight centroid shift
    t1 = t0 + timedelta(seconds=5)
    hs2 = ThermalHotspot(
        hotspot_id="HS-RAW-02",
        camera_id="CAM-TH-01",
        zone_id="Zone-A",
        asset_id="T-04",
        centroid_x_pct=0.31,
        centroid_y_pct=0.41,
        bbox_xywh=[0.25, 0.35, 0.12, 0.12],
        area_pixels=150,
        max_temperature_c=70.0,
        mean_temperature_c=65.0
    )
    tracked_f2 = tracker.update_hotspots("CAM-TH-01", [hs2], t1)
    assert len(tracked_f2) == 1
    # Must retain the exact same persistent hotspot ID
    assert tracked_f2[0].hotspot_id == persistent_id
    assert tracked_f2[0].persistence_sec >= 4.9
    # Rate of rise: (70 - 50) / 5s * 60 = 240 °C/min
    assert tracked_f2[0].rate_of_rise_c_min > 0

# 4. CCTV Optical Detection
def test_cctv_optical_adapter():
    adapter = CCTVAdapter()
    adapter.connect()

    # Synthetic optical flame image (bright orange/red pixels)
    frame = np.full((720, 1280, 3), 100, dtype=np.uint8)
    frame[300:400, 500:650, 0] = 230 # R
    frame[300:400, 500:650, 1] = 120 # G
    frame[300:400, 500:650, 2] = 20  # B

    evidence = adapter.process_optical_frame(frame)
    assert evidence.scene_status == "FLAME_SIGNATURE"
    assert evidence.flame_confidence > 0.60
    assert len(evidence.detections) >= 1
    assert evidence.detections[0].label == "OPTICAL_FLAME"

# 5. Camera Simulator Scenarios
def test_camera_simulator_scenarios():
    sim = CameraSimulator()
    
    # A. Normal
    sim.set_scenario(VisionSimulationScenario.NORMAL)
    th_norm = sim.generate_thermal_evidence()
    assert th_norm.hotspot_count == 0
    assert th_norm.max_temperature < 35.0

    # B. Rapid Heating
    sim.set_scenario(VisionSimulationScenario.RAPID_HEATING)
    th_rapid = sim.generate_thermal_evidence()
    assert th_rapid.quality_status == VisionQualityStatus.GOOD

    # C. Flame event
    sim.set_scenario(VisionSimulationScenario.FLAME_LIKE_EVENT)
    cctv_flame = sim.generate_cctv_evidence()
    assert cctv_flame.flame_confidence >= 0.90
    assert cctv_flame.scene_status == "FLAME_SIGNATURE"

    # D. Camera Failure
    sim.set_scenario(VisionSimulationScenario.CAMERA_FAILURE)
    th_fail = sim.generate_thermal_evidence()
    assert th_fail.quality_status == VisionQualityStatus.BAD
    assert "SENSOR_FAULT" in th_fail.data_quality_flags

# 6. Camera Quality & Frozen Stream Detection
def test_camera_quality_and_frozen_stream():
    engine = VisionQualityEngine()
    now = datetime.now(timezone.utc)

    # 1. Normal frames with variance
    for i in range(3):
        q, flags = engine.validate_frame_quality("CAM-01", now + timedelta(seconds=i), pixel_variance=15.0)
        assert q == VisionQualityStatus.GOOD

    # 2. Frozen frames (variance 0.0 for 5 consecutive frames)
    for i in range(3, 9):
        q, flags = engine.validate_frame_quality("CAM-01", now + timedelta(seconds=i), pixel_variance=0.0)
    
    assert q == VisionQualityStatus.FROZEN
    assert "FROZEN_STREAM" in flags

# 7. Multi-Frame Temporal Consistency
def test_temporal_consistency_engine():
    engine = VisionQualityEngine()
    
    # Single isolated anomaly frame -> WATCH
    status1, conf1 = engine.evaluate_temporal_consistency("CAM-TEST-01", is_anomalous_frame=True)
    assert status1 == "WATCH"

    # Populate history with consecutive anomalies
    engine.camera_frame_history["CAM-TEST-01"] = [
        {"is_anomaly": True},
        {"is_anomaly": True},
        {"is_anomaly": True}
    ]
    status2, conf2 = engine.evaluate_temporal_consistency("CAM-TEST-01", is_anomalous_frame=True)
    assert status2 == "ABNORMAL"
    assert conf2 > 0.85

# 8. Multi-Modal Cross-Correlation with Facility Telemetry
def test_cross_modal_telemetry_linkage():
    service = VisionPipelineService()
    # Trigger one tick to ensure latest state is populated
    service.generate_simulator_tick()
    
    correlation = service.get_linked_telemetry_for_visual_evidence("T-04")
    assert correlation["asset_id"] == "T-04"
    assert "telemetry_sensors" in correlation
    assert "visual_thermal_state" in correlation
    assert "visual_optical_state" in correlation

# 9. Vision Persistence & Historical Querying
def test_vision_repository_and_query():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        ev = VisualEvidence(
            evidence_id=f"TEST-EVID-{int(time.time())}",
            source_id="CAM-TH-TEST",
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            zone_id="Sector D",
            timestamp_utc=now,
            evidence_type=VisualEvidenceType.THERMAL_HOTSPOT,
            feature_name="peak_temperature",
            value=92.5,
            unit="°C",
            confidence=0.96,
            quality=VisionQualityStatus.GOOD,
            freshness_status=VisionFreshnessStatus.LIVE,
            is_live_data=False
        )
        saved = vision_repository.persist_visual_evidence(db, [ev])
        assert saved == 1

        query = VisionEventsQuery(
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            evidence_type=VisualEvidenceType.THERMAL_HOTSPOT,
            limit=10
        )
        results = vision_repository.query_events(db, query)
        assert len(results) >= 1
        assert any(r.evidence_id == ev.evidence_id for r in results)
    finally:
        db.close()

# 10. REST API Endpoints
def test_vision_api_endpoints():
    # 1. Health
    res = client.get("/api/vision/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["read_only_mode_verified"] is True
    assert len(data["cameras"]) >= 3

    # 2. Registered cameras
    res = client.get("/api/vision/cameras")
    assert res.status_code == 200
    assert len(res.json()) >= 3

    # 3. Latest facility vision
    res = client.get("/api/vision/facilities/FAC-IN-DAHEJ-001/latest")
    assert res.status_code == 200
    data = res.json()
    assert data["facility_id"] == "FAC-IN-DAHEJ-001"
    assert "thermal_cameras" in data

    # 4. Simulator scenario switch
    res = client.post("/api/vision/simulator/scenario", json={"scenario_name": "LOCAL_HOTSPOT"})
    assert res.status_code == 200
    assert res.json()["active_scenario"] == "LOCAL_HOTSPOT"

    # 5. Simulator tick
    res = client.post("/api/vision/simulator/tick")
    assert res.status_code == 200
    assert "thermal_evidence" in res.json()

    # 6. Correlated telemetry endpoint
    res = client.get("/api/vision/correlated/T-04")
    assert res.status_code == 200
    assert res.json()["asset_id"] == "T-04"

# 11. Performance & Latency Benchmarks
def test_vision_performance_benchmarks():
    service = VisionPipelineService()
    sim = CameraSimulator()
    
    ingest_times = []
    total_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        th_ev = sim.generate_thermal_evidence()
        t1 = time.perf_counter()
        service.ingest_thermal_evidence(th_ev)
        t2 = time.perf_counter()
        
        total_times.append((t2 - t0) * 1000.0)
        ingest_times.append((t2 - t1) * 1000.0)

    avg_ingest_ms = sum(ingest_times) / len(ingest_times)
    p95_ingest_ms = sorted(ingest_times)[int(len(ingest_times) * 0.95)]
    avg_total_ms = sum(total_times) / len(total_times)
    
    # Ingestion & tracking should take < 10ms per frame
    assert avg_ingest_ms < 10.0
    assert p95_ingest_ms < 20.0
    assert avg_total_ms < 60.0
