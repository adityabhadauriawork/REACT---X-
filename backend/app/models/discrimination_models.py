from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, Text
from datetime import datetime, timezone
from app.core.database import Base

class ThermalSourceDiscriminationRecord(Base):
    """
    Durable, immutable audit table recording thermal source discrimination results,
    authoritative land-cover context, observation quality, EO verification, and evidence decomposition.
    """
    __tablename__ = "thermal_source_discrimination_history"

    assessment_id = Column(String(64), primary_key=True, index=True)
    source_id = Column(String(64), nullable=False, index=True)
    centroid_lat = Column(Float, nullable=False, index=True)
    centroid_lon = Column(Float, nullable=False, index=True)
    h3_index = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    
    # Classification
    predicted_class = Column(String(64), nullable=False, index=True)
    class_probabilities_json = Column(JSON, nullable=True)
    classification_state = Column(String(32), default="CLASSIFIED", index=True)
    model_confidence = Column(Float, nullable=False)
    system_confidence = Column(Float, nullable=False)
    evidence_sufficiency = Column(String(32), default="SUFFICIENT")
    
    # Source Spatiotemporal Behavior
    persistence_state = Column(String(32), default="PERSISTENT", index=True)
    observation_count = Column(Integer, default=1)
    mean_frp_mw = Column(Float, default=0.0)
    max_frp_mw = Column(Float, default=0.0)
    diurnal_night_fraction = Column(Float, default=0.5)
    spatial_dispersion_r95_m = Column(Float, default=50.0)
    
    # Facility Context
    facility_attribution_status = Column(String(64), default="UNATTRIBUTED")
    attributed_facility_id = Column(String(64), nullable=True, index=True)
    attributed_facility_name = Column(String(128), nullable=True)
    facility_distance_m = Column(Float, default=0.0)
    is_inside_facility = Column(Boolean, default=False)
    
    # Land Cover
    land_cover_class = Column(String(64), nullable=False, index=True)
    land_cover_dataset = Column(String(128), default="Copernicus Global Land Service / ESA WorldCover (10m)")
    land_cover_consistency = Column(Float, default=0.9)
    
    # Observation Quality
    observation_quality = Column(String(32), default="GOOD")
    quality_explanation = Column(Text, nullable=True)
    is_potential_reflection = Column(Boolean, default=False, index=True)
    
    # EO Verification
    eo_verification_json = Column(JSON, nullable=True)
    eo_verification_required = Column(Boolean, default=False)
    
    # Evidence & Abstention
    top_supporting_evidence_json = Column(JSON, nullable=True)
    top_opposing_evidence_json = Column(JSON, nullable=True)
    abstention_reason = Column(Text, nullable=True)
    
    is_live_data = Column(Boolean, default=False)
    is_simulated = Column(Boolean, default=True)
    discrimination_version = Column(String(64), default="v1.0.0-multimodal-discrimination")

    __table_args__ = (
        Index("ix_discrim_source_time", "source_id", "created_at"),
        Index("ix_discrim_class_time", "predicted_class", "created_at"),
        Index("ix_discrim_fac_time", "attributed_facility_id", "created_at"),
    )
