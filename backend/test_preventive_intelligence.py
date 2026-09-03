import pytest
from app.services.predictive.early_warning_engine import early_warning_engine
from app.services.chemicals.chemical_registry import chemical_registry
from app.services.graph.risk_graph_service import risk_graph_service
from app.services.preventive.preventive_engine import preventive_engine
from app.services.preventive.preventive_whatif import preventive_whatif, PreventiveWhatIfRequest
from app.services.preventive.control_boundary import safety_control_boundary

def test_early_warning_multi_signal_fusion():
    print("\n--- 1. Testing Early Warning Multi-Signal Fusion Engine ---")
    
    # 1. Nominal T-04 Baseline
    res_normal = early_warning_engine.evaluate_asset_pre_incident_state(
        asset_id="T-04", asset_name="Ammonia Cryogenic Tank", chemical_name="Ammonia",
        pressure_bar=4.2, temperature_c=-33.0, vibration_mm_s=1.2, acoustic_db=14.0, maintenance_age_days=90
    )
    assert res_normal["state"] == "NORMAL"
    assert res_normal["early_warning_score"] < 35.0

    # 2. Critical Multi-Signal Excursion on T-04 (Pressure + Vibration + Acoustic + Thermal)
    res_crit = early_warning_engine.evaluate_asset_pre_incident_state(
        asset_id="T-04", asset_name="Ammonia Cryogenic Tank", chemical_name="Ammonia",
        pressure_bar=5.8, temperature_c=-22.0, vibration_mm_s=6.8, acoustic_db=42.0, maintenance_age_days=310,
        vision_thermal_anomaly=True
    )
    assert res_crit["state"] == "CRITICAL"
    assert res_crit["early_warning_score"] >= 75.0
    assert res_crit["confidence_pct"] >= 85.0
    assert len(res_crit["drivers_breakdown"]) == 5
    print(f"[PASS] Early warning state transitioned correctly: Score={res_crit['early_warning_score']}, State={res_crit['state']}, Top Driver={res_crit['top_driver']}")

def test_chemical_registry_and_incompatibility():
    print("\n--- 2. Testing Chemical Knowledge Layer & Incompatibility Matrix ---")
    
    nh3 = chemical_registry.get_chemical("CHEM-NH3")
    assert nh3 is not None
    assert nh3.cas_number == "7664-41-7"
    assert nh3.idlh_ppm == 300.0

    # Test Incompatibility: Ammonia + Chlorine -> Chloramines
    incomp = chemical_registry.check_incompatibility("CHEM-NH3", "CHEM-CL2")
    assert incomp["incompatible"] is True
    assert incomp["severity"] == "CRITICAL"
    assert "Chloramines" in incomp["reason"] or "Nitrogen Trichloride" in incomp["reason"]
    print("[PASS] Chemical knowledge and reactivity constraints verified.")

def test_risk_graph_and_domino_cascades():
    print("\n--- 3. Testing Multi-Relational Risk Graph & Domino Traversal ---")
    
    # 1. Cascade pathways from T-04
    cascade = risk_graph_service.analyze_cascade_pathways("T-04")
    assert cascade["primary_asset_id"] == "T-04"
    assert len(cascade["threatened_nodes"]) >= 2
    
    # Verify connected pipeline and synthesis loop are identified
    node_ids = [n["node_id"] for n in cascade["threatened_nodes"]]
    assert "PL-101" in node_ids or "PU-02" in node_ids

    # 2. Environmental consequence
    env = risk_graph_service.evaluate_environmental_consequence("T-04", wind_direction_deg=195.0)
    assert len(env) >= 3
    print(f"[PASS] Risk graph accurately traced {len(cascade['threatened_nodes'])} cascade nodes and {len(env)} environmental receptors.")

def test_preventive_whatif_simulator():
    print("\n--- 4. Testing Preventive What-If (PREDICT -> INTERVENE -> VERIFY) ---")
    
    req = PreventiveWhatIfRequest(
        asset_id="T-04",
        chemical_id="CHEM-NH3",
        base_risk_score=82.0,
        selected_action_ids=["ACT-T04-ISO", "ACT-T04-CURTAIN"]
    )
    outcome = preventive_whatif.simulate_intervention_outcome(req)
    
    assert outcome.mitigated_state["risk_score"] < outcome.base_state["risk_score"]
    assert outcome.deltas["risk_points_reduced"] >= 35.0
    assert outcome.deltas["risk_reduction_pct"] >= 45.0
    assert outcome.deltas["workers_saved"] >= 4
    print(f"[PASS] Preventive What-If verified: Base Risk={outcome.base_state['risk_score']} -> Mitigated={outcome.mitigated_state['risk_score']} (Delta: -{outcome.deltas['risk_reduction_pct']}%)")

def test_safety_control_boundary():
    print("\n--- 5. Testing Safety-Control Boundary & Human Authorization ---")
    
    # 1. Create Proposal (Read-Only)
    prop = safety_control_boundary.create_proposal(
        target_asset_id="T-04",
        action_type="ISOLATION",
        title="Actuate ROSOV-04A/B",
        command_params={"valve_tag": "V-101-ESD", "target_state": "CLOSED"}
    )
    assert prop.status == "PROPOSED"
    assert prop.checklist_verified is False

    # 2. Complete 3-item safety checklist and authorize
    auth_res = safety_control_boundary.authorize_control_action(
        action_id=prop.action_id,
        approver_name="Er. S. Nair",
        approver_role="HSE_COMMANDER",
        checklist_confirmations=[
            "Downwind gas concentrations verified via sniffer array",
            "Downstream process units notified and flare header clear",
            "Field ERT squad stationed at upwind perimeter"
        ]
    )
    assert auth_res["success"] is True
    assert auth_res["status"] == "AUTHORIZED"
    assert "AUTH-SIS-" in auth_res["authorization_token"]
    print("[PASS] Safety-Control boundary successfully enforced human authorization before control emission.")

if __name__ == "__main__":
    test_early_warning_multi_signal_fusion()
    test_chemical_registry_and_incompatibility()
    test_risk_graph_and_domino_cascades()
    test_preventive_whatif_simulator()
    test_safety_control_boundary()
    print("\nALL PREVENTIVE INTELLIGENCE TESTS PASSED (100% SUCCESS)!")
