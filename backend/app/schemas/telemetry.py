from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class TelemetryQuality(str, Enum):
    GOOD = "GOOD"
    WARNING = "WARNING"
    BAD = "BAD"
    STALE = "STALE"
    MISSING = "MISSING"

class SourceProtocol(str, Enum):
    OPC_UA = "OPC_UA"
    MQTT_SPARKPLUG = "MQTT_SPARKPLUG"
    SIMULATED_GATEWAY = "SIMULATED_GATEWAY"
    REST_PUSH = "REST_PUSH"
    MODBUS_TCP = "MODBUS_TCP"

class SensorType(str, Enum):
    TEMPERATURE = "TEMPERATURE"
    PRESSURE = "PRESSURE"
    GAS_CONCENTRATION = "GAS_CONCENTRATION"
    FLOW = "FLOW"
    VIBRATION = "VIBRATION"
    THERMAL_CAMERA_SUMMARY = "THERMAL_CAMERA_SUMMARY"
    PROCESS_STATE = "PROCESS_STATE"
    ACOUSTIC = "ACOUSTIC"

class FreshnessStatus(str, Enum):
    LIVE = "LIVE"
    FRESH = "FRESH"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"

class DataQualityFlag(str, Enum):
    NONE = "NONE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    DUPLICATE = "DUPLICATE"
    LATE = "LATE"
    CLOCK_SKEW = "CLOCK_SKEW"
    COMMUNICATION_LOSS = "COMMUNICATION_LOSS"
    SENSOR_FAULT = "SENSOR_FAULT"
    REPLAYED = "REPLAYED"

class GatewayStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"
    BUFFERING = "BUFFERING"

class SensorMetadata(BaseModel):
    """
    Sensor & Tag configuration metadata binding to plant/asset hierarchy.
    """
    model_config = ConfigDict(populate_by_name=True)

    sensor_id: str = Field(..., description="Unique physical or logical sensor ID (e.g. SENS-FAC001-T04-TEMP-01)")
    facility_id: str = Field(..., description="Parent facility ID (e.g. FAC-IN-DAHEJ-001 or PLANT-01)")
    plant_area: Optional[str] = Field(default="Sector D", description="Plant area / Battery limit")
    unit_id: Optional[str] = Field(default="UNIT-NH3-01", description="Processing unit identifier")
    asset_id: str = Field(..., description="Parent asset ID (e.g. T-04, T-03, PU-01)")
    tag_name: str = Field(..., description="Source native tag or OPC UA NodeID / MQTT topic")
    sensor_type: SensorType = Field(..., description="Physical measurement category")
    unit: str = Field(..., description="Standardized engineering unit (°C, bar, ppm, m3/h, mm/s)")
    expected_sampling_interval: float = Field(default=1.0, description="Expected sampling rate in seconds (1.0, 2.0, 5.0, 10.0, 30.0, 60.0)")
    valid_range_min: float = Field(..., description="Physical sensor hardware lower limit")
    valid_range_max: float = Field(..., description="Physical sensor hardware upper limit")
    warning_min: Optional[float] = Field(default=None, description="Operational warning low boundary")
    warning_max: Optional[float] = Field(default=None, description="Operational warning high boundary")
    critical_min: Optional[float] = Field(default=None, description="Critical safety trip low threshold")
    critical_max: Optional[float] = Field(default=None, description="Critical safety trip high threshold")
    source_protocol: SourceProtocol = Field(default=SourceProtocol.SIMULATED_GATEWAY)
    gateway_id: str = Field(default="GW-DAHEJ-EDGE-01")
    enabled: bool = Field(default=True)
    last_seen_at: Optional[datetime] = Field(default=None)
    calibration_reference: Optional[str] = Field(default="ISO/IEC 17025 Certified Reference")
    calibration_date: Optional[str] = Field(default="2026-01-15")
    calibration_drift_tolerance_pct: float = Field(default=1.0)
    sensor_quality_state: str = Field(default="HEALTHY")

