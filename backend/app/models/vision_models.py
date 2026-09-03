from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class CameraMetadataModel(Base):
    """
    Registered optical and thermal camera hardware catalog.
    """
    __tablename__ = "camera_metadata_catalog"

    camera_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(128), nullable=False, index=True)
    camera_type = Column(String(32), nullable=False)
    location_desc = Column(String(256), nullable=True)
    orientation_azimuth_deg = Column(Float, default=180.0)
    resolution_w = Column(Integer, default=640)
    resolution_h = Column(Integer, default=480)
    frame_rate_fps = Column(Float, default=2.0)
    status = Column(String(32), default="ONLINE")
    last_seen_at = Column(DateTime, nullable=True)
    temperature_measurement_capability = Column(Boolean, default=True)
    thermal_range_min_c = Column(Float, default=-50.0)
    thermal_range_max_c = Column(Float, default=350.0)
    calibration_reference = Column(String(128), nullable=True)
    calibration_date = Column(String(32), nullable=True)
    source_stream_url = Column(String(256), nullable=True)

class VisualEvidenceRecord(Base):
    """
    Durable time-series table for structured visual & thermal evidence events.
    Indexed for fast spatial, asset, and time-window queries.
    """
    __tablename__ = "visual_evidence_history"

    evidence_id = Column(String(64), primary_key=True, index=True)
    source_id = Column(String(64), nullable=False, index=True) # camera_id
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(128), nullable=False, index=True)
    
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    evidence_type = Column(String(64), nullable=False, index=True)
    feature_name = Column(String(64), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(32), default="°C")
    confidence = Column(Float, default=0.90)
    quality = Column(String(32), default="GOOD")
    freshness_status = Column(String(32), default="LIVE")
    
    is_live_data = Column(Boolean, default=False)
    model_version = Column(String(64), default="v1.0.0-vision-evidence")
    evidence_uri = Column(String(256), nullable=True)
    raw_metadata_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_vis_facility_time", "facility_id", "timestamp_utc"),
        Index("ix_vis_camera_time", "source_id", "timestamp_utc"),
        Index("ix_vis_asset_time", "asset_id", "timestamp_utc"),
        Index("ix_vis_type_time", "evidence_type", "timestamp_utc"),
    )
