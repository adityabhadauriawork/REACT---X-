import io
import csv
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.satellite.vnf_service import EOGNightfireVNFService, vnf_service
from app.services.satellite.nightfire_service import nightfire_service
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine, SATELLITE_REGISTRY
from app.schemas.thermal import CanonicalThermalEvent, VIIRSNightfireCharacterization

client = TestClient(app)

# 1. TEST VNF ACADEMIC LICENSE COMPLIANCE & PROVENANCE
def test_vnf_academic_license_compliance():
    """
    Verify that VNF service strictly adheres to the Academic License:
    - Reports data mode as 'ACADEMIC DATA / OFFLINE VALIDATION' (not LIVE).
    - Preserves authoritative EOG Payne Institute provenance credits.
    - Does not implement fake OAuth or unauthorized live streaming pathways.
    """
    svc = EOGNightfireVNFService()
    assert svc.data_mode == "ACADEMIC DATA / OFFLINE VALIDATION"
    assert "Payne Institute" in svc.PROVENANCE_CREDIT
    assert "Colorado School of Mines" in svc.PROVENANCE_CREDIT
    assert svc.is_configured is True


# 2. TEST ACADEMIC BASELINE BENCHMARK MATCHING & PLANCK COMBUSTION PHYSICS
def test_vnf_academic_reference_characterization():
    """
    Verify that academic benchmark catalog returns Planck blackbody combustion parameters
    (temperature in K, footprint area in m², radiant heat flux in W/m²) for known industrial clusters.
    """
    # Dahej PCPIR coordinates
    dahej_lat, dahej_lon = 21.6850, 72.5620
    matched = vnf_service.characterize_target_coordinates(latitude=dahej_lat, longitude=dahej_lon, buffer_deg=0.03)
    assert matched is not None
    assert matched["source"] == "EOG_VIIRS_NIGHTFIRE_ACADEMIC_DATASET"
    assert matched["data_mode"] == "ACADEMIC DATA / OFFLINE VALIDATION"
    assert matched["source_temperature_k"] >= 1400.0
    assert matched["source_footprint_area_m2"] > 0.0
    assert matched["radiant_heat_flux_w_m2"] > 0.0
    assert "Payne Institute" in matched["provenance_credit"]


# 3. TEST OFFLINE PLANCK PHYSICS COMPUTATION FOR ARBITRARY COORDINATES
def test_vnf_offline_planck_physics_calculation():
    """
    Verify physics-based Planck curve fitting for coordinates outside pre-seeded benchmarks.
    """
    res = vnf_service.get_offline_planck_physics(
        event_lat=20.5000,
        event_lon=73.0000,
        frp_mw=35.0,
        brightness_temp_k=350.0
    )
    assert res["data_mode"] == "ACADEMIC DATA / OFFLINE VALIDATION"
    assert res["is_live_data"] is False
    assert 1200.0 <= res["source_temperature_k"] <= 2000.0
    assert res["source_footprint_area_m2"] >= 5.0
    assert res["radiant_heat_flux_w_m2"] > 0.0
    assert res["planck_fit_quality"] >= 0.95


# 4. TEST OFFLINE ACADEMIC RESEARCH CSV PARSER
def test_vnf_parse_academic_research_csv():
    """
    Verify in-memory parsing of offline academic research VNF CSV datasets.
    """
    csv_data = (
        "Lat_BS,Lon_BS,Date_Mscan,Time_Mscan,Temp_BB,Area_BB,Rad_Heat_W_m2,QF\n"
        "21.6850,72.5620,20260904,213015,1620.5,42.0,325000.0,0\n" # Inside Dahej AOI
        "45.5000,-73.5673,20260904,213015,1350.0,18.0,120000.0,0\n" # Outside AOI (Montreal)
        "21.7100,72.6000,20260904,213015,1480.0,30.0,210000.0,0\n" # Inside Dahej AOI
    )

    svc = EOGNightfireVNFService()
    records = svc.parse_academic_vnf_csv(csv_data, aoi_bbox=[72.0, 21.0, 73.0, 22.0])
    assert len(records) == 2
    for rec in records:
        assert rec["source"] == "EOG_VIIRS_NIGHTFIRE_ACADEMIC_DATASET"
        assert rec["data_mode"] == "ACADEMIC DATA / OFFLINE VALIDATION"
        assert rec["source_temperature_k"] > 1000.0
        assert "Payne Institute" in rec["provenance_credit"]


# 5. TEST NIGHTFIRE SERVICE INTEGRATION & ACADEMIC DATA MODE
def test_nightfire_service_academic_validation():
    """
    Verify NightfireService produces VIIRSNightfireCharacterization with academic data mode.
    """
    event = CanonicalThermalEvent(
        event_id="EVT-TEST-ACADEMIC-01",
        dedup_key="DEDUP-KEY-ACADEMIC-01",
        latitude=21.6850,
        longitude=72.5620,
        brightness_temp_k=355.0,
        frp_mw=45.0,
        confidence="HIGH",
        confidence_pct=95.0,
        source_satellite="NOAA-20",
        sensor_name="VIIRS_375M",
        acquisition_timestamp=datetime.now(timezone.utc),
        classification="GAS_FLARE",
        abnormality_score=80.0
    )

    res = nightfire_service.characterize_thermal_source(event)
    assert isinstance(res, VIIRSNightfireCharacterization)
    assert res.data_mode == "ACADEMIC DATA / OFFLINE VALIDATION"
    assert res.source_temperature_k >= 1400.0
    assert res.source_footprint_area_m2 > 0.0
    assert res.planck_curve_fit_quality >= 0.95
    assert "Payne Institute" in res.provenance_credit


# 6. TEST /THERMAL/HEALTH ENDPOINT REPORTS ACADEMIC VNF
def test_thermal_health_reports_academic_vnf():
    """
    Verify /api/thermal/health endpoint clearly labels VNF as ACADEMIC DATA / OFFLINE VALIDATION.
    """
    resp = client.get("/api/thermal/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["viirs_nightfire_eog"] == "ACADEMIC DATA / OFFLINE VALIDATION"
    # Verify other live feeds remain active/operational
    assert "ACTIVE" in data["nasa_firms_viirs_feed"]


# 7. TEST EVIDENCE FUSION ENGINE REGISTRY LABELS VNF AS ACADEMIC VALIDATION
def test_evidence_fusion_engine_academic_vnf_labeling():
    """
    Verify evidence fusion engine satellite registry & health telemetry label VNF as ACADEMIC DATA / OFFLINE VALIDATION.
    """
    vnf_meta = SATELLITE_REGISTRY.get("VIIRS-NIGHTFIRE")
    assert vnf_meta is not None
    assert vnf_meta["tier"] == "TIER_2_ACADEMIC_VALIDATION"
    assert "EOG_VNF_ACADEMIC_VALIDATION" in vnf_meta["product"]

    health_telemetry = evidence_fusion_engine.get_satellite_health_status()
    vnf_health = next((h for h in health_telemetry if h.satellite_id == "VIIRS-NIGHTFIRE"), None)
    assert vnf_health is not None
    assert vnf_health.current_status == "ACADEMIC DATA / OFFLINE VALIDATION"
    assert vnf_health.api_endpoint_status == "ACADEMIC_VALIDATION_CATALOG"
