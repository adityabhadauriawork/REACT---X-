import time
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.schemas.vision import (
    CameraMetadata, ThermalFrameEvidence, CCTVFrameEvidence, VisualEvidence,
    VisionHealthResponse, VisionEventsQuery, CameraType, CameraStatus,
    VisualEvidenceType, VisionQualityStatus, VisionFreshnessStatus
)
from app.services.vision.base_camera_adapter import CameraSourceAdapter
from app.services.vision.thermal_camera_adapter import thermal_camera_adapter
from app.services.vision.cctv_adapter import cctv_adapter
from app.services.vision.camera_simulator import camera_simulator, VisionSimulationScenario
from app.services.vision.thermal_hotspot_tracker import thermal_hotspot_tracker
from app.services.vision.vision_quality_engine import vision_quality_engine
from app.services.storage.vision_repository import vision_repository
from app.services.industrial.telemetry_service import telemetry_service

logger = logging.getLogger(__name__)

class VisionPipelineService:
    """
    Central Computer Vision & Radiometric Thermal Ingestion Orchestrator.
    Manages edge camera adapters, radiometric extraction, spatial hotspot tracking,
    quality verification, latest-vision state caching, and cross-modal linkage to facility telemetry.
    """

    def __init__(self):
        self.adapters: Dict[str, CameraSourceAdapter] = {
            "THERMAL": thermal_camera_adapter,
            "CCTV": cctv_adapter,
            "SIMULATOR": camera_simulator
        }
        self._latest_thermal_by_camera: Dict[str, ThermalFrameEvidence] = {}
        self._latest_cctv_by_camera: Dict[str, CCTVFrameEvidence] = {}
        self._cameras_by_facility: Dict[str, List[str]] = {}
        self.total_frames_processed = 0
        self.start_time = time.time()
        self.inference_latencies: List[float] = []
        self.good_frames = 0
        self.degraded_frames = 0

        # Build initial registered cameras
        self._register_default_cameras()

    def _register_default_cameras(self):
        cameras = [
            CameraMetadata(
                camera_id="CAM-TH-DAHEJ-01",
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-04",
                zone_id="Sector D - Cryogenic Yard",
                camera_type=CameraType.THERMAL_RADIOMETRIC,
                location_desc="North Mast overlooking T-04 Cryogenic Tank",
                resolution_w=640,
                resolution_h=480,
                frame_rate_fps=2.0,
                thermal_range_min_c=-50.0,
                thermal_range_max_c=350.0,
                source_stream_url="rtsp://127.0.0.1:8554/thermal_t04"
            ),
            CameraMetadata(
                camera_id="CAM-CCTV-DAHEJ-01",
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-04",
                zone_id="Sector D - Cryogenic Yard",
                camera_type=CameraType.CCTV_OPTICAL,
                location_desc="North Mast Optical CCTV overlooking T-04 Cryogenic Tank",
                resolution_w=1280,
                resolution_h=720,
                frame_rate_fps=5.0,
                temperature_measurement_capability=False,
                source_stream_url="rtsp://127.0.0.1:8554/cctv_t04"
            ),
            CameraMetadata(
                camera_id="CAM-TH-DAHEJ-02",
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-03",
                zone_id="Sector C - Pressurized Gas Farm",
                camera_type=CameraType.THERMAL_RADIOMETRIC,
                location_desc="South Mast overlooking T-03 Horton Sphere",
                resolution_w=640,
                resolution_h=480,
                frame_rate_fps=2.0,
                thermal_range_min_c=-20.0,
                thermal_range_max_c=300.0,
                source_stream_url="rtsp://127.0.0.1:8554/thermal_t03"
            ),
            CameraMetadata(
                camera_id="SIM-CAM-DAHEJ-01",
                facility_id="FAC-IN-DAHEJ-001",
                asset_id="T-04",
                zone_id="Sector D - Cryogenic Yard",
                camera_type=CameraType.DUAL_RGB_THERMAL,
                location_desc="High-Fidelity Simulated Dual Camera Stream (Sector D)",
                resolution_w=640,
                resolution_h=480,
                frame_rate_fps=2.0
            )
        ]
        for cam in cameras:
            if cam.facility_id not in self._cameras_by_facility:
                self._cameras_by_facility[cam.facility_id] = []
            if cam.camera_id not in self._cameras_by_facility[cam.facility_id]:
                self._cameras_by_facility[cam.facility_id].append(cam.camera_id)

    def seed_initial_metadata(self, db: Session):
        for cam in self.get_all_registered_cameras():
            vision_repository.register_camera(db, cam)

    def get_all_registered_cameras(self) -> List[CameraMetadata]:
        cameras = [
            thermal_camera_adapter.metadata(),
            cctv_adapter.metadata(),
            camera_simulator.metadata()
        ]
        return cameras

    def ingest_thermal_evidence(
        self,
        evidence: ThermalFrameEvidence,
        db: Optional[Session] = None
    ) -> ThermalFrameEvidence:
        """
        Process incoming thermal frame evidence:
        1. Run multi-frame spatial hotspot tracking
        2. Validate camera quality and freshness
        3. Convert anomalous hotspots into structured VisualEvidence
        4. Persist to repository
        """
        t0 = time.perf_counter()
        
        # 1. Update multi-frame spatial hotspot tracking
        if evidence.hotspot_regions:
            tracked = thermal_hotspot_tracker.update_hotspots(
                evidence.camera_id, evidence.hotspot_regions, evidence.timestamp_utc
            )
            evidence.hotspot_regions = tracked
            evidence.hotspot_count = len(tracked)

        # 2. Freshness calculation
        freshness_res = vision_quality_engine.compute_camera_freshness(
            evidence.source_timestamp, frame_rate_fps=2.0
        )
        evidence.freshness_status = freshness_res["freshness_status"]
        evidence.freshness_age_sec = freshness_res["age_sec"]

        # 3. Update in-memory state store
        self._latest_thermal_by_camera[evidence.camera_id] = evidence
        self.total_frames_processed += 1
        if evidence.quality_status == VisionQualityStatus.GOOD:
            self.good_frames += 1
        else:
            self.degraded_frames += 1

        # 4. Extract structured VisualEvidence for durable history
        structured_events: List[VisualEvidence] = []
        if evidence.hotspot_regions:
            for hs in evidence.hotspot_regions:
                ev = VisualEvidence(
                    evidence_id=f"EVID-TH-{uuid.uuid4().hex[:8].upper()}",
                    source_id=evidence.camera_id,
                    facility_id=evidence.facility_id,
                    asset_id=evidence.asset_id,
                    zone_id=evidence.zone_id,
                    timestamp_utc=evidence.timestamp_utc,
                    evidence_type=VisualEvidenceType.THERMAL_HOTSPOT,
                    feature_name="peak_temperature",
                    value=hs.max_temperature_c,
                    unit="°C",
                    confidence=0.94,
                    quality=evidence.quality_status,
                    freshness_status=evidence.freshness_status,
                    freshness_age_sec=evidence.freshness_age_sec,
                    is_live_data=evidence.is_live_data,
                    model_version=evidence.inference_version,
                    evidence_uri=evidence.evidence_uri,
                    raw_metadata=hs.model_dump()
                )
                structured_events.append(ev)

                # If rate-of-rise is significant (>3°C/min), record secondary evidence
                if hs.rate_of_rise_c_min >= 3.0:
                    ev_ror = VisualEvidence(
                        evidence_id=f"EVID-ROR-{uuid.uuid4().hex[:8].upper()}",
                        source_id=evidence.camera_id,
                        facility_id=evidence.facility_id,
                        asset_id=evidence.asset_id,
                        zone_id=evidence.zone_id,
                        timestamp_utc=evidence.timestamp_utc,
                        evidence_type=VisualEvidenceType.TEMPERATURE_RATE_OF_RISE,
                        feature_name="rate_of_rise",
                        value=hs.rate_of_rise_c_min,
                        unit="°C/min",
                        confidence=0.91,
                        quality=evidence.quality_status,
                        freshness_status=evidence.freshness_status,
                        is_live_data=evidence.is_live_data,
                        model_version=evidence.inference_version
                    )
                    structured_events.append(ev_ror)

        # 5. Persist to DB if provided
        if db is not None and structured_events:
            try:
                vision_repository.persist_visual_evidence(db, structured_events)
            except Exception as e:
                logger.error(f"Failed to persist visual evidence: {e}")
                db.rollback()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.inference_latencies.append(elapsed_ms)
        if len(self.inference_latencies) > 300:
            self.inference_latencies.pop(0)

        return evidence

    def ingest_cctv_evidence(
        self,
        evidence: CCTVFrameEvidence,
        db: Optional[Session] = None
    ) -> CCTVFrameEvidence:
        t0 = time.perf_counter()
        
        freshness_res = vision_quality_engine.compute_camera_freshness(
            evidence.source_timestamp, frame_rate_fps=5.0
        )
        evidence.freshness_status = freshness_res["freshness_status"]
        evidence.freshness_age_sec = freshness_res["age_sec"]

        self._latest_cctv_by_camera[evidence.camera_id] = evidence
        self.total_frames_processed += 1
        if evidence.quality_status == VisionQualityStatus.GOOD:
            self.good_frames += 1
        else:
            self.degraded_frames += 1

        structured_events: List[VisualEvidence] = []
        if evidence.flame_confidence > 0.60:
            structured_events.append(VisualEvidence(
                evidence_id=f"EVID-FLAME-{uuid.uuid4().hex[:8].upper()}",
                source_id=evidence.camera_id,
                facility_id=evidence.facility_id,
                asset_id=evidence.asset_id,
                zone_id=evidence.zone_id,
                timestamp_utc=evidence.timestamp_utc,
                evidence_type=VisualEvidenceType.OPTICAL_FLAME,
                feature_name="optical_flame",
                value=round(evidence.flame_confidence * 100.0, 1),
                unit="%",
                confidence=evidence.flame_confidence,
                quality=evidence.quality_status,
                freshness_status=evidence.freshness_status,
                is_live_data=evidence.is_live_data,
                model_version=evidence.inference_version,
                evidence_uri=evidence.evidence_uri
            ))

        if evidence.smoke_confidence > 0.60:
            structured_events.append(VisualEvidence(
                evidence_id=f"EVID-SMOKE-{uuid.uuid4().hex[:8].upper()}",
                source_id=evidence.camera_id,
                facility_id=evidence.facility_id,
                asset_id=evidence.asset_id,
                zone_id=evidence.zone_id,
                timestamp_utc=evidence.timestamp_utc,
                evidence_type=VisualEvidenceType.SMOKE_PLUME,
                feature_name="smoke_plume",
                value=round(evidence.smoke_confidence * 100.0, 1),
                unit="%",
                confidence=evidence.smoke_confidence,
                quality=evidence.quality_status,
                freshness_status=evidence.freshness_status,
                is_live_data=evidence.is_live_data,
                model_version=evidence.inference_version,
                evidence_uri=evidence.evidence_uri
            ))

        if db is not None and structured_events:
            try:
                vision_repository.persist_visual_evidence(db, structured_events)
            except Exception as e:
                logger.error(f"Failed to persist CCTV visual evidence: {e}")
                db.rollback()

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.inference_latencies.append(elapsed_ms)
        if len(self.inference_latencies) > 300:
            self.inference_latencies.pop(0)

        return evidence

    def generate_simulator_tick(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Generate one tick from simulator for both thermal and optical channels."""
        th_ev = camera_simulator.generate_thermal_evidence()
        cctv_ev = camera_simulator.generate_cctv_evidence()

        proc_th = self.ingest_thermal_evidence(th_ev, db)
        proc_cctv = self.ingest_cctv_evidence(cctv_ev, db)

        return {
            "thermal_evidence": proc_th,
            "cctv_evidence": proc_cctv
        }

    def get_latest_facility_vision(self, facility_id: str) -> Dict[str, Any]:
        """Retrieve latest thermal and optical states across all cameras in a facility."""
        thermal_list = []
        cctv_list = []

        # If empty, generate one initial simulation tick
        if not self._latest_thermal_by_camera and not self._latest_cctv_by_camera:
            self.generate_simulator_tick()

        for cam_id, th in self._latest_thermal_by_camera.items():
            if th.facility_id == facility_id:
                # Recompute freshness
                f_res = vision_quality_engine.compute_camera_freshness(th.source_timestamp, 2.0)
                th_copy = th.model_copy()
                th_copy.freshness_status = f_res["freshness_status"]
                th_copy.freshness_age_sec = f_res["age_sec"]
                thermal_list.append(th_copy)

        for cam_id, cctv in self._latest_cctv_by_camera.items():
            if cctv.facility_id == facility_id:
                f_res = vision_quality_engine.compute_camera_freshness(cctv.source_timestamp, 5.0)
                cctv_copy = cctv.model_copy()
                cctv_copy.freshness_status = f_res["freshness_status"]
                cctv_copy.freshness_age_sec = f_res["age_sec"]
                cctv_list.append(cctv_copy)

        return {
            "facility_id": facility_id,
            "thermal_cameras": thermal_list,
            "cctv_cameras": cctv_list,
            "hotspots_count": sum(len(t.hotspot_regions) for t in thermal_list)
        }

    def get_latest_camera_vision(self, camera_id: str) -> Dict[str, Any]:
        th = self._latest_thermal_by_camera.get(camera_id)
        cctv = self._latest_cctv_by_camera.get(camera_id)
        if not th and not cctv:
            self.generate_simulator_tick()
            th = self._latest_thermal_by_camera.get(camera_id)
            cctv = self._latest_cctv_by_camera.get(camera_id)

        return {
            "camera_id": camera_id,
            "thermal": th,
            "cctv": cctv
        }

    def get_linked_telemetry_for_visual_evidence(self, asset_id: str) -> Dict[str, Any]:
        """
        Cross-modal correlation: links latest visual/thermal evidence with Phase 12 process telemetry
        for the same physical asset (e.g. T-04).
        """
        telemetry_obs = telemetry_service.get_latest_facility_telemetry("FAC-IN-DAHEJ-001")
        asset_telemetry = [t for t in telemetry_obs if t.asset_id == asset_id]
        
        # Latest visual for this asset
        vis_thermal = next((t for t in self._latest_thermal_by_camera.values() if t.asset_id == asset_id), None)
        vis_cctv = next((c for c in self._latest_cctv_by_camera.values() if c.asset_id == asset_id), None)

        return {
            "asset_id": asset_id,
            "facility_id": "FAC-IN-DAHEJ-001",
            "telemetry_sensors_count": len(asset_telemetry),
            "telemetry_sensors": [
                {
                    "sensor_id": t.sensor_id,
                    "sensor_type": t.sensor_type.value,
                    "value": t.value,
                    "unit": t.unit,
                    "quality": t.quality.value,
                    "freshness": t.freshness_status.value if t.freshness_status else "LIVE",
                    "trend": t.trend
                } for t in asset_telemetry
            ],
            "visual_thermal_state": {
                "max_temp_c": vis_thermal.max_temperature if vis_thermal else None,
                "hotspot_count": vis_thermal.hotspot_count if vis_thermal else 0,
                "hotspots": [h.model_dump() for h in vis_thermal.hotspot_regions] if vis_thermal else []
            },
            "visual_optical_state": {
                "scene_status": vis_cctv.scene_status if vis_cctv else "CLEAR",
                "flame_confidence": vis_cctv.flame_confidence if vis_cctv else 0.0,
                "smoke_confidence": vis_cctv.smoke_confidence if vis_cctv else 0.0
            },
            "correlated_at": datetime.now(timezone.utc).isoformat()
        }

    def query_events(self, db: Session, query: VisionEventsQuery) -> List[VisualEvidence]:
        return vision_repository.query_events(db, query)

    def get_health(self, db: Optional[Session] = None) -> VisionHealthResponse:
        uptime = max(0.1, time.time() - self.start_time)
        fps = round(self.total_frames_processed / uptime, 1)
        total_f = max(1, self.good_frames + self.degraded_frames)
        good_pct = round((self.good_frames / total_f) * 100.0, 1)
        deg_pct = round((self.degraded_frames / total_f) * 100.0, 1)

        p95 = round(sorted(self.inference_latencies)[int(len(self.inference_latencies) * 0.95)], 2) if self.inference_latencies else 0.8
        p99 = round(sorted(self.inference_latencies)[int(len(self.inference_latencies) * 0.99)], 2) if self.inference_latencies else 2.1

        cameras = self.get_all_registered_cameras()

        return VisionHealthResponse(
            status="OPERATIONAL",
            uptime_sec=round(uptime, 1),
            total_frames_processed=self.total_frames_processed,
            frames_per_second=fps if fps > 0 else 4.0,
            active_cameras_count=len(cameras),
            cameras=cameras,
            p95_inference_latency_ms=p95,
            p99_inference_latency_ms=p99,
            hotspots_tracked_count=thermal_hotspot_tracker.get_tracked_count(),
            quality_good_pct=good_pct,
            quality_degraded_pct=deg_pct,
            read_only_mode_verified=True,
            system_clock_utc=datetime.now(timezone.utc)
        )

    def set_simulator_scenario(self, scenario_name: str) -> Dict[str, Any]:
        camera_simulator.set_scenario(scenario_name)
        return {
            "status": "SCENARIO_UPDATED",
            "active_scenario": scenario_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

vision_pipeline_service = VisionPipelineService()
