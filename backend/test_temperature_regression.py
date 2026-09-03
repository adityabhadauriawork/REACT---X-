from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ambient_temperature_data_flow():
    print("==================================================")
    print("RUNNING AMBIENT TEMPERATURE REGRESSION TEST SUITE")
    print("==================================================")

    # 1. Test LIVE Mode Temperature from Open-Meteo
    weather_res = client.get("/api/weather/current?latitude=21.6850&longitude=72.5750")
    assert weather_res.status_code == 200
    live_w = weather_res.json()
    live_temp = live_w["temperature_c"]
    print(f"[OK] Fetched Live Weather: {live_temp}°C from Open-Meteo")

    live_sim_payload = {
        "title": "T-04 Live Weather Temperature Test",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "PIPELINE_LEAK",
        "release_rate_kg_s": 15.0,
        "release_duration_min": 30,
        "wind_speed_kmh": live_w["wind_speed_kmh"],
        "wind_direction_deg": live_w["wind_direction_deg"],
        "ambient_temp_c": live_temp,
        "atmospheric_stability": live_w["atmospheric_stability"],
        "weather_mode": "LIVE",
        "weather_source": "Open-Meteo"
    }

    sim_res = client.post("/api/hazard/simulate", json=live_sim_payload)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()

    # Verify ambient_temp_c is in HazardSimulationResult and matches exactly
    assert "ambient_temp_c" in sim_data, "ambient_temp_c missing in HazardSimulationResult schema"
    assert sim_data["ambient_temp_c"] == live_temp, f"Expected {live_temp}, got {sim_data['ambient_temp_c']}"
    print(f"[PASS] LIVE Mode HazardSimulationResult contains ambient_temp_c: {sim_data['ambient_temp_c']}°C")

    # Complete pipeline for LIVE mode
    imp = client.post("/api/impact/analyze?time_step_sec=120", json=sim_data).json()
    evac = client.post("/api/evacuation/route?origin_name=T-04%20Vicinity", json={
        "simulation_result": sim_data,
        "impact_result": imp,
        "origin_coords": sim_data["source_coordinates"]
    }).json()
    res = client.post("/api/resources/optimize", json={
        "simulation_result": sim_data,
        "impact_result": imp,
        "evacuation_plan": evac
    }).json()

    # Generate PDF and ensure it compiles cleanly with live temp
    pdf_res = client.post("/api/preplan/generate-pdf", json={
        "simulation_result": sim_data,
        "impact_result": imp,
        "evacuation_plan": evac,
        "resource_plan": res
    })
    assert pdf_res.status_code == 200
    print(f"[PASS] LIVE Mode Fire Pre-Plan PDF compiled successfully ({len(pdf_res.content):,} bytes)")

    # 2. Test DEMO Mode Custom Temperature (e.g. 38.5°C)
    demo_temp = 38.5
    demo_sim_payload = {
        "title": "T-04 Custom Demo Temperature Test",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "PIPELINE_LEAK",
        "release_rate_kg_s": 15.0,
        "release_duration_min": 30,
        "wind_speed_kmh": 8.0,
        "wind_direction_deg": 45.0,
        "ambient_temp_c": demo_temp,
        "atmospheric_stability": "D",
        "weather_mode": "DEMO",
        "weather_source": "Scenario Override"
    }

    demo_sim = client.post("/api/hazard/simulate", json=demo_sim_payload).json()
    assert demo_sim["ambient_temp_c"] == demo_temp, f"Expected {demo_temp}, got {demo_sim['ambient_temp_c']}"
    print(f"[PASS] DEMO Mode HazardSimulationResult contains custom ambient_temp_c: {demo_sim['ambient_temp_c']}°C")

    # 3. Test Presets Temperature Mapping
    presets = client.get("/api/scenarios/presets").json()
    for p in presets:
        p_sim = client.post("/api/hazard/simulate", json={
            "title": p["title"],
            "asset_id": p["asset_id"],
            "chemical_id": p["chemical_id"],
            "incident_type": p["incident_type"],
            "release_rate_kg_s": p["release_rate_kg_s"],
            "release_duration_min": p["release_duration_min"],
            "wind_speed_kmh": p["wind_speed_kmh"],
            "wind_direction_deg": p["wind_direction_deg"],
            "ambient_temp_c": p["ambient_temp_c"],
            "atmospheric_stability": p["atmospheric_stability"],
            "weather_mode": "DEMO",
            "weather_source": "Preset"
        }).json()
        assert p_sim["ambient_temp_c"] == p["ambient_temp_c"]
        print(f"[PASS] Preset {p['asset_id']} ({p['chemical_id']}) matches temperature: {p_sim['ambient_temp_c']}°C")

    print("\n==================================================")
    print("ALL AMBIENT TEMPERATURE REGRESSION TESTS PASSED (100%)!")
    print("==================================================")

if __name__ == "__main__":
    test_ambient_temperature_data_flow()
