from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class FacilityTelemetryRecord(Base):
    """
    Durable high-frequency time-series table for industrial sensor telemetry observations.
    Compatible with PostgreSQL, SQLite, and TimescaleDB hypertables.
    """
    __tablename__ = "facility_telemetry_history"

    telemetry_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    plant_area = Column(String(64), nullable=True)
    unit_id = Column(String(64), nullable=True)
    asset_id = Column(String(64), nullable=False, index=True)
    gateway_id = Column(String(64), nullable=False, index=True)
    sensor_id = Column(String(64), nullable=False, index=True)
    sensor_type = Column(String(32), nullable=False, index=True)
    tag_name = Column(String(128), nullable=False)
    
    timestamp_utc = Column(DateTime, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(32), nullable=False)
    quality = Column(String(16), default="GOOD", index=True)
    source_protocol = Column(String(32), default="SIMULATED_GATEWAY")
    
    source_timestamp = Column(DateTime, nullable=False)
    acquisition_timestamp = Column(DateTime, nullable=True)
    ingestion_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    processing_timestamp = Column(DateTime, nullable=True)
    
    sequence_number = Column(Integer, default=0)
    is_live_data = Column(Boolean, default=False)
    data_quality_status = Column(String(32), default="VALID")
    data_quality_flags = Column(JSON, default=list)
    freshness_status = Column(String(16), default="LIVE")
    trend = Column(String(16), default="STABLE")

    __table_args__ = (
        Index("ix_tel_facility_time", "facility_id", "timestamp_utc"),
        Index("ix_tel_sensor_time", "sensor_id", "timestamp_utc"),
        Index("ix_tel_asset_time", "asset_id", "timestamp_utc"),
        Index("ix_tel_type_time", "sensor_type", "timestamp_utc"),
    )

class SensorMetadataModel(Base):
    """
    Sensor and Tag catalog table holding hardware boundaries, units, and sampling rates.
    """
    __tablename__ = "sensor_metadata_catalog"

    sensor_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    plant_area = Column(String(64), nullable=True)
    unit_id = Column(String(64), nullable=True)
    asset_id = Column(String(64), nullable=False, index=True)
    tag_name = Column(String(128), nullable=False)
    sensor_type = Column(String(32), nullable=False)
    unit = Column(String(32), nullable=False)
    expected_sampling_interval = Column(Float, default=1.0)
    
    valid_range_min = Column(Float, nullable=False)
    valid_range_max = Column(Float, nullable=False)
    warning_min = Column(Float, nullable=True)
    warning_max = Column(Float, nullable=True)
    critical_min = Column(Float, nullable=True)
    critical_max = Column(Float, nullable=True)
    
    source_protocol = Column(String(32), default="SIMULATED_GATEWAY")
    gateway_id = Column(String(64), default="GW-DAHEJ-EDGE-01")
    enabled = Column(Boolean, default=True)
    last_seen_at = Column(DateTime, nullable=True)
    calibration_reference = Column(String(128), nullable=True)
    calibration_date = Column(String(32), nullable=True)
    sensor_quality_state = Column(String(32), default="HEALTHY")

class EdgeGatewayModel(Base):
    """
    Registered edge gateways managing data acquisition from plant PLCs.
    """
    __tablename__ = "edge_gateways"

    gateway_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    protocol = Column(String(32), nullable=False)
    endpoint = Column(String(256), nullable=False)
    status = Column(String(32), default="CONNECTED")
    last_heartbeat = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    firmware_version = Column(String(64), default="v2.4.1-lts-secure")
    time_sync_status = Column(String(64), default="NTP_SYNCHRONIZED_PTP_CLASS1")
    buffer_count = Column(Integer, default=0)
    dropped_count = Column(Integer, default=0)
    active_sensors_count = Column(Integer, default=0)
