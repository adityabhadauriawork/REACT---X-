from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AbnormalityStatus(str, Enum):
    NORMAL_BASELINE = "NORMAL_BASELINE"
    EXPECTED_RECURRING = "EXPECTED_RECURRING"
    EXPECTED_PERSISTENT = "EXPECTED_PERSISTENT"
    WATCH = "WATCH"
    ABNORMAL_THERMAL_BEHAVIOUR = "ABNORMAL_THERMAL_BEHAVIOUR"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    SPARSE_OBSERVATIONS = "SPARSE_OBSERVATIONS"
    DATA_QUALITY_LIMITED = "DATA_QUALITY_LIMITED"


class RobustFRPStats(BaseModel):
    mean: float
    median: float
    std: float
    iqr: float
    mad: float
    p10: float
    p25: float = 0.0
    p50: float
    p75: float = 0.0
    p90: float
    p95: float = 0.0
    p99: float = 0.0
    min: float
    max: float
    recent_mean: Optional[float] = None
    recent_median: Optional[float] = None
    recent_max: Optional[float] = None
    recent_percentile: Optional[float] = None

class RobustTempStats(BaseModel):
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    iqr: Optional[float] = None
    mad: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    max: Optional[float] = None
    recent_mean: Optional[float] = None
    recent_median: Optional[float] = None
    recent_max: Optional[float] = None
    recent_percentile: Optional[float] = None

class NASAStaticThermalAnomalyContext(BaseModel):
    sta_overlap: bool = False
    sta_context_source: str = "NASA_FIRMS_STA_V1"
    sta_reference_version: str = "2024.1"
    sta_persistence_tier: Optional[str] = None
    sta_distance_m: Optional[float] = None
    sta_notes: Optional[str] = "NASA STA represents contextual persistence, not ground truth verification."

class PlantOperatingContext(BaseModel):
    provenance: str = "PLANT-PROVIDED"
    operating_mode: Optional[str] = None  # NORMAL, TURNAROUND, HIGH_THROUGHPUT, STARTUP
    planned_shutdown: bool = False
    shutdown_schedule: Optional[str] = None
    known_flare_schedule: Optional[str] = None
    maintenance_state: Optional[str] = None
    is_verified_plant_feed: bool = False

class FeatureWithProvenance(BaseModel):
    feature_name: str
    value: Union[float, int, str, bool, None]
    unit: str
    source: str
    calculation_method: str
    calculated_at: datetime
    data_quality: str

class AbnormalityEvidence(BaseModel):
    frp_deviation: Dict[str, Any] = Field(default_factory=dict)
    temperature_deviation: Dict[str, Any] = Field(default_factory=dict)
    recurrence_change: Dict[str, Any] = Field(default_factory=dict)
    spatial_change: Dict[str, Any] = Field(default_factory=dict)
    diurnal_change: Dict[str, Any] = Field(default_factory=dict)
    seasonal_change: Dict[str, Any] = Field(default_factory=dict)
    recent_trend: Dict[str, Any] = Field(default_factory=dict)
    observation_coverage: Dict[str, Any] = Field(default_factory=dict)
    data_quality: Dict[str, Any] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    change_type: str = "STABLE_BASELINE"  # SUDDEN_SPIKE, GRADUAL_RISE, PERSISTENT_SHIFT, SPATIAL_EXPANSION, BEHAVIOURAL_CHANGE, NEW_SOURCE, STABLE_BASELINE

class FacilityThermalFingerprint(BaseModel):
    fingerprint_id: str
    facility_id: str
    facility_name: Optional[str] = None
    thermal_source_id: Optional[str] = None
    
    baseline_window: str = "90d"  # 30d, 90d, 180d, 365d, ALL
    window_days: int = 90
    baseline_start: datetime
    baseline_end: datetime
    last_updated: datetime
    
    observation_count: int
    active_days: int
    observation_opportunity_count: int
    recurrence_rate: float
    detection_rate: float
    longest_active_run_days: int
    median_gap_days: float
    gap_distribution: Dict[str, int] = Field(default_factory=dict)
    
    frp_statistics: RobustFRPStats
    temp_statistics: RobustTempStats
    
    day_count: int
    night_count: int
    diurnal_ratio: float
    night_fraction: float
    day_fraction: float = 0.0
    hourly_distribution: Dict[str, int] = Field(default_factory=dict)
    
    monthly_statistics: Dict[str, Any] = Field(default_factory=dict)
    seasonal_statistics: Dict[str, Any] = Field(default_factory=dict)
    sensor_statistics: Dict[str, Any] = Field(default_factory=dict)
    satellite_coverage: Dict[str, int] = Field(default_factory=dict)
    
    centroid_lat: float
    centroid_lon: float
    spatial_stability_score: float
    spatial_dispersion_radius_m: float
    bounding_box: Optional[List[float]] = None
    max_centroid_displacement_m: float = 0.0
    
    sta_context: NASAStaticThermalAnomalyContext = Field(default_factory=NASAStaticThermalAnomalyContext)
    plant_context: PlantOperatingContext = Field(default_factory=PlantOperatingContext)
    
    data_sufficiency: str  # INSUFFICIENT_HISTORY, LIMITED_HISTORY, DEVELOPING_BASELINE, ESTABLISHED_BASELINE
    fingerprint_version: str = "1.0"
    baseline_version: str = "v1.0"

    class Config:
        from_attributes = True

