"""
SIH26162 Phase 10 — Data Quality & Lineage Schemas

DataQualityState: GOOD | WARNING | DEGRADED | INVALID
AssessmentLineage: full data provenance chain for every IndustrialThermalAssessment
DataQualityReport: unified quality metrics
"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import ConfigDict


class DataQualityState(str, Enum):
    """Explicit data quality states. No silent degradation."""
    GOOD = "GOOD"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"


class AssessmentLineage(BaseModel):
    """
    Full data provenance chain for an IndustrialThermalAssessment.
    Every field links back to the specific input, version, or timestamp
    that produced the final assessment value.

    This enables reproducibility: given identical inputs and versions,
    the analytical output should be identical (within documented tolerance).
    """
    # Source observations
    source_observation_ids: List[str] = Field(
        default_factory=list,
        description="CanonicalThermalEvent IDs that contributed to this thermal source"
    )
    # Source object
    thermal_source_id: str = Field(description="ThermalSourceModel source_id")
    # Facility
    facility_id: Optional[str] = Field(
        default=None,
        description="Attributed IndustrialFacility ID (None if unattributed)"
    )
    # Baseline
    baseline_version: str = Field(
        default="NONE",
        description="Fingerprint baseline version used for abnormality assessment"
    )
    # ML classification
    classification_model_version: str = Field(
        default="UNKNOWN",
        description="ML classifier artifact version"
    )
    # Evidence fusion
    evidence_fusion_version: str = Field(
        default="UNKNOWN",
        description="Evidence fusion engine version"
    )
    # Risk algorithm
    risk_algorithm_version: str = Field(
        default="UNKNOWN",
        description="Industrial risk scoring algorithm version"
    )
    # Timestamps
    source_observation_start: Optional[datetime] = Field(
        default=None,
        description="Earliest contributing observation timestamp (UTC)"
    )
    source_observation_end: Optional[datetime] = Field(
        default=None,
        description="Latest contributing observation timestamp (UTC)"
    )
    processing_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when this assessment was computed (UTC)"
    )

    model_config = ConfigDict()


class DataQualityMetric(BaseModel):
    """A single data quality dimension."""
    state: DataQualityState
    value: Optional[float] = None
    note: Optional[str] = None


class DataQualityReport(BaseModel):
    """
    Unified data quality report for a thermal source or assessment.
    All dimensions are explicit — no silent drops.
    """
    overall_state: DataQualityState
    completeness: DataQualityMetric
    validity: DataQualityMetric
    timeliness: DataQualityMetric
    consistency: DataQualityMetric
    spatial_quality: DataQualityMetric
    source_provenance: DataQualityMetric
    duplicate_rate: DataQualityMetric
    missingness: DataQualityMetric
    observation_coverage: DataQualityMetric
    generated_at: Optional[datetime] = None

    model_config = ConfigDict()
