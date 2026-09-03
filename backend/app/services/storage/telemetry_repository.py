import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.telemetry_models import (
    FacilityTelemetryRecord, SensorMetadataModel, EdgeGatewayModel
)
from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, EdgeGateway,
    TelemetryHistoryQuery, TelemetryQuality, SensorType, SourceProtocol, GatewayStatus, DataQualityFlag
)

class TelemetryRepository:
    """
    DAO repository for industrial facility telemetry persistence, metadata catalog, and historical querying.
    Supports high-throughput batch inserts and indexed time-range scans.
    """

    def persist_observations(self, db: Session, observations: List[FacilityTelemetryObservation]) -> int:
        """Batch persist normalized telemetry observations into durable history."""
        if not observations:
            return 0
        records = []
        for obs in observations:
            rec = FacilityTelemetryRecord(
                telemetry_id=obs.telemetry_id or f"TEL-{uuid.uuid4().hex[:12].upper()}",
                facility_id=obs.facility_id,
                plant_area=obs.plant_area,
                unit_id=obs.unit_id,
                asset_id=obs.asset_id,
                gateway_id=obs.gateway_id,
                sensor_id=obs.sensor_id,
                sensor_type=obs.sensor_type.value if hasattr(obs.sensor_type, "value") else str(obs.sensor_type),
                tag_name=obs.tag_name,
                timestamp_utc=obs.timestamp_utc,
                value=obs.value,
                unit=obs.unit,
                quality=obs.quality.value if hasattr(obs.quality, "value") else str(obs.quality),
                source_protocol=obs.source_protocol.value if hasattr(obs.source_protocol, "value") else str(obs.source_protocol),
                source_timestamp=obs.source_timestamp,
                acquisition_timestamp=obs.acquisition_timestamp,
                ingestion_timestamp=obs.ingestion_timestamp or datetime.now(timezone.utc),
                processing_timestamp=obs.processing_timestamp,
                sequence_number=obs.sequence_number,
                is_live_data=obs.is_live_data,
                data_quality_status=obs.data_quality_status,
                data_quality_flags=[f.value if hasattr(f, "value") else str(f) for f in obs.data_quality_flags],
                freshness_status=obs.freshness_status.value if hasattr(obs.freshness_status, "value") else str(obs.freshness_status or "LIVE"),
                trend=obs.trend or "STABLE"
            )
            records.append(rec)
        db.bulk_save_objects(records)
        db.commit()
        return len(records)

    def query_history(self, db: Session, query: TelemetryHistoryQuery) -> List[FacilityTelemetryObservation]:
        """Fetch historical records with time-window filtering and pagination."""
        q = db.query(FacilityTelemetryRecord)
        
        if query.facility_id:
            q = q.filter(FacilityTelemetryRecord.facility_id == query.facility_id)
        if query.asset_id:
            q = q.filter(FacilityTelemetryRecord.asset_id == query.asset_id)
        if query.sensor_id:
            q = q.filter(FacilityTelemetryRecord.sensor_id == query.sensor_id)
        if query.sensor_type:
            stype_str = query.sensor_type.value if hasattr(query.sensor_type, "value") else str(query.sensor_type)
            q = q.filter(FacilityTelemetryRecord.sensor_type == stype_str)
        if query.start_time:
            q = q.filter(FacilityTelemetryRecord.timestamp_utc >= query.start_time)
        if query.end_time:
            q = q.filter(FacilityTelemetryRecord.timestamp_utc <= query.end_time)
        if query.quality:
            qual_str = query.quality.value if hasattr(query.quality, "value") else str(query.quality)
            q = q.filter(FacilityTelemetryRecord.quality == qual_str)

        q = q.order_by(desc(FacilityTelemetryRecord.timestamp_utc))
        records = q.offset(query.offset).limit(query.limit).all()

        results = []
        for r in records:
            flags = []
            if isinstance(r.data_quality_flags, list):
                for flag_str in r.data_quality_flags:
                    try:
                        flags.append(DataQualityFlag(flag_str))
                    except Exception:
                        flags.append(DataQualityFlag.NONE)
            if not flags:
                flags = [DataQualityFlag.NONE]

            results.append(FacilityTelemetryObservation(
                telemetry_id=r.telemetry_id,
                facility_id=r.facility_id,
                plant_area=r.plant_area,
                unit_id=r.unit_id,
                asset_id=r.asset_id,
                gateway_id=r.gateway_id,
                sensor_id=r.sensor_id,
                sensor_type=SensorType(r.sensor_type) if r.sensor_type in SensorType.__members__ else SensorType.TEMPERATURE,
                tag_name=r.tag_name,
                timestamp_utc=r.timestamp_utc.replace(tzinfo=timezone.utc) if r.timestamp_utc.tzinfo is None else r.timestamp_utc,
                value=r.value,
                unit=r.unit,
                quality=TelemetryQuality(r.quality) if r.quality in TelemetryQuality.__members__ else TelemetryQuality.GOOD,
                source_protocol=SourceProtocol(r.source_protocol) if r.source_protocol in SourceProtocol.__members__ else SourceProtocol.SIMULATED_GATEWAY,
                source_timestamp=r.source_timestamp.replace(tzinfo=timezone.utc) if r.source_timestamp.tzinfo is None else r.source_timestamp,
                acquisition_timestamp=r.acquisition_timestamp,
                ingestion_timestamp=r.ingestion_timestamp.replace(tzinfo=timezone.utc) if r.ingestion_timestamp and r.ingestion_timestamp.tzinfo is None else r.ingestion_timestamp,
                processing_timestamp=r.processing_timestamp,
                sequence_number=r.sequence_number,
                is_live_data=r.is_live_data,
                data_quality_status=r.data_quality_status,
                data_quality_flags=flags,
                freshness_status=r.freshness_status,
                trend=r.trend
            ))
        return results

    def get_latest_for_sensor(self, db: Session, sensor_id: str) -> Optional[FacilityTelemetryObservation]:
        """Fetch the most recent persisted observation for a sensor."""
        rec = db.query(FacilityTelemetryRecord).filter(
            FacilityTelemetryRecord.sensor_id == sensor_id
        ).order_by(desc(FacilityTelemetryRecord.timestamp_utc)).first()

        if not rec:
            return None
        
        flags = [DataQualityFlag.NONE]
        if isinstance(rec.data_quality_flags, list):
            flags = [DataQualityFlag(f) for f in rec.data_quality_flags if f in DataQualityFlag.__members__] or [DataQualityFlag.NONE]

        return FacilityTelemetryObservation(
            telemetry_id=rec.telemetry_id,
            facility_id=rec.facility_id,
            plant_area=rec.plant_area,
            unit_id=rec.unit_id,
            asset_id=rec.asset_id,
            gateway_id=rec.gateway_id,
            sensor_id=rec.sensor_id,
            sensor_type=SensorType(rec.sensor_type) if rec.sensor_type in SensorType.__members__ else SensorType.TEMPERATURE,
            tag_name=rec.tag_name,
            timestamp_utc=rec.timestamp_utc.replace(tzinfo=timezone.utc) if rec.timestamp_utc.tzinfo is None else rec.timestamp_utc,
            value=rec.value,
            unit=rec.unit,
            quality=TelemetryQuality(rec.quality) if rec.quality in TelemetryQuality.__members__ else TelemetryQuality.GOOD,
            source_protocol=SourceProtocol(rec.source_protocol) if rec.source_protocol in SourceProtocol.__members__ else SourceProtocol.SIMULATED_GATEWAY,
            source_timestamp=rec.source_timestamp.replace(tzinfo=timezone.utc) if rec.source_timestamp.tzinfo is None else rec.source_timestamp,
            acquisition_timestamp=rec.acquisition_timestamp,
            ingestion_timestamp=rec.ingestion_timestamp,
            processing_timestamp=rec.processing_timestamp,
            sequence_number=rec.sequence_number,
            is_live_data=rec.is_live_data,
            data_quality_status=rec.data_quality_status,
            data_quality_flags=flags,
            freshness_status=rec.freshness_status,
            trend=rec.trend
        )

    def register_sensor(self, db: Session, meta: SensorMetadata) -> SensorMetadataModel:
        """Register or update a sensor in the metadata catalog."""
        existing = db.query(SensorMetadataModel).filter(SensorMetadataModel.sensor_id == meta.sensor_id).first()
        if existing:
            for k, v in meta.model_dump().items():
                if hasattr(existing, k):
                    setattr(existing, k, v.value if hasattr(v, "value") else v)
            db.commit()
            return existing
        
        m = SensorMetadataModel(
            sensor_id=meta.sensor_id,
            facility_id=meta.facility_id,
            plant_area=meta.plant_area,
            unit_id=meta.unit_id,
            asset_id=meta.asset_id,
            tag_name=meta.tag_name,
            sensor_type=meta.sensor_type.value if hasattr(meta.sensor_type, "value") else str(meta.sensor_type),
            unit=meta.unit,
            expected_sampling_interval=meta.expected_sampling_interval,
            valid_range_min=meta.valid_range_min,
            valid_range_max=meta.valid_range_max,
            warning_min=meta.warning_min,
            warning_max=meta.warning_max,
            critical_min=meta.critical_min,
            critical_max=meta.critical_max,
            source_protocol=meta.source_protocol.value if hasattr(meta.source_protocol, "value") else str(meta.source_protocol),
            gateway_id=meta.gateway_id,
            enabled=meta.enabled,
            last_seen_at=meta.last_seen_at,
            calibration_reference=meta.calibration_reference,
            calibration_date=meta.calibration_date,
            sensor_quality_state=meta.sensor_quality_state
        )
        db.add(m)
        db.commit()
        return m

    def get_all_sensors_for_facility(self, db: Session, facility_id: str) -> List[SensorMetadataModel]:
        return db.query(SensorMetadataModel).filter(SensorMetadataModel.facility_id == facility_id).all()

    def register_gateway(self, db: Session, gw: EdgeGateway) -> EdgeGatewayModel:
        existing = db.query(EdgeGatewayModel).filter(EdgeGatewayModel.gateway_id == gw.gateway_id).first()
        if existing:
            for k, v in gw.model_dump().items():
                if hasattr(existing, k):
                    setattr(existing, k, v.value if hasattr(v, "value") else v)
            db.commit()
            return existing

        m = EdgeGatewayModel(
            gateway_id=gw.gateway_id,
            facility_id=gw.facility_id,
            protocol=gw.protocol.value if hasattr(gw.protocol, "value") else str(gw.protocol),
            endpoint=gw.endpoint,
            status=gw.status.value if hasattr(gw.status, "value") else str(gw.status),
            last_heartbeat=gw.last_heartbeat,
            firmware_version=gw.firmware_version,
            time_sync_status=gw.time_sync_status,
            buffer_count=gw.buffer_count,
            dropped_count=gw.dropped_count,
            active_sensors_count=gw.active_sensors_count
        )
        db.add(m)
        db.commit()
        return m

    def get_gateways(self, db: Session, facility_id: Optional[str] = None) -> List[EdgeGatewayModel]:
        q = db.query(EdgeGatewayModel)
        if facility_id:
            q = q.filter(EdgeGatewayModel.facility_id == facility_id)
        return q.all()

telemetry_repository = TelemetryRepository()
