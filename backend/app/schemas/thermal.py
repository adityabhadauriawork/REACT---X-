from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class GeoPoint(BaseModel):
    latitude: float
    longitude: float

class CanonicalThermalEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    dedup_key: str = Field(..., description="Deterministic SHA256 deduplication key")
    source: str = Field("NASA_FIRMS", description="Origin data provider e.g. NASA_FIRMS, EOG_VNF")
    source_satellite: str = Field(..., description="Normalized satellite name: NOAA-20, NOAA-21, SUOMI-NPP, TERRA, AQUA")
    sensor_name: str = Field(..., description="Sensor descriptor: VIIRS_375M, MODIS_1KM")
    source_version: Optional[str] = Field("NRT_v1.0", description="Data product version e.g. v1.0NRT, Collection 6")
    acquisition_timestamp: datetime = Field(..., description="UTC acquisition timestamp of satellite observation")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 Longitude")
    frp_mw: float = Field(..., ge=0.0, description="Fire Radiative Power in Megawatts (MW)")
    brightness_temp_k: Optional[float] = Field(None, ge=150.0, le=2500.0, description="Brightness temperature (e.g. T21, T31, or 4um band in Kelvin)")
    brightness_temp_i4_k: Optional[float] = Field(None, ge=150.0, le=2500.0, description="VIIRS I-band (375m) brightness temperature in Kelvin")
    confidence: str = Field("NOMINAL", description="Detection confidence: LOW, NOMINAL, HIGH")
    confidence_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Continuous confidence percentage 0-100%")
    day_night: str = Field("D", description="'D' for Day pass, 'N' for Night pass")
    scan: Optional[float] = Field(None, description="Along-scan pixel size in km")
    track: Optional[float] = Field(None, description="Along-track pixel size in km")
    
    # Data Quality & Provenance
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of ingestion")
    is_live_data: bool = Field(True, description="True for real satellite telemetry, False for benchmark simulation data")
    data_quality_status: str = Field("GOOD", description="GOOD, WARNING, INVALID, DUPLICATE, STALE")
    data_quality_flags: List[str] = Field(default_factory=list, description="Quality warnings e.g. SUSPECT_LOW_TEMP, SCAN_EDGE, RAPID_BURST")
    processing_status: str = Field("NORMALIZED", description="RAW, NORMALIZED, ATTRIBUTED, VALIDATED")
    
    # Spatial Indexing
    h3_index: Optional[str] = Field(None, description="Uber H3 spatial index at resolution 7")
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON Point representation {'type': 'Point', 'coordinates': [lon, lat]}")
    
    # Future Phase Attribution & Intelligence Hooks (Nullable / Default None)
    classification: Optional[str] = Field(None, description="INDUSTRIAL_FIRE, GAS_FLARE, ROUTINE_PROCESS_HEAT, MINING_PROCESS_HEAT, AGRICULTURAL_BURNING, WILDFIRE_NATURAL, OTHER_UNKNOWN")
    classification_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    persistence_category: Optional[str] = Field(None, description="EXPECTED_PERSISTENT, ABNORMAL_PERSISTENT, TRANSIENT, NATURAL_NON_INDUSTRIAL, UNCLASSIFIED")
    recurrence_count_30d: int = 0
    recurrence_rate_pct: float = 0.0
    abnormality_score: float = Field(0.0, description="Thermal abnormality score 0-100 based on z-score deviation")
    frp_delta_from_baseline_pct: float = 0.0
    risk_level: str = Field("NORMAL", description="CRITICAL, HIGH, MODERATE, LOW, NORMAL")
    
    attributed_facility_id: Optional[str] = None
    attributed_facility_name: Optional[str] = None
    facility_distance_m: Optional[float] = None
    is_inside_facility_boundary: bool = False
    model_version: Optional[str] = None
    
    # VIIRS Nightfire Physical Planck Hooks (Optional)
    nightfire_temp_k: Optional[float] = None
    nightfire_area_m2: Optional[float] = None
    nightfire_radiant_heat_w_m2: Optional[float] = None

class ThermalEventGeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any]

class ThermalEventGeoJSONCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[ThermalEventGeoJSONFeature]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ThermalEventStatsResponse(BaseModel):
    total_events_count: int
    live_events_count: int
    demo_events_count: int
    satellite_distribution: Dict[str, int]
    sensor_distribution: Dict[str, int]
    day_night_distribution: Dict[str, int]
    quality_status_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    max_frp_mw: float
    mean_frp_mw: float
    temporal_range_start: Optional[datetime] = None
    temporal_range_end: Optional[datetime] = None
    h3_clusters_count: int = 0

class FIRMSIngestRecord(BaseModel):
    latitude: float
    longitude: float
    bright_ti4: Optional[float] = None
    brightness: Optional[float] = None
    scan: Optional[float] = None
    track: Optional[float] = None
    acq_date: Optional[str] = None
    acq_time: Optional[str] = None
    satellite: Optional[str] = None
    confidence: Optional[str] = None
    version: Optional[str] = None
    bright_ti5: Optional[float] = None
    frp: Optional[float] = None
    daynight: Optional[str] = None

