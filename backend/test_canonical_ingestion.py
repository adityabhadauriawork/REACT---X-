import pytest
import math
from datetime import datetime, timezone, timedelta
from app.schemas.canonical import (
    CanonicalEvent, DataQualityFlag, SourceType, DataClassification, SensorType
)
from app.services.ingestion.quality_engine import data_quality_engine
from app.services.ingestion.stream_classifier import stream_classifier
from app.services.ingestion.rolling_buffer import rolling_buffer
from app.services.ingestion.stream_router import stream_router
from app.services.industrial.opcua_adapter import opcua_adapter
from app.services.industrial.mqtt_adapter import mqtt_adapter
from app.services.industrial.modbus_adapter import modbus_adapter

def test_canonical_event_and_quality_engine():
    print("\n--- 1. Testing Canonical Event Schema & Quality Engine ---")
    now = datetime.now(timezone.utc)
    
    # 1. Normal event validation
    normal_event = CanonicalEvent(
        timestamp=now,
        asset_id="T-04",
        signal_id="T04_PRESS_01",
        value=4.5,
        unit="bar",
        source="TEST_SUITE",
        source_type=SourceType.SIMULATED,
        sequence=1,
        sensor_type=SensorType.PRESSURE
    )
    enriched = data_quality_engine.validate_and_enrich(normal_event)
    assert enriched.quality == DataQualityFlag.GOOD
    assert enriched.severity_hint == "NORMAL"
    assert enriched.classification == DataClassification.WARM

    # 2. Critical range violation
    crit_event = CanonicalEvent(
        timestamp=now,
        asset_id="T-04",
        signal_id="T04_PRESS_01",
        value=8.5, # > critical_high (8.0 bar)
        unit="bar",
        source="TEST_SUITE",
        sequence=2,
        sensor_type=SensorType.PRESSURE
    )
    enriched_crit = data_quality_engine.validate_and_enrich(crit_event)
    enriched_crit.classification = stream_classifier.classify_event(enriched_crit)
    assert enriched_crit.severity_hint == "CRITICAL"
    assert enriched_crit.classification == DataClassification.HOT

    # 3. Stale data detection (>30s old)
    stale_event = CanonicalEvent(
        timestamp=now - timedelta(seconds=45),
        asset_id="T-04",
        signal_id="T04_PRESS_01",
        value=4.5,
        unit="bar",
        source="TEST_SUITE",
        sequence=3,
        sensor_type=SensorType.PRESSURE
    )
    enriched_stale = data_quality_engine.validate_and_enrich(stale_event)
    assert enriched_stale.quality == DataQualityFlag.STALE

    # 4. NaN / Infinite value handling
    bad_event = CanonicalEvent(
        timestamp=now,
        asset_id="T-04",
        signal_id="T04_PRESS_01",
        value=float("nan"),
        unit="bar",
        source="TEST_SUITE",
        sequence=4,
        sensor_type=SensorType.PRESSURE
    )
    enriched_bad = data_quality_engine.validate_and_enrich(bad_event)
    assert enriched_bad.quality == DataQualityFlag.BAD
    assert enriched_bad.severity_hint == "CRITICAL"

    print("[PASS] Canonical event validation, boundary checking, and stale detection verified.")

def test_rolling_buffer_and_router():
    print("\n--- 2. Testing In-Memory Rolling Buffer & Stream Router ---")
    now = datetime.now(timezone.utc)
    
    # Push 10 observations
    for i in range(10):
        ev = CanonicalEvent(
            timestamp=now + timedelta(seconds=i),
            asset_id="T-04",
            signal_id="T04_TEMP_SKIN",
            value=-33.0 + (i * 0.1),
            unit="degC",
            source="TEST_SUITE",
            sequence=100 + i,
            sensor_type=SensorType.TEMPERATURE
        )
        data_quality_engine.validate_and_enrich(ev)
        ev.classification = stream_classifier.classify_event(ev)
        stream_router.route_event(ev)

    pts = rolling_buffer.get_recent_points("T-04", "T04_TEMP_SKIN", count=5)
    assert len(pts) == 5
    assert pts[-1].value == pytest.approx(-32.1, 0.05)

    # Check pre/post event window extraction
    win = rolling_buffer.extract_event_window("T-04", "T04_TEMP_SKIN", now + timedelta(seconds=5), pre_window_sec=5, post_window_sec=5)
    assert len(win["event"]) >= 1
    print("[PASS] Rolling buffer and window slicing operational.")

def test_protocol_adapters():
    print("\n--- 3. Testing Industrial Protocol Adapters (OPC UA, MQTT, Modbus) ---")
    
    # 1. OPC UA Adapter
    opcua_adapter.connect()
    raw_opc = {
        "NodeId": "ns=2;s=Plant.SectorD.T04.PressureTransmitter_01",
        "Value": 4.65,
        "StatusCode": "Good",
        "SequenceNumber": 501
    }
    canon_opc = opcua_adapter.normalize_payload(raw_opc, "ns=2;s=Plant.SectorD.T04.PressureTransmitter_01")
    assert canon_opc is not None
    assert canon_opc.asset_id == "T-04"
    assert canon_opc.value == 4.65
    assert canon_opc.unit == "bar"

    # 2. MQTT Adapter
    mqtt_adapter.connect()
    raw_mqtt = {"val": 5.4, "q": "GOOD", "seq": 102}
    canon_mqtt = mqtt_adapter.normalize_payload(raw_mqtt, "plant/alpha/sector_d/T-04/press")
    assert canon_mqtt is not None
    assert canon_mqtt.signal_id == "T04_PRESS_01"
    assert canon_mqtt.value == 5.4

    # 3. Modbus TCP Adapter
    modbus_adapter.connect()
    raw_modbus = {"raw_val": 485, "status": 0, "seq": 204} # 485 * 0.01 = 4.85 bar
    canon_modbus = modbus_adapter.normalize_payload(raw_modbus, "REG_40001")
    assert canon_modbus is not None
    assert canon_modbus.value == 4.85
    assert canon_modbus.unit == "bar"

    print("[PASS] OPC UA, MQTT, and Modbus TCP adapters successfully normalized to CanonicalEvent.")

if __name__ == "__main__":
    test_canonical_event_and_quality_engine()
    test_rolling_buffer_and_router()
    test_protocol_adapters()
    print("\nALL CANONICAL INGESTION TESTS PASSED (100% SUCCESS)!")
