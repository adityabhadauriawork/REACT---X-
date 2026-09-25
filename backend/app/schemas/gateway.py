"""
REACT-X Data Gateway Schemas & Provenance Contracts
Exposes canonical envelopes for all external sources, reference data, and demo replay.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class SourceMode(str, Enum):
    """Explicit source provenance mode. No silent transformation."""
    LIVE = "LIVE"
    REFERENCE = "REFERENCE"
    REPLAY = "REPLAY"
    SIMULATION = "SIMULATION"
    UNAVAILABLE = "UNAVAILABLE"


class QualityState(str, Enum):
    """Canonical 10-state data quality taxonomy."""
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"
    STALE = "STALE"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID = "INVALID"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"


class PredictionState(str, Enum):
    """Explicit predictive intelligence availability state."""
    PREDICTION_AVAILABLE = "PREDICTION_AVAILABLE"
    PREDICTION_STANDBY = "PREDICTION_STANDBY"
    WAITING_FOR_VERIFIED_TELEMETRY = "WAITING_FOR_VERIFIED_TELEMETRY"
    DEGRADED = "DEGRADED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"


class GatewaySource(BaseModel):
    """Metadata for an upstream or internal data provider."""
    source_id: str
    source_type: str  # SATELLITE, TELEMETRY, WEATHER, EO_STAC, CCTV, REFERENCE_CATALOG
    source_name: str
    source_mode: SourceMode
    provider: str
    status: str  # ONLINE, DEGRADED, OFFLINE, STANDBY, REPLAYING
    last_observed_at: Optional[datetime] = None
    records_ingested: int = 0
    records_rejected: int = 0
    records_quarantined: int = 0
    quality_good_ratio: float = 1.0
    freshness_seconds: Optional[float] = None
    is_authoritative: bool = True
    connection_details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict()


class NormalizedEventRecord(BaseModel):
    """
    Canonical Data Gateway Observation Envelope.
    Preserves raw observation data alongside validated/cleaned data and full audit provenance.
    """
    event_id: str
    source_id: str
    source_type: str
    source_name: str
    source_mode: SourceMode = SourceMode.LIVE
    facility_id: Optional[str] = None
    asset_id: Optional[str] = None
    observed_at: datetime
    ingested_at: datetime
    processed_at: datetime
    trace_id: str
    schema_version: str = "2.0.0"
    quality_state: QualityState = QualityState.GOOD
    quality_score: float = 1.0
    validation_flags: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: str
    
    # Spatial & Thermal payload
    latitude: float
    longitude: float
    brightness_kelvin: Optional[float] = None
    frp_mw: Optional[float] = None
    confidence_pct: Optional[float] = None
    raw_payload: Optional[Dict[str, Any]] = None
    cleaned_payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict()


class NormalizedTelemetryRecord(BaseModel):
    """Canonical industrial OT telemetry envelope."""
    facility_id: str
    asset_id: str
    sensor_id: str
    metric_name: str
    raw_value: Any
    normalized_value: Optional[float] = None
    original_unit: str
    normalized_unit: str
    observed_at: datetime
    received_at: datetime
    quality_state: QualityState = QualityState.GOOD
    quality_score: float = 1.0
    validation_flags: List[str] = Field(default_factory=list)
    source_mode: SourceMode = SourceMode.LIVE
    source: str = "OPC_UA"
    sequence: int = 0
    schema_version: str = "2.0.0"
    trace_id: str
    correlation_id: str

    model_config = ConfigDict()


class GatewayQualitySummary(BaseModel):
    """Aggregate real-time data quality metrics across all gateway feeds."""
    total_records_evaluated: int = 0
    records_good: int = 0
    records_uncertain: int = 0
    records_bad: int = 0
    records_stale: int = 0
    records_quarantined: int = 0
    records_deduplicated: int = 0
    good_ratio: float = 1.0
    uncertain_ratio: float = 0.0
    bad_ratio: float = 0.0
    stale_ratio: float = 0.0
    active_quality_flags: List[str] = Field(default_factory=list)

    model_config = ConfigDict()


class GatewayStatusResponse(BaseModel):
    """Health, connectivity, and throughput posture of the REACT-X Data Gateway."""
    status: str = "HEALTHY"
    system_version: str = "REACT-X-v2.5-PROD"
    gateway_clock_utc: datetime
    uptime_seconds: float
    active_sources_count: int
    source_modes_breakdown: Dict[str, int]
    sources: List[GatewaySource]
    quality_summary: GatewayQualitySummary
    prediction_state: PredictionState = PredictionState.PREDICTION_STANDBY
    prediction_reason: str = "Awaiting verified live industrial hardware telemetry"

    model_config = ConfigDict()


class FailureInjectionCommand(BaseModel):
    """Simulation/Demo failure injection commands for testing resilient UI/ML transitions."""
    inject_missing_telemetry: bool = False
    inject_stale_telemetry: bool = False
    inject_sensor_spike: bool = False
    inject_duplicate_events: bool = False
    inject_out_of_order_events: bool = False
    inject_conflicting_evidence: bool = False
    inject_satellite_unavailable: bool = False
    inject_degraded_source: bool = False
    trigger_recovery: bool = False


class DemoScenario(BaseModel):
    """Metadata for reference/replay scenario."""
    scenario_id: str
    name: str
    facility_id: str
    facility_name: str
    asset_id: str
    chemical_id: str
    description: str
    total_steps: int
    duration_seconds: int
    hazard_type: str
    is_golden_deterministic: bool = True

    model_config = ConfigDict()


class DemoReplayState(BaseModel):
    """Real-time playback state of the Demo Command Room."""
    status: str = "IDLE"  # IDLE, RUNNING, PAUSED, COMPLETED, ERROR
    scenario_id: Optional[str] = None
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    coordinates: Optional[List[float]] = None
    current_step: int = 0
    total_steps: int = 0
    replay_speed: float = 1.0
    replay_started_at: Optional[datetime] = None
    replay_clock: Optional[datetime] = None
    latest_event_observed_at: Optional[datetime] = None
    latest_event_ingested_at: Optional[datetime] = None
    pipeline_stage: str = "IDLE"
    active_event: Optional[Dict[str, Any]] = None
    active_telemetry: Optional[Dict[str, Any]] = None
    active_classification: Optional[Dict[str, Any]] = None
    active_fusion: Optional[Dict[str, Any]] = None
    active_prediction: Optional[Dict[str, Any]] = None
    active_consequence: Optional[Dict[str, Any]] = None
    active_cascade: Optional[Dict[str, Any]] = None
    active_evacuation: Optional[Dict[str, Any]] = None
    active_preplan_summary: Optional[Dict[str, Any]] = None
    active_incident_packet: Optional[Dict[str, Any]] = None
    active_failure_injections: FailureInjectionCommand = Field(default_factory=FailureInjectionCommand)
    pipeline_telemetry: Dict[str, Any] = Field(default_factory=dict)
    provenance_trace: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict()

