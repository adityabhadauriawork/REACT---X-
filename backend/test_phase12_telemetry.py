import time
import math
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, SourceProtocol,
    SensorType, TelemetryQuality, GatewayStatus, DataQualityFlag, FreshnessStatus,
    TelemetryHistoryQuery
)
from app.services.industrial.opcua_adapter import opcua_adapter
from app.services.industrial.mqtt_adapter import mqtt_adapter
from app.services.industrial.telemetry_simulator import telemetry_simulator, SimulationScenario
from app.services.industrial.telemetry_service import telemetry_service
from app.services.ingestion.telemetry_freshness_engine import telemetry_freshness_engine
from app.services.ingestion.telemetry_buffer_queue import EdgeLocalBuffer, BackpressureQueue
from app.services.ingestion.telemetry_quality_validator import telemetry_quality_validator
from app.services.ingestion.telemetry_state_store import telemetry_state_store
from app.services.storage.telemetry_repository import telemetry_repository

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        telemetry_service.seed_initial_metadata(db)
        yield db
    finally:
        db.close()

# =========================================================================
# 1. PROTOCOL ADAPTERS & READ-ONLY SAFETY BOUNDARY TESTS
# =========================================================================

def test_opcua_adapter_read_only_and_normalization():
    """Verify OPC UA adapter connects, normalizes values, and strictly possesses zero write methods."""
    # Ensure zero write capability exists on adapter interface
    assert not hasattr(opcua_adapter, "write_node"), "OPC UA adapter must not have write_node"
    assert not hasattr(opcua_adapter, "write_value"), "OPC UA adapter must not have write_value"
    assert not hasattr(opcua_adapter, "set_point"), "OPC UA adapter must not have set_point"
    assert not hasattr(opcua_adapter, "send_command"), "OPC UA adapter must not have send_command"

    # Connect & health check
    connected = opcua_adapter.connect()
    assert connected is True
    health = opcua_adapter.health()
    assert health["read_only"] is True
    assert health["connected"] is True
    assert health["protocol"] == "OPC_UA"

    # Test normalization of mock OPC UA DataValue
    meta = next(iter(opcua_adapter.registered_sensors.values()))
    raw_payload = {
        "NodeId": meta.tag_name,
        "Value": 4.5,
        "StatusCode": "Good",
        "SourceTimestamp": "2026-09-01T05:00:00Z",
        "Sequence": 1001
    }
    obs = opcua_adapter.normalize(raw_payload, meta)
    assert obs is not None
    assert obs.value == 4.5
    assert obs.quality == TelemetryQuality.GOOD
    assert obs.source_protocol == SourceProtocol.OPC_UA
    assert obs.is_live_data is False
    assert obs.sequence_number == 1001

def test_mqtt_adapter_read_only_and_normalization():
    """Verify MQTT adapter consumes messages, parses Sparkplug B / JSON, and has zero publish/write methods."""
    # Ensure zero publish/write capability exists
    assert not hasattr(mqtt_adapter, "publish_command"), "MQTT adapter must not have publish_command"
    assert not hasattr(mqtt_adapter, "write_tag"), "MQTT adapter must not have write_tag"
    assert not hasattr(mqtt_adapter, "send_control"), "MQTT adapter must not have send_control"

    connected = mqtt_adapter.connect()
    assert connected is True
    health = mqtt_adapter.health()
    assert health["read_only"] is True
    assert health["protocol"] == "MQTT_SPARKPLUG"

    # Test normalization of Sparkplug B payload
    meta = next(iter(mqtt_adapter.registered_sensors.values()))
    raw_payload = {
        "value": 12.4,
        "quality": "GOOD",
        "timestamp": 1725184800000,
        "seq": 450
    }
    obs = mqtt_adapter.normalize(raw_payload, meta)
    assert obs is not None
    assert obs.value == 12.4
    assert obs.quality == TelemetryQuality.GOOD
    assert obs.source_protocol == SourceProtocol.MQTT_SPARKPLUG
    assert obs.sequence_number == 450

# =========================================================================
# 2. SCENARIO TESTS A THROUGH J
# =========================================================================

def test_scenario_a_normal_telemetry():
    """Scenario A: Normal baseline telemetry generation."""
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    assert len(batch) >= 10
    for obs in batch:
        assert obs.quality == TelemetryQuality.GOOD
        assert obs.is_live_data is False
        assert obs.data_quality_status == "VALID"

def test_scenario_b_temperature_drift():
    """Scenario B: Gradual thermal drift scenario."""
    telemetry_simulator.set_scenario(SimulationScenario.DRIFT)
    # Fast forward scenario clock
    telemetry_simulator.scenario_start_time = time.time() - 45.0
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    t04_temps = [obs for obs in batch if obs.asset_id == "T-04" and obs.sensor_type == SensorType.TEMPERATURE]
    assert len(t04_temps) > 0
    # Value drifted upwards relative to -32 baseline
    assert t04_temps[0].value > -30.0

