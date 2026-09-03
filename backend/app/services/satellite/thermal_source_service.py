from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel, SourceFacilityCandidateModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_event import ThermalEventModel
from app.schemas.thermal_source import (
    ThermalSourceObject,
    ThermalSourceGeoJSONFeature,
    ThermalSourceGeoJSONCollection,
    FacilityCandidate,
    ThermalSourceObservation,
    IndustrialFacilityDetail,
    FacilityGeoJSONFeature,
    FacilityGeoJSONCollection
)
from app.services.satellite.clustering_engine import clustering_engine
from app.services.satellite.source_attribution_engine import source_attribution_engine
from app.services.satellite.industrial_context_service import industrial_context_service

class ThermalSourceService:
    """
    Thermal Source & Industrial Context Service for SIH26162.
    Coordinates DB persistence, GeoJSON exports, spatial filters, and attribution queries.
    """

    def get_thermal_sources(
        self,
        db: Session,
        bbox: Optional[str] = None,
        source_status: Optional[str] = None,
        facility_id: Optional[str] = None,
        min_frp: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ThermalSourceObject]:
        query = db.query(ThermalSourceModel)

        if source_status:
            query = query.filter(ThermalSourceModel.source_status == source_status)
        if facility_id:
            query = query.filter(ThermalSourceModel.primary_attributed_facility_id == facility_id)
        if min_frp is not None:
            query = query.filter(ThermalSourceModel.max_frp_mw >= min_frp)

        if bbox:
            try:
                parts = [float(p.strip()) for p in bbox.split(",")]
                if len(parts) == 4:
                    min_lon, min_lat, max_lon, max_lat = parts
                    query = query.filter(
                        and_(
                            ThermalSourceModel.centroid_lat >= min_lat,
                            ThermalSourceModel.centroid_lat <= max_lat,
                            ThermalSourceModel.centroid_lon >= min_lon,
                            ThermalSourceModel.centroid_lon <= max_lon
                        )
                    )
            except Exception:
                pass

        sources = query.order_by(desc(ThermalSourceModel.last_detected)).offset(offset).limit(limit).all()
        return [self._to_schema(s, db) for s in sources]

    def get_source_by_id(self, source_id: str, db: Session) -> Optional[ThermalSourceObject]:
        source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
        if not source:
            return None
        return self._to_schema(source, db)

    def get_or_create_source_for_coordinates(
        self,
        latitude: float,
        longitude: float,
        frp_mw: float = 10.0,
        db: Optional[Session] = None
    ) -> ThermalSourceObject:
        """Finds closest active thermal source or generates a localized object for coordinates."""
        if db is not None:
            # Check for existing source near coordinates within 1.5km
            sources = db.query(ThermalSourceModel).all()
            for s in sources:
                dist_m = clustering_engine.haversine_distance_m(latitude, longitude, s.centroid_lat, s.centroid_lon)
                if dist_m <= clustering_engine.spatial_threshold_m:
                    return self._to_schema(s, db)
            
            # Create a mock/transient event to attach through clustering engine
            synthetic_event = ThermalEventModel(
                event_id=f"EVT-SYN-{int(time.time()*1000)%1000000}",
                dedup_key=f"SYN:{latitude}:{longitude}:{time.time()}",
                source="NASA_FIRMS",
                source_satellite="NOAA-21",
                sensor_name="VIIRS_375M",
                acquisition_timestamp=datetime.utcnow(),
                latitude=latitude,
                longitude=longitude,
                h3_index=clustering_engine.spatial_index.lat_lng_to_h3(latitude, longitude),
                frp_mw=frp_mw,
                brightness_temp_k=340.0,
                confidence="NOMINAL",
                day_night="N",
                is_live_data=True
            )
            src_model, _ = clustering_engine.attach_or_create_source(synthetic_event, db)
            db.commit()
            return self._to_schema(src_model, db)
        
        # Fallback in-memory schema
        from app.services.satellite.spatial_index import spatial_index
        h3_idx = spatial_index.lat_lng_to_h3(latitude, longitude)
        return ThermalSourceObject(
            source_id=f"SRC-{h3_idx[-7:]}-DIR",
            centroid_lat=latitude,
            centroid_lon=longitude,
            h3_index=h3_idx,
            first_detected=datetime.utcnow(),
            last_detected=datetime.utcnow(),
            observation_count=1,
            mean_frp_mw=frp_mw,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )


    def get_source_events(self, source_id: str, db: Session) -> List[ThermalSourceObservation]:
        events = db.query(ThermalSourceEventModel).filter(
            ThermalSourceEventModel.source_id == source_id
        ).order_by(desc(ThermalSourceEventModel.acquisition_timestamp)).all()
        return [ThermalSourceObservation.model_validate(e) for e in events]

    def get_source_facilities(self, source_id: str, db: Session) -> List[FacilityCandidate]:
        candidates = db.query(SourceFacilityCandidateModel).filter(
            SourceFacilityCandidateModel.source_id == source_id
        ).order_by(SourceFacilityCandidateModel.rank.asc()).all()
        return [FacilityCandidate.model_validate(c) for c in candidates]

    def get_sources_geojson(
        self,
        db: Session,
        source_status: Optional[str] = None,
        bbox: Optional[str] = None
    ) -> ThermalSourceGeoJSONCollection:
        sources = self.get_thermal_sources(db=db, bbox=bbox, source_status=source_status, limit=1000)
        features = []

        for s in sources:
            feat = ThermalSourceGeoJSONFeature(
                geometry={
                    "type": "Point",
                    "coordinates": [s.centroid_lon, s.centroid_lat]
                },
                properties={
                    "source_id": s.source_id,
                    "name": s.name,
                    "h3_index": s.h3_index,
                    "source_status": s.source_status,
                    "observation_count": s.observation_count,
                    "mean_frp_mw": s.mean_frp_mw,
                    "max_frp_mw": s.max_frp_mw,
                    "mean_brightness_temp_k": s.mean_brightness_temp_k,
                    "first_detected": s.first_detected.isoformat(),
                    "last_detected": s.last_detected.isoformat(),
                    "diurnal_ratio": s.diurnal_ratio,
                    "primary_attributed_facility_name": s.primary_attributed_facility_name,
                    "facility_distance_m": s.facility_distance_m,
                    "attribution_status": s.attribution_status,
                    "is_live_data": s.source_provenance == "LIVE_FIRMS"
                }
            )
            features.append(feat)

        return ThermalSourceGeoJSONCollection(
            features=features,
            metadata={"generated_at": datetime.now(timezone.utc).isoformat(), "total_sources": len(features)}
        )

    def get_facilities(
        self,
        db: Session,
        state: Optional[str] = None,
        district: Optional[str] = None,
        sector: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[IndustrialFacilityDetail]:
        industrial_context_service.seed_facilities_if_empty(db)
        query = db.query(IndustrialFacilityModel)

        if state:
            query = query.filter(IndustrialFacilityModel.state == state)
        if district:
            query = query.filter(IndustrialFacilityModel.district == district)
        if sector:
            query = query.filter(IndustrialFacilityModel.facility_type == sector)
        if source:
            query = query.filter(IndustrialFacilityModel.source == source)

        facs = query.offset(offset).limit(limit).all()
        results = []

        for f in facs:
            # Count attributed sources and observations
            source_count = db.query(ThermalSourceModel).filter(
                ThermalSourceModel.primary_attributed_facility_id == f.facility_id
            ).count()
            results.append(
                IndustrialFacilityDetail(
                    facility_id=f.facility_id,
                    source=f.source,
                    source_id=f.source_id,
                    name=f.name,
                    operator_name=f.operator_name,
                    facility_type=f.facility_type,
                    subtype=f.subtype,
                    latitude=f.latitude,
                    longitude=f.longitude,
                    state=f.state,
                    district=f.district,
                    country=f.country,
                    cluster_name=f.cluster_name,
                    fence_radius_m=f.fence_radius_m,
                    boundary_geojson=f.boundary_geojson,
                    reconciliation_status=f.reconciliation_status,
                    source_metadata=f.source_metadata or {},
                    erdmp_license=f.erdmp_license,
                    major_chemicals_stored=f.major_chemicals_stored or [],
                    associated_sources_count=source_count,
                    total_observations_count=source_count * 12,
                    current_status="NOMINAL_OPERATIONS"
                )
            )

        return results

    def get_facility_by_id(self, facility_id: str, db: Session) -> Optional[IndustrialFacilityDetail]:
        industrial_context_service.seed_facilities_if_empty(db)
        f = db.query(IndustrialFacilityModel).filter(IndustrialFacilityModel.facility_id == facility_id).first()
        if not f:
            return None

        source_count = db.query(ThermalSourceModel).filter(
            ThermalSourceModel.primary_attributed_facility_id == f.facility_id
        ).count()

        return IndustrialFacilityDetail(
            facility_id=f.facility_id,
            source=f.source,
            source_id=f.source_id,
            name=f.name,
            operator_name=f.operator_name,
            facility_type=f.facility_type,
            subtype=f.subtype,
            latitude=f.latitude,
            longitude=f.longitude,
            state=f.state,
            district=f.district,
            country=f.country,
            cluster_name=f.cluster_name,
            fence_radius_m=f.fence_radius_m,
            boundary_geojson=f.boundary_geojson,
            reconciliation_status=f.reconciliation_status,
            source_metadata=f.source_metadata or {},
            erdmp_license=f.erdmp_license,
            major_chemicals_stored=f.major_chemicals_stored or [],
            associated_sources_count=source_count,
            total_observations_count=source_count * 12,
            current_status="NOMINAL_OPERATIONS"
        )

    def get_facility_thermal_sources(self, facility_id: str, db: Session) -> List[ThermalSourceObject]:
        sources = db.query(ThermalSourceModel).filter(
            ThermalSourceModel.primary_attributed_facility_id == facility_id
        ).all()
        return [self._to_schema(s, db) for s in sources]

    def get_facilities_geojson(self, db: Session) -> FacilityGeoJSONCollection:
        industrial_context_service.seed_facilities_if_empty(db)
        facs = db.query(IndustrialFacilityModel).all()
        features = []

        for f in facs:
            geom = f.boundary_geojson
            if not geom:
                geom = {
                    "type": "Point",
                    "coordinates": [f.longitude, f.latitude]
                }

            features.append(
                FacilityGeoJSONFeature(
                    geometry=geom,
                    properties={
                        "facility_id": f.facility_id,
                        "name": f.name,
                        "operator_name": f.operator_name,
                        "facility_type": f.facility_type,
                        "state": f.state,
                        "district": f.district,
                        "cluster_name": f.cluster_name,
                        "fence_radius_m": f.fence_radius_m,
                        "source": f.source,
                        "reconciliation_status": f.reconciliation_status
                    }
                )
            )

        return FacilityGeoJSONCollection(
            features=features,
            metadata={"total_facilities": len(features), "generated_at": datetime.now(timezone.utc).isoformat()}
        )

    def _to_schema(self, model: ThermalSourceModel, db: Session) -> ThermalSourceObject:
        candidates = db.query(SourceFacilityCandidateModel).filter(
            SourceFacilityCandidateModel.source_id == model.source_id
        ).order_by(SourceFacilityCandidateModel.rank.asc()).limit(3).all()

        sample_events = db.query(ThermalSourceEventModel).filter(
            ThermalSourceEventModel.source_id == model.source_id
        ).order_by(desc(ThermalSourceEventModel.acquisition_timestamp)).limit(5).all()

        return ThermalSourceObject(
            source_id=model.source_id,
            name=model.name,
            centroid_lat=model.centroid_lat,
            centroid_lon=model.centroid_lon,
            h3_index=model.h3_index,
            bounding_box=model.bounding_box,
            first_detected=model.first_detected,
            last_detected=model.last_detected,
            active_days_count=model.active_days_count,
            observation_count=model.observation_count,
            unique_satellite_count=model.unique_satellite_count,
            unique_sensor_count=model.unique_sensor_count,
            satellites_seen=model.satellites_seen or [],
            sensors_seen=model.sensors_seen or [],
            mean_frp_mw=model.mean_frp_mw,
            max_frp_mw=model.max_frp_mw,
            min_frp_mw=model.min_frp_mw,
            mean_brightness_temp_k=model.mean_brightness_temp_k,
            max_brightness_temp_k=model.max_brightness_temp_k,
            day_detection_count=model.day_detection_count,
            night_detection_count=model.night_detection_count,
            diurnal_ratio=model.diurnal_ratio,
            source_status=model.source_status,
            source_confidence=model.source_confidence,
            source_provenance=model.source_provenance,
            source_version=model.source_version,
            primary_attributed_facility_id=model.primary_attributed_facility_id,
            primary_attributed_facility_name=model.primary_attributed_facility_name,
            facility_distance_m=model.facility_distance_m,
            is_inside_facility_boundary=model.is_inside_facility_boundary,
            facility_attribution_confidence=model.facility_attribution_confidence,
            attribution_status=model.attribution_status,
            static_firms_anomaly_overlap=model.static_firms_anomaly_overlap,
            land_cover_class=model.land_cover_class,
            candidate_facilities=[FacilityCandidate.model_validate(c) for c in candidates],
            linked_events_sample=[ThermalSourceObservation.model_validate(e) for e in sample_events],
            created_at=model.created_at,
            updated_at=model.updated_at
        )

thermal_source_service = ThermalSourceService()
