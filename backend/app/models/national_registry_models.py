from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class NationalFacilityRegistryRecord(Base):
    """
    Durable registry table for all monitored industrial facilities across India.
    """
    __tablename__ = "national_facility_registry"

    facility_id = Column(String(64), primary_key=True, index=True)
    facility_name = Column(String(128), nullable=False, index=True)
    facility_type = Column(String(64), nullable=False, index=True)
    country = Column(String(64), default="India")
    state = Column(String(64), nullable=False, index=True)
    district = Column(String(64), nullable=False, index=True)
    city_locality = Column(String(128), nullable=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    boundary_polygon_json = Column(JSON, nullable=True)
    criticality = Column(String(32), default="TIER_1_CRITICAL", index=True)
    hazard_profile_json = Column(JSON, nullable=True)
    capabilities_json = Column(JSON, nullable=True)
    connectivity_status = Column(String(64), default="SATELLITE_ONLY", index=True)
    baseline_stage = Column(String(64), default="CONTEXT_ONLY", index=True)
    provenance_json = Column(JSON, nullable=True)
    areas_hierarchy_json = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True, index=True)
    is_reference_environment = Column(Boolean, default=False, index=True)
    is_simulated = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_nat_fac_state_type", "state", "facility_type"),
        Index("ix_nat_fac_lat_lon", "latitude", "longitude"),
    )

class FacilitySensorConfigRecord(Base):
    """
    Registered sensors configured per facility and asset.
    """
    __tablename__ = "facility_sensor_configs"

    sensor_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(64), nullable=True)
    sensor_type = Column(String(64), nullable=False, index=True)
    unit = Column(String(32), nullable=False)
    expected_interval_sec = Column(Float, default=1.0)
    valid_range_min = Column(Float, nullable=False)
    valid_range_max = Column(Float, nullable=False)
    protocol = Column(String(32), default="OPC_UA")
    gateway_id = Column(String(64), nullable=True)
    quality_policy = Column(String(32), default="STANDARD")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class FacilityCameraConfigRecord(Base):
    """
    Registered cameras configured per facility and asset.
    """
    __tablename__ = "facility_camera_configs"

    camera_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(64), nullable=True)
    camera_type = Column(String(64), nullable=False, index=True)
    position_json = Column(JSON, nullable=True)
    orientation_deg = Column(Float, default=0.0)
    sampling_fps = Column(Float, default=1.0)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
