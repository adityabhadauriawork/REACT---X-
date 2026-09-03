import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_phase2_backend_intelligence():
    print("================================================================================")
    print("TESTING PHASE-2 INTELLIGENCE MODULE BACKEND ENDPOINTS")
    print("================================================================================")

    # 1. WHAT-IF SCENARIO COMPARISON
    print("\n--- 1. TESTING WHAT-IF COMPARISON ENDPOINT ---")
    whatif_payload = {
        "scenario_a": {
            "label": "Base Incident (15 kg/s)",
            "asset_id": "T-04",
            "chemical_id": "CHEM-NH3",
            "incident_type": "PIPELINE_LEAK",
            "release_rate_kg_s": 15.0,
            "wind_speed_kmh": 8.0,
            "wind_direction_deg": 45.0
        },
        "scenario_b": {
            "label": "Doubled Release (30 kg/s)",
            "asset_id": "T-04",
            "chemical_id": "CHEM-NH3",
            "incident_type": "PIPELINE_LEAK",
            "release_rate_kg_s": 30.0,
            "wind_speed_kmh": 8.0,
            "wind_direction_deg": 45.0
        }
    }
    w_res = client.post("/api/intelligence/whatif/compare", json=whatif_payload)
    assert w_res.status_code == 200, f"What-If failed: {w_res.text}"
    w_data = w_res.json()
    assert w_data["scenario_b"]["red_reach_m"] > w_data["scenario_a"]["red_reach_m"]
    assert w_data["deltas"]["red_reach_delta_m"] > 0
    print(f"[PASS] What-If Comparison: Red Zone A={w_data['scenario_a']['red_reach_m']}m -> B={w_data['scenario_b']['red_reach_m']}m (Delta: +{w_data['deltas']['red_reach_delta_m']}m, +{w_data['deltas']['red_reach_delta_pct']}%)")
    print(f"       Summary: {w_data['deltas']['comparative_summary']}")

    # 2. HISTORICAL INCIDENT ANALYTICS
    print("\n--- 2. TESTING HISTORICAL ANALYTICS ENDPOINT ---")
    a_res = client.get("/api/intelligence/analytics/summary")
    assert a_res.status_code == 200, f"Analytics failed: {a_res.text}"
    a_data = a_res.json()
    assert a_data["total_historical_incidents"] >= 20
    assert len(a_data["asset_risk_rankings"]) > 0
    assert len(a_data["chemical_breakdowns"]) > 0
    print(f"[PASS] Analytics Summary: {a_data['total_historical_incidents']} seeded events analyzed.")
    print(f"       Avg Response Time: {a_data['avg_response_time_min']}m, Top Vulnerable Asset: {a_data['top_vulnerable_asset']}, High/Crit Count: {a_data['high_critical_incident_count']}")

    # 3. PREDICTIVE MAINTENANCE / ASSET EARLY WARNING
    print("\n--- 3. TESTING PREDICTIVE ASSET HEALTH ENDPOINT ---")
    p_res = client.get("/api/intelligence/predictive/assets")
    assert p_res.status_code == 200, f"Predictive failed: {p_res.text}"
    p_data = p_res.json()
    assert p_data["total_monitored_assets"] >= 8
    assert p_data["critical_risk_count"] + p_data["high_risk_count"] > 0
    top_risk_asset = p_data["assets"][0]
    print(f"[PASS] Predictive Asset Health: {p_data['total_monitored_assets']} assets monitored.")
    print(f"       Top Risk Asset: {top_risk_asset['asset_id']} (Score: {top_risk_asset['failure_risk_score']}/100, Category: {top_risk_asset['risk_category']})")
    print(f"       Top Driver: {top_risk_asset['top_risk_driver']}")

    # 4. COMPUTER VISION DETECTION
    print("\n--- 4. TESTING COMPUTER VISION DETECTION ENDPOINT ---")
    v_presets = client.get("/api/intelligence/vision/presets").json()
    assert len(v_presets) >= 4
    v_res = client.post("/api/intelligence/vision/detect", data={"camera_id": "CAM-01", "simulate_hazard_type": "SMOKE"})
    assert v_res.status_code == 200, f"Vision failed: {v_res.text}"
    v_data = v_res.json()
    assert len(v_data["detections"]) > 0
    assert v_data["incident_suggested"] is True
    print(f"[PASS] Vision Detection: Analyzed {v_data['camera_id']} ({v_data['camera_location']})")
    print(f"       Alert Level: {v_data['alert_level']}, Detected: {[d['label'] for d in v_data['detections']]}")
    print(f"       Suggestion: Asset={v_data['suggested_asset_id']}, Chem={v_data['suggested_chemical_id']}")

    # 5. AI EMERGENCY COPILOT
    print("\n--- 5. TESTING AI EMERGENCY COPILOT ENDPOINT ---")
    
    # Query 1: Evacuation reasoning
    c1 = client.post("/api/intelligence/copilot/chat", json={
        "query": "Why is AP-1 unsafe?",
        "simulation_result": w_data["scenario_a_simulation"],
        "impact_result": {"total_workers_at_site": 28, "affected_workers_count": 0},
        "evacuation_plan": w_data["scenario_a_evacuation"],
        "resource_plan": w_data["scenario_a_resources"]
    }).json()
    assert c1["intent_detected"] == "EVACUATION_RATIONALE"
    print(f"[PASS] Copilot (Evacuation Query): Intent='{c1['intent_detected']}'")
    safe_preview = c1['reply'][:120].encode('ascii', 'replace').decode('ascii')
    print(f"       Reply Preview: {safe_preview}...")

    # Query 2: What-if hypothetical reasoning
    c2 = client.post("/api/intelligence/copilot/chat", json={
        "query": "What if the release rate doubles?",
        "simulation_result": w_data["scenario_a_simulation"],
        "impact_result": {"total_workers_at_site": 28, "affected_workers_count": 0},
        "evacuation_plan": w_data["scenario_a_evacuation"],
        "resource_plan": w_data["scenario_a_resources"]
    }).json()
    assert c2["intent_detected"] == "WHAT_IF_HYPOTHETICAL"
    assert "red_reach_delta_m" in c2["grounded_metrics"]
    print(f"[PASS] Copilot (Hypothetical Query): Intent='{c2['intent_detected']}', Red Reach Delta: +{c2['grounded_metrics']['red_reach_delta_m']}m")

    # Query 3: HSE Briefing
    c3 = client.post("/api/intelligence/copilot/chat", json={
        "query": "Generate an executive briefing for HSE controller",
        "simulation_result": w_data["scenario_a_simulation"],
        "impact_result": {"total_workers_at_site": 28, "affected_workers_count": 0, "risk_assessment": {"overall_score": 75, "risk_category": "HIGH"}},
        "evacuation_plan": w_data["scenario_a_evacuation"],
        "resource_plan": w_data["scenario_a_resources"]
    }).json()
    assert c3["intent_detected"] == "HSE_EXECUTIVE_BRIEFING"
    print(f"[PASS] Copilot (HSE Briefing Query): Intent='{c3['intent_detected']}'")

    print("\n================================================================================")
    print("ALL 5 PHASE-2 INTELLIGENCE ENDPOINTS 100% OPERATIONAL & VERIFIED!")
    print("================================================================================")

if __name__ == "__main__":
    test_phase2_backend_intelligence()
