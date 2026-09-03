from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.vision import CameraMetadata, CameraStatus, CameraType

class CameraSourceAdapter(ABC):
    """
    Abstract Hardware-Agnostic Camera Ingestion Interface.
    Normalizes thermal radiometric cameras, visible-spectrum CCTV feeds, and simulators
    into canonical frame representations.
    
    STRICT READ-ONLY SAFETY BOUNDARY:
    Camera adapters are strictly read-only sensory ingestion components.
    Under NO circumstances may an adapter implement or expose PTZ control overrides,
    firmware modification, or actuator control interfaces.
    """

    def __init__(self, camera_meta: CameraMetadata):
        self._meta = camera_meta
        self.is_connected = False
        self.frames_processed_count = 0
        self.last_frame_time: Optional[datetime] = None

    @abstractmethod
    def connect(self, endpoint: Optional[str] = None, credentials: Optional[Dict[str, Any]] = None) -> bool:
        """Establish read-only connection or RTSP stream ingestion."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Safely disconnect from video stream or edge gateway."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return camera connection status, FPS rate, and diagnostic metrics."""
        pass

    @abstractmethod
    def read_frame(self) -> Optional[Any]:
        """Acquire latest raw frame (radiometric numpy matrix or RGB image)."""
        pass

    def metadata(self) -> CameraMetadata:
        """Return configured camera catalog metadata."""
        return self._meta

    @abstractmethod
    def close(self) -> None:
        """Release video capture resources and network sockets."""
        pass
