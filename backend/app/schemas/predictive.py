from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

# Legacy Schemas for backward compatibility
class AssetHealthItem(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    chemical_id: str
    sector: str
    operating_hours: float
    maintenance_age_days: int
    vibration_mm_s: float
    temperature_c: float
    pressure_bar: float
    acoustic_leak_db: float
    anomaly_count_30d: int
    last_inspection_date: str
    failure_risk_score: float
    risk_category: str
    top_risk_driver: str
    recommended_action: str

class AssetHealthSummaryResponse(BaseModel):
    total_monitored_assets: int
    critical_risk_count: int
    high_risk_count: int
    moderate_risk_count: int
    healthy_asset_count: int
    highest_risk_asset_id: str
    assets: List[AssetHealthItem]
    model_metadata: Dict[str, Any]

# Phase 14 Canonical Predictive Intelligence Schemas
class HazardState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ABNORMAL = "ABNORMAL"
    HAZARD_DEVELOPING = "HAZARD_DEVELOPING"
    CRITICAL = "CRITICAL"
    INCIDENT = "INCIDENT"

class HazardFamily(str, Enum):
    THERMAL_ESCALATION = "THERMAL_ESCALATION"
    GAS_RELEASE = "GAS_RELEASE"
    PRESSURE_ABNORMALITY = "PRESSURE_ABNORMALITY"
    PROCESS_INSTABILITY = "PROCESS_INSTABILITY"
    FIRE_DEVELOPMENT = "FIRE_DEVELOPMENT"
    EQUIPMENT_THERMAL_FAILURE = "EQUIPMENT_THERMAL_FAILURE"

class TrendDirection(str, Enum):
    STABLE = "STABLE"
    RISING = "RISING"
    RAPIDLY_RISING = "RAPIDLY_RISING"
    FALLING = "FALLING"
    RAPIDLY_FALLING = "RAPIDLY_FALLING"
    OSCILLATING = "OSCILLATING"
    UNKNOWN = "UNKNOWN"

class ForecastHorizon(str, Enum):
    HORIZON_1M = "1m"
    HORIZON_5M = "5m"
    HORIZON_10M = "10m"
    HORIZON_15M = "15m"
    HORIZON_30M = "30m"

class UncertaintyState(str, Enum):
    CONFIRMED = "CONFIRMED"
    MODERATE_UNCERTAINTY = "MODERATE_UNCERTAINTY"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DEGRADED = "DEGRADED"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"

class FeatureContribution(BaseModel):
    """Explainable evidence feature contribution to the predicted hazard state."""
    model_config = ConfigDict(populate_by_name=True)

    feature_name: str = Field(..., description="e.g. skin_temperature_slope, vessel_pressure_zscore")
    display_name: str = Field(..., description="Human-readable feature description")
    current_value: float
    baseline_value: float
    delta_value: float
    unit: str
    contribution_pct: float = Field(..., ge=0.0, le=100.0, description="Relative % contribution to warning")
    importance_level: str = Field(default="MODERATE", description="LOW, MODERATE, HIGH, CRITICAL")
    direction: str = Field(default="INCREASING", description="INCREASING, DECREASING, ELEVATED, UNSTABLE")

class HazardPrediction(BaseModel):
    """
    Canonical Short-Horizon Hazard Prediction Event.
    """
    model_config = ConfigDict(populate_by_name=True)

    prediction_id: str = Field(..., description="Unique prediction identifier")
    facility_id: str = Field(..., description="Monitored facility ID")
    asset_id: str = Field(..., description="Target equipment ID (e.g. T-04)")
    zone_id: str = Field(default="Sector D - Cryogenic Yard")
    hazard_family: HazardFamily = Field(default=HazardFamily.THERMAL_ESCALATION)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    observation_window_start: datetime
    observation_window_end: datetime
    forecast_horizon: ForecastHorizon = Field(default=ForecastHorizon.HORIZON_10M)
    
    current_state: HazardState = Field(default=HazardState.NORMAL)
    predicted_state: HazardState = Field(default=HazardState.WATCH)
    trend: TrendDirection = Field(default=TrendDirection.STABLE)
    
    escalation_probability: float = Field(..., ge=0.0, le=1.0, description="Calibrated likelihood of entering HAZARD_DEVELOPING")
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence [0.0 - 1.0]")
    uncertainty_state: UncertaintyState = Field(default=UncertaintyState.CONFIRMED)
    
    top_contributing_features: List[FeatureContribution] = Field(default_factory=list)
    anomaly_score: float = Field(default=0.0, ge=0.0, le=1.0)
    change_point_detected: bool = Field(default=False)
    change_point_strength: float = Field(default=0.0)
    
    recommended_monitoring_level: str = Field(default="STANDARD", description="STANDARD, ELEVATED_WATCH, INTENSIVE_SURVEILLANCE, EMERGENCY_STANDBY")
    recommendation_reason: str = Field(default="Asset operating within nominal parameters.")
    
    data_sufficiency: str = Field(default="COMPLETE", description="COMPLETE, PARTIAL, DEGRADED, INSUFFICIENT")
    telemetry_freshness: str = Field(default="LIVE")
    thermal_vision_available: bool = Field(default=True)
    is_simulated_pipeline: bool = Field(default=True)
    model_version: str = "v1.0.0-hazard-trajectory"
    baseline_version: str = "v1.0.0-dahej-base"

class PredictiveTimelinePoint(BaseModel):
    timestamp_utc: datetime
    relative_time_label: str  # e.g. "t-10m", "t-5m", "NOW", "t+5m", "t+10m"
    temperature_c: float
    pressure_bar: float
    gas_concentration_ppm: float
    hazard_score: float
    state: HazardState
    is_forecast: bool = False

class FacilityPredictiveTimelineResponse(BaseModel):
    facility_id: str
    asset_id: str
    current_prediction: HazardPrediction
    timeline_points: List[PredictiveTimelinePoint]
    forecast_horizon_valid: bool = True

class PredictionEvaluationRequest(BaseModel):
    facility_id: str = "FAC-IN-DAHEJ-001"
    asset_id: str = "T-04"
    forecast_horizon: ForecastHorizon = ForecastHorizon.HORIZON_10M
    force_stale_telemetry: bool = False
    simulate_missing_sensors: List[str] = Field(default_factory=list)

class PredictionExplanationResponse(BaseModel):
    prediction_id: str
    facility_id: str
    asset_id: str
    hazard_family: HazardFamily
    current_state: HazardState
    predicted_state: HazardState
    confidence_calibration_curve: Dict[str, float]
    brier_score: float
    feature_contributions: List[FeatureContribution]
    dominant_evidence_narrative: str
    read_only_advisory: str = "ADVISORY DECISION SUPPORT ONLY — NO DIRECT ACTUATION OR AUTOMATIC SHUTDOWN ACCESS."
