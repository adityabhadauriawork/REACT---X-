from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class FacilityType(str, Enum):
    REFINERY = "REFINERY"
    PETROCHEMICAL = "PETROCHEMICAL"
    CHEMICAL = "CHEMICAL"
    STEEL = "STEEL"
    CEMENT = "CEMENT"
    THERMAL_POWER = "THERMAL_POWER"
    MINING = "MINING"
    LNG = "LNG"
    STORAGE = "STORAGE"
    MANUFACTURING = "MANUFACTURING"
    OTHER = "OTHER"

class FacilityConnectivityStatus(str, Enum):
    NOT_CONNECTED = "NOT_CONNECTED"
    SATELLITE_ONLY = "SATELLITE_ONLY"
    PARTIAL_TELEMETRY = "PARTIAL_TELEMETRY"
    VISUAL_CONNECTED = "VISUAL_CONNECTED"
    FULLY_INSTRUMENTED = "FULLY_INSTRUMENTED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"

class FacilityCapability(str, Enum):
    SATELLITE = "SATELLITE"
    TELEMETRY = "TELEMETRY"
    THERMAL_CAMERA = "THERMAL_CAMERA"
    CCTV = "CCTV"
    GAS = "GAS"
    PRESSURE = "PRESSURE"
    TEMPERATURE = "TEMPERATURE"
    FLOW = "FLOW"
    VIBRATION = "VIBRATION"
    WEATHER = "WEATHER"

class HazardProfileType(str, Enum):
    THERMAL = "THERMAL"
    FIRE = "FIRE"
    GAS = "GAS"
    PRESSURE = "PRESSURE"
    PROCESS = "PROCESS"
    ELECTRICAL = "ELECTRICAL"
    EQUIPMENT = "EQUIPMENT"

class FacilityBaselineStage(str, Enum):
    CONTEXT_ONLY = "CONTEXT_ONLY"
    BASELINE_BUILDING = "BASELINE_BUILDING"
    BASELINE_READY = "BASELINE_READY"
    PREDICTION_ENABLED = "PREDICTION_ENABLED"

class DataProvenance(BaseModel):
    facility_source: str = "OFFICIAL_REGISTRY"
    source_version: str = "v1.0"
    source_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SensorConfig(BaseModel):
    sensor_id: str
    facility_id: str
    asset_id: str
    zone_id: Optional[str] = None
    sensor_type: str  # TEMPERATURE, PRESSURE, GAS_CONCENTRATION, FLOW_RATE, VIBRATION
    unit: str
    expected_interval_sec: float = 1.0
    valid_range_min: float
    valid_range_max: float
    protocol: str = "OPC_UA"  # OPC_UA, MQTT, REST, MODBUS
    gateway_id: Optional[str] = None
    enabled: bool = True
    quality_policy: str = "STANDARD"

class CameraConfig(BaseModel):
    camera_id: str
    facility_id: str
    asset_id: str
    zone_id: Optional[str] = None
    camera_type: str  # THERMAL_LWIR, OPTICAL_CCTV, DUAL_THERMAL_RGB
    position: Optional[List[float]] = None  # [lat, lon, alt_m]
    orientation_deg: Optional[float] = 0.0
    enabled: bool = True
    sampling_fps: float = 1.0

class ZoneConfig(BaseModel):
    zone_id: str
    zone_name: str
    hazard_types: List[HazardProfileType] = Field(default_factory=list)
    boundary_polygon: Optional[List[List[float]]] = None

class AssetConfig(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: str
    zones: List[ZoneConfig] = Field(default_factory=list)
    sensors: List[SensorConfig] = Field(default_factory=list)
    cameras: List[CameraConfig] = Field(default_factory=list)

class UnitConfig(BaseModel):
    unit_id: str
    unit_name: str
    assets: List[AssetConfig] = Field(default_factory=list)

class AreaConfig(BaseModel):
    area_id: str
    area_name: str
    units: List[UnitConfig] = Field(default_factory=list)

class FacilityConfig(BaseModel):
    """Generic, geography-independent facility configuration model."""
    model_config = ConfigDict(from_attributes=True)

    facility_id: str
    facility_name: str
    facility_type: FacilityType
    country: str = "India"
    state: str
    district: str
    city_locality: Optional[str] = None
    latitude: float
    longitude: float
    boundary_polygon: Optional[List[List[float]]] = None
    criticality: str = "TIER_1_CRITICAL"  # TIER_1_CRITICAL, TIER_2_MAJOR, TIER_3_STANDARD
    hazard_profile: List[HazardProfileType] = Field(default_factory=list)
    capabilities: List[FacilityCapability] = Field(default_factory=list)
    connectivity_status: FacilityConnectivityStatus = FacilityConnectivityStatus.SATELLITE_ONLY
    baseline_stage: FacilityBaselineStage = FacilityBaselineStage.CONTEXT_ONLY
    provenance: DataProvenance = Field(default_factory=DataProvenance)
    enabled: bool = True
    is_reference_environment: bool = False
    is_simulated: bool = False
    areas: List[AreaConfig] = Field(default_factory=list)

class NationalCoverageSummary(BaseModel):
    """Real-time calculated national coverage summary across India."""
    total_known_facilities: int
    monitored_facilities: int
    connected_facilities: int
    fully_instrumented_facilities: int
    active_states_count: int
    coverage_by_state: Dict[str, int] = Field(default_factory=dict)
    coverage_by_industry: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RegionFreshnessSummary(BaseModel):
    """Calculated regional data freshness metrics."""
    region_name: str
    total_sources: int
    fresh_count: int
    degraded_count: int
    stale_count: int
    fresh_percent: float
    degraded_percent: float
    stale_percent: float
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FacilityConfigExport(BaseModel):
    """Clean JSON export format for facility configuration (credentials excluded)."""
    export_version: str = "v1.0"
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    facility: FacilityConfig

class FacilityConfigImportRequest(BaseModel):
    """Request payload for importing a validated facility configuration."""
    configuration_json: Dict[str, Any]
    dry_run: bool = False
