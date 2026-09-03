import time
import uuid
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.vision.base_camera_adapter import CameraSourceAdapter
from app.schemas.vision import (
    CameraMetadata, CameraType, CameraStatus, ThermalFrameEvidence,
    CCTVFrameEvidence, ThermalHotspot, VisionDetectionItem,
    VisionQualityStatus, VisionFreshnessStatus
)

class VisionSimulationScenario:
    # Thermal Scenarios
    NORMAL = "NORMAL"
    GRADUAL_HEATING = "GRADUAL_HEATING"
    LOCAL_HOTSPOT = "LOCAL_HOTSPOT"
    RAPID_HEATING = "RAPID_HEATING"
    HOTSPOT_GROWTH = "HOTSPOT_GROWTH"
    MULTIPLE_HOTSPOTS = "MULTIPLE_HOTSPOTS"
    
    # Optical CCTV Scenarios
    SMOKE_LIKE_EVENT = "SMOKE_LIKE_EVENT"
    FLAME_LIKE_EVENT = "FLAME_LIKE_EVENT"
    OBSCURED_SCENE = "OBSCURED_SCENE"
    
    # Common Failure
    CAMERA_FAILURE = "CAMERA_FAILURE"

class CameraSimulator(CameraSourceAdapter):
    """
    High-Fidelity Facility Visual & Thermal Radiometric Simulator.
    Simulates physically realistic thermal heat fields (Gaussian hotspot plumes, conduction diffusion,
    rate-of-rise dT/dt) and optical CCTV smoke/flame signatures across plant assets.
    """

    def __init__(self, camera_meta: Optional[CameraMetadata] = None):
        meta = camera_meta or CameraMetadata(
            camera_id="SIM-CAM-DAHEJ-01",
            facility_id="FAC-IN-DAHEJ-001",
            asset_id="T-04",
            zone_id="Sector D - Cryogenic Yard",
            camera_type=CameraType.DUAL_RGB_THERMAL,
            location_desc="Simulated Dual Thermal/Optical Mast (Sector D)",
            resolution_w=640,
            resolution_h=480,
            frame_rate_fps=2.0,
            thermal_range_min_c=-50.0,
            thermal_range_max_c=350.0
        )
        super().__init__(meta)
        self.active_scenario = VisionSimulationScenario.NORMAL
        self.scenario_start_time = time.time()
        self.sequence_counter = 0
        self.last_thermal_matrix: Optional[np.ndarray] = None
        self.last_max_temp = 25.0
        self.connect()

    def set_scenario(self, scenario: str):
        if hasattr(VisionSimulationScenario, scenario):
            self.active_scenario = scenario
            self.scenario_start_time = time.time()
        else:
            raise ValueError(f"Unknown vision scenario: {scenario}")

    def connect(self, endpoint: Optional[str] = None, credentials: Optional[Dict[str, Any]] = None) -> bool:
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
            "active_scenario": self.active_scenario,
            "scenario_elapsed_sec": round(time.time() - self.scenario_start_time, 1),
            "status": self._meta.status.value,
            "connected": self.is_connected,
            "frames_processed": self.frames_processed_count,
            "is_live_data": False,
            "read_only": True
        }

    def read_frame(self) -> Optional[np.ndarray]:
        if not self.is_connected:
            return None
        return self.generate_thermal_matrix()

    def generate_thermal_matrix(self) -> np.ndarray:
        """
        Generates realistic 2D temperature array (H x W in °C) with Gaussian thermal diffusion.
        """
        h, w = self._meta.resolution_h, self._meta.resolution_w
        elapsed = time.time() - self.scenario_start_time

        # Baseline ambient field
        base_temp = 25.0
        matrix = np.full((h, w), base_temp, dtype=np.float32)
        noise = np.random.normal(0.0, 0.2, (h, w)).astype(np.float32)
        matrix += noise

        # Generate X, Y coordinate grids for 2D Gaussian heat spot
        y_grid, x_grid = np.ogrid[:h, :w]

        if self.active_scenario == VisionSimulationScenario.GRADUAL_HEATING:
            # Monotonic heating over 60s
            progress = min(1.0, elapsed / 60.0)
            peak_temp = base_temp + (progress * 28.0) # 25 -> 53 °C
            cx, cy = int(w * 0.45), int(h * 0.40)
            sigma = 40.0
            gaussian = np.exp(-((x_grid - cx)**2 + (y_grid - cy)**2) / (2 * sigma**2))
            matrix += gaussian * (peak_temp - base_temp)

        elif self.active_scenario == VisionSimulationScenario.LOCAL_HOTSPOT:
            # Concentrated high temperature hotspot on flange
            cx, cy = int(w * 0.50), int(h * 0.35)
            sigma = 25.0
            gaussian = np.exp(-((x_grid - cx)**2 + (y_grid - cy)**2) / (2 * sigma**2))
            matrix += gaussian * 62.0 # 25 + 62 = 87 °C

        elif self.active_scenario == VisionSimulationScenario.RAPID_HEATING:
            # Acute boil-off or exothermic run-away
            progress = min(1.0, elapsed / 25.0)
            cx, cy = int(w * 0.40), int(h * 0.50)
            sigma = 50.0
            gaussian = np.exp(-((x_grid - cx)**2 + (y_grid - cy)**2) / (2 * sigma**2))
            matrix += gaussian * (progress * 95.0) # 25 -> 120 °C

        elif self.active_scenario == VisionSimulationScenario.HOTSPOT_GROWTH:
            # Spatial expansion over time
            progress = min(1.0, elapsed / 40.0)
            cx, cy = int(w * 0.55), int(h * 0.45)
            sigma = 20.0 + (progress * 60.0) # Area expanding
            gaussian = np.exp(-((x_grid - cx)**2 + (y_grid - cy)**2) / (2 * sigma**2))
            matrix += gaussian * 75.0

        elif self.active_scenario == VisionSimulationScenario.MULTIPLE_HOTSPOTS:
            # Dual hotspots (e.g. pump seal + discharge header)
            cx1, cy1 = int(w * 0.30), int(h * 0.40)
            g1 = np.exp(-((x_grid - cx1)**2 + (y_grid - cy1)**2) / (2 * 30.0**2))
            cx2, cy2 = int(w * 0.70), int(h * 0.60)
            g2 = np.exp(-((x_grid - cx2)**2 + (y_grid - cy2)**2) / (2 * 25.0**2))
            matrix += (g1 * 68.0) + (g2 * 54.0)

        elif self.active_scenario == VisionSimulationScenario.CAMERA_FAILURE:
            # Corrupted / frozen noise
            matrix = np.full((h, w), -999.0, dtype=np.float32)

        self.last_thermal_matrix = matrix
        return matrix

    def generate_thermal_evidence(self) -> ThermalFrameEvidence:
        """Generate structured radiometric thermal frame evidence."""
        now_utc = datetime.now(timezone.utc)
        self.sequence_counter += 1

        if self.active_scenario == VisionSimulationScenario.CAMERA_FAILURE:
            return ThermalFrameEvidence(
                frame_id=f"FRM-SIM-TH-{self.sequence_counter:06d}",
                camera_id=self._meta.camera_id,
                facility_id=self._meta.facility_id,
                asset_id=self._meta.asset_id,
                zone_id=self._meta.zone_id,
                timestamp_utc=now_utc,
                source_timestamp=now_utc,
                min_temperature=-999.0,
                max_temperature=-999.0,
                mean_temperature=-999.0,
                percentile_95_temperature=-999.0,
                hotspot_count=0,
                quality_status=VisionQualityStatus.BAD,
                data_quality_flags=["SENSOR_FAULT"],
                freshness_status=VisionFreshnessStatus.DEGRADED,
                is_live_data=False
            )

        matrix = self.generate_thermal_matrix()
        h, w = matrix.shape
        min_t = float(np.min(matrix))
        max_t = float(np.max(matrix))
        mean_t = float(np.mean(matrix))
        p95_t = float(np.percentile(matrix, 95))

        dT_dt = round((max_t - self.last_max_temp) * 60.0, 1) if self.last_max_temp else 0.0
        self.last_max_temp = max_t

        hotspots: List[ThermalHotspot] = []
        hotspot_mask = matrix >= 45.0
        if np.any(hotspot_mask):
            y_i, x_i = np.where(hotspot_mask)
            area_px = int(len(x_i))
            cx = float(np.mean(x_i)) / w
            cy = float(np.mean(y_i)) / h
            x_min, x_max = float(np.min(x_i)) / w, float(np.max(x_i)) / w
            y_min, y_max = float(np.min(y_i)) / h, float(np.max(y_i)) / h

            sev = "WATCH"
            if max_t >= 80.0 or dT_dt >= 15.0:
                sev = "CRITICAL"
            elif max_t >= 55.0 or dT_dt >= 5.0:
                sev = "ABNORMAL"

            hotspots.append(ThermalHotspot(
                hotspot_id=f"HS-SIM-{self._meta.camera_id}-01",
                camera_id=self._meta.camera_id,
                zone_id=self._meta.zone_id,
                asset_id=self._meta.asset_id,
                centroid_x_pct=round(cx, 3),
                centroid_y_pct=round(cy, 3),
                bbox_xywh=[round(x_min, 3), round(y_min, 3), round(max(0.05, x_max - x_min), 3), round(max(0.05, y_max - y_min), 3)],
                area_pixels=area_px,
                area_estimated_m2=round(area_px * 0.002, 3),
                max_temperature_c=round(max_t, 1),
                mean_temperature_c=round(float(np.mean(matrix[hotspot_mask])), 1),
                baseline_temp_c=25.0,
                delta_t_baseline_c=round(max_t - 25.0, 1),
                rate_of_rise_c_min=dT_dt,
                persistence_sec=max(1.0, time.time() - self.scenario_start_time),
                growth_rate_pct_sec=1.5 if self.active_scenario == VisionSimulationScenario.HOTSPOT_GROWTH else 0.0,
                severity=sev
            ))

        self.frames_processed_count += 1
        return ThermalFrameEvidence(
            frame_id=f"FRM-SIM-TH-{self.sequence_counter:06d}",
            camera_id=self._meta.camera_id,
            facility_id=self._meta.facility_id,
            asset_id=self._meta.asset_id,
            zone_id=self._meta.zone_id,
            timestamp_utc=now_utc,
            source_timestamp=now_utc,
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
            inference_version="v1.0.0-sim-radiometric",
            is_live_data=False,
            evidence_uri=f"evidence://sim/thermal/{self._meta.camera_id}.bin" if hotspots else None
        )

    def generate_cctv_evidence(self) -> CCTVFrameEvidence:
        """Generate structured optical CCTV frame evidence."""
        now_utc = datetime.now(timezone.utc)
        detections: List[VisionDetectionItem] = []
        scene_status = "CLEAR"
        smoke_conf = 0.0
        flame_conf = 0.0

        if self.active_scenario == VisionSimulationScenario.FLAME_LIKE_EVENT:
            flame_conf = 0.94
            smoke_conf = 0.82
            scene_status = "FLAME_SIGNATURE"
            detections.append(VisionDetectionItem(
                id="DET-SIM-FLAME-01",
                label="OPTICAL_FLAME",
                confidence_pct=94.0,
                bbox_xywh=[0.42, 0.40, 0.22, 0.32],
                color_hex="#ef4444"
            ))
            detections.append(VisionDetectionItem(
                id="DET-SIM-SMOKE-01",
                label="SMOKE_PLUME",
                confidence_pct=82.0,
                bbox_xywh=[0.30, 0.15, 0.45, 0.40],
                color_hex="#f97316"
            ))

        elif self.active_scenario == VisionSimulationScenario.SMOKE_LIKE_EVENT:
            smoke_conf = 0.89
            scene_status = "SMOKE_HAZE"
            detections.append(VisionDetectionItem(
                id="DET-SIM-SMOKE-01",
                label="SMOKE_PLUME",
                confidence_pct=89.0,
                bbox_xywh=[0.28, 0.20, 0.48, 0.45],
                color_hex="#f97316"
            ))

        elif self.active_scenario == VisionSimulationScenario.OBSCURED_SCENE:
            scene_status = "OBSCURED"

        return CCTVFrameEvidence(
            frame_id=f"FRM-SIM-CCTV-{self.sequence_counter:06d}",
            camera_id=self._meta.camera_id,
            facility_id=self._meta.facility_id,
            asset_id=self._meta.asset_id,
            zone_id=self._meta.zone_id,
            timestamp_utc=now_utc,
            source_timestamp=now_utc,
            acquisition_timestamp=now_utc,
            ingestion_timestamp=now_utc,
            detections=detections,
            scene_status=scene_status,
            smoke_confidence=smoke_conf,
            flame_confidence=flame_conf,
            personnel_count=1 if scene_status == "CLEAR" else 0,
            vehicle_count=1 if scene_status == "CLEAR" else 0,
            quality_status=VisionQualityStatus.GOOD if scene_status != "OBSCURED" else VisionQualityStatus.WARNING,
            data_quality_flags=["NONE"] if scene_status != "OBSCURED" else ["SCENE_OCCLUSION"],
            freshness_status=VisionFreshnessStatus.LIVE,
            freshness_age_sec=0.0,
            inference_version="v1.0.0-sim-optical",
            is_live_data=False,
            evidence_uri=f"evidence://sim/cctv/{self._meta.camera_id}.jpg" if (flame_conf > 0 or smoke_conf > 0) else None
        )

    def close(self) -> None:
        self.disconnect()

camera_simulator = CameraSimulator()
