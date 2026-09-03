from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class EvidenceSourceType(str, Enum):
    SATELLITE = "SATELLITE"
    TELEMETRY = "TELEMETRY"
    THERMAL_CAMERA = "THERMAL_CAMERA"
    CCTV = "CCTV"
    PREDICTION = "PREDICTION"
    WEATHER = "WEATHER"
    FACILITY_CONTEXT = "FACILITY_CONTEXT"

class EvidenceSupportState(str, Enum):
    SUPPORTING = "SUPPORTING"       # Positively supports hazard escalation
    CONTRADICTING = "CONTRADICTING" # Disagrees with hazard escalation (shows nominal/recovering)
    NEUTRAL = "NEUTRAL"             # Inconclusive or baseline
    CONFLICTING = "CONFLICTING"     # Internal sensor disagreement
    STALE = "STALE"                 # Outdated observation window
    MISSING = "MISSING"             # Sensor uninstrumented or failed to report

class FusedHazardState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ABNORMAL = "ABNORMAL"
    HAZARD_DEVELOPING = "HAZARD_DEVELOPING"
    CRITICAL = "CRITICAL"
    INCIDENT = "INCIDENT"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"

class EvidenceItem(BaseModel):
    """
    Canonical, traceable evidence item extracted from an upstream sensory modality.
    """
    model_config = ConfigDict(populate_by_name=True)

    evidence_id: str = Field(..., description="Unique evidence identifier")
    facility_id: str
    asset_id: str
    zone_id: str
    source_id: str = Field(..., description="Sensor ID, Camera ID, Satellite overpass ID, or Model ID")
    source_type: EvidenceSourceType
    evidence_type: str = Field(..., description="e.g. process_temperature, skin_thermal_hotspot, cctv_flame, hazard_trajectory, satellite_frp")
    
    observation_timestamp: datetime
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    raw_value: float
    unit: str
    normalized_score: float = Field(..., ge=0.0, le=1.0, description="Normalized hazard evidence strength [0.0 - 1.0]")
    
    quality: str = Field(default="GOOD", description="GOOD, WARNING, BAD, DEGRADED, FROZEN")
    freshness_status: str = Field(default="LIVE", description="LIVE, FRESH, STALE, DEGRADED, UNAVAILABLE")
    freshness_age_sec: float = Field(default=0.0)
    
    reliability_score: float = Field(default=0.90, ge=0.0, le=1.0, description="Calibrated sensor reliability [0.0 - 1.0]")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    support_state: EvidenceSupportState = Field(default=EvidenceSupportState.NEUTRAL)
    
    is_live_data: bool = Field(default=False)
    is_simulated: bool = Field(default=True)
    evidence_uri: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DempsterShaferMass(BaseModel):
    """Mathematical frame of discernment masses and combination statistics."""
    model_config = ConfigDict(populate_by_name=True)

    hypothesis_masses: Dict[str, float] = Field(default_factory=dict) # e.g. {"NORMAL": 0.05, "THERMAL_ESCALATION": 0.82}
    uncertainty_mass: float = Field(default=0.10, ge=0.0, le=1.0, description="m(Θ) - unassigned belief mass")
    conflict_mass_k: float = Field(default=0.0, ge=0.0, le=1.0, description="K - orthogonal conflict metric")
    belief: Dict[str, float] = Field(default_factory=dict) # Bel(A)
    plausibility: Dict[str, float] = Field(default_factory=dict) # Pl(A)

class EvidenceAgreementMatrix(BaseModel):
    """Categorized agreement matrix across modalities."""
    supporting_signals: List[EvidenceItem] = Field(default_factory=list)
    contradicting_signals: List[EvidenceItem] = Field(default_factory=list)
    conflicting_signals: List[EvidenceItem] = Field(default_factory=list)
    stale_signals: List[EvidenceItem] = Field(default_factory=list)
    missing_modalities: List[str] = Field(default_factory=list)

class SynchronizedTimelineEvent(BaseModel):
    timestamp_utc: datetime
    relative_time: str
    source_type: EvidenceSourceType
    source_name: str
    description: str
    state_impact: str

class FusedHazardAssessment(BaseModel):
    """
    Canonical, explainable, uncertainty-aware multimodal hazard assessment.
    """
    model_config = ConfigDict(populate_by_name=True)

    assessment_id: str = Field(..., description="Unique assessment ID (e.g. FUSED-ASM-20260901-01)")
    facility_id: str
    asset_id: str
    zone_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assessment_window_start: datetime
    assessment_window_end: datetime
    
    hazard_family: str = Field(default="THERMAL_ESCALATION")
    fused_state: FusedHazardState = Field(default=FusedHazardState.NORMAL)
    
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence [0.0 - 1.0]")
    uncertainty_score: float = Field(..., ge=0.0, le=1.0, description="Total uncertainty (m(Θ) + data gaps)")
    conflict_mass_k: float = Field(default=0.0, ge=0.0, le=1.0)
    
    dempster_shafer: DempsterShaferMass
    agreement_matrix: EvidenceAgreementMatrix
    
    top_supporting_evidence: List[str] = Field(default_factory=list)
    conflict_explanation: Optional[str] = None
    missing_evidence_explanation: Optional[str] = None
    
    recommended_action: str = Field(default="ROUTINE_MONITORING")
    recommended_action_detail: str = Field(default="Normal operations within design parameters.")
    human_review_required: bool = Field(default=False)
    
    evidence_timeline: List[SynchronizedTimelineEvent] = Field(default_factory=list)
    data_lineage: Dict[str, Any] = Field(default_factory=dict)
    
    is_live_data: bool = Field(default=False)
    is_simulated: bool = Field(default=True)
    fusion_engine_version: str = "v1.0.0-dempster-shafer-multimodal"

class MultimodalAblationResult(BaseModel):
    modality_combination: str
    precision: float
    recall: float
    f1_score: float
    false_alarm_rate: float
    miss_rate: float
    warning_lead_time_min: float
    brier_score: float
    uncertainty_avg: float

class FusionEvaluationRequest(BaseModel):
    facility_id: str = "FAC-IN-DAHEJ-001"
    asset_id: str = "T-04"
    force_satellite_anomaly: bool = False
    force_satellite_stale: bool = False
    force_telemetry_stale: bool = False
    simulate_missing_sources: List[str] = Field(default_factory=list)
