from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class IncidentEvidence(BaseModel):
    sensor_signals: List[Dict[str, Any]] = Field(default_factory=list)
    camera_detections: List[Dict[str, Any]] = Field(default_factory=list)
    early_warning_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    risk_graph_threats: List[Dict[str, Any]] = Field(default_factory=list)

class IncidentPacket(BaseModel):
    """
    Authoritative Incident Packet:
    The central data bridge connecting streaming pre-incident telemetry,
    early-warning alerts, hazard dispersion, evacuation, and emergency resource management.
    """
    model_config = ConfigDict(populate_by_name=True)

    incident_id: str = Field(..., description="Unique incident identifier (e.g. INC-T04-20260828)")
    title: str = Field(default="Emerging Industrial Hazard Incident")
    hazard_type: str = Field(..., description="TOXIC_RELEASE, FIRE_EXPLOSION, PIPELINE_LEAK, OVERPRESSURE")
    source_asset_id: str = Field(..., description="Originating plant asset ID")
    chemical_id: str = Field(..., description="Hazardous substance ID")
    chemical_name: str = Field(..., description="Hazardous substance common name")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Overall explainable risk score")
    risk_category: str = Field(default="MODERATE", description="LOW, MODERATE, HIGH, CRITICAL")
    confidence: float = Field(default=0.92, ge=0.0, le=1.0, description="Confidence metric [0.0 - 1.0]")
    affected_zone: str = Field(default="Sector D - Cryogenic Chemical Yard")
    status: str = Field(default="OPEN", description="OPEN, ACKNOWLEDGED, MITIGATED, ESCALATED, CLOSED")
    first_detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    leading_indicators: List[str] = Field(default_factory=list)
    evidence: IncidentEvidence = Field(default_factory=IncidentEvidence)
    recommended_preventive_action: Optional[str] = None
    recommended_emergency_action: Optional[str] = None
    model_version: str = Field(default="v2.0-Production")
    schema_version: str = Field(default="1.0.0")
    source_ids: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
