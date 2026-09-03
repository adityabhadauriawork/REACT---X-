from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class ThermalEvidenceBundleModel(Base):
    """
    Persistent table for multi-satellite corroboration evidence bundles.
    Fuses NASA FIRMS, VIIRS Nightfire, INSAT geostationary, Sentinel-2 SWIR, and Landsat TIRS.
    """
    __tablename__ = "thermal_evidence_bundles"

    bundle_id = Column(String(64), primary_key=True, index=True)
    thermal_source_id = Column(String(64), ForeignKey("thermal_source_objects.source_id"), nullable=True, index=True)
    facility_id = Column(String(64), nullable=True, index=True)
    facility_name = Column(String(255), nullable=True)
    
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)

    # Fusion State & Overall Confidence
    evidence_status = Column(String(32), nullable=False, index=True)  # SINGLE_SOURCE, MULTI_SOURCE, CORROBORATED, etc.
    overall_evidence_confidence = Column(Float, nullable=False, default=0.50)

    # Counters
    source_count = Column(Integer, nullable=False, default=1)
    satellite_count = Column(Integer, nullable=False, default=1)
    independent_satellite_count = Column(Integer, nullable=False, default=1)

    # Multi-Component Agreement JSON structures
    temporal_agreement = Column(JSON, nullable=False)
    spatial_agreement = Column(JSON, nullable=False)
    thermal_agreement = Column(JSON, nullable=False)

    # High-Resolution Spatial Context
    image_confirmation_status = Column(String(32), nullable=False, default="NOT_REQUESTED")
    image_confirmation = Column(JSON, nullable=True)

    # Explainability Dossier
    primary_corroboration_summary = Column(Text, nullable=True)
    supporting_reasons = Column(JSON, nullable=False, default=list)
    conflicting_reasons = Column(JSON, nullable=False, default=list)
    limitations_and_uncertainties = Column(JSON, nullable=False, default=list)

    # Versioning & Audit
    fusion_algorithm_version = Column(String(32), nullable=False, default="v1.0.0")
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationship to members
    members = relationship("ThermalEvidenceMemberModel", back_populates="bundle", cascade="all, delete-orphan")


class ThermalEvidenceMemberModel(Base):
    """
    Individual sensor observations comprising a multi-satellite evidence bundle.
    """
    __tablename__ = "thermal_evidence_members"

    member_id = Column(String(64), primary_key=True, index=True)
    bundle_id = Column(String(64), ForeignKey("thermal_evidence_bundles.bundle_id"), nullable=False, index=True)

    satellite_name = Column(String(64), nullable=False)
    sensor_name = Column(String(64), nullable=False)
    source_product = Column(String(64), nullable=False)
    processing_version = Column(String(32), nullable=False, default="v1.0")
    role = Column(String(64), nullable=False)
    observation_status = Column(String(32), nullable=False, default="OBSERVED")
    
    acquisition_timestamp = Column(DateTime, nullable=True)
    spatial_distance_m = Column(Float, nullable=True)
    temporal_offset_min = Column(Float, nullable=True)

    measured_values = Column(JSON, nullable=False, default=dict)
    data_quality = Column(String(32), nullable=False, default="GOOD")
    quality_flags = Column(JSON, nullable=False, default=dict)

    is_dependent_on_member_id = Column(String(64), nullable=True)
    dependency_group_id = Column(String(64), nullable=True)
    evidence_weight = Column(Float, nullable=False, default=1.0)
    evidence_contribution_sign = Column(String(8), nullable=False, default="+")
    explanation_text = Column(Text, nullable=True)

    bundle = relationship("ThermalEvidenceBundleModel", back_populates="members")