def test_scenario_c_gas_concentration_increase():
    """Scenario C: Toxic gas sniffer increase."""
    telemetry_simulator.set_scenario(SimulationScenario.GAS_LEAK_PATTERN)
    telemetry_simulator.scenario_start_time = time.time() - 20.0
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    gas_sensors = [obs for obs in batch if obs.asset_id == "T-04" and obs.sensor_type == SensorType.GAS_CONCENTRATION]
    assert len(gas_sensors) > 0
    assert gas_sensors[0].value > 50.0 # High concentration detected

def test_scenario_d_pressure_deviation():
    """Scenario D: Internal vessel boil-off overpressure rise."""
    telemetry_simulator.set_scenario(SimulationScenario.PRESSURE_RISE)
    telemetry_simulator.scenario_start_time = time.time() - 30.0
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    press_sensors = [obs for obs in batch if obs.asset_id == "T-04" and obs.sensor_type == SensorType.PRESSURE]
    assert len(press_sensors) > 0
    assert press_sensors[0].value >= 5.5 # Exceeds warning threshold

def test_scenario_e_multiple_sensors_deviate():
    """Scenario E: Correlated multi-sensor deviation (temperature, pressure, gas, thermal score)."""
    telemetry_simulator.set_scenario(SimulationScenario.MULTI_SENSOR_DEVIATION)
    telemetry_simulator.scenario_start_time = time.time() - 35.0
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    t04_obs = {obs.sensor_type: obs for obs in batch if obs.asset_id == "T-04"}
    
    assert SensorType.TEMPERATURE in t04_obs
    assert SensorType.PRESSURE in t04_obs
    assert SensorType.GAS_CONCENTRATION in t04_obs
    assert t04_obs[SensorType.TEMPERATURE].value > -25.0
    assert t04_obs[SensorType.PRESSURE].value > 5.0
    assert t04_obs[SensorType.GAS_CONCENTRATION].value > 100.0

def test_scenario_f_sensor_offline_vs_zero():
    """Scenario F: Telemetry engine distinguishes reporting 0.0 from sensor stopped reporting."""
    telemetry_simulator.set_scenario(SimulationScenario.SENSOR_FAILURE)
    batch = telemetry_simulator.generate_tick_batch(force_all=True)
    failed_sensor = next((obs for obs in batch if "PRESS_01" in obs.sensor_id and obs.asset_id == "T-04"), None)
    assert failed_sensor is not None
    assert failed_sensor.quality == TelemetryQuality.BAD
    assert DataQualityFlag.SENSOR_FAULT in failed_sensor.data_quality_flags
    # Distinguish from valid zero:
    valid_zero_obs = FacilityTelemetryObservation(
        telemetry_id="TEL-TEST-001", facility_id="FAC-IN-DAHEJ-001", asset_id="T-04",
        gateway_id="GW-01", sensor_id="SENS-FLOW-01", sensor_type=SensorType.FLOW,
        tag_name="T04.Flow", timestamp_utc=datetime.now(timezone.utc), value=0.0,
        unit="m³/h", quality=TelemetryQuality.GOOD, source_protocol=SourceProtocol.SIMULATED_GATEWAY,
        source_timestamp=datetime.now(timezone.utc)
    )
    validated = telemetry_quality_validator.normalize_and_validate(valid_zero_obs)
    assert validated.value == 0.0
    assert validated.quality == TelemetryQuality.GOOD

def test_scenario_g_communication_loss():
    """Scenario G: Network/gateway goes offline."""
    telemetry_simulator.set_scenario(SimulationScenario.COMMUNICATION_LOSS)
    batch = telemetry_simulator.generate_tick_batch(force_all=False)
    # No data generated during communication loss
    assert len(batch) == 0

def test_scenario_h_late_replayed_out_of_order_telemetry():
    """Scenario H: Edge buffering, offline replay, and out-of-order timestamp preservation."""
    buffer = EdgeLocalBuffer(max_capacity=100)
    now = datetime.now(timezone.utc)

    obs1 = FacilityTelemetryObservation(
        telemetry_id="TEL-01", facility_id="FAC-01", asset_id="T-04", gateway_id="GW-01",
        sensor_id="SENS-T04-TEMP-01", sensor_type=SensorType.TEMPERATURE, tag_name="T04.Temp",
        timestamp_utc=now - timedelta(seconds=10), value=-32.0, unit="°C",
        quality=TelemetryQuality.GOOD, source_protocol=SourceProtocol.SIMULATED_GATEWAY,
        source_timestamp=now - timedelta(seconds=10), sequence_number=1
    )
    obs2 = FacilityTelemetryObservation(
        telemetry_id="TEL-02", facility_id="FAC-01", asset_id="T-04", gateway_id="GW-01",
        sensor_id="SENS-T04-TEMP-01", sensor_type=SensorType.TEMPERATURE, tag_name="T04.Temp",
        timestamp_utc=now - timedelta(seconds=5), value=-31.5, unit="°C",
        quality=TelemetryQuality.GOOD, source_protocol=SourceProtocol.SIMULATED_GATEWAY,
        source_timestamp=now - timedelta(seconds=5), sequence_number=2
    )

    buffer.push(obs2) # Push out-of-order
    buffer.push(obs1)

    replayed = buffer.replay_all(sort_by_timestamp=True)
    assert len(replayed) == 2
    assert replayed[0].telemetry_id == "TEL-01" # Properly ordered by source timestamp
    assert replayed[1].telemetry_id == "TEL-02"
    assert DataQualityFlag.REPLAYED in replayed[0].data_quality_flags

