from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EvidenceState(str, Enum):
    SINGLE_SOURCE = "SINGLE_SOURCE"
    MULTI_SOURCE = "MULTI_SOURCE"
    CORROBORATED = "CORROBORATED"
    PARTIALLY_CORROBORATED = "PARTIALLY_CORROBORATED"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ObservationStatus(str, Enum):
    OBSERVED = "OBSERVED"
    NOT_OBSERVED = "NOT_OBSERVED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    OBSCURED = "OBSCURED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SatelliteSensorRole(str, Enum):
    THERMAL_DETECTION = "THERMAL_DETECTION"  # VIIRS / MODIS (FIRMS)
    PHYSICAL_CHARACTERIZATION = "PHYSICAL_CHARACTERIZATION"  # VIIRS Nightfire (EOG)
    HIGH_CADENCE_TEMPORAL = "HIGH_CADENCE_TEMPORAL"  # INSAT-3D/3DR (MOSDAC)
    SPATIAL_OPTICAL_SWIR_CONTEXT = "SPATIAL_OPTICAL_SWIR_CONTEXT"  # Sentinel-2 MSI
    HIGH_RES_THERMAL = "HIGH_RES_THERMAL"  # Landsat-8/9 TIRS


class ImageConfirmationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    OBSERVATION_OBSCURED = "OBSERVATION_OBSCURED"
    NO_SIGNAL_OBSERVED = "NO_SIGNAL_OBSERVED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"


class SatelliteHealthStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    satellite_id: str  # e.g., "NOAA-20", "NOAA-21", "SUOMI-NPP", "TERRA", "AQUA", "INSAT-3DR", "SENTINEL-2B", "LANDSAT-9"
    sensor_id: str  # e.g., "VIIRS", "MODIS", "IMAGER-TIR", "MSI", "TIRS-2"
    tier: str  # "TIER_1_DETECTION", "TIER_2_CHARACTERIZATION", "TIER_3_TEMPORAL", "TIER_4_CONTEXT"
    role: SatelliteSensorRole
    current_status: str = "OPERATIONAL"  # OPERATIONAL, DEGRADED, NOT_AVAILABLE, OFFLINE
    coverage_area: str = "Global / India Region"
    nominal_revisit_cadence: str = "12 Hours"
    latest_ingestion_utc: Optional[datetime] = None
    api_endpoint_status: str = "ACTIVE"
    data_latency_typical: str = "30-180 min"
    spatial_resolution: str = "375m"
    spectral_capabilities: List[str] = Field(default_factory=list)


class ThermalEvidenceMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_id: str
    satellite_name: str  # "NOAA-20", "TERRA", "INSAT-3DR", etc.
    sensor_name: str  # "VIIRS", "MODIS", "MSI", "TIRS", etc.
    source_product: str  # "FIRMS_VIIRS_NRT", "VNF_PLANCK_v3", "MOSDAC_TIR_15MIN", "S2_MSI_L2A", "L9_TIRS_L2"
    processing_version: str = "v1.0"
    role: SatelliteSensorRole
    observation_status: ObservationStatus = ObservationStatus.OBSERVED
    acquisition_timestamp: Optional[datetime] = None
    spatial_distance_m: Optional[float] = None
    temporal_offset_min: Optional[float] = None
    
    # Measured Radiometric / Physical Values
    measured_values: Dict[str, Any] = Field(default_factory=dict)
    # Examples:
    # {"frp_mw": 45.2, "brightness_temp_k": 348.0, "confidence": "high"}
    # {"source_temp_k": 1450.0, "radiant_heat_w_m2": 2400.0, "footprint_area_m2": 32.0}
    # {"swir_b12_reflectance": 0.88, "burn_index": 0.65, "smoke_detected": True}
    # {"tirs_ground_temp_c": 68.5, "band10_radiance": 14.2}
    # {"geo_hotspot_prob": 0.91, "temporal_continuity": "ACTIVE"}

    data_quality: str = "GOOD"  # GOOD, DEGRADED, OBSCURED, UNRELIABLE
    quality_flags: Dict[str, Any] = Field(default_factory=dict)
    # Examples: {"cloud_fraction_pct": 12.0, "view_zenith_angle_deg": 34.5}

    is_dependent_on_member_id: Optional[str] = None
    dependency_group_id: Optional[str] = None  # e.g., "SUOMI_NPP_PASS_20260830_0845"
    evidence_weight: float = 1.0
    evidence_contribution_sign: str = "+"  # "+", "-", "NEUTRAL"
    explanation_text: str = ""


class ThermalEvidenceAgreement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agreement_score: float = Field(..., ge=0.0, le=1.0)
    status: str = "AGREEMENT_STRONG"  # AGREEMENT_STRONG, AGREEMENT_MODERATE, PARTIAL_AGREEMENT, CONFLICTING, INSUFFICIENT_DATA
    summary: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class OnDemandImageConfirmation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    source_id: str
    satellite: str  # "Sentinel-2" or "Landsat-8/9"
    sensor: str  # "MSI" or "TIRS"
    scene_id: Optional[str] = None
    tile_id: Optional[str] = None
    acquisition_timestamp: Optional[datetime] = None
    cloud_coverage_pct: float = 0.0
    spatial_window_bbox: List[float] = Field(default_factory=list)  # [min_lon, min_lat, max_lon, max_lat]
    confirmation_status: ImageConfirmationStatus = ImageConfirmationStatus.NOT_REQUESTED
    swir_hotspot_detected: bool = False
    thermal_anomaly_detected: bool = False
    structural_context_summary: str = ""
    cached_at: Optional[datetime] = None
    is_cached: bool = False


class ThermalEvidenceBundle(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bundle_id: str
    thermal_source_id: str
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    centroid_lat: float
    centroid_lon: float

    # Overall Fusion States & Confidence
    evidence_status: EvidenceState = EvidenceState.SINGLE_SOURCE
    overall_evidence_confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Aggregation Counters
    source_count: int = 1
    satellite_count: int = 1
    independent_satellite_count: int = 1

    # Multi-Component Evidence Agreements
    temporal_agreement: ThermalEvidenceAgreement
    spatial_agreement: ThermalEvidenceAgreement
    thermal_agreement: ThermalEvidenceAgreement
    
    # High-Resolution Context Status
    image_confirmation_status: ImageConfirmationStatus = ImageConfirmationStatus.NOT_REQUESTED
    image_confirmation: Optional[OnDemandImageConfirmation] = None

    # Transparent "Why?" Explainability Dossier
    primary_corroboration_summary: str = ""
    supporting_reasons: List[str] = Field(default_factory=list)
    conflicting_reasons: List[str] = Field(default_factory=list)
    limitations_and_uncertainties: List[str] = Field(default_factory=list)

    # Detailed Member Observations
    members: List[ThermalEvidenceMember] = Field(default_factory=list)

    # Metadata & Versioning
    fusion_algorithm_version: str = "v1.0.0"
    created_at: datetime
    updated_at: datetime


class CorroborationRequest(BaseModel):
    source_id: Optional[str] = None
    temporal_window_hours: float = 24.0
    spatial_tolerance_meters: float = 1500.0
    include_on_demand_optical: bool = False
    force_recalculate: bool = False
