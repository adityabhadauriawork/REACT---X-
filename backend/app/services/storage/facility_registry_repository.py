from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.national_registry_models import (
    NationalFacilityRegistryRecord,
    FacilitySensorConfigRecord,
    FacilityCameraConfigRecord
)
from app.schemas.facility_config import (
    FacilityConfig, FacilityType, FacilityConnectivityStatus,
    FacilityBaselineStage, HazardProfileType, FacilityCapability,
    DataProvenance, AreaConfig, SensorConfig, CameraConfig
)

class FacilityRegistryRepository:
    """
    DAO repository for managing national facility registry, configurations, and spatial indexing.
    """

    def upsert_facility(self, db: Session, cfg: FacilityConfig) -> NationalFacilityRegistryRecord:
        rec = db.query(NationalFacilityRegistryRecord).filter(
            NationalFacilityRegistryRecord.facility_id == cfg.facility_id
        ).first()

        now_utc = datetime.now(timezone.utc)
        hp_vals = [h.value if hasattr(h, "value") else str(h) for h in cfg.hazard_profile]
        cap_vals = [c.value if hasattr(c, "value") else str(c) for c in cfg.capabilities]
        areas_dict = [a.model_dump(mode="json") for a in cfg.areas] if cfg.areas else []

        if not rec:
            rec = NationalFacilityRegistryRecord(
                facility_id=cfg.facility_id,
                facility_name=cfg.facility_name,
                facility_type=cfg.facility_type.value if hasattr(cfg.facility_type, "value") else str(cfg.facility_type),
                country=cfg.country,
                state=cfg.state,
                district=cfg.district,
                city_locality=cfg.city_locality,
                latitude=cfg.latitude,
                longitude=cfg.longitude,
                boundary_polygon_json=cfg.boundary_polygon,
                criticality=cfg.criticality,
                hazard_profile_json=hp_vals,
                capabilities_json=cap_vals,
                connectivity_status=cfg.connectivity_status.value if hasattr(cfg.connectivity_status, "value") else str(cfg.connectivity_status),
                baseline_stage=cfg.baseline_stage.value if hasattr(cfg.baseline_stage, "value") else str(cfg.baseline_stage),
                provenance_json=cfg.provenance.model_dump(mode="json") if cfg.provenance else {},
                areas_hierarchy_json=areas_dict,
                enabled=cfg.enabled,
                is_reference_environment=cfg.is_reference_environment,
                is_simulated=cfg.is_simulated,
                created_at=now_utc,
                updated_at=now_utc
            )
            db.add(rec)
        else:
            rec.facility_name = cfg.facility_name
            rec.facility_type = cfg.facility_type.value if hasattr(cfg.facility_type, "value") else str(cfg.facility_type)
            rec.state = cfg.state
            rec.district = cfg.district
            rec.city_locality = cfg.city_locality
            rec.latitude = cfg.latitude
            rec.longitude = cfg.longitude
            rec.boundary_polygon_json = cfg.boundary_polygon
            rec.criticality = cfg.criticality
            rec.hazard_profile_json = hp_vals
            rec.capabilities_json = cap_vals
            rec.connectivity_status = cfg.connectivity_status.value if hasattr(cfg.connectivity_status, "value") else str(cfg.connectivity_status)
            rec.baseline_stage = cfg.baseline_stage.value if hasattr(cfg.baseline_stage, "value") else str(cfg.baseline_stage)
            rec.provenance_json = cfg.provenance.model_dump(mode="json") if cfg.provenance else {}
            rec.areas_hierarchy_json = areas_dict
            rec.enabled = cfg.enabled
            rec.is_reference_environment = cfg.is_reference_environment
            rec.is_simulated = cfg.is_simulated
            rec.updated_at = now_utc

        db.commit()
        db.refresh(rec)
        return rec

    def get_facility(self, db: Session, facility_id: str) -> Optional[FacilityConfig]:
        rec = db.query(NationalFacilityRegistryRecord).filter(
            NationalFacilityRegistryRecord.facility_id == facility_id
        ).first()
        if not rec:
            return None
        return self._record_to_schema(rec)

    def list_facilities(
        self,
        db: Session,
        state: Optional[str] = None,
        district: Optional[str] = None,
        facility_type: Optional[str] = None,
        connectivity_status: Optional[str] = None,
        baseline_stage: Optional[str] = None,
        bbox: Optional[Tuple[float, float, float, float]] = None,  # (min_lat, min_lon, max_lat, max_lon)
        enabled_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[FacilityConfig]:
        q = db.query(NationalFacilityRegistryRecord)
        if enabled_only:
            q = q.filter(NationalFacilityRegistryRecord.enabled == True)
        if state:
            q = q.filter(NationalFacilityRegistryRecord.state == state)
        if district:
            q = q.filter(NationalFacilityRegistryRecord.district == district)
        if facility_type:
            q = q.filter(NationalFacilityRegistryRecord.facility_type == facility_type)
        if connectivity_status:
            q = q.filter(NationalFacilityRegistryRecord.connectivity_status == connectivity_status)
        if baseline_stage:
            q = q.filter(NationalFacilityRegistryRecord.baseline_stage == baseline_stage)
        if bbox:
            min_lat, min_lon, max_lat, max_lon = bbox
            q = q.filter(
                NationalFacilityRegistryRecord.latitude >= min_lat,
                NationalFacilityRegistryRecord.latitude <= max_lat,
                NationalFacilityRegistryRecord.longitude >= min_lon,
                NationalFacilityRegistryRecord.longitude <= max_lon
            )

        records = q.order_by(NationalFacilityRegistryRecord.facility_id).offset(offset).limit(limit).all()
        return [self._record_to_schema(r) for r in records]

    def update_baseline_stage(self, db: Session, facility_id: str, stage: FacilityBaselineStage) -> Optional[FacilityConfig]:
        rec = db.query(NationalFacilityRegistryRecord).filter(
            NationalFacilityRegistryRecord.facility_id == facility_id
        ).first()
        if not rec:
            return None
        rec.baseline_stage = stage.value if hasattr(stage, "value") else str(stage)
        rec.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rec)
        return self._record_to_schema(rec)

    def count_facilities_by_state(self, db: Session) -> Dict[str, int]:
        rows = db.query(
            NationalFacilityRegistryRecord.state,
            func.count(NationalFacilityRegistryRecord.facility_id)
        ).group_by(NationalFacilityRegistryRecord.state).all()
        return {r[0]: r[1] for r in rows}

    def count_facilities_by_industry(self, db: Session) -> Dict[str, int]:
        rows = db.query(
            NationalFacilityRegistryRecord.facility_type,
            func.count(NationalFacilityRegistryRecord.facility_id)
        ).group_by(NationalFacilityRegistryRecord.facility_type).all()
        return {r[0]: r[1] for r in rows}

    def count_facilities_by_connectivity(self, db: Session) -> Dict[str, int]:
        rows = db.query(
            NationalFacilityRegistryRecord.connectivity_status,
            func.count(NationalFacilityRegistryRecord.facility_id)
        ).group_by(NationalFacilityRegistryRecord.connectivity_status).all()
        return {r[0]: r[1] for r in rows}

    def _record_to_schema(self, rec: NationalFacilityRegistryRecord) -> FacilityConfig:
        ft = FacilityType(rec.facility_type) if rec.facility_type in FacilityType.__members__ else FacilityType.OTHER
        conn = FacilityConnectivityStatus(rec.connectivity_status) if rec.connectivity_status in FacilityConnectivityStatus.__members__ else FacilityConnectivityStatus.SATELLITE_ONLY
        stage = FacilityBaselineStage(rec.baseline_stage) if rec.baseline_stage in FacilityBaselineStage.__members__ else FacilityBaselineStage.CONTEXT_ONLY

        hp = []
        for h in (rec.hazard_profile_json or []):
            if h in HazardProfileType.__members__:
                hp.append(HazardProfileType(h))

        caps = []
        for c in (rec.capabilities_json or []):
            if c in FacilityCapability.__members__:
                caps.append(FacilityCapability(c))

        prov = DataProvenance(**rec.provenance_json) if rec.provenance_json else DataProvenance()
        areas = [AreaConfig(**a) for a in (rec.areas_hierarchy_json or [])]

        return FacilityConfig(
            facility_id=rec.facility_id,
            facility_name=rec.facility_name,
            facility_type=ft,
            country=rec.country,
            state=rec.state,
            district=rec.district,
            city_locality=rec.city_locality,
            latitude=rec.latitude,
            longitude=rec.longitude,
            boundary_polygon=rec.boundary_polygon_json,
            criticality=rec.criticality,
            hazard_profile=hp,
            capabilities=caps,
            connectivity_status=conn,
            baseline_stage=stage,
            provenance=prov,
            enabled=rec.enabled,
            is_reference_environment=rec.is_reference_environment,
            is_simulated=rec.is_simulated,
            areas=areas
        )

facility_registry_repository = FacilityRegistryRepository()
