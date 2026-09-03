from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, SourceProtocol, GatewayStatus
)

class TelemetrySourceAdapter(ABC):
    """
    Standard vendor-agnostic read-only industrial telemetry source interface.
    Normalizes heterogeneous protocols (OPC UA, MQTT / Sparkplug B, Modbus, Telemetry Simulator)
    into the canonical FacilityTelemetryObservation contract.
    
    STRICT SAFETY RULE:
    REACT-X industrial adapters are strictly READ-ONLY consumers.
    Under NO circumstances may an adapter implement, expose, or execute write operations
    to PLCs, DCS, SIS, ESD, valves, or plant control systems.
    """

    def __init__(self, name: str, protocol: SourceProtocol, gateway_id: str, facility_id: str):
        self.name = name
        self.protocol = protocol
        self.gateway_id = gateway_id
        self.facility_id = facility_id
        self.status = GatewayStatus.DISCONNECTED
        self.is_connected = False
        self.registered_sensors: Dict[str, SensorMetadata] = {}
        self.total_observations_ingested = 0
        self.last_ingestion_time = None

    @abstractmethod
    def connect(self, endpoint: str, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Establish read-only connection or subscription to industrial endpoint / broker."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Safely terminate read-only connection."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return adapter connection health, sensor count, and ingestion diagnostics."""
        pass

    @abstractmethod
    def subscribe_or_poll(self) -> List[FacilityTelemetryObservation]:
        """Acquire latest high-frequency observations from edge endpoint or active buffer."""
        pass

    @abstractmethod
    def normalize(self, raw_payload: Any, metadata: SensorMetadata) -> Optional[FacilityTelemetryObservation]:
        """Convert native protocol frame into validated canonical observation."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release all network sockets, subscriptions, and system resources."""
        pass

    def register_sensor_metadata(self, metadata: SensorMetadata):
        """Register tag mapping and physical validation parameters for a sensor."""
        self.registered_sensors[metadata.sensor_id] = metadata

    def get_registered_sensors(self) -> List[SensorMetadata]:
        return list(self.registered_sensors.values())
