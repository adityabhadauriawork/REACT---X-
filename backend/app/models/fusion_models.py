from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class FusedHazardAssessmentRecord(Base):
    """
    Durable time-series persistence for multimodal fused hazard assessments.
    """
    __tablename__ = "fused_hazard_assessment_history"

    assessment_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(128), nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, index=True)
    assessment_window_start = Column(DateTime, nullable=False)
    assessment_window_end = Column(DateTime, nullable=False)
    
    hazard_family = Column(String(64), nullable=False, index=True)
    fused_state = Column(String(32), nullable=False, index=True)
    
    confidence = Column(Float, nullable=False)
    uncertainty_score = Column(Float, nullable=False)
    conflict_mass_k = Column(Float, default=0.0)
    
    recommended_action = Column(String(64), default="ROUTINE_MONITORING")
    recommended_action_detail = Column(String(256), nullable=True)
    human_review_required = Column(Boolean, default=False)
    
    is_live_data = Column(Boolean, default=False)
    is_simulated = Column(Boolean, default=True)
    fusion_engine_version = Column(String(64), default="v1.0.0-dempster-shafer-multimodal")
    
    dempster_shafer_json = Column(JSON, nullable=True)
    agreement_matrix_json = Column(JSON, nullable=True)
    top_supporting_evidence_json = Column(JSON, nullable=True)
    timeline_events_json = Column(JSON, nullable=True)
    data_lineage_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_fuse_facility_time", "facility_id", "created_at"),
        Index("ix_fuse_asset_time", "asset_id", "created_at"),
        Index("ix_fuse_state_time", "fused_state", "created_at"),
        Index("ix_fuse_family_time", "hazard_family", "created_at"),
    )