class FIRMSIngestBatchRequest(BaseModel):
    records: List[Dict[str, Any]]
    source_satellite_override: Optional[str] = None
    sensor_name_override: Optional[str] = None
    is_live_data: bool = True
    mark_status: str = "GOOD"

class FIRMSIngestSummaryResponse(BaseModel):
    source: str = "NASA_FIRMS"
    records_received: int
    records_parsed: int
    records_validated: int
    duplicates_skipped: int
    records_persisted: int
    records_flagged_warning: int
    records_rejected_invalid: int
    ingestion_duration_ms: float
    inserted_event_ids: List[str] = []
    quality_summary: Dict[str, int] = {}

class IndustrialFacility(BaseModel):
    id: str
    name: str
    sector: str = Field(..., description="PETROCHEMICAL, REFINERY, THERMAL_POWER, STEEL, CEMENT, MINING, FERTILIZER, CHEMICAL")
    state: str = "Gujarat"
    district: str = "Bharuch"
    cluster_name: str = "Dahej Petroleum, Chemicals & Petrochemicals Investment Region (PCPIR)"
    coordinates: List[float]
    boundary_polygon: Optional[List[List[float]]] = None
    fence_radius_m: float = 800.0
    operator_name: str
    erdmp_license: Optional[str] = None
    major_chemicals_stored: List[str] = []
    
    # Thermal Baseline & Profile
    known_flares_count: int = 0
    known_furnaces_count: int = 0
    baseline_mean_frp_mw: float = 15.0
    baseline_std_frp_mw: float = 4.5
    baseline_max_frp_mw: float = 45.0
    baseline_mean_temp_k: float = 335.0
    expected_diurnal_ratio: float = 1.05
    historical_detections_count: int = 142
    current_status: str = "NOMINAL_OPERATIONS"
    current_abnormality_score: float = 0.0

class PersistentThermalCluster(BaseModel):
    cluster_id: str
    center_coordinates: List[float]
    radius_m: float = 500.0
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    primary_source_type: str = "FLARE_STACK"
    category: str = "EXPECTED_PERSISTENT"
    detections_last_90d: int = 80
    daytime_detections: int = 40
    nighttime_detections: int = 40
    recurrence_rate_pct: float = 92.5
    mean_frp_mw: float = 18.0
    std_frp_mw: float = 4.0
    max_frp_mw: float = 35.0
    current_frp_mw: float = 18.0
    frp_deviation_zscore: float = 0.0
    is_abnormal: bool = False
    abnormality_reason: Optional[str] = None
    last_detected_timestamp: datetime
    h3_index_res7: Optional[str] = None

class FeatureAttribution(BaseModel):
    feature_name: str
    feature_value: Any
    importance_weight: float
    contribution_direction: str
    human_explanation: str

class ThermalClassificationResult(BaseModel):
    event_id: str
    predicted_class: str
    confidence_score: float
    class_probabilities: Dict[str, float]
    top_feature_attributions: List[FeatureAttribution]
    explanation_summary: str
    ml_model_version: str = "SIH26162-Taxonomy-XGB-v1.0"
    classified_at: datetime = Field(default_factory=datetime.utcnow)

class VIIRSNightfireCharacterization(BaseModel):
    event_id: str
    source_temperature_k: float
    radiant_heat_flux_w_m2: float
    source_footprint_area_m2: float
    planck_curve_fit_quality: float
    estimated_emissions_co2_eq_kg_hr: Optional[float] = None
    gas_flaring_methane_combustion_eff_pct: Optional[float] = 98.2

class MultiSatelliteConfirmation(BaseModel):
    event_id: str
    firms_viirs_detected: bool = True
    viirs_nightfire_confirmed: bool = True
    sentinel2_swir_confirmation: Optional[Dict[str, Any]] = None
    landsat_thermal_confirmation: Optional[Dict[str, Any]] = None
    insat_geostationary_corroboration: Optional[Dict[str, Any]] = None
    overall_corroboration_score: float = 0.92
    corroborating_sensors_count: int = 4

class ThermalAnomalyHandoffRequest(BaseModel):
    event_id: str
    facility_id: str
    initiator_role: str = "HSE_COMMANDER"
    initiator_name: str = "NTRO Watch Officer"
    incident_type_override: Optional[str] = None
    notes: Optional[str] = None

class ThermalAnomalyHandoffResponse(BaseModel):
    handoff_status: str
    incident_id: str
    target_facility_id: str
    target_facility_name: str
    target_asset_id: str
    chemical_id: str
    chemical_name: str
    estimated_release_rate_kg_s: float
    handoff_timestamp: datetime
    simulation_initiated: bool
    emergency_command_url: str
