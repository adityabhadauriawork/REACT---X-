from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.schemas.orchestration import RegisteredSourceItem, SystemDataMode

class UnifiedSourceRegistryService:
    """
    Tracks all active multi-modal telemetry and visual sensing sources across REACT-X.
    """

    def __init__(self):
        self.sources: Dict[str, RegisteredSourceItem] = {
            "SRC-SAT-FIRMS-VIIRS": RegisteredSourceItem(
                source_id="SRC-SAT-FIRMS-VIIRS",
                source_type="SATELLITE_FIRMS",
                facility_id=None,
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.95,
                adapter_version="v2.1-viirs-snpp"
            ),
            "SRC-OPCUA-DAHEJ-GW01": RegisteredSourceItem(
                source_id="SRC-OPCUA-DAHEJ-GW01",
                source_type="OPC_UA_TELEMETRY",
                facility_id="FAC-IN-DAHEJ-001",
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.98,
                adapter_version="v1.0-opcua-read-only"
            ),
            "SRC-MQTT-DAHEJ-BRK01": RegisteredSourceItem(
                source_id="SRC-MQTT-DAHEJ-BRK01",
                source_type="MQTT_TELEMETRY",
                facility_id="FAC-IN-DAHEJ-001",
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.97,
                adapter_version="v1.0-mqtt-tls"
            ),
            "SRC-CAM-TH-01": RegisteredSourceItem(
                source_id="SRC-CAM-TH-01",
                source_type="THERMAL_CAMERA",
                facility_id="FAC-IN-DAHEJ-001",
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.92,
                adapter_version="v1.0-flir-lwir"
            ),
            "SRC-CAM-CCTV-01": RegisteredSourceItem(
                source_id="SRC-CAM-CCTV-01",
                source_type="CCTV",
                facility_id="FAC-IN-DAHEJ-001",
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.88,
                adapter_version="v1.0-rtsp-optical"
            ),
            "SRC-ENV-WEATHER-01": RegisteredSourceItem(
                source_id="SRC-ENV-WEATHER-01",
                source_type="WEATHER_API",
                facility_id=None,
                status="CONNECTED",
                data_mode=SystemDataMode.SIMULATION,
                quality_score=0.95,
                adapter_version="v1.0-openmeteo"
            )
        }

    def list_sources(self) -> List[RegisteredSourceItem]:
        return list(self.sources.values())

    def get_source(self, source_id: str) -> Optional[RegisteredSourceItem]:
        return self.sources.get(source_id)

    def update_source_heartbeat(self, source_id: str, status: str = "CONNECTED", quality: float = 1.0):
        if source_id in self.sources:
            src = self.sources[source_id]
            src.status = status
            src.quality_score = quality
            src.last_seen = datetime.now(timezone.utc)

source_registry_service = UnifiedSourceRegistryService()
