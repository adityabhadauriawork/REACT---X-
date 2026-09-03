import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.vision_models import CameraMetadataModel, VisualEvidenceRecord
from app.schemas.vision import (
    VisualEvidence, CameraMetadata, VisionEventsQuery,
    CameraType, CameraStatus, VisualEvidenceType, VisionQualityStatus, VisionFreshnessStatus
)

class VisionRepository:
    """
    DAO repository for camera metadata registration, structured visual evidence persistence,
    and historical event time-window queries.
    """

    def persist_visual_evidence(self, db: Session, evidence_list: List[VisualEvidence]) -> int:
        if not evidence_list:
            return 0
        records = []
        for ev in evidence_list:
            rec = VisualEvidenceRecord(
                evidence_id=ev.evidence_id or f"EVID-{uuid.uuid4().hex[:10].upper()}",
                source_id=ev.source_id,
                facility_id=ev.facility_id,
                asset_id=ev.asset_id,
                zone_id=ev.zone_id,
                timestamp_utc=ev.timestamp_utc,
                evidence_type=ev.evidence_type.value if hasattr(ev.evidence_type, "value") else str(ev.evidence_type),
                feature_name=ev.feature_name,
                value=ev.value,
                unit=ev.unit,
                confidence=ev.confidence,
                quality=ev.quality.value if hasattr(ev.quality, "value") else str(ev.quality),
                freshness_status=ev.freshness_status.value if hasattr(ev.freshness_status, "value") else str(ev.freshness_status),
                is_live_data=ev.is_live_data,
                model_version=ev.model_version,
                evidence_uri=ev.evidence_uri,
                raw_metadata_json=ev.raw_metadata or {}
            )
            records.append(rec)
        db.bulk_save_objects(records)
        db.commit()
        return len(records)

    def query_events(self, db: Session, query: VisionEventsQuery) -> List[VisualEvidence]:
        q = db.query(VisualEvidenceRecord)
        if query.facility_id:
            q = q.filter(VisualEvidenceRecord.facility_id == query.facility_id)
        if query.camera_id:
            q = q.filter(VisualEvidenceRecord.source_id == query.camera_id)
        if query.asset_id:
            q = q.filter(VisualEvidenceRecord.asset_id == query.asset_id)
        if query.zone_id:
            q = q.filter(VisualEvidenceRecord.zone_id == query.zone_id)
        if query.evidence_type:
            type_str = query.evidence_type.value if hasattr(query.evidence_type, "value") else str(query.evidence_type)
            q = q.filter(VisualEvidenceRecord.evidence_type == type_str)
        if query.start_time:
            q = q.filter(VisualEvidenceRecord.timestamp_utc >= query.start_time)
        if query.end_time:
            q = q.filter(VisualEvidenceRecord.timestamp_utc <= query.end_time)
        if query.min_confidence is not None:
            q = q.filter(VisualEvidenceRecord.confidence >= query.min_confidence)

        q = q.order_by(desc(VisualEvidenceRecord.timestamp_utc))
        records = q.offset(query.offset).limit(query.limit).all()

        results = []
        for r in records:
            results.append(VisualEvidence(
                evidence_id=r.evidence_id,
                source_id=r.source_id,
                facility_id=r.facility_id,
                asset_id=r.asset_id,
                zone_id=r.zone_id,
                timestamp_utc=r.timestamp_utc.replace(tzinfo=timezone.utc) if r.timestamp_utc.tzinfo is None else r.timestamp_utc,
                evidence_type=VisualEvidenceType(r.evidence_type) if r.evidence_type in VisualEvidenceType.__members__ else VisualEvidenceType.THERMAL_HOTSPOT,
                feature_name=r.feature_name,
                value=r.value,
                unit=r.unit,
                confidence=r.confidence,
                quality=VisionQualityStatus(r.quality) if r.quality in VisionQualityStatus.__members__ else VisionQualityStatus.GOOD,
                freshness_status=VisionFreshnessStatus(r.freshness_status) if r.freshness_status in VisionFreshnessStatus.__members__ else VisionFreshnessStatus.LIVE,
                is_live_data=r.is_live_data,
                model_version=r.model_version,
                evidence_uri=r.evidence_uri,
                raw_metadata=r.raw_metadata_json or {}
            ))
        return results

    def register_camera(self, db: Session, meta: CameraMetadata) -> CameraMetadataModel:
        existing = db.query(CameraMetadataModel).filter(CameraMetadataModel.camera_id == meta.camera_id).first()
        if existing:
            for k, v in meta.model_dump().items():
                if hasattr(existing, k):
                    setattr(existing, k, v.value if hasattr(v, "value") else v)
            db.commit()
            return existing

        m = CameraMetadataModel(
            camera_id=meta.camera_id,
            facility_id=meta.facility_id,
            asset_id=meta.asset_id,
            zone_id=meta.zone_id,
            camera_type=meta.camera_type.value if hasattr(meta.camera_type, "value") else str(meta.camera_type),
            location_desc=meta.location_desc,
            orientation_azimuth_deg=meta.orientation_azimuth_deg,
            resolution_w=meta.resolution_w,
            resolution_h=meta.resolution_h,
            frame_rate_fps=meta.frame_rate_fps,
            status=meta.status.value if hasattr(meta.status, "value") else str(meta.status),
            last_seen_at=meta.last_seen_at,
            temperature_measurement_capability=meta.temperature_measurement_capability,
            thermal_range_min_c=meta.thermal_range_min_c,
            thermal_range_max_c=meta.thermal_range_max_c,
            calibration_reference=meta.calibration_reference,
            calibration_date=meta.calibration_date,
            source_stream_url=meta.source_stream_url
        )
        db.add(m)
        db.commit()
        return m

    def get_cameras(self, db: Session, facility_id: Optional[str] = None) -> List[CameraMetadataModel]:
        q = db.query(CameraMetadataModel)
        if facility_id:
            q = q.filter(CameraMetadataModel.facility_id == facility_id)
        return q.all()

vision_repository = VisionRepository()
