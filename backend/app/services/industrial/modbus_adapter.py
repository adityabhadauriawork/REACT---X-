import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.services.industrial.base_adapter import BaseProtocolAdapter
from app.schemas.canonical import CanonicalEvent, SourceType, SensorType, DataQualityFlag
from app.services.ingestion.quality_engine import data_quality_engine
from app.services.ingestion.stream_classifier import stream_classifier

class ModbusTcpAdapter(BaseProtocolAdapter):
    """
    Modbus TCP Protocol Adapter:
    Maps 16-bit / 32-bit Modbus Holding Registers & Input Registers to canonical engineering units.
    """
    def __init__(self):
        super().__init__(name="MODBUS_TCP_GATEWAY", protocol_type="MODBUS_TCP")
        self._seed_register_mappings()

    def _seed_register_mappings(self):
        # Register addresses: 40001+
        regs = [
            ("REG_40001", "T-04", "T04_PRESS_01", "bar", 0.01, SensorType.PRESSURE),      # 450 -> 4.50 bar
            ("REG_40002", "T-04", "T04_TEMP_SKIN", "degC", 0.1, SensorType.TEMPERATURE),   # -330 -> -33.0 degC
            ("REG_40003", "T-04", "T04_VIB_RMS", "mm/s", 0.01, SensorType.VIBRATION),     # 120 -> 1.20 mm/s
            ("REG_40004", "T-03", "T03_PRESS_01", "bar", 0.01, SensorType.PRESSURE),      # 1200 -> 12.00 bar
        ]
        for reg_id, asset_id, signal_id, unit, scale, sensor_type in regs:
            self.tag_mappings[reg_id] = {
                "asset_id": asset_id,
                "signal_id": signal_id,
                "unit": unit,
                "scale_factor": scale,
                "sensor_type": sensor_type
            }

    def connect(self, endpoint: Optional[str] = None, credentials: Optional[Dict[str, Any]] = None) -> bool:
        self.is_connected = True
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        return True

    def register_tag_mapping(self, source_tag: str, asset_id: str, signal_id: str, unit: str, sensor_type: Any):
        self.tag_mappings[source_tag] = {
            "asset_id": asset_id,
            "signal_id": signal_id,
            "unit": unit,
            "scale_factor": 1.0,
            "sensor_type": sensor_type
        }

    def normalize_payload(self, raw_payload: Any, source_identifier: str) -> Optional[CanonicalEvent]:
        """
        Translates raw integer register reading: { "reg": "REG_40001", "raw_val": 485, "status": 0 }
        into CanonicalEvent.
        """
        mapping = self.tag_mappings.get(source_identifier)
        if not mapping:
            return None

        raw_int = float(raw_payload.get("raw_val", 0.0))
        scale = mapping.get("scale_factor", 1.0)
        val = round(raw_int * scale, 3)

        status = raw_payload.get("status", 0)
        quality = DataQualityFlag.GOOD if status == 0 else DataQualityFlag.BAD

        event = CanonicalEvent(
            timestamp=datetime.now(timezone.utc),
            asset_id=mapping["asset_id"],
            signal_id=mapping["signal_id"],
            value=val,
            unit=mapping["unit"],
            quality=quality,
            source="MODBUS_TCP_GATEWAY",
            source_type=SourceType.SIMULATED,
            sequence=int(raw_payload.get("seq", 0)),
            sensor_type=mapping["sensor_type"],
            correlation_id=str(uuid.uuid4())[:8]
        )

        enriched = data_quality_engine.validate_and_enrich(event)
        enriched.classification = stream_classifier.classify_event(enriched)
        return enriched

modbus_adapter = ModbusTcpAdapter()
