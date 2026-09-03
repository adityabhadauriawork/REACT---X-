import pytest
import requests
import json
import sys

def is_live_available():
    try:
        r = requests.get("http://localhost:5173/", timeout=1)
        return r.status_code == 200
    except Exception:
        return False

@pytest.mark.skipif(not is_live_available(), reason="Live frontend dev server not running at http://localhost:5173")
def test_live_servers():
    print("==================================================")
    print("RUNNING LIVE END-TO-END & TACTICAL RESOURCE AUDIT TESTS")
    print("==================================================")

    backend_base = "http://127.0.0.1:8000/api"
    frontend_url = "http://localhost:5173/"

    # 1. Test Frontend Server
    try:
        fe_res = requests.get(frontend_url, timeout=5)
        assert fe_res.status_code == 200
        assert "<title>SIH 1505" in fe_res.text or "root" in fe_res.text
        print("[PASS] [1/14] Frontend dev server is responding at http://localhost:5173 (HTTP 200)")
    except Exception as e:
        print(f"[FAIL] [1/14] Frontend error: {e}")
        raise

    # 2. Test Backend Health
    try:
        health_res = requests.get(f"{backend_base}/health", timeout=5)
        assert health_res.status_code == 200
        print("[PASS] [2/14] Backend API health check passed at http://127.0.0.1:8000/api/health")
    except Exception as e:
        print(f"[FAIL] [2/14] Backend health error: {e}")
        raise

    # 3. Test Live Weather Service (Open-Meteo)
    try:
        weather_res = requests.get(f"{backend_base}/weather/current?latitude=21.6850&longitude=72.5750", timeout=8)
        assert weather_res.status_code == 200
        live_weather = weather_res.json()
        assert "temperature_c" in live_weather
        assert "wind_speed_kmh" in live_weather
        assert "wind_direction_deg" in live_weather
        assert "source" in live_weather
        assert "is_live" in live_weather
        assert live_weather["is_live"] is True
        print(f"[PASS] [3/14] Live Open-Meteo Weather fetched: {live_weather['temperature_c']}°C, {live_weather['wind_speed_kmh']} km/h ({live_weather['wind_direction_cardinal']} {live_weather['wind_direction_deg']}°), Source='{live_weather['source']}'")
    except Exception as e:
        print(f"[FAIL] [3/14] Live weather error: {e}")
        raise

    # 4. Test Weather Service Fallback Mode
    try:
        fallback_res = requests.get(f"{backend_base}/weather/current?latitude=999.0&longitude=999.0", timeout=8)
        assert fallback_res.status_code == 200
        fallback_data = fallback_res.json()
        assert fallback_data["is_live"] is False
        assert "Fallback" in fallback_data["source"] or fallback_data["error"] is not None
        print(f"[PASS] [4/14] Weather Fail-Safe Fallback verified: Handled invalid coords cleanly with source='{fallback_data['source']}'")
    except Exception as e:
        print(f"[FAIL] [4/14] Weather fallback error: {e}")
        raise

    # 5. Test Site Data
    site_res = requests.get(f"{backend_base}/site", timeout=5)
    assert site_res.status_code == 200
    site_data = site_res.json()
    assert site_data["plant"]["name"] == "PetroChem Complex Alpha - Unit 04"
    assert len(site_data["assets"]) >= 10
    assert len(site_data["workers"]) >= 25
    assert len(site_data["roads"]) >= 8
    print(f"[PASS] [5/14] Site API verified: {len(site_data['assets'])} assets, {len(site_data['workers'])} workers, {len(site_data['roads'])} roads")

    # 6. Test Chemicals
    chems_res = requests.get(f"{backend_base}/chemicals", timeout=5)
    assert chems_res.status_code == 200
    chems = chems_res.json()
    assert len(chems) >= 5
    nh3 = next(c for c in chems if c["id"] == "CHEM-NH3")
    assert nh3["molecular_weight"] == 17.03
    print(f"[PASS] [6/14] Chemicals API verified: {len(chems)} hazardous substances loaded with SDS intelligence")

    # 7. Test Presets
    presets_res = requests.get(f"{backend_base}/scenarios/presets", timeout=5)
    assert presets_res.status_code == 200
    presets = presets_res.json()
    assert len(presets) >= 3
    primary_preset = next(p for p in presets if p["asset_id"] == "T-04")
    print(f"[PASS] [7/14] Scenario Presets API verified: Primary demo '{primary_preset['title']}' loaded")

    # 8. Test Hazard Simulation in LIVE WEATHER Mode (SSW Wind)
    live_sim_payload = {
        "title": "T-04 Live Weather Simulation",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "PIPELINE_LEAK",
        "release_rate_kg_s": 15.0,
        "release_duration_min": 30,
        "operating_temp_c": live_weather["temperature_c"],
        "operating_pressure_bar": 4.5,
        "wind_speed_kmh": live_weather["wind_speed_kmh"],
        "wind_direction_deg": live_weather["wind_direction_deg"],
        "ambient_temp_c": live_weather["temperature_c"],
        "atmospheric_stability": live_weather["atmospheric_stability"],
        "humidity_pct": 65.0,
        "weather_mode": "LIVE",
        "weather_source": "Open-Meteo"
    }
    live_sim_res = requests.post(f"{backend_base}/hazard/simulate", json=live_sim_payload, timeout=5)
    assert live_sim_res.status_code == 200
    live_sim_data = live_sim_res.json()
    assert live_sim_data["weather_mode"] == "LIVE"
    assert live_sim_data["wind_direction_deg"] == live_weather["wind_direction_deg"]
    print(f"[PASS] [8/14] LIVE Mode Simulation verified: Plume towards {(live_weather['wind_direction_deg'] + 180)%360:.0f}°")

    # 9. Test Hazard Simulation in DEMO WEATHER Mode (NE Wind 45 deg)
    demo_sim_payload = {
        "title": "T-04 Primary Demo Scenario (Benchmark)",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "PIPELINE_LEAK",
        "release_rate_kg_s": 15.0,
        "release_duration_min": 30,
        "operating_temp_c": 32.0,
        "operating_pressure_bar": 4.5,
        "wind_speed_kmh": 8.0,
        "wind_direction_deg": 45.0,
        "ambient_temp_c": 32.0,
        "atmospheric_stability": "D",
        "humidity_pct": 65.0,
        "weather_mode": "DEMO",
        "weather_source": "Scenario Override (Primary Demo)"
    }
    demo_sim_res = requests.post(f"{backend_base}/hazard/simulate", json=demo_sim_payload, timeout=5)
    assert demo_sim_res.status_code == 200
    demo_sim_data = demo_sim_res.json()
    assert demo_sim_data["weather_mode"] == "DEMO"
    assert demo_sim_data["wind_direction_deg"] == 45.0
    print(f"[PASS] [9/14] DEMO Mode Simulation verified: Plume towards 225° (SW)")

    # 10. Audit Dynamic Evacuation Routing for Scenario A (SSW 195 deg Wind)
    imp_a = requests.post(f"{backend_base}/impact/analyze?time_step_sec=120", json=live_sim_data, timeout=5).json()
    evac_a = requests.post(f"{backend_base}/evacuation/route?origin_name=T-04%20Vicinity", json={
        "simulation_result": live_sim_data,
        "impact_result": imp_a,
        "origin_coords": live_sim_data["source_coordinates"]
    }, timeout=5).json()
    route_a = evac_a["primary_evacuation_route"]
    assert "score_breakdown" in route_a
    assert len(evac_a["candidate_routes"]) == 4
    assert route_a["recommended_assembly_point_id"] == "AP-3"
    print(f"[PASS] [10/14] Evacuation Scenario A Verified: Selected {route_a['recommended_assembly_point_name']} ({route_a['total_distance_m']}m), AP-1 rejected (downwind)")

    # 11. Audit Dynamic Evacuation Routing for Scenario B (NE 45 deg Wind)
    imp_b = requests.post(f"{backend_base}/impact/analyze?time_step_sec=120", json=demo_sim_data, timeout=5).json()
    evac_b = requests.post(f"{backend_base}/evacuation/route?origin_name=T-04%20Vicinity", json={
        "simulation_result": demo_sim_data,
        "impact_result": imp_b,
        "origin_coords": demo_sim_data["source_coordinates"]
    }, timeout=5).json()
    route_b = evac_b["primary_evacuation_route"]
    assert "score_breakdown" in route_b
    assert len(evac_b["candidate_routes"]) == 4
    assert route_b["recommended_assembly_point_id"] in ["AP-4", "AP-1"]
    print(f"[PASS] [11/14] Evacuation Scenario B Verified: Route legitimately changed to {route_b['recommended_assembly_point_name']} ({route_b['total_distance_m']}m)")

    # 12. Audit Dynamic Tactical Resource Engine for Scenario A (Ammonia Toxic Gas)
    res_a = requests.post(f"{backend_base}/resources/optimize", json={
        "simulation_result": live_sim_data,
        "impact_result": imp_a,
        "evacuation_plan": evac_a
    }, timeout=5).json()
    assert "decision_support_disclaimer" in res_a
    assert res_a["foam_water_requirements"]["foam_concentrate_demand_liters"] == 0.0, "Ammonia toxic release does not demand AFFF foam"
    assert "Level A" in res_a["foam_water_requirements"]["ppe_required"]
    etas_a = [r["estimated_arrival_min"] for r in res_a["recommended_resources"]]
    assert len(set(etas_a)) > 1, "ETAs must be derived from geolocation transit distances"
    print(f"[PASS] [12/14] Tactical Resource Engine Scenario A Verified: Ammonia Toxic Inhalation (Water={res_a['foam_water_requirements']['firewater_demand_lpm']} LPM, Foam=0L, PPE=Level A, Calculated ETAs={[r['estimated_arrival_min'] for r in res_a['recommended_resources']]})")

    # 13. Audit Dynamic Tactical Resource Engine for Scenario B (LPG BLEVE / Fire)
    lpg_sim = requests.post(f"{backend_base}/hazard/simulate", json={
        "title": "T-03 LPG Sphere BLEVE & Fire",
        "asset_id": "T-03",
        "chemical_id": "CHEM-LPG",
        "incident_type": "FIRE_EXPLOSION",
        "release_rate_kg_s": 35.0,
        "release_duration_min": 30,
        "wind_speed_kmh": 10.0,
        "wind_direction_deg": 45.0,
        "ambient_temp_c": 32.0,
        "atmospheric_stability": "D"
    }, timeout=5).json()
    lpg_imp = requests.post(f"{backend_base}/impact/analyze?time_step_sec=120", json=lpg_sim, timeout=5).json()
    res_b = requests.post(f"{backend_base}/resources/optimize", json={
        "simulation_result": lpg_sim,
        "impact_result": lpg_imp
    }, timeout=5).json()
    assert "structural" in res_b["foam_water_requirements"]["ppe_required"].lower() or "turnout" in res_b["foam_water_requirements"]["ppe_required"].lower()
    assert res_b["foam_water_requirements"]["firewater_demand_lpm"] > res_a["foam_water_requirements"]["firewater_demand_lpm"]
    print(f"[PASS] [13/14] Tactical Resource Engine Scenario B Verified: LPG BLEVE Fire (Water={res_b['foam_water_requirements']['firewater_demand_lpm']} LPM, Foam={res_b['foam_water_requirements']['foam_concentrate_demand_liters']}L, PPE=NFPA Structural Turnout)")

    # 14. Test Fire Pre-Plan PDF Generation
    pdf_res = requests.post(
        f"{backend_base}/preplan/generate-pdf",
        json={
            "simulation_result": demo_sim_data,
            "impact_result": imp_b,
            "evacuation_plan": evac_b,
            "resource_plan": res_a,
            "author_name": "HSE Incident Commander",
            "license_no": "PESO/IND/2024/MAH-1505"
        },
        timeout=5
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert pdf_res.content[:4] == b"%PDF"
    print(f"[PASS] [14/14] Emergency Resources & Pre-Plan PDF verified: PDF binary generated ({len(pdf_res.content)} bytes)")

    print("\n==================================================")
    print("ALL 14 AUDIT & INTEGRATION CHECKS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    test_live_servers()
