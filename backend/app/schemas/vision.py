from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class CameraType(str, Enum):
    THERMAL_RADIOMETRIC = "THERMAL_RADIOMETRIC"
    CCTV_OPTICAL = "CCTV_OPTICAL"
    DUAL_RGB_THERMAL = "DUAL_RGB_THERMAL"

class CameraStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    FROZEN = "FROZEN"
    OCCLUDED = "OCCLUDED"
    DEGRADED = "DEGRADED"

class VisualEvidenceType(str, Enum):
    THERMAL_HOTSPOT = "THERMAL_HOTSPOT"
    SMOKE_PLUME = "SMOKE_PLUME"
    OPTICAL_FLAME = "OPTICAL_FLAME"
    TEMPERATURE_RATE_OF_RISE = "TEMPERATURE_RATE_OF_RISE"
    SCENE_OBSTRUCTION = "SCENE_OBSTRUCTION"
    PERSONNEL_COUNT = "PERSONNEL_COUNT"

class VisionQualityStatus(str, Enum):
    GOOD = "GOOD"
    WARNING = "WARNING"
    BAD = "BAD"
    STALE = "STALE"
    FROZEN = "FROZEN"

class VisionFreshnessStatus(str, Enum):
    LIVE = "LIVE"
    FRESH = "FRESH"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"

# Legacy Detection Item for backward compatibility
class VisionDetectionItem(BaseModel):
    id: str
    label: str  # FIRE, SMOKE, PERSON, VEHICLE, THERMAL_HOTSPOT
    confidence_pct: float
    bbox_xywh: List[float]  # [x_pct, y_pct, width_pct, height_pct] (normalized 0.0 - 1.0)
    color_hex: str

class VisionCameraPreset(BaseModel):
    camera_id: str
    camera_name: str
    sector: str
    associated_asset_id: str
    chemical_id: Optional[str] = None
    feed_status: str
    default_scenario: str

class VisionAnalysisResponse(BaseModel):
    image_id: str
    camera_id: str
    camera_location: str
    sector: str
    timestamp: str
    alert_level: str  # CRITICAL, WARNING, NORMAL
    detections: List[VisionDetectionItem]
    incident_suggested: bool
    suggested_asset_id: Optional[str] = None
    suggested_chemical_id: Optional[str] = None
    suggested_incident_type: Optional[str] = None
    suggested_release_rate_kg_s: Optional[float] = None
    suggestion_summary: str
    disclaimer: str = "PROTOTYPE COMPUTER VISION DETECTION — Non-Certified Prototype. Requires Human Triage."

# Phase 13 Canonical Contracts
class CameraMetadata(BaseModel):
    """Camera hardware and spatial placement catalog metadata."""
    model_config = ConfigDict(populate_by_name=True)

    camera_id: str = Field(..., description="Unique camera identifier (e.g. CAM-TH-01)")
    facility_id: str = Field(..., description="Parent facility ID (e.g. FAC-IN-DAHEJ-001)")
    asset_id: str = Field(..., description="Target monitored asset ID (e.g. T-04)")
    zone_id: str = Field(default="Sector D - Cryogenic Yard", description="Facility operational zone")
    camera_type: CameraType = Field(default=CameraType.THERMAL_RADIOMETRIC)
    location_desc: str = Field(default="Cryogenic Ammonia Storage Yard — North Mast")
    orientation_azimuth_deg: float = Field(default=180.0, description="Camera optical heading in degrees")
    resolution_w: int = Field(default=640)
    resolution_h: int = Field(default=480)
    frame_rate_fps: float = Field(default=2.0, description="Configurable sampling rate (1, 2, 5, 10 FPS)")
    status: CameraStatus = Field(default=CameraStatus.ONLINE)
    last_seen_at: Optional[datetime] = Field(default=None)
    temperature_measurement_capability: bool = Field(default=True)
    thermal_range_min_c: float = Field(default=-50.0)
    thermal_range_max_c: float = Field(default=350.0)
    calibration_reference: str = Field(default="FLIR Blackbody Model 200 Reference")
    calibration_date: str = Field(default="2026-02-10")
    source_stream_url: Optional[str] = Field(default=None, description="RTSP / ONVIF read-only URI")

