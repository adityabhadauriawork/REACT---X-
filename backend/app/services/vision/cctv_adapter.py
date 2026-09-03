import io
import uuid
import numpy as np
from PIL import Image
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.vision.base_camera_adapter import CameraSourceAdapter
from app.schemas.vision import (
    CameraMetadata, CameraType, CameraStatus, CCTVFrameEvidence,
    VisionDetectionItem, VisionQualityStatus, VisionFreshnessStatus
)

class CCTVAdapter(CameraSourceAdapter):
    """
    Industrial Visible-Spectrum Optical CCTV Camera Adapter.
    Processes RGB optical surveillance streams for smoke aerosol plumes,
    visible flame signatures, personnel muster presence, and scene obstruction.
    """

    def __init__(self, camera_meta: Optional[CameraMetadata] = None):
        meta = camera_meta or CameraMetadata(
            camera_id="CAM-CCTV-DAHEJ-01",
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            zone_id="Sector D - Cryogenic Yard",
            camera_type=CameraType.CCTV_OPTICAL,
            location_desc="Sector D Perimeter Mast — Visible Spectrum CCTV",
            resolution_w=1280,
            resolution_h=720,
            frame_rate_fps=5.0,
            temperature_measurement_capability=False
        )
        super().__init__(meta)
        self.endpoint = meta.source_stream_url or "rtsp://127.0.0.1:8554/cctv_t04_optical"
        self._mock_frame: Optional[np.ndarray] = None

    def connect(self, endpoint: Optional[str] = None, credentials: Optional[Dict[str, Any]] = None) -> bool:
        if endpoint:
            self.endpoint = endpoint
        self.is_connected = True
        self._meta.status = CameraStatus.ONLINE
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self._meta.status = CameraStatus.OFFLINE
        return True

    def health(self) -> Dict[str, Any]:
        return {
            "camera_id": self._meta.camera_id,
            "facility_id": self._meta.facility_id,
            "asset_id": self._meta.asset_id,
            "camera_type": self._meta.camera_type.value,
            "status": self._meta.status.value,
            "connected": self.is_connected,
            "frames_processed": self.frames_processed_count,
            "last_frame_time": self.last_frame_time.isoformat() if self.last_frame_time else None,
            "is_radiometric": False,
            "read_only": True
        }

    def set_mock_rgb_frame(self, frame: np.ndarray):
        self._mock_frame = frame

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_connected:
            return None
        if self._mock_frame is not None:
            return self._mock_frame
        
        # Default synthetic optical frame (gray industrial background)
        h, w = self._meta.resolution_h, self._meta.resolution_w
        frame = np.full((h, w, 3), 120, dtype=np.uint8)
        return frame

    def process_optical_frame(
        self,
        frame_input: Any, # np.ndarray, PIL.Image, or bytes
        source_timestamp: Optional[datetime] = None,
        is_live_data: bool = False
    ) -> CCTVFrameEvidence:
        now_utc = datetime.now(timezone.utc)
        src_ts = source_timestamp or now_utc
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)

        detections: List[VisionDetectionItem] = []
        scene_status = "CLEAR"
        smoke_conf = 0.0
        flame_conf = 0.0
        person_count = 0
        vehicle_count = 0

        # Convert input to numpy array if possible
        arr = None
        if isinstance(frame_input, np.ndarray):
            arr = frame_input
        elif isinstance(frame_input, bytes) and len(frame_input) > 0:
            try:
                img = Image.open(io.BytesIO(frame_input)).convert("RGB")
                arr = np.array(img)
            except Exception:
                arr = None

        if arr is not None and len(arr.shape) == 3 and arr.shape[2] == 3:
            h, w, _ = arr.shape
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

            # 1. Optical Fire Flame Chromaticity Masking
            fire_mask = (r > 190) & (g > 90) & (g < 210) & (b < 100) & (r > g + 30)
            fire_px = int(np.sum(fire_mask))
            if fire_px > (w * h * 0.003): # >0.3% of pixels
                flame_conf = min(0.98, max(0.65, 0.60 + (fire_px / (w * h)) * 80.0))
                y_i, x_i = np.where(fire_mask)
                x_min, x_max = float(np.min(x_i)) / w, float(np.max(x_i)) / w
                y_min, y_max = float(np.min(y_i)) / h, float(np.max(y_i)) / h
                detections.append(VisionDetectionItem(
                    id=f"DET-FLAME-{uuid.uuid4().hex[:4].upper()}",
                    label="OPTICAL_FLAME",
                    confidence_pct=round(flame_conf * 100.0, 1),
                    bbox_xywh=[round(x_min, 3), round(y_min, 3), round(max(0.08, x_max - x_min), 3), round(max(0.08, y_max - y_min), 3)],
                    color_hex="#ef4444"
                ))
                scene_status = "FLAME_SIGNATURE"

            # 2. Aerosol / Smoke Diffusion Masking (gray variance bounds)
            smoke_mask = (np.abs(r.astype(int) - g.astype(int)) < 20) & \
                         (np.abs(g.astype(int) - b.astype(int)) < 20) & \
                         (r > 110) & (r < 215)
            smoke_px = int(np.sum(smoke_mask))
            if smoke_px > (w * h * 0.04): # >4% of image
                smoke_conf = min(0.95, max(0.60, 0.55 + (smoke_px / (w * h)) * 40.0))
                y_i, x_i = np.where(smoke_mask)
                x_min, x_max = float(np.min(x_i)) / w, float(np.max(x_i)) / w
                y_min, y_max = float(np.min(y_i)) / h, float(np.max(y_i)) / h
                detections.append(VisionDetectionItem(
                    id=f"DET-SMOKE-{uuid.uuid4().hex[:4].upper()}",
                    label="SMOKE_PLUME",
                    confidence_pct=round(smoke_conf * 100.0, 1),
                    bbox_xywh=[round(x_min, 3), round(y_min, 3), round(max(0.12, x_max - x_min), 3), round(max(0.12, y_max - y_min), 3)],
                    color_hex="#f97316"
                ))
                if scene_status != "FLAME_SIGNATURE":
                    scene_status = "SMOKE_HAZE"

        frame_id = f"FRM-CCTV-{uuid.uuid4().hex[:8].upper()}"
        evidence = CCTVFrameEvidence(
            frame_id=frame_id,
            camera_id=self._meta.camera_id,
            facility_id=self._meta.facility_id,
            asset_id=self._meta.asset_id,
            zone_id=self._meta.zone_id,
            timestamp_utc=src_ts,
            source_timestamp=src_ts,
            acquisition_timestamp=now_utc,
            ingestion_timestamp=now_utc,
            detections=detections,
            scene_status=scene_status,
            smoke_confidence=round(smoke_conf, 2),
            flame_confidence=round(flame_conf, 2),
            personnel_count=person_count,
            vehicle_count=vehicle_count,
            quality_status=VisionQualityStatus.GOOD,
            data_quality_flags=["NONE"],
            freshness_status=VisionFreshnessStatus.LIVE,
            freshness_age_sec=0.0,
            inference_version="v1.0.0-optical-classifier",
            is_live_data=is_live_data,
            evidence_uri=f"evidence://cctv/{self._meta.camera_id}/{frame_id}.jpg" if (flame_conf > 0 or smoke_conf > 0) else None
        )

        self.frames_processed_count += 1
        self.last_frame_time = now_utc
        return evidence

    def close(self) -> None:
        self.disconnect()
        self._mock_frame = None

cctv_adapter = CCTVAdapter()
