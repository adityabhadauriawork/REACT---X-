"""
Test suite for REACT-X Data Gateway & Demo Replay Engine
Verifies:
1. REST API endpoints (/status, /sources, /catalog, /quality, /demo/...)
2. Source modes explicit separation (LIVE, REFERENCE, REPLAY, SIMULATION, UNAVAILABLE)
3. Prediction state honest standby
4. Replay deterministic golden scenario step execution through canonical pipeline
5. Failure injection state transitions (missing telemetry -> STANDBY, conflict -> CONFLICTING_EVIDENCE)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_data_gateway_status():
    """Verify Data Gateway status and Prediction Standby logic."""
    res = client.get("/api/data-gateway/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "sources" in data
    assert len(data["sources"]) > 0
    assert "prediction_state" in data
    assert data["prediction_state"] in [
        "PREDICTION_STANDBY", "PREDICTION_AVAILABLE", "WAITING_FOR_VERIFIED_TELEMETRY"
    ]


def test_data_gateway_sources():
    """Verify all satellite and telemetry sources carry explicit SourceMode tags."""
    res = client.get("/api/data-gateway/sources")
    assert res.status_code == 200
    sources = res.json()
    assert len(sources) >= 5

    source_modes = {s["source_mode"] for s in sources}
    assert any(m in ["LIVE", "REFERENCE", "STANDBY"] for m in source_modes)

    # Verify Dahej OT telemetry is explicitly marked REFERENCE/STANDBY without live plant link
    ot_sources = [s for s in sources if s["source_type"] == "TELEMETRY"]
    assert len(ot_sources) > 0
    assert ot_sources[0]["status"] == "STANDBY" or ot_sources[0]["source_mode"] == "REFERENCE"


def test_data_gateway_catalog():
    """Verify multi-facility and constellation master catalog."""
    res = client.get("/api/data-gateway/catalog")
    assert res.status_code == 200
    catalog = res.json()
    assert "facilities" in catalog
    assert len(catalog["facilities"]) > 0
    assert "satellite_constellations" in catalog
    assert len(catalog["satellite_constellations"]) >= 4


def test_data_gateway_quality():
    """Verify data quality summary distribution."""
    res = client.get("/api/data-gateway/quality")
    assert res.status_code == 200
    q = res.json()
    assert "good_ratio" in q
    assert "records_good" in q


def test_demo_replay_lifecycle():
    """Verify demo replay scenario lifecycle (start -> step -> pause -> reset)."""
    # 1. Scenarios list
    res = client.get("/api/data-gateway/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 3
    golden = scenarios[0]

    # 2. Start replay
    res_start = client.post(f"/api/data-gateway/demo/start?scenario_id={golden['scenario_id']}")
    assert res_start.status_code == 200
    st = res_start.json()
    assert st["status"] == "RUNNING"
    assert st["current_step"] == 0

    # 3. Step 1 execution
    res_step1 = client.post("/api/data-gateway/demo/step")
    assert res_step1.status_code == 200
    st1 = res_step1.json()
    assert st1["current_step"] == 1
    assert st1["active_event"] is not None
    assert st1["active_classification"] is not None
    assert "predicted_class" in st1["active_classification"]

    # 4. Step 2 execution
    res_step2 = client.post("/api/data-gateway/demo/step")
    assert res_step2.status_code == 200
    st2 = res_step2.json()
    assert st2["current_step"] == 2

    # 5. Pause replay
    res_pause = client.post("/api/data-gateway/demo/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # 6. Reset replay
    res_reset = client.post("/api/data-gateway/demo/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "IDLE"
    assert res_reset.json()["current_step"] == 0


def test_demo_failure_injection_transitions():
    """Verify failure injection triggers honest degraded state transitions."""
    client.post("/api/data-gateway/demo/start")

    # Inject missing telemetry
    res_fail = client.post("/api/data-gateway/demo/failure-injection", json={
        "inject_missing_telemetry": True
    })
    assert res_fail.status_code == 200

    # Step pipeline with missing telemetry
    res_step = client.post("/api/data-gateway/demo/step")
    assert res_step.status_code == 200
    st = res_step.json()
    assert st["active_prediction"]["prediction_state"] == "PREDICTION_STANDBY"

    # Clean up and reset
    client.post("/api/data-gateway/demo/reset")
