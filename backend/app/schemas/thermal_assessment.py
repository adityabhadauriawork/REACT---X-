from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.thermal_classification import TargetSourceClass as ThermalSourceClass
from app.schemas.thermal_fingerprint import AbnormalityStatus
from app.schemas.thermal_corroboration import EvidenceState
from app.schemas.data_quality import AssessmentLineage, DataQualityState


# =============================================================================
# ENUMS & STATUS CODES
# =============================================================================

class IndustrialRiskLevel(str, Enum):
    NOMINAL = "NOMINAL"           # Routine stable thermal activity, non-industrial context, or negligible hazard
    LOW = "LOW"                   # Controlled routine heat, low baseline departure, robust containment
    MODERATE = "MODERATE"         # Moderate flaring surge or intermediate thermal abnormality; monitoring required
    HIGH = "HIGH"                 # Significant unpredicted thermal surge or classified industrial fire candidate
    CRITICAL = "CRITICAL"         # Severe industrial fire with multi-satellite corroboration inside critical facility


class HandoffEligibility(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"               # Routine operation, non-industrial burn, or low data quality
    REVIEW_REQUIRED = "REVIEW_REQUIRED"         # Moderate risk or borderline confidence requiring human inspection
    INCIDENT_DRAFT_READY = "INCIDENT_DRAFT_READY"# Confirmed abnormal industrial thermal event eligible for incident creation
    INCIDENT_ACTIVE = "INCIDENT_ACTIVE"         # Promoted to active REACT-X emergency incident workspace


class AssessmentStatus(str, Enum):
    INITIAL = "INITIAL"           # First assessment produced for thermal source
    UPDATED = "UPDATED"           # Re-evaluated following subsequent satellite overpasses
    CONFIRMED = "CONFIRMED"       # Operator verified or confirmed by ground telemetry
    DOWNGRADED = "DOWNGRADED"     # De-escalated following clear-sky nominal pass or operator review
    CLOSED = "CLOSED"             # Event concluded or source became inactive


# =============================================================================
# EVIDENCE ITEM & PROVENANCE GRAPH
# =============================================================================

class EvidenceItem(BaseModel):
    """Explicit, auditable evidence item supporting the final assessment."""
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(..., description="e.g. NASA_FIRMS_VIIRS, VIIRS_NIGHTFIRE, INSAT_3DR, COPERNICUS_S2, OSM_REGISTRY, ML_CLASSIFIER, BASELINE_ENGINE")
    record_id: str = Field(..., description="Unique record identifier or overpass key")
    timestamp: datetime = Field(..., description="UTC acquisition or generation timestamp")
    quality: str = Field(default="GOOD", description="HIGH, GOOD, MARGINAL, UNCERTAIN, OBSCURED")
    role: str = Field(..., description="PRIMARY_TRIGGER, PHYSICAL_FIT, TEMPORAL_CONTINUITY, SPATIAL_CONTEXT, STATISTICAL_BASELINE, AI_PREDICTION")
    result: str = Field(..., description="Observable result or finding summary")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Confidence contribution [0.0 - 1.0]")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Underlying telemetry, coordinates, and product parameters")


# =============================================================================
# REACT-X INCIDENT DRAFT (SAFE SATELLITE -> EMERGENCY HANDOFF)
# =============================================================================

class ReactXIncidentDraft(BaseModel):
    """
    Structured incident draft prepared by the satellite assessment engine.
    Does NOT autonomously trigger physical equipment, PLC shutdowns, or sirens.
    """
    model_config = ConfigDict(populate_by_name=True)

    draft_id: str = Field(..., description="Draft identifier (e.g. DRAFT-INC-20260830-DHJ-01)")
    source_id: str = Field(..., description="Originating thermal source ID")
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    suggested_incident_type: str = Field(default="FIRE_EXPLOSION", description="FIRE_EXPLOSION, TOXIC_RELEASE, PROCESS_OVERPRESSURE")
    suggested_severity: str = Field(default="HIGH", description="LOW, MODERATE, HIGH, CRITICAL")
    coordinates: List[float] = Field(..., description="[Latitude, Longitude] centroid of hotspot")
    thermal_summary: str = Field(..., description="FRP and brightness temperature summary")
    ml_classification: str = Field(..., description="Predicted source type and confidence")
    abnormality_summary: str = Field(..., description="Empirical baseline departure summary")
    multi_satellite_summary: str = Field(..., description="Cross-sensor corroboration summary")
    chemical_consequence_status: str = Field(
        default="INSUFFICIENT_DATA",
        description="CHEMICAL CONSEQUENCE MODEL: INSUFFICIENT DATA (unless plant chemical inventory is confirmed)"
    )
    site_evacuation_status: str = Field(
        default="SITE_LEVEL_DATA_UNAVAILABLE",
        description="SITE-LEVEL RESPONSE DATA UNAVAILABLE (unless plant worker roster is confirmed)"
    )
    suggested_next_actions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# INDUSTRIAL THERMAL ASSESSMENT (AUTHORITATIVE FIRST-CLASS ENTITY)
# =============================================================================

