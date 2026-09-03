from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class TargetSourceClass(str, Enum):
    INDUSTRIAL_FIRE = "INDUSTRIAL_FIRE"
    GAS_FLARE = "GAS_FLARE"
    ROUTINE_PROCESS_HEAT = "ROUTINE_PROCESS_HEAT"
    MINING_PROCESS_HEAT = "MINING_PROCESS_HEAT"
    AGRICULTURAL_BURNING = "AGRICULTURAL_BURNING"
    WILDFIRE_NATURAL = "WILDFIRE_NATURAL"
    OTHER_UNKNOWN = "OTHER_UNKNOWN"


class ClassificationState(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    MODEL_ANALYSIS = "MODEL_ANALYSIS"
    CLASSIFIED = "CLASSIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    MODEL_COVERAGE_LIMITED = "MODEL_COVERAGE_LIMITED"


class FeatureExplanationItem(BaseModel):
    feature_name: str
    feature_value: float
    contribution_sign: str = Field(..., description="'+' (supports class) or '-' (opposes class)")
    impact_weight: float = Field(..., description="Normalized contribution magnitude [0.0 - 1.0]")
    explanation_text: str


class ClassificationExplanation(BaseModel):
    predicted_class: str
    reasons: List[str] = Field(default_factory=list)
    top_supporting_features: List[FeatureExplanationItem] = Field(default_factory=list)
    top_opposing_features: List[FeatureExplanationItem] = Field(default_factory=list)
    alternative_class: Optional[str] = None
    alternative_probability: Optional[float] = None
    is_out_of_distribution: bool = False
    calibration_applied: bool = True


class ThermalClassificationResult(BaseModel):
    result_id: str
    source_id: str
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    predicted_class: str
    class_probabilities: Dict[str, float] = Field(default_factory=dict)
    model_name: str
    model_version: str
    feature_version: str
    model_confidence: float = Field(..., ge=0.0, le=1.0, description="Raw calibrated model softmax probability")
    system_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall system confidence incorporating data sufficiency")
    classification_state: str
    explanation: Dict[str, Any] = Field(default_factory=dict)
    data_quality: str = "VALID"
    created_at: datetime


class PerClassMetric(BaseModel):
    class_name: str
    precision: float
    recall: float
    f1_score: float
    support: int


class ModelStatusResponse(BaseModel):
    model_name: str
    model_version: str
    dataset_version: str
    feature_version: str
    trained_at: str
    primary_model_type: str
    fallback_model_type: str
    overall_accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class_metrics: List[PerClassMetric]
    confusion_matrix: List[List[int]]
    classes: List[str]
    training_sample_count: int
    validation_sample_count: int
    test_sample_count: int
    calibration_method: str
    is_production_ready: bool
    leakage_audit_passed: bool
    governance_status: str


class ControlledInferenceRequest(BaseModel):
    source_id: Optional[str] = None
    facility_id: Optional[str] = None
    features: Dict[str, float] = Field(default_factory=dict)