class ThermalHotspot(BaseModel):
    """Individual spatial hotspot object tracked across sequential frames."""
    model_config = ConfigDict(populate_by_name=True)

    hotspot_id: str = Field(..., description="Unique persistent hotspot identifier")
    camera_id: str
    zone_id: str
    asset_id: str
    centroid_x_pct: float = Field(..., description="Normalized X coordinate [0.0 - 1.0]")
    centroid_y_pct: float = Field(..., description="Normalized Y coordinate [0.0 - 1.0]")
    bbox_xywh: List[float] = Field(..., description="[x, y, w, h] normalized coordinates")
    area_pixels: int = Field(default=120)
    area_estimated_m2: float = Field(default=0.45)
    max_temperature_c: float = Field(..., description="Peak pixel temperature in hotspot")
    mean_temperature_c: float = Field(..., description="Average temperature across hotspot region")
    baseline_temp_c: float = Field(default=25.0)
    delta_t_baseline_c: float = Field(default=0.0, description="Difference from zone baseline")
    rate_of_rise_c_min: float = Field(default=0.0, description="dT/dt temperature slope in °C/min")
    persistence_sec: float = Field(default=0.0, description="Continuous duration tracked in seconds")
    growth_rate_pct_sec: float = Field(default=0.0, description="Area growth percentage per second")
    severity: str = Field(default="WATCH", description="NORMAL, WATCH, ABNORMAL, CRITICAL")

class ThermalFrameEvidence(BaseModel):
    """Derived radiometric evidence extracted from a thermal camera frame."""
    model_config = ConfigDict(populate_by_name=True)

    frame_id: str
    camera_id: str
    facility_id: str
    asset_id: str
    zone_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_timestamp: datetime
    acquisition_timestamp: Optional[datetime] = None
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    width: int = 640
    height: int = 480
    temperature_unit: str = "°C"
    is_radiometric: bool = True
    min_temperature: float = -35.0
    max_temperature: float = 32.0
    mean_temperature: float = 24.5
    percentile_95_temperature: float = 28.2
    hotspot_count: int = 0
    hotspot_regions: List[ThermalHotspot] = Field(default_factory=list)
    quality_status: VisionQualityStatus = Field(default=VisionQualityStatus.GOOD)
    data_quality_flags: List[str] = Field(default_factory=lambda: ["NONE"])
    freshness_status: VisionFreshnessStatus = Field(default=VisionFreshnessStatus.LIVE)
    freshness_age_sec: float = 0.0
    inference_version: str = "v1.0.0-radiometric-contour"
    is_live_data: bool = False
    evidence_uri: Optional[str] = None

class CCTVFrameEvidence(BaseModel):
    """Derived visual evidence extracted from a visible-spectrum optical CCTV frame."""
    model_config = ConfigDict(populate_by_name=True)

    frame_id: str
    camera_id: str
    facility_id: str
    asset_id: str
    zone_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_timestamp: datetime
    acquisition_timestamp: Optional[datetime] = None
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    detections: List[VisionDetectionItem] = Field(default_factory=list)
    scene_status: str = Field(default="CLEAR", description="CLEAR, SMOKE_HAZE, FLAME_SIGNATURE, OBSCURED, CAMERA_FAULT")
    smoke_confidence: float = 0.0
    flame_confidence: float = 0.0
    personnel_count: int = 0
    vehicle_count: int = 0
    quality_status: VisionQualityStatus = Field(default=VisionQualityStatus.GOOD)
    data_quality_flags: List[str] = Field(default_factory=lambda: ["NONE"])
    freshness_status: VisionFreshnessStatus = Field(default=VisionFreshnessStatus.LIVE)
    freshness_age_sec: float = 0.0
    inference_version: str = "v1.0.0-optical-classifier"
    is_live_data: bool = False
    evidence_uri: Optional[str] = None

class VisualEvidence(BaseModel):
    """
    Unified canonical visual evidence contract for multimodal fusion and predictive engines.
    """
    model_config = ConfigDict(populate_by_name=True)

    evidence_id: str = Field(..., description="Unique visual evidence record ID")
    source_id: str = Field(..., description="Originating Camera ID")
    facility_id: str
    asset_id: str
    zone_id: str
    timestamp_utc: datetime
    evidence_type: VisualEvidenceType
    feature_name: str = Field(..., description="e.g. peak_temperature, rate_of_rise, smoke_plume, optical_flame")
    value: float = Field(..., description="Quantitative metric (temperature in °C, rate in °C/min, confidence [0-1])")
    unit: str = Field(default="°C")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    quality: VisionQualityStatus = Field(default=VisionQualityStatus.GOOD)
    freshness_status: VisionFreshnessStatus = Field(default=VisionFreshnessStatus.LIVE)
    freshness_age_sec: float = 0.0
    is_live_data: bool = False
    model_version: str = "v1.0.0-vision-evidence"
    evidence_uri: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None

class VisionHealthResponse(BaseModel):
    status: str
    uptime_sec: float
    total_frames_processed: int
    frames_per_second: float
    active_cameras_count: int
    cameras: List[CameraMetadata]
    p95_inference_latency_ms: float
    p99_inference_latency_ms: float
    hotspots_tracked_count: int
    quality_good_pct: float
    quality_degraded_pct: float
    read_only_mode_verified: bool = True
    system_clock_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VisionEventsQuery(BaseModel):
    facility_id: Optional[str] = None
    camera_id: Optional[str] = None
    asset_id: Optional[str] = None
    zone_id: Optional[str] = None
    evidence_type: Optional[VisualEvidenceType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_confidence: Optional[float] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
