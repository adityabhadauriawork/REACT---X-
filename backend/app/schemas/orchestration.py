from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class SystemDataMode(str, Enum):
    LIVE = "LIVE"
    REFERENCE = "REFERENCE"
    SIMULATION = "SIMULATION"
    MIXED = "MIXED"

class PipelineStageStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"

class StageExecutionRecord(BaseModel):
    """Detailed audit record for an individual pipeline execution stage."""
    stage_name: str
    stage_index: int
    status: PipelineStageStatus
    duration_ms: float
    summary: str
    stage_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RegisteredSourceItem(BaseModel):
    """Entry in unified source registry."""
    source_id: str
    source_type: str  # SATELLITE_FIRMS, OPC_UA_TELEMETRY, MQTT_TELEMETRY, THERMAL_CAMERA, CCTV, WEATHER_API
    facility_id: Optional[str] = None
    status: str = "CONNECTED"  # CONNECTED, DEGRADED, SIMULATED, UNAVAILABLE
    data_mode: SystemDataMode = SystemDataMode.SIMULATION
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    quality_score: float = 1.0
    adapter_version: str = "v1.0.0"

class ConsequenceSummary(BaseModel):
    """Summary of heavy-gas dispersion and consequence estimation."""
    chemical_name: str = "Ammonia (NH3)"
    release_rate_kg_s: float = 15.0
    toxic_plume_length_m: float = 850.0
    aegl_2_affected_area_m2: float = 125000.0
    evacuation_zone_radius_m: float = 1200.0
    primary_wind_direction_deg: float = 240.0
    wind_speed_m_s: float = 3.5

class IncidentPacket(BaseModel):
    """
    Standardized, self-contained handoff packet for operational emergency response.
    Requires human review; contains zero physical actuation commands.
    """
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    trace_id: str
    facility_id: str
    facility_name: str
    asset_id: str
    zone_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_mode: SystemDataMode = SystemDataMode.SIMULATION

    # Assessment & Evidence
    hazard_state: str  # NOMINAL_BASELINE, WATCH_STATE, ABNORMAL_EXCURSION, HAZARD_DEVELOPING, CRITICAL_ANOMALY
    fused_confidence: float = Field(..., ge=0.0, le=1.0)
    classification_category: str = "INDUSTRIAL_FIRE"
    supporting_evidence_count: int = 4
    evidence_breakdown: List[Dict[str, Any]] = Field(default_factory=list)

    # Predictive Horizon
    predicted_escalation_minutes: Optional[int] = 15
    rate_of_rise: float = 0.0

    # Adaptive Surveillance
    monitoring_level: str = "LEVEL_3_TARGETED_EXPANSION"
    analytical_priority: str = "HIGH_PRIORITY"

    # Consequence & Response
    consequence: Optional[ConsequenceSummary] = None
    recommended_evacuation_routes: List[str] = Field(default_factory=list)
    allocated_resources: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Governance & Safety Boundary
    human_review_required: bool = True
    authorized_by: Optional[str] = None
    authorization_status: str = "PENDING_INCIDENT_COMMANDER_REVIEW"
    is_plant_actuation_blocked: bool = True
    actuation_warning: str = "REACT-X operates strictly as a read-only advisory platform. Physical PLC/DCS actuation is prohibited."

class EndToEndExecutionTrace(BaseModel):
    """Complete audit trace of a pipeline execution cycle across all 11 stages."""
    model_config = ConfigDict(from_attributes=True)

    trace_id: str
    event_id: str
    facility_id: str
    asset_id: str
    data_mode: SystemDataMode
    started_at: datetime
    completed_at: datetime
    total_duration_ms: float
    overall_status: PipelineStageStatus
    stages_executed: List[StageExecutionRecord] = Field(default_factory=list)
    incident_packet: Optional[IncidentPacket] = None
    orchestrator_version: str = "v1.0.0-reactx-orchestrator"

class SystemReadinessReport(BaseModel):
    """System-level health, readiness, and dependency evaluation."""
    status: str = "READY"  # READY, DEGRADED, NOT_READY
    data_mode: SystemDataMode = SystemDataMode.SIMULATION
    database_connected: bool = True
    models_calibrated: bool = True
    redis_cache_available: bool = True
    adapters_operational: Dict[str, bool] = Field(default_factory=dict)
    registered_facilities_count: int = 10
    active_sources_count: int = 6
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
