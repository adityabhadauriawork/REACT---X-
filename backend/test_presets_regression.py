import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_preset_pipeline(preset_id, expected_asset, expected_chem_id, expected_chem_name):
    print(f"\n=======================================================")
    print(f"TESTING PRESET: {preset_id}")
    print(f"Expected: Asset={expected_asset}, ChemID={expected_chem_id}, Name={expected_chem_name}")
    print(f"=======================================================")

    # 1. Fetch presets catalog
    presets_res = client.get("/api/scenarios/presets")
    assert presets_res.status_code == 200
    presets = presets_res.json()
    preset = next((p for p in presets if p["id"] == preset_id or p["asset_id"] == expected_asset), None)
    assert preset is not None, f"Preset {preset_id} not found in catalog"

    print(f"[OK] Found Preset: '{preset['title']}'")
    assert preset["asset_id"] == expected_asset
    assert preset["chemical_id"] == expected_chem_id

    # 2. Step 1: Run Hazard Simulation
    sim_payload = {
        "title": preset["title"],
        "asset_id": preset["asset_id"],
        "chemical_id": preset["chemical_id"],
        "incident_type": preset["incident_type"],
        "release_rate_kg_s": preset["release_rate_kg_s"],
        "release_duration_min": preset["release_duration_min"],
        "operating_temp_c": preset["operating_temp_c"],
        "operating_pressure_bar": preset["operating_pressure_bar"],
        "wind_speed_kmh": preset["wind_speed_kmh"],
        "wind_direction_deg": preset["wind_direction_deg"],
        "ambient_temp_c": preset["ambient_temp_c"],
        "atmospheric_stability": preset["atmospheric_stability"],
        "humidity_pct": preset["humidity_pct"],
        "weather_mode": "DEMO",
        "weather_source": "Scenario Preset"
    }
    sim_res = client.post("/api/hazard/simulate", json=sim_payload)
    assert sim_res.status_code == 200, f"Simulate failed for {preset_id}: {sim_res.text}"
    sim_data = sim_res.json()
    assert sim_data["chemical_id"] == expected_chem_id
    assert expected_chem_name.lower() in sim_data["chemical_name"].lower()
    print(f"[OK] Step 1 Simulation: Chemical='{sim_data['chemical_name']}', Zones={len(sim_data['summary_zones'])}, RedReach={sim_data['summary_zones'][0]['max_downwind_distance_m']}m")

    # 3. Step 2: Spatial Impact
    imp_res = client.post("/api/impact/analyze?time_step_sec=120", json=sim_data)
    assert imp_res.status_code == 200, f"Impact failed for {preset_id}: {imp_res.text}"
    imp_data = imp_res.json()
    print(f"[OK] Step 2 Impact: AffectedWorkers={imp_data['affected_workers_count']}, BlockedRoads={imp_data['blocked_roads_count']}, RiskScore={imp_data['risk_assessment']['overall_score']}")

    # 4. Step 3: Evacuation Routing
    evac_res = client.post(f"/api/evacuation/route?origin_name={expected_asset}%20Vicinity", json={
        "simulation_result": sim_data,
        "impact_result": imp_data,
        "origin_coords": sim_data["source_coordinates"]
    })
    assert evac_res.status_code == 200, f"Evacuation failed for {preset_id}: {evac_res.text}"
    evac_data = evac_res.json()
    route = evac_data["primary_evacuation_route"]
    print(f"[OK] Step 3 Evacuation: Target='{route['recommended_assembly_point_name']}' via '{route['recommended_gate_name']}', Distance={route['total_distance_m']}m")

    # 5. Step 4: Tactical Resources
    res_res = client.post("/api/resources/optimize", json={
        "simulation_result": sim_data,
        "impact_result": imp_data,
        "evacuation_plan": evac_data
    })
    assert res_res.status_code == 200, f"Resources failed for {preset_id}: {res_res.text}"
    res_data = res_res.json()
    assert len(res_data["recommended_resources"]) >= 3
    print(f"[OK] Step 4 Resources: DispatchedUnits={len(res_data['recommended_resources'])}, Water={res_data['foam_water_requirements']['firewater_demand_lpm']} LPM, Foam={res_data['foam_water_requirements']['foam_concentrate_demand_liters']} L, PPE={res_data['foam_water_requirements']['ppe_required'].split('(')[0]}")

    return {
        "sim": sim_data,
        "imp": imp_data,
        "evac": evac_data,
        "res": res_data
    }

def test_full_preset_regression():
    print("==================================================")
    print("RUNNING MULTI-PRESET SWITCHING REGRESSION SUITE")
    print("==================================================")

    # Test 1: T-04 Ammonia Preset
    res_t04 = run_preset_pipeline("SCEN-PRIMARY-01", "T-04", "CHEM-NH3", "Ammonia")

    # Test 2: T-03 LPG Preset (The failing preset)
    res_t03 = run_preset_pipeline("SCEN-LPG-02", "T-03", "CHEM-LPG", "Liquefied Petroleum Gas")

    # Test 3: T-02 Chlorine Preset
    res_t02 = run_preset_pipeline("SCEN-CL2-03", "T-02", "CHEM-CL2", "Chlorine")

    # Test 4: Switch Back to T-04 (Ensuring State Stability)
    print("\n--- SWITCHING BACK TO T-04 AMMONIA ---")
    res_t04_retest = run_preset_pipeline("SCEN-PRIMARY-01", "T-04", "CHEM-NH3", "Ammonia")

    # Verify chemical differences across presets
    assert res_t04["sim"]["chemical_id"] != res_t03["sim"]["chemical_id"]
    assert res_t03["sim"]["chemical_id"] != res_t02["sim"]["chemical_id"]
    assert res_t04["res"]["foam_water_requirements"]["foam_concentrate_demand_liters"] == 0.0
    assert res_t03["res"]["foam_water_requirements"]["foam_concentrate_demand_liters"] > 0.0

    print("\n==================================================")
    print("ALL MULTI-PRESET REGRESSION TESTS PASSED (100% SUCCESS)!")
    print("==================================================")

if __name__ == "__main__":
    test_full_preset_regression()
