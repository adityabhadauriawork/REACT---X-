import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_national_facilities_registry():
    """Verify all national industrial facilities are registered across Indian states."""
    res = client.get("/api/thermal/facilities")
    assert res.status_code == 200
    facs = res.json()
    assert len(facs) >= 18, f"Expected at least 18 registered facilities, got {len(facs)}"
    
    # Verify key national complexes across states
    facility_ids = {f["id"] for f in facs}
    assert "FAC-DAHEJ-PCH01" in facility_ids # Gujarat
    assert "FAC-JAMNAGAR-REF01" in facility_ids # Gujarat
    assert "FAC-HAZIRA-GAS01" in facility_ids # Gujarat
    assert "FAC-VADODARA-REF01" in facility_ids # Gujarat
    assert "FAC-MUMBAI-REF01" in facility_ids # Maharashtra
    assert "FAC-ROURKELA-STEEL01" in facility_ids # Odisha
    assert "FAC-PARADIP-PETRO01" in facility_ids # Odisha
    assert "FAC-KORBA-PWR01" in facility_ids # Chhattisgarh
    assert "FAC-JSR-STEEL01" in facility_ids # Jharkhand
    assert "FAC-MANALI-CHEM01" in facility_ids # Tamil Nadu
    assert "FAC-VIZAG-STEEL01" in facility_ids # Andhra Pradesh
    assert "FAC-NUMALIGARH-REF01" in facility_ids # Assam
    assert "FAC-UDAIPUR-MINE01" in facility_ids # Rajasthan
    assert "FAC-MANGALORE-CHEM01" in facility_ids # Karnataka
    assert "FAC-PATA-PETRO01" in facility_ids # Uttar Pradesh
    assert "FAC-HALDIA-PETRO01" in facility_ids # West Bengal

def test_thermal_events_and_geojson():
    """Verify thermal events query and GeoJSON endpoints."""
    res = client.get("/api/thermal/events")
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)

    res_geo = client.get("/api/thermal/events/geojson")
    assert res_geo.status_code == 200
    geo = res_geo.json()
    assert geo.get("type") == "FeatureCollection"

def test_explainable_7class_classification():
    """Verify 7-class AI classification on a thermal anomaly with 23-feature model."""
    res_events = client.get("/api/thermal/events")
    events = res_events.json()
    if events:
        event_id = events[0]["event_id"]
        res_clf = client.post(f"/api/thermal/classify/{event_id}")
        assert res_clf.status_code == 200
        clf = res_clf.json()
        assert "predicted_class" in clf
        assert "confidence_score" in clf
        assert "class_probabilities" in clf
        assert len(clf["class_probabilities"]) == 7
        assert clf["ml_model_version"] is not None

def test_multi_satellite_corroboration():
    """Verify multi-satellite corroboration endpoint."""
    res_events = client.get("/api/thermal/events")
    events = res_events.json()
    if events:
        event_id = events[0]["event_id"]
        res_sat = client.get(f"/api/thermal/multi-satellite/{event_id}")
        assert res_sat.status_code == 200
        sat = res_sat.json()
        assert "overall_corroboration_score" in sat
        assert "firms_viirs_detected" in sat

def test_national_facility_configuration_endpoint():
    """Verify GET /api/national/facilities returns configuration models."""
    res = client.get("/api/national/facilities")
    assert res.status_code == 200
    facs = res.json()
    assert len(facs) >= 18

def test_data_gateway_demo_scenarios():
    """Verify Data Gateway scenarios and state."""
    res_scenarios = client.get("/api/data-gateway/demo/scenarios")
    assert res_scenarios.status_code == 200
    scenarios = res_scenarios.json()
    assert len(scenarios) >= 3 # Dahej, Hazira, Vadodara

    res_state = client.get("/api/data-gateway/demo/state")
    assert res_state.status_code == 200

def test_hazard_simulation_and_evacuation():
    """Verify physical dispersion model and Dijkstra evacuation engine."""
    payload = {
        "facility_id": "FAC-DAHEJ-PCH01",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "release_type": "CONTINUOUS_TOXIC_PLUME",
        "release_rate_kg_s": 15.0,
        "release_duration_sec": 1800,
        "ambient_temperature_c": 32.0,
        "wind_speed_m_s": 2.2,
        "wind_direction_deg": 45.0,
        "atmospheric_stability": "D"
    }
    res_sim = client.post("/api/hazard/simulate", json=payload)
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert "time_steps" in sim_data
    assert "current_geojson" in sim_data

    # Evacuation
    res_impact = client.post("/api/impact/analyze?time_step_sec=120", json=sim_data)
    assert res_impact.status_code == 200
    impact_data = res_impact.json()

    res_evac = client.post("/api/evacuation/route", json={
        "simulation_result": sim_data,
        "impact_result": impact_data,
        "origin_coords": [21.6850, 72.5750]
    })
    assert res_evac.status_code == 200
    evac_data = res_evac.json()
    assert "primary_evacuation_route" in evac_data

def test_preplan_pdf_generation():
    """Verify ERDMP Pre-Plan PDF export generates valid PDF bytes."""
    sim_payload = {
        "facility_id": "FAC-DAHEJ-PCH01",
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "release_type": "CONTINUOUS_TOXIC_PLUME",
        "release_rate_kg_s": 15.0,
        "release_duration_sec": 1800,
        "ambient_temperature_c": 32.0,
        "wind_speed_m_s": 2.2,
        "wind_direction_deg": 45.0,
        "atmospheric_stability": "D"
    }
    res_sim = client.post("/api/hazard/simulate", json=sim_payload)
    sim_data = res_sim.json()
    res_impact = client.post("/api/impact/analyze?time_step_sec=120", json=sim_data)
    impact_data = res_impact.json()
    res_evac = client.post("/api/evacuation/route", json={
        "simulation_result": sim_data,
        "impact_result": impact_data
    })
    evac_data = res_evac.json()

    res_res = client.post("/api/resources/optimize", json={
        "simulation_result": sim_data,
        "impact_result": impact_data,
        "evacuation_plan": evac_data
    })
    assert res_res.status_code == 200
    resource_data = res_res.json()

    pdf_req = {
        "simulation_result": sim_data,
        "impact_result": impact_data,
        "evacuation_plan": evac_data,
        "resource_plan": resource_data,
        "author_name": "Command HSE Incident Officer",
        "facility_ref": "Dahej Petrochemical Complex Alpha"
    }
    res_pdf = client.post("/api/preplan/generate-pdf", json=pdf_req)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000 # Valid non-empty PDF file