# Canonical alias
ThermalBehaviourBaseline = FacilityThermalFingerprint


class ThermalAbnormalityAssessment(BaseModel):
    assessment_id: str
    source_id: str
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    assessment_time: datetime
    
    current_frp_mw: float
    current_temp_k: Optional[float] = None
    current_lat: float
    current_lon: float
    
    frp_deviation: float
    frp_robust_zscore: float
    frp_standard_zscore: float
    frp_percentile: float
    
    temperature_deviation: float
    temperature_percentile: Optional[float] = None
    
    frequency_deviation: float
    spatial_change_score: float
    spatial_displacement_m: float
    
    diurnal_deviation: float
    seasonal_deviation: float
    
    overall_abnormality_score: float  # 0.0 - 100.0
    confidence: float                 # 0.0 - 1.0
    status: str                       # NORMAL_BASELINE, EXPECTED_RECURRING, EXPECTED_PERSISTENT, WATCH, ABNORMAL_THERMAL_BEHAVIOUR, INSUFFICIENT_HISTORY, DATA_QUALITY_LIMITED
    
    change_type: str = "STABLE_BASELINE"  # SUDDEN_SPIKE, GRADUAL_RISE, PERSISTENT_SHIFT, SPATIAL_EXPANSION, BEHAVIOURAL_CHANGE, NEW_SOURCE
    evidence: Dict[str, Any] = Field(default_factory=dict)
    feature_vector: Dict[str, Any] = Field(default_factory=dict)
    
    algorithm_version: str = "1.0"
    weight_version: str = "v1.0_heuristic_validated"
    baseline_version: str = "v1.0"
    created_at: datetime

    class Config:
        from_attributes = True


class ThermalHealthResponse(BaseModel):
    """
    Facility Thermal Health / Facility Thermal Profile Dossier.
    """
    facility_id: str
    facility_name: str
    facility_type: str
    state: str
    district: str
    
    # Status & Gauge
    thermal_health_status: str  # NORMAL_BASELINE, EXPECTED_RECURRING, EXPECTED_PERSISTENT, WATCH, ABNORMAL_THERMAL_BEHAVIOUR, INSUFFICIENT_HISTORY
    overall_abnormality_score: float
    confidence: float
    data_sufficiency: str  # INSUFFICIENT_HISTORY, LIMITED_HISTORY, DEVELOPING_BASELINE, ESTABLISHED_BASELINE
    
    # Operational Comparison
    current_frp_mw: float
    historical_median_frp_mw: float
    historical_iqr_frp_mw: float
    historical_p90_frp_mw: float
    historical_range_mw: List[float]  # [p10, p90]
    
    frp_deviation_ratio: float
    recent_trend: str  # STABLE, SUDDEN_SPIKE, GRADUAL_RISE, PERSISTENT_SHIFT, COOLING_DECREASE
    
    # Behavior Signatures
    active_days_total: int
    recurrence_rate: float
    diurnal_ratio: float
    night_fraction: float
    spatial_stability_score: float
    
    last_observation_timestamp: Optional[datetime] = None
    active_sources_count: int
    
    # Explanatory & Evidence Items
    evidence_reasons: List[str]
    timeline_sparkline: List[Dict[str, Any]] = Field(default_factory=list)
    fingerprint_id: Optional[str] = None
    baseline_version: str = "v1.0"
    
    sta_context: Optional[NASAStaticThermalAnomalyContext] = None
    plant_context: Optional[PlantOperatingContext] = None

# Canonical alias
FacilityThermalProfile = ThermalHealthResponse


class FingerprintFeatureVector(BaseModel):
    """
    Phase 7 Prepared Feature Vector Schema with full provenance.
    """
    source_id: str
    facility_id: Optional[str] = None
    timestamp: datetime
    
    frp_current: float
    frp_median: float
    frp_p90: float
    frp_deviation: float
    frp_robust_zscore: float
    
    temperature_current: Optional[float] = None
    temperature_percentile: Optional[float] = None
    
    recurrence_rate: float
    active_days: int
    observation_count: int
    detection_rate: float
    
    day_night_ratio: float
    night_fraction: float
    spatial_stability: float
    spatial_displacement_m: float
    
    facility_distance_m: Optional[float] = None
    is_inside_boundary: bool = False
    facility_type: Optional[str] = None
    sta_overlap: bool = False
    
    satellite_count: int
    data_sufficiency: str
    provenance: str = "PHASE6_SYNTHESIZED"
    features_provenance: Dict[str, Any] = Field(default_factory=dict)


class AbnormalityGeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [lon, lat]

class AbnormalityGeoJSONProperties(BaseModel):
    assessment_id: str
    source_id: str
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    status: str
    overall_abnormality_score: float
    confidence: float
    current_frp_mw: float
    frp_deviation: float
    reasons: List[str]
    assessment_time: str

class AbnormalityGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: AbnormalityGeoJSONGeometry
    properties: AbnormalityGeoJSONProperties

class AbnormalityGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[AbnormalityGeoJSONFeature]
    metadata: Dict[str, Any] = Field(default_factory=dict)
