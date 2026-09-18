import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.services.site.site_service import site_service
from app.services.satellite.industrial_context_service import industrial_context_service
from app.services.satellite.fingerprint_engine import fingerprint_engine

from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_handoff_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    site_service.load_seed_data_if_empty(db)
    industrial_context_service.seed_facilities_if_empty(db)
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)

def test_api_thermal_endpoints():
    # 1. Fetch thermal events
    r = client.get("/api/thermal/events")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 8
    
    # Verify canonical structure
    sample = events[0]
    assert "event_id" in sample
    assert "source_satellite" in sample
    assert "frp_mw" in sample
    assert "classification" in sample
    assert "abnormality_score" in sample

    # 2. Fetch industrial facilities
    r_fac = client.get("/api/thermal/facilities")
    assert r_fac.status_code == 200
    facs = r_fac.json()
    assert len(facs) >= 7

    # 3. Fetch persistent thermal clusters
    r_clus = client.get("/api/thermal/persistent-sources")
    assert r_clus.status_code == 200
    clusters = r_clus.json()
    assert len(clusters) >= 6

    # 4. Classify an event with explainable AI
    target_event_id = "FIRMS-VIIRS-20260830-DHJ-01"
    r_class = client.post(f"/api/thermal/classify/{target_event_id}")
    assert r_class.status_code == 200
    class_res = r_class.json()
    assert class_res["predicted_class"] in ["INDUSTRIAL_FIRE", "GAS_FLARE", "ROUTINE_PROCESS_HEAT"]
    assert "top_feature_attributions" in class_res
    assert len(class_res["top_feature_attributions"]) >= 2

    # 5. Nightfire Characterization
    r_vnf = client.get(f"/api/thermal/nightfire/{target_event_id}")
    assert r_vnf.status_code == 200
    vnf_res = r_vnf.json()
    assert vnf_res["source_temperature_k"] > 1000.0
    assert vnf_res["radiant_heat_flux_w_m2"] > 0

    # 6. Multi-Satellite Confirmation
    r_corrob = client.get(f"/api/thermal/multi-satellite/{target_event_id}")
    assert r_corrob.status_code == 200
    corrob_res = r_corrob.json()
    assert corrob_res["overall_corroboration_score"] >= 0.8

    # 7. Execute Emergency Handoff
    r_handoff = client.post("/api/thermal/handoff", json={
        "event_id": target_event_id,
        "facility_id": "FAC-DAHEJ-PCH01",
        "initiator_role": "HSE_COMMANDER",
        "initiator_name": "NTRO Watch Officer"
    })
    assert r_handoff.status_code == 200
    handoff_res = r_handoff.json()
    assert handoff_res["handoff_status"] == "EMERGENCY_INCIDENT_ACTIVE"
    assert "incident_id" in handoff_res
    assert handoff_res["target_asset_id"] == "T-04"

def test_emergency_simulation_after_handoff():
    # Verify that the standard hazard simulation works seamlessly
    sim_payload = {
        "asset_id": "T-04",
        "chemical_id": "CHEM-NH3",
        "incident_type": "TOXIC_GAS_RELEASE",
        "release_rate_kg_s": 18.5,
        "release_duration_min": 30,
        "wind_speed_m_s": 2.2,
        "wind_direction_deg": 45.0,
        "ambient_temp_c": 32.0,
        "atmospheric_stability": "D"
    }
    r = client.post("/api/hazard/simulate", json=sim_payload)
    assert r.status_code == 200
    sim_res = r.json()
    assert sim_res["source_asset_id"] == "T-04"
    assert len(sim_res["time_steps"]) >= 4

    # Run Impact Analysis (body is sim_res directly)
    r_impact = client.post("/api/impact/analyze?time_step_sec=120", json=sim_res)
    assert r_impact.status_code == 200
    impact_res = r_impact.json()
    assert impact_res["risk_assessment"]["risk_category"] in ["CRITICAL", "HIGH", "MODERATE"]

    # Run Dijkstra Evacuation Route
    r_evac = client.post("/api/evacuation/route", json={"simulation_result": sim_res, "impact_result": impact_res})
    assert r_evac.status_code == 200
    evac_res = r_evac.json()
    assert "primary_evacuation_route" in evac_res
    assert len(evac_res["primary_evacuation_route"]["route_coordinates"]) > 0