class EdgeGateway(BaseModel):
    """
    Conceptual and operational Edge Gateway model separating plant PLC from REACT-X ingestion.
    """
    model_config = ConfigDict(populate_by_name=True)

    gateway_id: str = Field(..., description="Unique edge gateway identifier")
    facility_id: str = Field(..., description="Target facility ID")
    protocol: SourceProtocol = Field(..., description="Source industrial protocol")
    endpoint: str = Field(..., description="Gateway broker URL or OPC UA server endpoint")
    status: GatewayStatus = Field(default=GatewayStatus.CONNECTED)
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    firmware_version: str = Field(default="v2.4.1-lts-secure")
    time_sync_status: str = Field(default="NTP_SYNCHRONIZED_PTP_CLASS1")
    buffer_count: int = Field(default=0, description="Buffered observations during network drops")
    dropped_count: int = Field(default=0, description="Dropped non-critical observations under backpressure")
    active_sensors_count: int = Field(default=0)

class FacilityTelemetryObservation(BaseModel):
    """
    Canonical vendor-neutral high-frequency industrial telemetry observation.
    Maintains complete provenance: measurement time, ingestion time, gateway, facility/asset, and quality flags.
    """
    model_config = ConfigDict(populate_by_name=True)

    telemetry_id: str = Field(..., description="Unique UUID/identifier for observation")
    facility_id: str = Field(..., description="Authoritative facility ID")
    plant_area: Optional[str] = Field(default=None, description="Plant area / Battery limit")
    unit_id: Optional[str] = Field(default=None, description="Process unit ID")
    asset_id: str = Field(..., description="Associated asset identifier (e.g. T-04, T-03)")
    gateway_id: str = Field(..., description="Edge gateway identifier")
    sensor_id: str = Field(..., description="Unique sensor identifier")
    sensor_type: SensorType = Field(..., description="Normalized sensor type category")
    tag_name: str = Field(..., description="Source-native tag identifier")
    timestamp_utc: datetime = Field(..., description="Normalized UTC measurement timestamp")
    value: float = Field(..., description="Numerical process value in normalized unit")
    unit: str = Field(..., description="Standardized engineering unit")
    quality: TelemetryQuality = Field(default=TelemetryQuality.GOOD, description="Primary quality status")
    source_protocol: SourceProtocol = Field(default=SourceProtocol.SIMULATED_GATEWAY)
    source_timestamp: datetime = Field(..., description="When the physical value was measured at the transmitter")
    acquisition_timestamp: Optional[datetime] = Field(default=None, description="When edge gateway acquired the measurement")
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When REACT-X ingested the reading")
    processing_timestamp: Optional[datetime] = Field(default=None, description="When normalization/quality evaluation completed")
    sequence_number: int = Field(default=0, description="Monotonically increasing sequence number from edge")
    is_live_data: bool = Field(default=False, description="False for simulated/replayed data, True only for real hardware gateway")
    data_quality_status: str = Field(default="VALID", description="VALID, DEGRADED, ANOMALOUS, REJECTED")
    data_quality_flags: List[DataQualityFlag] = Field(default_factory=lambda: [DataQualityFlag.NONE])
    freshness_status: Optional[FreshnessStatus] = Field(default=FreshnessStatus.LIVE)
    freshness_age_sec: Optional[float] = Field(default=0.0)
    trend: Optional[str] = Field(default="STABLE", description="STABLE, RISING, FALLING, RAPID_RISE, RAPID_FALL")
    raw_payload_sample: Optional[Dict[str, Any]] = Field(default=None, description="Raw protocol frame preview if debug enabled")

class TelemetryHistoryQuery(BaseModel):
    facility_id: Optional[str] = None
    asset_id: Optional[str] = None
    sensor_id: Optional[str] = None
    sensor_type: Optional[SensorType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    quality: Optional[TelemetryQuality] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

class TelemetryHealthResponse(BaseModel):
    status: str
    uptime_sec: float
    events_ingested_total: int
    events_per_second: float
    active_gateways_count: int
    active_sensors_count: int
    gateways: List[EdgeGateway]
    quality_good_pct: float
    quality_warning_pct: float
    quality_bad_pct: float
    quality_stale_pct: float
    p95_ingestion_latency_ms: float
    p99_ingestion_latency_ms: float
    backpressure_queue_size: int
    backpressure_dropped_count: int
    read_only_mode_verified: bool = True
    system_clock_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
