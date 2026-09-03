import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from app.core.database import Base

class ThermalEventModel(Base):
    __tablename__ = "thermal_events"

    event_id = Column(String, primary_key=True, index=True)
    dedup_key = Column(String, unique=True, index=True, nullable=False)
    
    # Provenance
    source = Column(String, default="NASA_FIRMS", index=True, nullable=False)
    source_satellite = Column(String, index=True, nullable=False)
    sensor_name = Column(String, index=True, nullable=False)
    source_version = Column(String, nullable=True)
    
    # Spatio-Temporal Observables
    acquisition_timestamp = Column(DateTime, index=True, nullable=False)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    h3_index = Column(String, index=True, nullable=True)
    geometry_geojson = Column(JSON, nullable=True)
    
    # Radiometry & Optics
    frp_mw = Column(Float, nullable=False)
    brightness_temp_k = Column(Float, nullable=True)
    brightness_temp_i4_k = Column(Float, nullable=True)
    confidence = Column(String, default="NOMINAL", index=True)
    confidence_pct = Column(Float, nullable=True)
    day_night = Column(String, default="D", index=True)
    scan = Column(Float, nullable=True)
    track = Column(Float, nullable=True)
    
    # Data Quality & Ingestion Lifecycle
    ingested_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    is_live_data = Column(Boolean, default=True, index=True)
    data_quality_status = Column(String, default="GOOD", index=True)  # GOOD, WARNING, INVALID, DUPLICATE, STALE
    data_quality_flags = Column(JSON, default=list)
    processing_status = Column(String, default="NORMALIZED", index=True)
    
    # Downstream / Future Phase Hooks (Optional & Default None)
    classification = Column(String, nullable=True, index=True)
    classification_confidence = Column(Float, nullable=True)
    persistence_category = Column(String, nullable=True, index=True)
    abnormality_score = Column(Float, nullable=True)
    attributed_facility_id = Column(String, nullable=True, index=True)
    attributed_facility_name = Column(String, nullable=True)
    facility_distance_m = Column(Float, nullable=True)
    is_inside_facility_boundary = Column(Boolean, default=False)
    model_version = Column(String, nullable=True)
    raw_payload = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_thermal_lat_lon", "latitude", "longitude"),
        Index("idx_thermal_acq_sat", "acquisition_timestamp", "source_satellite"),
        Index("idx_thermal_h3_time", "h3_index", "acquisition_timestamp"),
        Index("idx_thermal_quality", "data_quality_status", "is_live_data"),
    )
