import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index
)
from app.core.database import Base


class IndustrialThermalAssessmentModel(Base):
    """
    SQLAlchemy model for persistent storage of Phase 9 Industrial Thermal Assessments.
    Stores full audit trail, 4 confidences, multi-factor risk, evidence items, and handoff state.
    """
    __tablename__ = "industrial_thermal_assessments"

    assessment_id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("thermal_source_objects.source_id"), index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=True)
    facility_name = Column(String, nullable=True)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)

    # 4 Independent Confidences
    attribution_confidence = Column(Float, nullable=False)
    classification_confidence = Column(Float, nullable=False)
    abnormality_confidence = Column(Float, nullable=False)
    overall_evidence_confidence = Column(Float, nullable=False)

    # Analytical outputs
    classification = Column(String, nullable=False)
    classification_probabilities = Column(JSON, nullable=False)
    abnormality_score = Column(Float, nullable=False)
    abnormality_status = Column(String, nullable=False)
    robust_zscore = Column(Float, default=0.0)
    attribution_status = Column(String, default="ATTRIBUTED_HIGH_CONFIDENCE")
    corroboration_status = Column(String, nullable=False)

    # Industrial Risk
    industrial_risk_level = Column(String, nullable=False)
    industrial_risk_score = Column(Float, nullable=False)
    risk_confidence = Column(Float, nullable=False)
    risk_label = Column(String, default="SCREENING-LEVEL INDUSTRIAL RISK")

    # Operational status
    is_routine_operation = Column(Boolean, default=True)
    operational_concern_summary = Column(String, nullable=False)
    evidence_summary = Column(String, nullable=False)
    evidence_items = Column(JSON, nullable=False)

    # Handoff state
    handoff_eligibility = Column(String, nullable=False)
    incident_draft = Column(JSON, nullable=True)

    # Lifecycle & Versioning
    assessment_status = Column(String, default="INITIAL", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    parent_assessment_id = Column(String, nullable=True)

    classification_model_version = Column(String, default="IHS_INDIA_HGB_v1.0")
    abnormality_algorithm_version = Column(String, default="TF-LEVEL5-v1.0")
    attribution_algorithm_version = Column(String, default="OSM-GEM-H3-v1.0")
    evidence_fusion_version = Column(String, default="EFE-4TIER-v1.0")
    risk_algorithm_version = Column(String, default="MFR-SCREENING-v1.0")

    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_assessments_facility_risk", "facility_id", "industrial_risk_level"),
        Index("ix_assessments_source_version", "source_id", "version"),
    )
