from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FacilityCandidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    facility_id: str
    facility_name: str
    rank: int = 1
    distance_m: float
    is_inside_boundary: bool = False
    attribution_confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_summary: Optional[str] = None

class ThermalSourceObservation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    acquisition_timestamp: datetime
    latitude: float
    longitude: float
    frp_mw: float
    brightness_temp_k: Optional[float] = None
    satellite: str
    sensor: str
    day_night: str = "D"
    attached_at: Optional[datetime] = None

class ThermalSourceObject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    name: Optional[str] = None
    
    # Spatio-Temporal Observables
    centroid_lat: float
    centroid_lon: float
    h3_index: str
    bounding_box: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    
    first_detected: datetime
    last_detected: datetime
    active_days_count: int = 1
    observation_count: int = 1
    unique_satellite_count: int = 1
    unique_sensor_count: int = 1
    satellites_seen: List[str] = Field(default_factory=list)
    sensors_seen: List[str] = Field(default_factory=list)
    
    # Radiometry & Temporal Statistics
    mean_frp_mw: float = 0.0
    max_frp_mw: float = 0.0
    min_frp_mw: float = 0.0
    mean_brightness_temp_k: Optional[float] = None
    max_brightness_temp_k: Optional[float] = None
    
    day_detection_count: int = 0
    night_detection_count: int = 0
    diurnal_ratio: float = 1.0
    
    # Lifecycle & Status
    source_status: str = "NEW_SOURCE"  # NEW_SOURCE, RECURRING_SOURCE, PERSISTENT_SOURCE, INACTIVE_SOURCE, UNCLASSIFIED_SOURCE
    source_confidence: str = "NOMINAL"  # HIGH, NOMINAL, LOW
    source_provenance: str = "LIVE_FIRMS"
    source_version: str = "v1.0"
    
    # Industrial Context Attribution
    primary_attributed_facility_id: Optional[str] = None
    primary_attributed_facility_name: Optional[str] = None
    facility_distance_m: Optional[float] = None
    is_inside_facility_boundary: bool = False
    facility_attribution_confidence: Optional[float] = None
    attribution_status: str = "UNATTRIBUTED"  # ATTRIBUTED_HIGH_CONFIDENCE, ATTRIBUTED_MEDIUM_CONFIDENCE, MULTIPLE_CANDIDATES, UNATTRIBUTED, INSUFFICIENT_DATA
    
    # NASA Static Anomaly Overlay
    static_firms_anomaly_overlap: bool = False
    land_cover_class: Optional[str] = None
    
    # Candidate Facilities
    candidate_facilities: List[FacilityCandidate] = Field(default_factory=list)
    linked_events_sample: List[ThermalSourceObservation] = Field(default_factory=list)
    
    created_at: datetime
    updated_at: datetime

class ThermalSourceGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]  # Point or Polygon
    properties: Dict[str, Any]

class ThermalSourceGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[ThermalSourceGeoJSONFeature]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class IndustrialFacilityDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    facility_id: str
    source: str
    source_id: Optional[str] = None
    name: str
    operator_name: Optional[str] = None
    facility_type: str
    subtype: Optional[str] = None
    latitude: float
    longitude: float
    state: str
    district: str
    country: str = "India"
    cluster_name: Optional[str] = None
    fence_radius_m: float = 1000.0
    boundary_geojson: Optional[Dict[str, Any]] = None
    reconciliation_status: str = "SINGLE_SOURCE"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    erdmp_license: Optional[str] = None
    major_chemicals_stored: List[str] = Field(default_factory=list)
    
    # Associated Sources Count
    associated_sources_count: int = 0
    total_observations_count: int = 0
    current_status: str = "NOMINAL_OPERATIONS"

class FacilityGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]  # Point or Polygon
    properties: Dict[str, Any]

class FacilityGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[FacilityGeoJSONFeature]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ClusteringSummaryResponse(BaseModel):
    total_events_evaluated: int
    sources_created: int
    sources_updated: int
    total_active_sources: int
    clustering_duration_ms: float
    sources_by_status: Dict[str, int] = Field(default_factory=dict)
