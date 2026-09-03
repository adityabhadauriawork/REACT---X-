import pytest
from app.services.satellite.firms_service import firms_service
from app.services.satellite.attribution_service import attribution_service
from app.services.satellite.persistence_service import persistence_service
from app.services.satellite.classification_service import classification_service
from app.services.satellite.nightfire_service import nightfire_service
from app.services.satellite.confirmation_service import confirmation_service

def test_firms_and_attribution():
    events = firms_service.get_thermal_events()
    assert len(events) >= 8
    
    # Check Dahej anomaly
    dhj = [e for e in events if "DHJ-01" in e.event_id][0]
    assert dhj.attributed_facility_id == "FAC-DAHEJ-PCH01"
    assert dhj.is_inside_facility_boundary is True
    assert dhj.frp_mw > 80.0
    assert dhj.abnormality_score > 80.0
    assert dhj.risk_level == "CRITICAL"

def test_persistence_clustering_and_abnormality():
    clusters = persistence_service.get_all_clusters()
    assert len(clusters) >= 7
    
    abnormal = persistence_service.get_abnormal_clusters()
    assert len(abnormal) >= 1
    assert abnormal[0].facility_id == "FAC-DAHEJ-PCH01"
    assert abnormal[0].is_abnormal is True
    assert abnormal[0].frp_deviation_zscore > 3.0

def test_explainable_classification():
    events = firms_service.get_thermal_events()
    dhj_fire = [e for e in events if "DHJ-01" in e.event_id][0]
    res_fire = classification_service.classify_thermal_event(dhj_fire)
    
    assert res_fire.predicted_class == "INDUSTRIAL_FIRE"
    assert len(res_fire.top_feature_attributions) >= 2
    assert "surveillance" not in res_fire.explanation_summary.lower()

    # Test agricultural stubble fire
    pb_agri = [e for e in events if "PB-01" in e.event_id][0]
    res_agri = classification_service.classify_thermal_event(pb_agri)
    assert res_agri.predicted_class == "AGRICULTURAL_BURNING"

def test_nightfire_physical_characterization():
    events = firms_service.get_thermal_events()
    jam_flare = [e for e in events if "JMN-01" in e.event_id][0]
    vnf = nightfire_service.characterize_thermal_source(jam_flare)
    
    assert vnf.source_temperature_k >= 1400.0
    assert vnf.radiant_heat_flux_w_m2 > 10000.0
    assert vnf.source_footprint_area_m2 > 10.0
    assert vnf.planck_curve_fit_quality > 0.9

def test_multi_satellite_corroboration():
    events = firms_service.get_thermal_events()
    dhj = [e for e in events if "DHJ-01" in e.event_id][0]
    corrob = confirmation_service.corroborate_event(dhj)
    
    assert corrob.overall_corroboration_score >= 0.85
    assert corrob.sentinel2_swir_confirmation is not None
    assert corrob.insat_geostationary_corroboration is not None
    assert corrob.corroborating_sensors_count >= 3

if __name__ == "__main__":
    test_firms_and_attribution()
    test_persistence_clustering_and_abnormality()
    test_explainable_classification()
    test_nightfire_physical_characterization()
    test_multi_satellite_corroboration()
    print("SUCCESS: All SIH26162 Satellite Thermal Intelligence unit tests passed!")
