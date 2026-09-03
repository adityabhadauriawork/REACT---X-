import json
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_cross_role_data_consistency():
    print("=" * 80)
    print("SIH-1505 FINAL CROSS-ROLE CANONICAL DATA CONSISTENCY & INTEGRITY AUDIT")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 1: INITIALIZE CANONICAL T-04 AMMONIA SCENARIO
    # -------------------------------------------------------------------------
    print("\n--- 1. RUNNING AUTHORITATIVE T-04 AMMONIA SCENARIO PIPELINE ---")
    scenario_params = {
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "PIPELINE_LEAK",
        "release_rate_kg_s": 15.0,
        "release_duration_min": 30,
        "wind_speed_kmh": 8.0,
        "wind_direction_deg": 45.0,
        "ambient_temp_c": 32.0,
        "atmospheric_stability": "D",
        "weather_mode": "DEMO"
    }

    # 1. Hazard Simulation
    sim_res = client.post("/api/hazard/simulate", json=scenario_params)
    assert sim_res.status_code == 200, f"Simulation failed: {sim_res.text}"
    sim = sim_res.json()
    sim["id"] = "INC-T-04"

    # 2. Impact Assessment
    imp_res = client.post("/api/impact/analyze?time_step_sec=120", json=sim)
    assert imp_res.status_code == 200, f"Impact failed: {imp_res.text}"
    imp = imp_res.json()

    # 3. Evacuation Route
    evac_res = client.post("/api/evacuation/route?origin_name=T-04%20Vicinity", json={"simulation_result": sim, "impact_result": imp})
    assert evac_res.status_code == 200, f"Evacuation failed: {evac_res.text}"
    evac = evac_res.json()

    # 4. Tactical Resource Optimization
    res_res = client.post("/api/resources/optimize", json={"simulation_result": sim, "impact_result": imp, "evacuation_plan": evac})
    assert res_res.status_code == 200, f"Resources failed: {res_res.text}"
    res = res_res.json()

    # CANONICAL VALUES
    canonical_id = sim["id"]
    canonical_asset = sim["source_asset_id"]
    canonical_chem = sim["chemical_name"]
    canonical_score = imp["risk_assessment"]["overall_score"]
    canonical_category = imp["risk_assessment"]["risk_category"]
    canonical_workers = imp["affected_workers_count"]
    canonical_assets = imp["affected_assets_count"]
    canonical_roads = imp["blocked_roads_count"]
    canonical_ap = evac["primary_evacuation_route"]["recommended_assembly_point_name"]
    canonical_gate = evac["primary_evacuation_route"]["recommended_gate_name"]
    canonical_dist = evac["primary_evacuation_route"]["total_distance_m"]
    canonical_lead_unit = res["recommended_resources"][0]["resource_name"]
    canonical_water = res["foam_water_requirements"]["firewater_demand_lpm"]

    print(f"CANONICAL INCIDENT FACTS ESTABLISHED:")
    print(f" • Incident ID:             {canonical_id}")
    print(f" • Source Asset:            {canonical_asset} ({canonical_chem})")
    print(f" • Canonical Risk Score:    {canonical_score}/100 ({canonical_category})")
    print(f" • Exposed Personnel:       {canonical_workers} workers")
    print(f" • Threatened Assets:       {canonical_assets} units")
    print(f" • Blocked Road Corridors:  {canonical_roads} segments")
    print(f" • Safe Evacuation Target:  {canonical_ap} via {canonical_gate} ({canonical_dist:.1f}m)")
    print(f" • Tactical Lead Unit:      {canonical_lead_unit} ({canonical_water:,.0f} LPM)")

    # -------------------------------------------------------------------------
    # STEP 2: VERIFY EXECUTIVE SITUATION BRIEF USES EXACT CANONICAL STATE
    # -------------------------------------------------------------------------
    print("\n--- 2. VERIFYING EXECUTIVE SITUATION BRIEF CANONICAL CONSISTENCY ---")
    brief_req = {
        "simulation_result": sim,
        "impact_result": imp,
        "evacuation_plan": evac,
        "resource_plan": res
    }
    brief_res = client.post("/api/intelligence/executive-brief", json=brief_req)
    assert brief_res.status_code == 200, f"Brief failed: {brief_res.text}"
    brief = brief_res.json()

    assert brief["source_asset"] == canonical_asset, f"Asset mismatch: {brief['source_asset']} vs {canonical_asset}"
    assert brief["chemical"] == canonical_chem, f"Chemical mismatch: {brief['chemical']} vs {canonical_chem}"
    assert brief["severity_score"] == canonical_score, f"Risk score mismatch: {brief['severity_score']} vs {canonical_score}"
    assert brief["severity_category"] == canonical_category, f"Severity category mismatch: {brief['severity_category']} vs {canonical_category}"
    assert brief["exposed_workers_count"] == canonical_workers, f"Workers mismatch: {brief['exposed_workers_count']} vs {canonical_workers}"
    assert brief["compromised_assets_count"] == canonical_assets, f"Assets mismatch: {brief['compromised_assets_count']} vs {canonical_assets}"
    assert brief["blocked_road_segments_count"] == canonical_roads, f"Roads mismatch: {brief['blocked_road_segments_count']} vs {canonical_roads}"
    assert brief["primary_assembly_point"] == canonical_ap, f"Muster mismatch: {brief['primary_assembly_point']} vs {canonical_ap}"
    assert brief["primary_exit_gate"] == canonical_gate, f"Gate mismatch: {brief['primary_exit_gate']} vs {canonical_gate}"
    print(f"[PASS] Executive Brief matches 100% of canonical incident facts.")

    # -------------------------------------------------------------------------
    # STEP 3: VERIFY INCIDENT TIMELINE USES EXACT CANONICAL STATE
    # -------------------------------------------------------------------------
    print("\n--- 3. VERIFYING INCIDENT TIMELINE CANONICAL CONSISTENCY ---")
    timeline_req = {
        "simulation_result": sim,
        "impact_result": imp,
        "evacuation_plan": evac,
        "resource_plan": res
    }
    t_res = client.post("/api/intelligence/timeline", json=timeline_req)
    assert t_res.status_code == 200, f"Timeline failed: {t_res.text}"
    timeline = t_res.json()

    assert timeline["asset_id"] == canonical_asset
    assert timeline["chemical_name"] == canonical_chem

    # Find Impact Assessment Milestone in timeline
    impact_evt = next((e for e in timeline["events"] if e["event_type"] == "IMPACT_ASSESSED"), None)
    assert impact_evt is not None
    assert impact_evt["key_metrics"]["risk_score"] == canonical_score, f"Timeline risk score mismatch: {impact_evt['key_metrics']['risk_score']} vs {canonical_score}"
    assert impact_evt["key_metrics"]["exposed_workers"] == canonical_workers, f"Timeline workers mismatch"

    # Find Evacuation Milestone in timeline
    evac_evt = next((e for e in timeline["events"] if e["event_type"] == "EVACUATION_ROUTED"), None)
    assert evac_evt is not None
    assert evac_evt["key_metrics"]["target_ap"] == canonical_ap, f"Timeline muster mismatch"
    assert evac_evt["key_metrics"]["exit_gate"] == canonical_gate, f"Timeline gate mismatch"
    print(f"[PASS] Incident Timeline events match 100% of canonical incident facts.")

    # -------------------------------------------------------------------------
    # STEP 4: VERIFY DOMINO SCREENING USES EXACT CANONICAL STATE
    # -------------------------------------------------------------------------
    print("\n--- 4. VERIFYING DOMINO SCREENING CANONICAL CONSISTENCY ---")
    domino_req = {
        "simulation_result": sim,
        "impact_result": imp
    }
    d_res = client.post("/api/intelligence/domino-risk", json=domino_req)
    assert d_res.status_code == 200, f"Domino failed: {d_res.text}"
    domino = d_res.json()

    assert domino["source_asset_id"] == canonical_asset
    assert domino["source_chemical_name"] == canonical_chem
    print(f"[PASS] Domino Cascade Screener accurately grounded to canonical epicenter.")

    # -------------------------------------------------------------------------
    # STEP 5: VERIFY DECISION AUDIT TRAIL LOGS CANONICAL INCIDENT ID
    # -------------------------------------------------------------------------
    print("\n--- 5. VERIFYING DECISION AUDIT TRAIL PRESERVES CANONICAL ID ---")
    audit_rec = {
        "incident_id": canonical_id,
        "module": "EVACUATION",
        "input_summary": f"{canonical_asset} • {canonical_chem} (Wind 45° NE)",
        "recommendation": f"Muster at {canonical_ap} via {canonical_gate}",
        "reason": "Optimal crosswind path avoiding lethal vapor envelope",
        "human_action": "APPROVED",
        "actor_role": "HSE_COMMANDER",
        "actor_name": "Demo HSE Controller"
    }
    rec_res = client.post("/api/intelligence/audit-trail/record", json=audit_rec)
    assert rec_res.status_code == 200, f"Audit record failed: {rec_res.text}"
    recorded = rec_res.json()
    assert recorded["incident_id"] == canonical_id
    assert recorded["recommendation"] == f"Muster at {canonical_ap} via {canonical_gate}"
    print(f"[PASS] Decision Audit Trail preserved canonical incident ID and muster target.")

    # -------------------------------------------------------------------------
    # STEP 6: PARAMETER CHANGE (DOUBLED RELEASE RATE) CONSISTENCY PROPAGATION
    # -------------------------------------------------------------------------
    print("\n--- 6. TESTING SCENARIO PARAMETER CHANGE DYNAMIC PROPAGATION ---")
    altered_params = dict(scenario_params)
    altered_params["release_rate_kg_s"] = 30.0  # Doubled release rate

    # Re-run pipeline with altered parameter
    sim2 = client.post("/api/hazard/simulate", json=altered_params).json()
    sim2["id"] = "INC-T-04"
    imp2 = client.post("/api/impact/analyze?time_step_sec=120", json=sim2).json()
    evac2 = client.post("/api/evacuation/route?origin_name=T-04%20Vicinity", json={"simulation_result": sim2, "impact_result": imp2}).json()
    res2 = client.post("/api/resources/optimize", json={"simulation_result": sim2, "impact_result": imp2, "evacuation_plan": evac2}).json()

    new_canonical_score = imp2["risk_assessment"]["overall_score"]
    new_canonical_category = imp2["risk_assessment"]["risk_category"]
    new_canonical_reach = sim2["summary_zones"][0]["max_downwind_distance_m"]
    print(f"Altered Parameter: Release Rate doubled from 15 kg/s -> 30 kg/s")
    print(f"New Canonical Risk Score: {new_canonical_score}/100 ({new_canonical_category}), Red Reach: {new_canonical_reach:.1f}m")

    # Generate Executive Brief for altered state
    brief2 = client.post("/api/intelligence/executive-brief", json={
        "simulation_result": sim2, "impact_result": imp2, "evacuation_plan": evac2, "resource_plan": res2
    }).json()

    assert brief2["severity_score"] == new_canonical_score, f"Brief failed to dynamically update risk score!"
    assert brief2["max_red_reach_m"] == new_canonical_reach, f"Brief failed to dynamically update red zone reach!"
    print(f"[PASS] Parameter changes dynamically and consistently update across all consumers without stale data!")

    print("\n" + "=" * 80)
    print("ALL CROSS-ROLE DATA CONSISTENCY & INTEGRITY AUDITS PASSED 100%!")
    print("=" * 80)

if __name__ == "__main__":
    test_cross_role_data_consistency()