class IndustrialThermalAssessment(BaseModel):
    """
    Authoritative, multi-factor analytical assessment of an industrial thermal source.
    Maintains independent confidences across attribution, classification, abnormality, and evidence.
    """
    model_config = ConfigDict(populate_by_name=True)

    assessment_id: str = Field(..., description="Unique assessment ID (e.g. ASM-20260830-DHJ-01-v1)")
    source_id: str = Field(..., description="Target ThermalSourceObject ID")
    facility_id: Optional[str] = Field(None, description="Attributed industrial facility ID")
    facility_name: Optional[str] = Field(None, description="Attributed industrial facility name")
    centroid_lat: float
    centroid_lon: float

    # --- 4 SEPARATE & INDEPENDENT CONFIDENCES ---
    attribution_confidence: float = Field(..., ge=0.0, le=1.0, description="Spatial and cadastral attribution confidence")
    classification_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated ML classification confidence (p)")
    abnormality_confidence: float = Field(..., ge=0.0, le=1.0, description="Historical baseline data sufficiency confidence")
    overall_evidence_confidence: float = Field(..., ge=0.0, le=1.0, description="Multi-satellite corroboration & consistency confidence")

    # --- ANALYTICAL DIMENSIONS ---
    classification: ThermalSourceClass = Field(..., description="Top predicted thermal source class")
    classification_probabilities: Dict[str, float] = Field(default_factory=dict)
    
    abnormality_score: float = Field(..., ge=0.0, le=100.0, description="Baseline abnormality score [0.0 - 100.0]")
    abnormality_status: str = Field(..., description="NORMAL_BASELINE, MODERATE_DEPARTURE, SEVERE_ABNORMALITY, etc.")
    robust_zscore: float = Field(default=0.0, description="Median Absolute Deviation robust Z-score")

    attribution_status: str = Field(default="ATTRIBUTED_HIGH_CONFIDENCE")
    corroboration_status: EvidenceState = Field(..., description="CORROBORATED, PARTIALLY_CORROBORATED, SINGLE_SOURCE, CONFLICTING, etc.")

    # --- MULTI-FACTOR INDUSTRIAL RISK ---
    industrial_risk_level: IndustrialRiskLevel = Field(..., description="NOMINAL, LOW, MODERATE, HIGH, CRITICAL")
    industrial_risk_score: float = Field(..., ge=0.0, le=100.0, description="Explainable multi-factor risk score [0.0 - 100.0]")
    risk_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the risk assessment")
    risk_label: str = Field(default="SCREENING-LEVEL INDUSTRIAL RISK", description="Explicitly states screening nature")

    # --- OPERATIONAL DISTINCTION ---
    is_routine_operation: bool = Field(..., description="True if normal routine industrial heat; False if unpredicted surge")
    operational_concern_summary: str = Field(..., description="High-level operational interpretation")

    # --- EVIDENCE PACKAGE ---
    evidence_summary: str = Field(..., description="Executive evidence synthesis")
    evidence_items: List[EvidenceItem] = Field(default_factory=list)

    # --- EMERGENCY HANDOFF GATEWAY ---
    handoff_eligibility: HandoffEligibility = Field(..., description="Eligibility status for REACT-X emergency incident workspace")
    incident_draft: Optional[ReactXIncidentDraft] = Field(None, description="Pre-configured incident scenario draft (if eligible)")

    # --- LIFECYCLE & REPRODUCIBILITY VERSIONING ---
    assessment_status: AssessmentStatus = Field(default=AssessmentStatus.INITIAL)
    version: int = Field(default=1, description="Sequential assessment version counter")
    parent_assessment_id: Optional[str] = Field(None, description="Prior version ID if reassessed")

    classification_model_version: str = Field(default="IHS_INDIA_HGB_v1.0")
    abnormality_algorithm_version: str = Field(default="TF-LEVEL5-v1.0")
    attribution_algorithm_version: str = Field(default="OSM-GEM-H3-v1.0")
    evidence_fusion_version: str = Field(default="EFE-4TIER-v1.0")
    risk_algorithm_version: str = Field(default="MFR-SCREENING-v1.0")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # --- PHASE 10: DATA LINEAGE & QUALITY ---
    data_lineage: Optional[AssessmentLineage] = Field(
        default=None,
        description="Full data provenance chain: observation IDs, versions, timestamps"
    )
    data_quality_state: DataQualityState = Field(
        default=DataQualityState.GOOD,
        description="Explicit data quality state for this assessment"
    )


# =============================================================================
# REQUEST & RESPONSE SCHEMAS
# =============================================================================

class AssessmentRequest(BaseModel):
    source_id: Optional[str] = None
    force_recalculate: bool = False
    include_on_demand_optical: bool = True
    temporal_window_hours: float = 48.0


class IncidentPromotionRequest(BaseModel):
    """Operator action authorizing promotion of an assessment to an active REACT-X incident."""
    operator_id: str = Field(..., description="Authenticated operator username or employee ID")
    operator_role: str = Field(default="HSE_COMMANDER", description="HSE_COMMANDER, SHIFT_ENGINEER, DISPATCHER")
    justification: str = Field(..., description="Mandatory operational rationale for incident activation")
    assigned_sector: Optional[str] = None
    custom_title: Optional[str] = None


class IncidentRejectionRequest(BaseModel):
    """Operator action marking an assessment as non-emergency routine operation or false alarm."""
    operator_id: str = Field(..., description="Authenticated operator username or employee ID")
    operator_role: str = Field(default="HSE_COMMANDER")
    rejection_reason: str = Field(..., description="e.g. AUTHORIZED_MAINTENANCE_FLARING, SENSOR_ARTIFACT, CONTROLLED_SLAG_COOLING")
    notes: Optional[str] = None


class AssessmentExecutiveBriefResponse(BaseModel):
    assessment_id: str
    source_id: str
    facility_name: str
    brief_markdown: str
    generated_at: datetime
