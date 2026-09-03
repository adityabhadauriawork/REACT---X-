import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, ForeignKey, Text
from app.core.database import Base


class ThermalClassificationResultModel(Base):
    """
    Thermal Classification Result Model.
    Stores auditable, versioned AI/ML multi-class inference results for thermal sources.
    """
    __tablename__ = "thermal_classification_results"

    result_id = Column(String, primary_key=True, index=True)  # e.g., CLS-SRC-20260830-001
    source_id = Column(String, index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=True)
    facility_name = Column(String, nullable=True)

    # Classification Outputs
    predicted_class = Column(String, index=True, nullable=False)  # TargetSourceClass enum
    class_probabilities = Column(JSON, nullable=False)             # Dict[class_name -> calibrated_prob]
    
    # Model Metadata & Provenance
    model_name = Column(String, nullable=False)                  # e.g., "SIH26162_ENSEMBLE_CLASSIFIER"
    model_version = Column(String, nullable=False)               # e.g., "v1.0.0"
    feature_version = Column(String, nullable=False)             # e.g., "THERMAL_FEATURES_v1"
    
    # Dual-Confidence Governance
    model_confidence = Column(Float, nullable=False)             # Calibrated softmax output [0.0 - 1.0]
    system_confidence = Column(Float, nullable=False)            # Overall system confidence [0.0 - 1.0]
    classification_state = Column(String, index=True, nullable=False)  # CLASSIFIED, NEEDS_REVIEW, etc.
    
    # Explainable Evidence Dossier
    explanation = Column(JSON, nullable=False)                   # Structured reasons & feature attributions
    
    # Quality & Lifecycle
    data_quality = Column(String, default="VALID")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_cls_src_time", "source_id", "created_at"),
        Index("idx_cls_pred_state", "predicted_class", "classification_state"),
    )
