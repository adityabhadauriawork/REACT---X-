import pytest
import time
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.orchestration import (
    SystemDataMode, PipelineStageStatus, IncidentPacket, EndToEndExecutionTrace
)
from app.services.orchestration.pipeline_orchestrator import pipeline_orchestrator
from app.services.orchestration.source_registry_service import source_registry_service
from app.services.industrial.telemetry_simulator import telemetry_simulator, SimulationScenario
from app.core.database import SessionLocal

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_telemetry():
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)
    yield
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)

# 1. Full 11-Stage End-to-End Execution Trace
def test_full_trace_end_to_end_pipeline_execution():
    db = SessionLocal()
    try:
        trace = pipeline_orchestrator.execute_pipeline(
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            latitude=21.6850,
            longitude=72.5620,
            frp_mw=38.5,
            data_mode=SystemDataMode.SIMULATION,
            db=db
        )
        assert trace is not None
        assert trace.trace_id.startswith("TRC-")
        assert trace.event_id.startswith("EVT-")
        assert len(trace.stages_executed) == 11
        assert trace.total_duration_ms > 0

        # Verify all stage names
        stage_names = [s.stage_name for s in trace.stages_executed]
        assert "INGESTION_AND_NORMALIZATION" in stage_names
        assert "THERMAL_SOURCE_CLUSTERING" in stage_names
        assert "FACILITY_CONTEXT_AND_LAND_COVER" in stage_names
        assert "SOURCE_DISCRIMINATION" in stage_names
        assert "FACILITY_TELEMETRY_INGESTION" in stage_names
        assert "THERMAL_VISION_AND_CCTV_LINKAGE" in stage_names
        assert "HAZARD_TRAJECTORY_AND_PREDICTION" in stage_names
        assert "MULTIMODAL_EVIDENCE_FUSION" in stage_names
        assert "ADAPTIVE_MONITORING_ORCHESTRATION" in stage_names
        assert "CONSEQUENCE_AND_RESPONSE_ANALYSIS" in stage_names
        assert "INCIDENT_PACKET_SYNTHESIS" in stage_names

        # Verify IncidentPacket
        packet = trace.incident_packet
        assert packet is not None
        assert packet.human_review_required is True
        assert packet.is_plant_actuation_blocked is True
        assert packet.consequence is not None
        assert len(packet.recommended_evacuation_routes) >= 1
    finally:
        db.close()

# 2. Golden Scenarios A through J
@pytest.mark.parametrize("scenario_id,expected_frp", [
    ("SCENARIO_A", 18.0), # Normal facility
    ("SCENARIO_B", 32.0), # Satellite detects new anomaly
    ("SCENARIO_C", 18.0), # Persistent industrial source
    ("SCENARIO_D", 45.0), # Telemetry drift
    ("SCENARIO_E", 45.0), # Telemetry + camera agree
    ("SCENARIO_F", 32.0), # Satellite anomaly, local normal
    ("SCENARIO_G", 18.0), # Local abnormal, satellite stale
    ("SCENARIO_H", 18.0), # Sensor loss / abstention
    ("SCENARIO_I", 85.0), # Confirmed critical event
    ("SCENARIO_J", 12.0), # Cooldown & recovery
])
def test_golden_scenarios_a_through_j(scenario_id, expected_frp):
    db = SessionLocal()
    try:
        res = client.get(f"/api/orchestration/scenarios/{scenario_id}?facility_id=FAC-IN-DAHEJ-001")
        assert res.status_code == 200
        data = res.json()
        assert data["trace_id"].startswith("TRC-")
        assert len(data["stages_executed"]) == 11
        assert data["incident_packet"] is not None
        assert data["incident_packet"]["human_review_required"] is True
    finally:
        db.close()

# 3. Graceful Degradation on Missing Sources
def test_graceful_degradation_missing_sources():
    db = SessionLocal()
    try:
        # Pass remote coordinate with no local sensors
        trace = pipeline_orchestrator.execute_pipeline(
            facility_id="FAC-IN-REMOTE-999",
            asset_id="T-UNKNOWN",
            latitude=28.5000,
            longitude=77.2000,
            frp_mw=15.0,
            db=db
        )
        assert trace is not None
        assert len(trace.stages_executed) == 11
        # Should finish gracefully without unhandled exception
        assert trace.incident_packet is not None
    finally:
        db.close()

# 4. System Readiness & Source Registry
def test_system_readiness_and_source_registry():
    # Readiness check
    res_ready = client.get("/api/orchestration/readiness")
    assert res_ready.status_code == 200
    r_data = res_ready.json()
    assert r_data["status"] in ["READY", "DEGRADED"]
    assert r_data["database_connected"] is True
    assert r_data["registered_facilities_count"] >= 1

    # Source registry list
    res_src = client.get("/api/orchestration/sources")
    assert res_src.status_code == 200
    src_list = res_src.json()
    assert len(src_list) >= 4
    src_types = [s["source_type"] for s in src_list]
    assert "SATELLITE_FIRMS" in src_types
    assert "OPC_UA_TELEMETRY" in src_types

# 5. REST API Execution & Packet Retrieval
def test_orchestration_api_endpoints():
    # Trigger execution via API
    res = client.post("/api/orchestration/pipeline/execute?facility_id=FAC-IN-DAHEJ-001&asset_id=T-04&frp_mw=42.0")
    assert res.status_code == 200
    data = res.json()
    trace_id = data["trace_id"]
    incident_id = data["incident_packet"]["incident_id"]

    # Fetch trace
    res_trc = client.get(f"/api/orchestration/pipeline/traces/{trace_id}")
    assert res_trc.status_code == 200
    assert res_trc.json()["trace_id"] == trace_id

    # Fetch incident packet
    res_pkt = client.get(f"/api/orchestration/incident-packets/{incident_id}")
    assert res_pkt.status_code == 200
    assert res_pkt.json()["incident_id"] == incident_id

# 6. Performance & Latency Benchmarks
def test_end_to_end_performance_benchmarks():
    db = SessionLocal()
    times = []
    try:
        for _ in range(15):
            t0 = time.perf_counter()
            pipeline_orchestrator.execute_pipeline(
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-04",
                frp_mw=25.0,
                db=db
            )
            times.append((time.perf_counter() - t0) * 1000.0)

        times.sort()
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        
        # Whole 11-stage pipeline should complete within 600ms under full test runner load
        assert p50 < 600.0
    finally:
        db.close()
