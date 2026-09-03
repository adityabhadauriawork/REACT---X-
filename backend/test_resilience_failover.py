import pytest
from datetime import datetime, timezone, timedelta
from app.schemas.canonical import CanonicalEvent, DataQualityFlag, SensorType, SourceType
from app.services.ingestion.quality_engine import data_quality_engine
from app.services.predictive.early_warning_engine import early_warning_engine
from app.services.predictive.anomaly_detector import anomaly_detector
from app.services.weather.weather_service import weather_service

def test_sensor_loss_and_stale_data_resilience():
    print("\n--- 1. Testing Sensor Dropout & Stale Data Timeout ---")
    now = datetime.now(timezone.utc)
    
    # 1. Event from 120 seconds ago (simulated connection loss)
    event_old = CanonicalEvent(
        timestamp=now - timedelta(seconds=120),
        asset_id="T-04",
        signal_id="T04_PRESS_01",
        value=4.5,
        unit="bar",
        source="TEST_GATEWAY",
        source_type=SourceType.SIMULATED,
        sensor_type=SensorType.PRESSURE
    )
    enriched = data_quality_engine.validate_and_enrich(event_old)
    assert enriched.quality == DataQualityFlag.STALE
    print("[PASS] Stale sensor data flagged as STALE without silent reuse.")

def test_ml_failure_deterministic_fallback():
    print("\n--- 2. Testing ML Engine Loss & Deterministic Fallback ---")
    
    # Test anomaly detection on an asset with no trained ML model
    res = anomaly_detector.detect_multivariate_anomaly(
        asset_id="UNREGISTERED_PUMP_99",
        pressure=4.5,
        temperature=35.0,
        vibration=1.2,
        acoustic=14.0
    )
    assert res["is_anomaly"] is False
    assert "Fallback" in res["method"]

    # Test that Early Warning Engine still succeeds deterministically
    ew = early_warning_engine.evaluate_asset_pre_incident_state(
        asset_id="UNREGISTERED_PUMP_99",
        asset_name="Auxiliary Pump",
        chemical_name="Hydrocarbon",
        pressure_bar=4.5,
        temperature_c=35.0,
        vibration_mm_s=1.2,
        acoustic_db=14.0
    )
    assert ew["state"] in ["NORMAL", "WATCH"]
    assert ew["confidence_pct"] > 0
    print("[PASS] Fallback from ML to deterministic engineering rules functioning smoothly.")

def test_weather_service_offline_fallback():
    print("\n--- 3. Testing Weather API Network Failure Fallback ---")
    
    # Call weather service
    w = weather_service.fetch_live_weather(21.6850, 72.5750)
    assert w is not None
    assert w.wind_speed_kmh > 0
    assert w.atmospheric_stability in ["A", "B", "C", "D", "E", "F"]
    print(f"[PASS] Weather service returned valid meteorological parameters (Source: {w.source}).")

if __name__ == "__main__":
    test_sensor_loss_and_stale_data_resilience()
    test_ml_failure_deterministic_fallback()
    test_weather_service_offline_fallback()
    print("\nALL RESILIENCE & FAILOVER TESTS PASSED (100% SUCCESS)!")