def test_scenario_i_unit_normalization():
    """Scenario I: Unit conversion from psi, kPa, Kelvin, and L/min."""
    # psi -> bar
    val, unit = telemetry_quality_validator.convert_units_if_needed(100.0, "psi", "bar", SensorType.PRESSURE)
    assert round(val, 2) == 6.89
    assert unit == "bar"

    # kPa -> bar
    val, unit = telemetry_quality_validator.convert_units_if_needed(450.0, "kPa", "bar", SensorType.PRESSURE)
    assert val == 4.5
    assert unit == "bar"

    # K -> °C
    val, unit = telemetry_quality_validator.convert_units_if_needed(300.0, "K", "°C", SensorType.TEMPERATURE)
    assert round(val, 2) == 26.85
    assert unit == "°C"

    # L/min -> m3/h
    val, unit = telemetry_quality_validator.convert_units_if_needed(500.0, "L/min", "m³/h", SensorType.FLOW)
    assert val == 30.0
    assert unit == "m³/h"

def test_scenario_j_invalid_value_and_bounds_rejection():
    """Scenario J: Invalid value (NaN, Inf, hardware limits) is properly flagged and rejected."""
    nan_obs = FacilityTelemetryObservation(
        telemetry_id="TEL-NAN", facility_id="FAC-01", asset_id="T-04", gateway_id="GW-01",
        sensor_id="SENS-T04-TEMP-01", sensor_type=SensorType.TEMPERATURE, tag_name="T04.Temp",
        timestamp_utc=datetime.now(timezone.utc), value=float("nan"), unit="°C",
        quality=TelemetryQuality.GOOD, source_protocol=SourceProtocol.SIMULATED_GATEWAY,
        source_timestamp=datetime.now(timezone.utc)
    )
    validated = telemetry_quality_validator.normalize_and_validate(nan_obs)
    assert validated.quality == TelemetryQuality.BAD
    assert validated.data_quality_status == "REJECTED"

# =========================================================================
# 3. DYNAMIC FRESHNESS & BACKPRESSURE TESTS
# =========================================================================

def test_dynamic_freshness_scaling():
    """Verify that freshness is calculated relative to individual sensor expected intervals."""
    now = datetime.now(timezone.utc)
    
    # 1-second sensor: 2 seconds old -> FRESH (ratio 2.0 < 3.0), 15 seconds old -> UNAVAILABLE (ratio 15.0 >= 12.0)
    res_1s_live = telemetry_freshness_engine.compute_freshness(now - timedelta(seconds=0.8), expected_sampling_interval_sec=1.0, current_time_utc=now)
    assert res_1s_live["freshness_status"] == FreshnessStatus.LIVE

    res_1s_fresh = telemetry_freshness_engine.compute_freshness(now - timedelta(seconds=2.0), expected_sampling_interval_sec=1.0, current_time_utc=now)
    assert res_1s_fresh["freshness_status"] == FreshnessStatus.FRESH

    res_1s_unavail = telemetry_freshness_engine.compute_freshness(now - timedelta(seconds=15.0), expected_sampling_interval_sec=1.0, current_time_utc=now)
    assert res_1s_unavail["freshness_status"] == FreshnessStatus.UNAVAILABLE

    # 60-second sensor: 15 seconds old is still LIVE (ratio 15/60 = 0.25 < 1.5)
    res_60s = telemetry_freshness_engine.compute_freshness(now - timedelta(seconds=15.0), expected_sampling_interval_sec=60.0, current_time_utc=now)
    assert res_60s["freshness_status"] == FreshnessStatus.LIVE

