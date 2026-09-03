import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON, Index, Text
from app.core.database import Base

class IndustrialFacilityModel(Base):
    __tablename__ = "industrial_facilities"

    facility_id = Column(String, primary_key=True, index=True)
    source = Column(String, default="OSM", index=True, nullable=False)  # OSM, GEM, RECONCILED, BHUVAN, REGULATORY
    source_id = Column(String, index=True, nullable=True)
    name = Column(String, index=True, nullable=False)
    operator_name = Column(String, nullable=True)
    
    # Classification & Hierarchy
    facility_type = Column(String, index=True, nullable=False)  # PETROCHEMICAL, REFINERY, THERMAL_POWER, STEEL, CEMENT, MINING, CHEMICAL, FERTILIZER, OTHER_INDUSTRIAL
    subtype = Column(String, nullable=True)
    
    # Geography & Spatial Indexing
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    state = Column(String, default="Gujarat", index=True)
    district = Column(String, default="Bharuch", index=True)
    country = Column(String, default="India", index=True)
    cluster_name = Column(String, nullable=True, index=True)
    
    # Boundary & Footprint
    fence_radius_m = Column(Float, default=1000.0)
    boundary_geojson = Column(JSON, nullable=True)  # Polygon or MultiPolygon GeoJSON
    
    # Multi-Source Reconciliation & Data Provenance
    reconciliation_status = Column(String, default="SINGLE_SOURCE", index=True)  # SINGLE_SOURCE, RECONCILED_MATCH, UNRESOLVED_DISCREPANCY
    source_metadata = Column(JSON, default=dict)
    erdmp_license = Column(String, nullable=True)
    major_chemicals_stored = Column(JSON, default=list)
    
    # Lifecycle & Timestamps
    ingested_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_facility_lat_lon", "latitude", "longitude"),
        Index("idx_facility_state_district", "state", "district"),
        Index("idx_facility_type_source", "facility_type", "source"),
    )
