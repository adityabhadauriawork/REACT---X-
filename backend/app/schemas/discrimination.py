from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class LandCoverClass(str, Enum):
    INDUSTRIAL_BUILT_UP = "INDUSTRIAL_BUILT_UP"
    FOREST = "FOREST"
    AGRICULTURE_CROPLAND = "AGRICULTURE_CROPLAND"
    SHRUBLAND_GRASSLAND = "SHRUBLAND_GRASSLAND"
    BARE_GROUND_DESERT = "BARE_GROUND_DESERT"
    WATER_BODIES = "WATER_BODIES"
    WETLANDS = "WETLANDS"
    MINING_QUARRY = "MINING_QUARRY"
    SETTLEMENT_URBAN = "SETTLEMENT_URBAN"
    LAND_COVER_UNAVAILABLE = "LAND_COVER_UNAVAILABLE"

class ObservationQualityState(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    POOR = "POOR"
    POTENTIAL_REFLECTION = "POTENTIAL_REFLECTION"

class SourcePersistenceState(str, Enum):
    TRANSIENT = "TRANSIENT"       # 1 observation / single day
    INTERMITTENT = "INTERMITTENT" # Multiple days but irregular
    PERSISTENT = "PERSISTENT"     # Consistent recurrence across weeks/months
    NEW = "NEW"                   # First seen < 24h ago
    CHANGING = "CHANGING"         # Substantial FRP or spatial growth
    UNKNOWN = "UNKNOWN"

class EOStructuralMatchStatus(str, Enum):
    STRONG_SPATIAL_MATCH = "STRONG_SPATIAL_MATCH" # < 50m to identified industrial structure
    PARTIAL_MATCH = "PARTIAL_MATCH"               # 50-150m to industrial boundary / road
    WEAK_MATCH = "WEAK_MATCH"                     # > 150m to nearest structure
    NO_MATCH = "NO_MATCH"                         # Located in open water / barren soil
    IMAGERY_UNAVAILABLE = "IMAGERY_UNAVAILABLE"   # No high-res pass available

class EOStructuralFeature(BaseModel):
    feature_type: str = Field(..., description="FLARE_STACK, STORAGE_TANK, PROCESS_UNIT, COOLING_TOWER, ROAD, VEGETATION")
    confidence: float = Field(..., ge=0.0, le=1.0)
    distance_m: float = Field(..., description="Distance from thermal centroid to structure")
    footprint_area_m2: Optional[float] = None
    bounding_box: Optional[List[float]] = None

class EOVerificationResult(BaseModel):
    """Result of selective High-Resolution Earth Observation verification."""
    model_config = ConfigDict(from_attributes=True)

    verification_id: str
    source_id: str
    imagery_source: str = "Sentinel-2 MSI / PlanetScope (Simulated)"
    acquisition_timestamp: datetime
    cloud_cover_percent: float = 5.0
    spatial_resolution_m: float = 10.0
    structural_match_status: EOStructuralMatchStatus = EOStructuralMatchStatus.STRONG_SPATIAL_MATCH
    detected_structures: List[EOStructuralFeature] = Field(default_factory=list)
    has_plume_or_burn_scar: bool = False
    verification_summary: str
    is_live_imagery: bool = False
    is_simulated: bool = True
    # Copernicus Data Space Provenance
    source_provenance: str = "COPERNICUS_SENTINEL2"
    copernicus_scene_id: Optional[str] = None
    copernicus_product_id: Optional[str] = None
    processing_timestamp: Optional[datetime] = None
    aoi_bbox: Optional[List[float]] = None
    bands_used: List[str] = Field(default_factory=lambda: ["B04", "B08", "B11", "B12"])
    quality_status: str = "VALIDATED"
    is_live_copernicus: bool = False
    spectral_indices: Optional[Dict[str, float]] = None

class LandCoverContextResult(BaseModel):
    """Authoritative land-cover context for thermal coordinates."""
    model_config = ConfigDict(from_attributes=True)

    land_cover_class: LandCoverClass
    dataset_source: str = "Copernicus Global Land Service / ESA WorldCover (10m)"
    dataset_version: str = "2024-v1.2"
    spatial_confidence: float = 0.95
    consistency_with_industrial: float = Field(..., ge=0.0, le=1.0)
    is_authoritative: bool = True

class EvidenceExplanationItem(BaseModel):
    evidence_type: str = Field(..., description="FINGERPRINT, LAND_COVER, FACILITY_GEOMETRY, EO_VERIFICATION, DIURNAL, QUALITY")
    description: str
    support_state: str = Field(..., description="SUPPORTING, CONTRADICTING, NEUTRAL")
    weight: float = Field(..., ge=0.0, le=1.0)

class DiscriminationAssessment(BaseModel):
    """
    Complete canonical assessment uniting thermal fingerprints, land cover,
    geometric facility attribution, observation quality, and selective EO verification.
    """
    model_config = ConfigDict(from_attributes=True)

    assessment_id: str
    source_id: str
    centroid_lat: float
    centroid_lon: float
    h3_index: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Classification
    predicted_class: str
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    classification_state: str = "CLASSIFIED"  # CLASSIFIED, NEEDS_REVIEW, INSUFFICIENT_EVIDENCE
    model_confidence: float = Field(..., ge=0.0, le=1.0)
    system_confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_sufficiency: str = "SUFFICIENT"   # SUFFICIENT, DEGRADED, INSUFFICIENT
    
    # Source Spatiotemporal Behavior
    persistence_state: SourcePersistenceState = SourcePersistenceState.PERSISTENT
    observation_count: int = 1
    mean_frp_mw: float = 0.0
    max_frp_mw: float = 0.0
    diurnal_night_fraction: float = 0.5
    spatial_dispersion_r95_m: float = 50.0
    
    # Context Layers
    facility_attribution_status: str = "ATTRIBUTED_INSIDE_BOUNDARY"
    attributed_facility_id: Optional[str] = None
    attributed_facility_name: Optional[str] = None
    facility_distance_m: float = 0.0
    is_inside_facility: bool = False
    
    land_cover: LandCoverContextResult
    observation_quality: ObservationQualityState = ObservationQualityState.GOOD
    quality_explanation: Optional[str] = None
    is_potential_reflection: bool = False
    
    # EO Verification
    eo_verification: Optional[EOVerificationResult] = None
    eo_verification_required: bool = False
    
    # Evidence Decomposition
    top_supporting_evidence: List[EvidenceExplanationItem] = Field(default_factory=list)
    top_opposing_evidence: List[EvidenceExplanationItem] = Field(default_factory=list)
    abstention_reason: Optional[str] = None
    
    is_live_data: bool = False
    is_simulated: bool = True
    discrimination_version: str = "v1.0.0-multimodal-discrimination"
