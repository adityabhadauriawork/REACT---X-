from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.schemas.canonical import CanonicalEvent

class BaseProtocolAdapter(ABC):
    """
    Abstract industrial protocol connector interface.
    Normalizes heterogeneous protocols (OPC UA, MQTT, Modbus TCP, RTSP)
    into the canonical event schema.
    """
    def __init__(self, name: str, protocol_type: str):
        self.name = name
        self.protocol_type = protocol_type
        self.is_connected = False
        self.tag_mappings: Dict[str, Dict[str, Any]] = {}

    @abstractmethod
    def connect(self, endpoint: str, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Establish connection to industrial endpoint or broker."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Safely terminate connection."""
        pass

    @abstractmethod
    def register_tag_mapping(self, source_tag: str, asset_id: str, signal_id: str, unit: str, sensor_type: str):
        """Map a proprietary PLC tag or topic to canonical asset signal."""
        pass

    @abstractmethod
    def normalize_payload(self, raw_payload: Any, source_identifier: str) -> Optional[CanonicalEvent]:
        """Convert native protocol frame into a validated canonical event."""
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "adapter_name": self.name,
            "protocol": self.protocol_type,
            "connected": self.is_connected,
            "mapped_tags_count": len(self.tag_mappings)
        }
