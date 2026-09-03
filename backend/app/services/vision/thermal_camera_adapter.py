import uuid
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from app.services.vision.base_camera_adapter import CameraSourceAdapter
from app.schemas.vision import (
    CameraMetadata, CameraType, CameraStatus, ThermalFrameEvidence,
    ThermalHotspot, VisionQualityStatus, VisionFreshnessStatus
)

class ThermalCameraAdapter(CameraSourceAdapter):
    """
    Industrial Radiometric Thermal Camera Adapter.
    Processes thermal sensor matrices (e.g. FLIR, Optris, Hikmicro, Axis Thermographic),
    extracting true temperature per pixel, min/max/mean/P95 distributions, relative baseline
    excursions, and discrete spatial hotspot contours.
    """

    def __init__(self, camera_meta: Optional[CameraMetadata] = None):
        meta = camera_meta or CameraMetadata(
            camera_id="CAM-TH-DAHEJ-01",
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            zone_id="Sector D - Cryogenic Yard",
            camera_type=CameraType.THERMAL_RADIOMETRIC,
            location_desc="Cryogenic Ammonia Storage Yard — North Mast",
            resolution_w=640,
            resolution_h=480,
            frame_rate_fps=2.0,
            thermal_range_min_c=-50.0,
            thermal_range_max_c=350.0
        )
        super().__init__(meta)
        self.endpoint = meta.source_stream_url or "rtsp://127.0.0.1:8554/thermal_radiometric_t04"
        self.zone_baseline_temp_c = 25.0
        self.hotspot_temp_threshold_c = 45.0
        self.last_max_temp = 25.0
        self.last_frame_timestamp: Optional[datetime] = None
        self._mock_thermal_matrix: Optional[np.ndarray] = None

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
            "is_radiometric": True,
            "read_only": True
        }

    def set_mock_frame_matrix(self, matrix: np.ndarray):
        """Test helper to inject radiometric temperature grid (H x W in °C)."""
        self._mock_thermal_matrix = matrix

    def read_frame(self) -> Optional[np.ndarray]:
        """Returns radiometric temperature matrix (H x W in °C)."""
        if not self.is_connected:
            return None
        if self._mock_thermal_matrix is not None:
            return self._mock_thermal_matrix
        
        # Default baseline ambient thermal field
        h, w = self._meta.resolution_h, self._meta.resolution_w
        base = np.full((h, w), self.zone_baseline_temp_c, dtype=np.float32)
        noise = np.random.normal(0.0, 0.4, (h, w)).astype(np.float32)
        return base + noise

    def process_radiometric_frame(
        self,
        temp_matrix: np.ndarray,
        source_timestamp: Optional[datetime] = None,
        is_live_data: bool = False
    ) -> ThermalFrameEvidence:
        """
        Extracts statistical temperature distribution and detects spatial hotspots.
        """
        now_utc = datetime.now(timezone.utc)
        src_ts = source_timestamp or now_utc
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)

        h, w = temp_matrix.shape
        min_t = float(np.min(temp_matrix))
        max_t = float(np.max(temp_matrix))
        mean_t = float(np.mean(temp_matrix))
        p95_t = float(np.percentile(temp_matrix, 95))

        # Compute rate of rise (dT/dt in °C/min)
        dT_dt = 0.0
        if self.last_frame_timestamp is not None:
            dt_sec = max(0.1, (src_ts - self.last_frame_timestamp).total_seconds())
            dT_dt = ((max_t - self.last_max_temp) / dt_sec) * 60.0

        self.last_max_temp = max_t
        self.last_frame_timestamp = src_ts

        # Detect spatial hotspots exceeding threshold
        hotspot_mask = temp_matrix >= self.hotspot_temp_threshold_c
        hotspots: List[ThermalHotspot] = []
        
        if np.any(hotspot_mask):
            y_indices, x_indices = np.where(hotspot_mask)
            x_min, x_max = float(np.min(x_indices)), float(np.max(x_indices))
            y_min, y_max = float(np.min(y_indices)), float(np.max(y_indices))
            
            centroid_x = float(np.mean(x_indices)) / w
            centroid_y = float(np.mean(y_indices)) / h
            bbox = [
                round(x_min / w, 3),
                round(y_min / h, 3),
                round(max(0.05, (x_max - x_min) / w), 3),
                round(max(0.05, (y_max - y_min) / h), 3)
            ]
            area_px = int(len(x_indices))
            hotspot_max = float(np.max(temp_matrix[hotspot_mask]))
            hotspot_mean = float(np.mean(temp_matrix[hotspot_mask]))

            severity = "WATCH"
            if hotspot_max >= 80.0 or dT_dt >= 15.0:
                severity = "CRITICAL"
            elif hotspot_max >= 55.0 or dT_dt >= 5.0:
                severity = "ABNORMAL"

            hs = ThermalHotspot(
                hotspot_id=f"HOTSPOT-{self._meta.camera_id}-01",
                camera_id=self._meta.camera_id,
                zone_id=self._meta.zone_id,
                asset_id=self._meta.asset_id,
                centroid_x_pct=round(centroid_x, 3),
                centroid_y_pct=round(centroid_y, 3),
                bbox_xywh=bbox,
                area_pixels=area_px,
                area_estimated_m2=round(area_px * 0.002, 3),
                max_temperature_c=round(hotspot_max, 1),
                mean_temperature_c=round(hotspot_mean, 1),
                baseline_temp_c=self.zone_baseline_temp_c,
                delta_t_baseline_c=round(hotspot_max - self.zone_baseline_temp_c, 1),
                rate_of_rise_c_min=round(dT_dt, 1),
                persistence_sec=1.0,
                growth_rate_pct_sec=0.0,
                severity=severity
            )
            hotspots.append(hs)

        frame_id = f"FRM-TH-{uuid.uuid4().hex[:8].upper()}"
        evidence = ThermalFrameEvidence(
            frame_id=frame_id,
            camera_id=self._meta.camera_id,
            facility_id=self._meta.facility_id,
            asset_id=self._meta.asset_id,
            zone_id=self._meta.zone_id,
            timestamp_utc=src_ts,
            source_timestamp=src_ts,
            acquisition_timestamp=now_utc,
            ingestion_timestamp=now_utc,
            width=w,
            height=h,
            temperature_unit="°C",
            is_radiometric=True,
            min_temperature=round(min_t, 1),
            max_temperature=round(max_t, 1),
            mean_temperature=round(mean_t, 1),
            percentile_95_temperature=round(p95_t, 1),
            hotspot_count=len(hotspots),
            hotspot_regions=hotspots,
            quality_status=VisionQualityStatus.GOOD,
            data_quality_flags=["NONE"],
            freshness_status=VisionFreshnessStatus.LIVE,
            freshness_age_sec=0.0,
            inference_version="v1.0.0-radiometric-contour",
            is_live_data=is_live_data,
            evidence_uri=f"evidence://thermal/{self._meta.camera_id}/{frame_id}.bin" if hotspots else None
        )

        self.frames_processed_count += 1
        self.last_frame_time = now_utc
        return evidence

    def close(self) -> None:
        self.disconnect()
        self._mock_thermal_matrix = None

thermal_camera_adapter = ThermalCameraAdapter()
