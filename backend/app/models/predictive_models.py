from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index
from datetime import datetime, timezone
from app.core.database import Base

class HazardPredictionRecord(Base):
    """
    Durable time-series table for short-horizon hazard trajectory predictions.
    Indexed for fast facility, asset, and time-range queries.
    """
    __tablename__ = "hazard_prediction_history"

    prediction_id = Column(String(64), primary_key=True, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    asset_id = Column(String(64), nullable=False, index=True)
    zone_id = Column(String(128), nullable=False, index=True)
    hazard_family = Column(String(64), nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, index=True)
    observation_window_start = Column(DateTime, nullable=False)
    observation_window_end = Column(DateTime, nullable=False)
    forecast_horizon = Column(String(16), default="10m")
    
    current_state = Column(String(32), default="NORMAL", index=True)
    predicted_state = Column(String(32), default="WATCH", index=True)
    trend = Column(String(32), default="STABLE")
    
    escalation_probability = Column(Float, nullable=False)
    calibrated_confidence = Column(Float, nullable=False)
    uncertainty_state = Column(String(32), default="CONFIRMED")
    
    anomaly_score = Column(Float, default=0.0)
    change_point_detected = Column(Boolean, default=False)
    change_point_strength = Column(Float, default=0.0)
    
    recommended_monitoring_level = Column(String(32), default="STANDARD")
    recommendation_reason = Column(String(256), nullable=True)
    
    data_sufficiency = Column(String(32), default="COMPLETE")
    telemetry_freshness = Column(String(32), default="LIVE")
    thermal_vision_available = Column(Boolean, default=True)
    is_simulated_pipeline = Column(Boolean, default=True)
    model_version = Column(String(64), default="v1.0.0-hazard-trajectory")
    baseline_version = Column(String(64), default="v1.0.0-dahej-base")
    
    top_contributing_features_json = Column(JSON, nullable=True)
    raw_metrics_json = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_pred_facility_time", "facility_id", "created_at"),
        Index("ix_pred_asset_time", "asset_id", "created_at"),
        Index("ix_pred_family_time", "hazard_family", "created_at"),
        Index("ix_pred_state_time", "predicted_state", "created_at"),
    )