def test_backpressure_queue_priority_shed():
    """Verify backpressure queue sheds routine GOOD data while retaining warning/critical data."""
    queue = BackpressureQueue(max_queue_size=5)
    now = datetime.now(timezone.utc)

    # Enqueue 5 normal observations
    for i in range(5):
        obs = FacilityTelemetryObservation(
            telemetry_id=f"TEL-NORM-{i}", facility_id="FAC-01", asset_id="T-04", gateway_id="GW-01",
            sensor_id=f"SENS-{i}", sensor_type=SensorType.TEMPERATURE, tag_name="T.Tag",
            timestamp_utc=now, value=25.0, unit="°C", quality=TelemetryQuality.GOOD,
            source_protocol=SourceProtocol.SIMULATED_GATEWAY, source_timestamp=now, trend="STABLE"
        )
        queue.enqueue(obs)

    # Enqueue 1 critical observation
    crit_obs = FacilityTelemetryObservation(
        telemetry_id="TEL-CRIT-01", facility_id="FAC-01", asset_id="T-04", gateway_id="GW-01",
        sensor_id="SENS-CRIT", sensor_type=SensorType.PRESSURE, tag_name="T.Press",
        timestamp_utc=now, value=8.5, unit="bar", quality=TelemetryQuality.WARNING,
        source_protocol=SourceProtocol.SIMULATED_GATEWAY, source_timestamp=now, trend="RAPID_RISE"
    )
    queue.enqueue(crit_obs)

    drained = queue.drain_batch(10)
    assert len(drained) == 5
    assert any(o.telemetry_id == "TEL-CRIT-01" for o in drained)

# =========================================================================
# 4. REST API ENDPOINT TESTS
# =========================================================================

def test_api_telemetry_health():
    """Verify GET /api/telemetry/health response structure."""
    res = client.get("/api/telemetry/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "OPERATIONAL"
    assert data["read_only_mode_verified"] is True
    assert data["active_gateways_count"] >= 3
    assert len(data["gateways"]) >= 3

def test_api_facility_latest_and_history(db_session: Session):
    """Verify GET /api/telemetry/facilities/{facility_id}/latest and history."""
    # Reset to normal
    telemetry_simulator.set_scenario(SimulationScenario.NORMAL)
    telemetry_service.generate_simulator_tick(db_session)

    # Latest
    res = client.get("/api/telemetry/facilities/FAC-IN-DAHEJ-001/latest")
    assert res.status_code == 200
    latest_data = res.json()
    assert len(latest_data) > 0
    assert all(o["facility_id"] == "FAC-IN-DAHEJ-001" for o in latest_data)

    # History
    res_hist = client.get("/api/telemetry/facilities/FAC-IN-DAHEJ-001/history?limit=10")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert isinstance(hist_data, list)

def test_api_sensor_latest_and_history(db_session: Session):
    """Verify GET /api/telemetry/sensors/{sensor_id}/latest and history."""
    res = client.get("/api/telemetry/sensors/SENS-T-04-PRESS_01/latest")
    assert res.status_code == 200
    sensor_data = res.json()
    assert sensor_data["sensor_id"] == "SENS-T-04-PRESS_01"

def test_api_scenario_switch_and_tick():
    """Verify POST /api/telemetry/simulator/scenario and tick generation."""
    res_scn = client.post("/api/telemetry/simulator/scenario", json={"scenario_name": "THERMAL_RISE"})
    assert res_scn.status_code == 200
    assert res_scn.json()["active_scenario"] == "THERMAL_RISE"

    res_tick = client.post("/api/telemetry/simulator/tick")
    assert res_tick.status_code == 200
    assert len(res_tick.json()) > 0

# =========================================================================
# 5. DATA RATE & LOAD PERFORMANCE BENCHMARKS (10, 100, 1000 SENSORS)
# =========================================================================

def test_performance_benchmarks_scale(db_session: Session):
    """Benchmark ingestion and lookup performance at 10, 100, and 1,000 sensors."""
    for count in [10, 100, 1000]:
        telemetry_simulator.set_sensor_count(count)
        telemetry_service._sync_sensors_to_state_store()

        # Ingestion Latency Measurement
        t0 = time.perf_counter()
        raw_batch = telemetry_simulator.generate_tick_batch(force_all=True)
        t_gen = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        processed = telemetry_service.ingest_observations(raw_batch, db_session)
        t_ingest_db = (time.perf_counter() - t1) * 1000.0

        # Latest State Store Lookup Latency
        t2 = time.perf_counter()
        latest_results = telemetry_service.get_latest_facility_telemetry("FAC-IN-DAHEJ-001")
        t_lookup = (time.perf_counter() - t2) * 1000.0

        assert len(processed) == count
        assert len(latest_results) == count
        print(f"\n[BENCHMARK] {count} Sensors | Generation: {t_gen:.2f}ms | Ingest+DB: {t_ingest_db:.2f}ms | Latest Lookup: {t_lookup:.2f}ms")
        
        # Verify sub-second processing for up to 1,000 sensors
        assert t_lookup < 20.0, f"Latest-value lookup took {t_lookup}ms, expected <20ms"
