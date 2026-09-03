from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class MonitoringLevel(str, Enum):
    LEVEL_0_BASELINE = "LEVEL_0_BASELINE"                   # Normal routine monitoring
    LEVEL_1_WATCH = "LEVEL_1_WATCH"                         # Mild anomaly / trend drift
    LEVEL_2_ABNORMAL = "LEVEL_2_ABNORMAL"                   # Persistent / worsening deviation
    LEVEL_3_HAZARD_DEVELOPING = "LEVEL_3_HAZARD_DEVELOPING" # Multi-signal evolving hazard
    LEVEL_4_CRITICAL = "LEVEL_4_CRITICAL"                   # Acute excursion / incident preparation
    LEVEL_5_INCIDENT = "LEVEL_5_INCIDENT"                   # Active emergency handoff

class AnalyticalPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class FacilityCriticalityTier(str, Enum):
    TIER_1_CRITICAL = "TIER_1_CRITICAL" # Extreme consequence (e.g. Ammonia cryogenic, chlorine bullets, heavy population)
    TIER_2_MAJOR = "TIER_2_MAJOR"       # Major industrial (e.g. LPG Horton spheres, hydrocracker)
    TIER_3_STANDARD = "TIER_3_STANDARD" # Standard industrial (e.g. diesel storage, utility sub-station)

class ValueOfInformationItem(BaseModel):
    """Specific evidence source requested to reduce analytical uncertainty."""
    target_modality: str = Field(..., description="TELEMETRY, THERMAL_CAMERA, CCTV, SATELLITE, WEATHER")
    specific_signal: str = Field(..., description="e.g. temperature_rate_of_rise, gas_sniffer_ppm, cctv_flame_contour")
    rationale: str
    expected_uncertainty_reduction: float = Field(..., ge=0.0, le=1.0)
    urgency: AnalyticalPriority = Field(default=AnalyticalPriority.MEDIUM)

class MonitoringPolicy(BaseModel):
    """Analytical parameters applied during this monitoring level."""
    telemetry_evaluation_window_sec: float = Field(default=60.0, description="Rolling window size for feature extraction")
    telemetry_sampling_interval_sec: float = Field(default=5.0, description="Rate of continuous analytical evaluation")
    thermal_camera_tracking_mode: str = Field(default="PERIODIC", description="PERIODIC, CONTINUOUS_CONTOUR, MAXIMUM_FRAME_RATE")
    cctv_frame_extraction_fps: float = Field(default=1.0)
    satellite_query_priority: str = Field(default="BACKGROUND", description="BACKGROUND, EXPEDITE_NEXT_OVERPASS, HIGH_PRIORITY_REVISE")
    multi_modal_fusion_cadence_sec: float = Field(default=30.0)

class AdaptiveMonitoringDecision(BaseModel):
    """
    Authoritative decision specifying the adaptive monitoring level and prioritized evidence requests.
    """
    model_config = ConfigDict(populate_by_name=True)

    decision_id: str = Field(..., description="Unique decision ID (e.g. ADAPT-DEC-20260901-01)")
    facility_id: str
    asset_id: str
    zone_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    
    monitoring_level: MonitoringLevel = Field(default=MonitoringLevel.LEVEL_0_BASELINE)
    previous_level: MonitoringLevel = Field(default=MonitoringLevel.LEVEL_0_BASELINE)
    
    hazard_state: str = Field(default="NORMAL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    uncertainty_score: float = Field(..., ge=0.0, le=1.0)
    conflict_mass_k: float = Field(default=0.0, ge=0.0, le=1.0)
    
    facility_criticality: FacilityCriticalityTier = Field(default=FacilityCriticalityTier.TIER_1_CRITICAL)
    priority: AnalyticalPriority = Field(default=AnalyticalPriority.LOW)
    priority_score: float = Field(default=10.0, description="Composite ranking score including risk and aging")
    
    reason: str = Field(..., description="Human-readable explanation of why monitoring level changed or maintained")
    requested_evidence: List[str] = Field(default_factory=list, description="Specific sensory modalities prioritized")
    value_of_information: List[ValueOfInformationItem] = Field(default_factory=list)
    
    applied_policy: MonitoringPolicy = Field(default_factory=MonitoringPolicy)
    
    is_in_cooldown: bool = Field(default=False)
    cooldown_remaining_sec: float = Field(default=0.0)
    
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    is_live_data: bool = Field(default=False)
    is_simulated: bool = Field(default=True)
    orchestration_version: str = "v1.0.0-adaptive-risk-orchestrator"

class NationalPriorityItem(BaseModel):
    """Ranked facility in the national surveillance queue."""
    rank: int
    facility_id: str
    facility_name: str
    monitoring_level: MonitoringLevel
    hazard_state: str
    priority: AnalyticalPriority
    priority_score: float
    last_observation_age_sec: float
    freshness_status: str
    primary_reason: str
    requested_evidence_count: int

class AdaptiveEvaluationRequest(BaseModel):
    facility_id: str = "FAC-IN-DAHEJ-001"
    asset_id: str = "T-04"
    force_hazard_state: Optional[str] = None
    force_uncertainty: Optional[float] = None
    force_missing_sources: List[str] = Field(default_factory=list)

class AdaptiveAcknowledgementRequest(BaseModel):
    operator_name: str = "Safety Director / Commander"
    notes: Optional[str] = None
