from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON
from datetime import datetime
from app.core.database import Base

class PlantOperatingLimitModel(Base):
    __tablename__ = "plant_operating_limits"

    id = Column(String, primary_key=True, index=True)
    asset_id = Column(String, index=True)
    chemical_id = Column(String, index=True)
    signal_id = Column(String, index=True)
    unit = Column(String)
    nominal_low = Column(Float, nullable=True)
    nominal_high = Column(Float, nullable=True)
    warning_low = Column(Float, nullable=True)
    warning_high = Column(Float, nullable=True)
    critical_low = Column(Float, nullable=True)
    critical_high = Column(Float, nullable=True)
    source_document = Column(String, default="Plant Technical Safety Manual v4.2")
    verified_by = Column(String, default="Lead Process Safety Engineer")
    effective_date = Column(DateTime, default=datetime.utcnow)

class SensorTelemetryRecord(Base):
    __tablename__ = "sensor_telemetry_history"

    id = Column(String, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    asset_id = Column(String, index=True)
    signal_id = Column(String, index=True)
    value = Column(Float)
    unit = Column(String)
    quality = Column(String, default="GOOD")
    source = Column(String, default="EDGE_GATEWAY")
    source_type = Column(String, default="SIMULATED")
    sequence = Column(Integer, default=0)
    operating_mode = Column(String, default="NORMAL")
    severity_hint = Column(String, default="NORMAL")
    correlation_id = Column(String, nullable=True)

class IncidentPacketModel(Base):
    __tablename__ = "incident_packets_archive"

    incident_id = Column(String, primary_key=True, index=True)
    hazard_type = Column(String)
    risk_score = Column(Float)
    confidence = Column(Float, default=1.0)
    affected_zone = Column(String)
    first_detected = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="OPEN")
    source_asset_id = Column(String)
    chemical_id = Column(String)
    model_version = Column(String, default="v2.0-Production")
    schema_version = Column(String, default="1.0.0")
    evidence_json = Column(JSON, nullable=True)
    recommendations_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class LineageRecordModel(Base):
    __tablename__ = "data_lineage_logs"

    id = Column(String, primary_key=True, index=True)
    source = Column(String)
    source_type = Column(String)
    device_id = Column(String, nullable=True)
    operator_role = Column(String, nullable=True)
    model_version = Column(String, default="v2.0")
    schema_version = Column(String, default="1.0.0")
    processing_stage = Column(String)
    transformation = Column(String)
    final_decision = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
