"""
Tests for Multi-Scenario Deterministic Replay and State Isolation in REACT-X Data Gateway.
Validates Dahej Golden Flow, Hazira Domino Cascade, and Vadodara Routine Flare Discrimination.
Verifies no state leakage across scenarios.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_scenario_catalog_and_isolation():
    """Verify all 3 scenarios are available in catalog and have distinct authoritative metadata."""
    res = client.get("/api/data-gateway/demo/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 3

    scenario_ids = [s["scenario_id"] for s in scenarios]
    assert "SCENARIO-DAHEJ-AMMONIA-CRYO-01" in scenario_ids
    assert "SCENARIO-HAZIRA-LNG-03" in scenario_ids
    assert "SCENARIO-ROUTINE-FLARE-02" in scenario_ids


def test_dahej_scenario_execution():
    """Verify Dahej Golden Scenario lifecycle and pipeline execution."""
    # 1. Start Dahej
    start_res = client.post("/api/data-gateway/demo/start?scenario_id=SCENARIO-DAHEJ-AMMONIA-CRYO-01")
    assert start_res.status_code == 200
    state = start_res.json()
    assert state["scenario_id"] == "SCENARIO-DAHEJ-AMMONIA-CRYO-01"
    assert state["facility_id"] == "FAC-IN-DAHEJ-001"
    assert state["current_step"] == 0

    # 2. Step through all 5 steps
    for step_num in range(1, 6):
        step_res = client.post("/api/data-gateway/demo/step")
        assert step_res.status_code == 200
        step_state = step_res.json()
        assert step_state["current_step"] == step_num
        assert step_state["active_event"] is not None
        assert step_state["active_classification"] is not None
        assert step_state["active_fusion"] is not None

    assert step_state["status"] == "COMPLETED"


def test_hazira_domino_cascade_scenario_isolation():
    """Verify Hazira Scenario switches correctly, resets Dahej state, and generates genuine cascade graph."""
    # 1. Start Hazira Scenario
    start_res = client.post("/api/data-gateway/demo/start?scenario_id=SCENARIO-HAZIRA-LNG-03")
    assert start_res.status_code == 200
    state = start_res.json()
    assert state["scenario_id"] == "SCENARIO-HAZIRA-LNG-03"
    assert state["facility_id"] == "FAC-IN-HAZ-003"
    assert state["current_step"] == 0
    assert state["coordinates"] == [21.1155, 72.6355]

    # 2. Step through Hazira steps
    for step_num in range(1, 5):
        step_res = client.post("/api/data-gateway/demo/step")
        assert step_res.status_code == 200
        step_state = step_res.json()
        assert step_state["current_step"] == step_num
        assert step_state["active_cascade"] is not None
        assert step_state["active_cascade"]["primary_asset_id"] == "TANK-LNG-02"
        assert len(step_state["active_cascade"]["threatened_nodes"]) > 0

    assert step_state["status"] == "COMPLETED"


def test_vadodara_routine_flare_scenario_isolation():
    """Verify Vadodara Scenario discriminates routine flaring without false fire alarms."""
    # 1. Start Vadodara Scenario
    start_res = client.post("/api/data-gateway/demo/start?scenario_id=SCENARIO-ROUTINE-FLARE-02")
    assert start_res.status_code == 200
    state = start_res.json()
    assert state["scenario_id"] == "SCENARIO-ROUTINE-FLARE-02"
    assert state["facility_id"] == "FAC-IN-VAD-002"
    assert state["current_step"] == 0
    assert state["coordinates"] == [22.3552, 73.1352]

    # 2. Step 1 (Routine flaring)
    step_res = client.post("/api/data-gateway/demo/step")
    assert step_res.status_code == 200
    step_state = step_res.json()
    assert step_state["current_step"] == 1
    cls_res = step_state["active_classification"]
    assert cls_res["predicted_class"] in ["GAS_FLARE", "ROUTINE_PROCESS_HEAT"]
    assert step_state["active_fusion"]["fused_state"] == "ROUTINE_FLARING"
