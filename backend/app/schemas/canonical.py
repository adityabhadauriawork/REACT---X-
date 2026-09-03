from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DataQualityFlag(str, Enum):
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"
    STALE = "STALE"

class SourceType(str, Enum):
    OFFICIAL = "OFFICIAL"
    PLANT = "PLANT"
    PUBLIC = "PUBLIC"
    SYNTHETIC = "SYNTHETIC"
    SIMULATED = "SIMULATED"
    LIVE = "LIVE"

class DataClassification(str, Enum):
    HOT = "HOT"     # 0-10s: critical anomalies, active incident state, predictive alerts, hazard fusion
    WARM = "WARM"   # minutes-hours: rolling aggregates, trends, operational history
    COLD = "COLD"   # days-years: historical archive, model training, forensic audits

class SensorType(str, Enum):
    PRESSURE = "PRESSURE"
    TEMPERATURE = "TEMPERATURE"
    VIBRATION = "VIBRATION"
    ACOUSTIC = "ACOUSTIC"
    GAS_CONCENTRATION = "GAS_CONCENTRATION"
    FLOW_RATE = "FLOW_RATE"
    VALVE_STATE = "VALVE_STATE"
    ESD_STATUS = "ESD_STATUS"
    THERMAL_RADIATION = "THERMAL_RADIATION"
    CORRIDOR_OCCUPANCY = "CORRIDOR_OCCUPANCY"
    WEATHER_WIND = "WEATHER_WIND"
    WEATHER_TEMP = "WEATHER_TEMP"

class CanonicalEvent(BaseModel):
    """
    Standard vendor-neutral canonical observation model.
    Every industrial sensor reading, PLC tag, edge observation, or simulated telemetry
    is normalized into this unified structure.
    """
    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC observation timestamp")
    asset_id: str = Field(..., description="Unique plant asset identifier (e.g. T-04, PU-01, PL-101)")
    signal_id: str = Field(..., description="Unique telemetry signal tag (e.g. T04_PRESS_01)")
    value: float = Field(..., description="Engineering unit numerical value")
    unit: str = Field(..., description="Engineering unit (e.g. bar, degC, mm/s, dB, ppm, m3/h)")
    quality: DataQualityFlag = Field(default=DataQualityFlag.GOOD, description="Signal data quality indicator")
    source: str = Field(default="EDGE_GATEWAY_01", description="Authoritative gateway or adapter source")
    source_type: SourceType = Field(default=SourceType.SIMULATED, description="Provenance data type classification")
    sequence: int = Field(default=0, description="Monotonically increasing sequence number")
    operating_mode: str = Field(default="NORMAL", description="Asset operating mode (NORMAL, TRANSIENT, EMERGENCY, SHUTDOWN)")
    zone: str = Field(default="General Plant Area", description="Plant physical/battery-limit sector")
    severity_hint: str = Field(default="NORMAL", description="Preliminary severity hint (NORMAL, WATCH, WARNING, CRITICAL)")
    schema_version: str = Field(default="1.0.0", description="Canonical schema version")
    site_id: str = Field(default="PLANT-01", description="Plant/Complex identifier")
    area_id: Optional[str] = Field(default=None, description="Plant area or battery limit")
    device_id: Optional[str] = Field(default=None, description="Physical transmitter/sensor device ID")
    sensor_type: Optional[SensorType] = Field(default=None, description="Physical measurement category")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Measurement reliability confidence [0.0 - 1.0]")
    correlation_id: Optional[str] = Field(default=None, description="Traceability correlation identifier")
    provenance: Optional[Dict[str, Any]] = Field(default=None, description="Source adapter and transformation metadata")
    classification: DataClassification = Field(default=DataClassification.HOT, description="Hot/Warm/Cold path classification")

class SignalRangeConfig(BaseModel):
    signal_id: str
    sensor_type: SensorType
    unit: str
    nominal_min: float
    nominal_max: float
    warning_low: Optional[float] = None
    warning_high: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    max_rate_of_change_per_sec: Optional[float] = None
    stale_timeout_sec: float = 30.0

class IngestionMetrics(BaseModel):
    events_ingested_total: int
    events_per_second: float
    active_streams_count: int
    quality_good_pct: float
    quality_bad_pct: float
    quality_stale_pct: float
    hot_path_events_sec: float
    warm_path_aggregates_sec: float
    p95_ingest_latency_ms: float
    p99_ingest_latency_ms: float
    last_updated: datetime = Field(default_factory=datetime.utcnow)
