from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class AdaptiveMonitoringDecisionRecord(Base):
    """
    Durable, immutable audit table recording adaptive surveillance decisions,
    monitoring level transitions, requested evidence, and operator acknowledgements.
    """
    __tablename__ = "adaptive_monitoring_decision_history"

    decision_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(128), nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    
    monitoring_level = Column(String(32), nullable=False, index=True)
    previous_level = Column(String(32), nullable=False)
    hazard_state = Column(String(32), nullable=False, index=True)
    
    confidence = Column(Float, nullable=False)
    uncertainty_score = Column(Float, nullable=False)
    conflict_mass_k = Column(Float, default=0.0)
    
    facility_criticality = Column(String(32), default="TIER_1_CRITICAL")
    priority = Column(String(16), default="LOW", index=True)
    priority_score = Column(Float, default=10.0)
    
    reason = Column(Text, nullable=False)
    requested_evidence_json = Column(JSON, nullable=True)
    value_of_information_json = Column(JSON, nullable=True)
    applied_policy_json = Column(JSON, nullable=True)
    
    is_in_cooldown = Column(Boolean, default=False)
    cooldown_remaining_sec = Column(Float, default=0.0)
    
    acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_by = Column(String(64), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    is_live_data = Column(Boolean, default=False)
    is_simulated = Column(Boolean, default=True)
    orchestration_version = Column(String(64), default="v1.0.0-adaptive-risk-orchestrator")

    __table_args__ = (
        Index("ix_adapt_facility_time", "facility_id", "created_at"),
        Index("ix_adapt_level_time", "monitoring_level", "created_at"),
        Index("ix_adapt_priority_time", "priority", "created_at"),
    )
