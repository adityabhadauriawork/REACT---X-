import pytest
import time
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.orchestration import SystemDataMode, PipelineStageStatus
from app.services.orchestration.pipeline_orchestrator import pipeline_orchestrator
from app.services.industrial.telemetry_simulator import telemetry_simulator, SimulationScenario
from app.core.database import SessionLocal

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_telemetry():
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)
    yield
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)

# 1. Definitive End-to-End Single Event Trace
def test_definitive_end_to_end_single_event_trace():
    db = SessionLocal()
    try:
        trace = pipeline_orchestrator.execute_pipeline(
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            latitude=21.6850,
            longitude=72.5620,
            frp_mw=45.0,
            data_mode=SystemDataMode.SIMULATION,
            db=db
        )
        assert trace is not None
        assert trace.trace_id.startswith("TRC-")
        assert trace.event_id.startswith("EVT-")
        assert len(trace.stages_executed) == 11
        assert trace.total_duration_ms > 0

        # Verify exact 11 stage sequence
        expected_stages = [
            "INGESTION_AND_NORMALIZATION",
            "THERMAL_SOURCE_CLUSTERING",
            "FACILITY_CONTEXT_AND_LAND_COVER",
            "SOURCE_DISCRIMINATION",
            "FACILITY_TELEMETRY_INGESTION",
            "THERMAL_VISION_AND_CCTV_LINKAGE",
            "HAZARD_TRAJECTORY_AND_PREDICTION",
            "MULTIMODAL_EVIDENCE_FUSION",
            "ADAPTIVE_MONITORING_ORCHESTRATION",
            "CONSEQUENCE_AND_RESPONSE_ANALYSIS",
            "INCIDENT_PACKET_SYNTHESIS"
        ]
        actual_stages = [s.stage_name for s in trace.stages_executed]
        assert actual_stages == expected_stages

        # Verify IncidentPacket
        packet = trace.incident_packet
        assert packet is not None
        assert packet.incident_id.startswith("INC-")
        assert packet.trace_id == trace.trace_id
        assert packet.human_review_required is True
        assert packet.is_plant_actuation_blocked is True
        assert packet.consequence is not None
        assert packet.consequence.toxic_plume_length_m > 0
        assert len(packet.recommended_evacuation_routes) >= 1
    finally:
        db.close()

# 2. Multi-Industry Execution Consistency (Zero Code Change)
@pytest.mark.parametrize("fac_id,ind_name", [
    ("FAC-IN-DAHEJ-001", "Petrochemical"),
    ("FAC-IN-JAMNAGAR-001", "Refinery"),
    ("FAC-IN-ROURKELA-001", "Steel"),
    ("FAC-IN-KORBA-001", "Thermal Power"),
    ("FAC-IN-UDAIPUR-001", "Mining"),
])
def test_multi_industry_execution_consistency(fac_id, ind_name):
    db = SessionLocal()
    try:
        trace = pipeline_orchestrator.execute_pipeline(
            facility_id=fac_id,
            asset_id="T-01",
            latitude=21.6850,
            longitude=72.5620,
            frp_mw=30.0,
            db=db
        )
        assert trace is not None
        assert len(trace.stages_executed) == 11
        assert trace.incident_packet is not None
        assert trace.incident_packet.human_review_required is True
    finally:
        db.close()

# 3. Golden Scenarios A through J Full Verification
@pytest.mark.parametrize("scenario_id", [
    "SCENARIO_A", "SCENARIO_B", "SCENARIO_C", "SCENARIO_D", "SCENARIO_E",
    "SCENARIO_F", "SCENARIO_G", "SCENARIO_H", "SCENARIO_I", "SCENARIO_J"
])
def test_golden_scenarios_a_through_j_full_coverage(scenario_id):
    db = SessionLocal()
    try:
        res = client.get(f"/api/orchestration/scenarios/{scenario_id}?facility_id=FAC-IN-DAHEJ-001")
        assert res.status_code == 200
        data = res.json()
        assert data["trace_id"].startswith("TRC-")
        assert len(data["stages_executed"]) == 11
        assert data["incident_packet"]["human_review_required"] is True
    finally:
        db.close()

# 4. Safety Interlock & Human Decision Boundary Guarantee
def test_safety_interlock_read_only_guarantee():
    db = SessionLocal()
    try:
        trace = pipeline_orchestrator.execute_pipeline(
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            frp_mw=90.0, # Extreme critical event
            db=db
        )
        pkt = trace.incident_packet
        assert pkt is not None
        assert pkt.human_review_required is True
        assert pkt.is_plant_actuation_blocked is True
        assert "read-only advisory" in pkt.actuation_warning.lower()
    finally:
        db.close()

# 5. Overall System Latency Benchmark
def test_overall_system_latency_benchmark():
    db = SessionLocal()
    times = []
    try:
        # Warmup
        pipeline_orchestrator.execute_pipeline(facility_id="FAC-IN-DAHEJ-001", asset_id="T-04", frp_mw=30.0, db=db)
        for _ in range(15):
            t0 = time.perf_counter()
            pipeline_orchestrator.execute_pipeline(
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-04",
                frp_mw=30.0,
                db=db
            )
            times.append((time.perf_counter() - t0) * 1000.0)

        times.sort()
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        
        assert p50 < 350.0
        assert p95 < 1500.0
    finally:
        db.close()
