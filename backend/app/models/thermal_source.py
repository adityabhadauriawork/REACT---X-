import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, ForeignKey
from app.core.database import Base

class ThermalSourceModel(Base):
    __tablename__ = "thermal_source_objects"

    source_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    
    # Spatio-Temporal Observables
    centroid_lat = Column(Float, nullable=False, index=True)
    centroid_lon = Column(Float, nullable=False, index=True)
    h3_index = Column(String, index=True, nullable=False)  # Uber H3 Res 7
    bounding_box = Column(JSON, nullable=True)  # [min_lon, min_lat, max_lon, max_lat]
    
    first_detected = Column(DateTime, index=True, nullable=False)
    last_detected = Column(DateTime, index=True, nullable=False)
    active_days_count = Column(Integer, default=1)
    observation_count = Column(Integer, default=1, index=True)
    unique_satellite_count = Column(Integer, default=1)
    unique_sensor_count = Column(Integer, default=1)
    satellites_seen = Column(JSON, default=list)
    sensors_seen = Column(JSON, default=list)
    
    # Radiometry & Temporal Statistics
    mean_frp_mw = Column(Float, default=0.0)
    max_frp_mw = Column(Float, default=0.0)
    min_frp_mw = Column(Float, default=0.0)
    mean_brightness_temp_k = Column(Float, nullable=True)
    max_brightness_temp_k = Column(Float, nullable=True)
    
    day_detection_count = Column(Integer, default=0)
    night_detection_count = Column(Integer, default=0)
    diurnal_ratio = Column(Float, default=1.0)
    
    # Lifecycle & Source Status
    source_status = Column(String, default="NEW_SOURCE", index=True)  # NEW_SOURCE, RECURRING_SOURCE, PERSISTENT_SOURCE, INACTIVE_SOURCE, UNCLASSIFIED_SOURCE
    source_confidence = Column(String, default="NOMINAL", index=True)  # HIGH, NOMINAL, LOW
    source_provenance = Column(String, default="LIVE_FIRMS", index=True)  # LIVE_FIRMS, HISTORICAL_CLUSTER, BENCHMARK
    source_version = Column(String, default="v1.0")
    
    # Industrial Context Attribution
    primary_attributed_facility_id = Column(String, nullable=True, index=True)
    primary_attributed_facility_name = Column(String, nullable=True)
    facility_distance_m = Column(Float, nullable=True)
    is_inside_facility_boundary = Column(Boolean, default=False)
    facility_attribution_confidence = Column(Float, nullable=True)
    attribution_status = Column(String, default="UNATTRIBUTED", index=True)  # ATTRIBUTED_HIGH_CONFIDENCE, ATTRIBUTED_MEDIUM_CONFIDENCE, MULTIPLE_CANDIDATES, UNATTRIBUTED, INSUFFICIENT_DATA
    
    # NASA Static Thermal Anomaly Overlay
    static_firms_anomaly_overlap = Column(Boolean, default=False, index=True)
    land_cover_class = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_source_lat_lon", "centroid_lat", "centroid_lon"),
        Index("idx_source_h3_status", "h3_index", "source_status"),
        Index("idx_source_detected_range", "first_detected", "last_detected"),
    )

class ThermalSourceEventModel(Base):
    __tablename__ = "thermal_source_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, ForeignKey("thermal_source_objects.source_id", ondelete="CASCADE"), index=True, nullable=False)
    event_id = Column(String, index=True, nullable=False)
    
    # Event Snapshot
    acquisition_timestamp = Column(DateTime, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    frp_mw = Column(Float, nullable=False)
    brightness_temp_k = Column(Float, nullable=True)
    satellite = Column(String, nullable=False)
    sensor = Column(String, nullable=False)
    day_night = Column(String, default="D")
    attached_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_src_event_link", "source_id", "event_id"),
    )

class SourceFacilityCandidateModel(Base):
    __tablename__ = "thermal_source_facility_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, ForeignKey("thermal_source_objects.source_id", ondelete="CASCADE"), index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=False)
    facility_name = Column(String, nullable=False)
    rank = Column(Integer, default=1)  # 1 for closest/highest confidence
    distance_m = Column(Float, nullable=False)
    is_inside_boundary = Column(Boolean, default=False)
    attribution_confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    evidence_summary = Column(String, nullable=True)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_src_fac_rank", "source_id", "rank"),
    )
