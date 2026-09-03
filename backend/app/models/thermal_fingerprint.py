import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, JSON, Index, ForeignKey, Text
from app.core.database import Base

class FacilityThermalFingerprintModel(Base):
    """
    Facility Thermal Fingerprint Model.
    Stores the empirical, multi-dimensional historical behavioral profile of a facility or persistent source.
    """
    __tablename__ = "facility_thermal_fingerprints"

    fingerprint_id = Column(String, primary_key=True, index=True)  # e.g., FP-FAC-IND-OSM-DAHEJ-01
    facility_id = Column(String, index=True, nullable=False)
    facility_name = Column(String, nullable=True)
    thermal_source_id = Column(String, index=True, nullable=True)
    
    # Baseline Observation Window
    baseline_start = Column(DateTime, nullable=False)
    baseline_end = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)
    
    # Temporal & Opportunity Metrics
    observation_count = Column(Integer, default=0, index=True)
    active_days = Column(Integer, default=0)
    observation_opportunity_count = Column(Integer, default=1)
    recurrence_rate = Column(Float, default=0.0)  # active_days / total_calendar_days
    detection_rate = Column(Float, default=0.0)   # observation_count / observation_opportunity_count
    longest_active_run_days = Column(Integer, default=0)
    median_gap_days = Column(Float, default=0.0)
    
    # Robust FRP Statistics (Level 2)
    frp_mean = Column(Float, default=0.0)
    frp_median = Column(Float, default=0.0)
    frp_std = Column(Float, default=0.0)
    frp_iqr = Column(Float, default=0.0)
    frp_mad = Column(Float, default=0.0)  # Median Absolute Deviation
    frp_p10 = Column(Float, default=0.0)
    frp_p50 = Column(Float, default=0.0)
    frp_p90 = Column(Float, default=0.0)
    frp_min = Column(Float, default=0.0)
    frp_max = Column(Float, default=0.0)
    
    # Brightness Temperature Statistics
    temp_mean = Column(Float, nullable=True)
    temp_median = Column(Float, nullable=True)
    temp_std = Column(Float, nullable=True)
    temp_iqr = Column(Float, nullable=True)
    temp_p10 = Column(Float, nullable=True)
    temp_p50 = Column(Float, nullable=True)
    temp_p90 = Column(Float, nullable=True)
    temp_max = Column(Float, nullable=True)
    
    # Diurnal & Hourly Behavioral Signatures
    day_count = Column(Integer, default=0)
    night_count = Column(Integer, default=0)
    diurnal_ratio = Column(Float, default=1.0)  # (day + 0.1) / (night + 0.1)
    night_fraction = Column(Float, default=0.5)
    hourly_distribution = Column(JSON, default=dict)  # {"00": count, "01": count, ...}
    
    # Seasonal & Monthly Baselines
    monthly_statistics = Column(JSON, default=dict)   # {"01": {"median_frp": X, "count": Y}, ...}
    seasonal_statistics = Column(JSON, default=dict)  # {"WINTER": ..., "SUMMER": ..., "MONSOON": ...}
    
    # Sensor & Satellite Breakdown
    sensor_statistics = Column(JSON, default=dict)    # {"VIIRS_375M": {...}, "MODIS_1KM": {...}}
    satellite_coverage = Column(JSON, default=dict)   # {"NOAA-20": count, "SUOMI-NPP": count, ...}
    
    # Spatial Footprint & Stability
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    spatial_stability_score = Column(Float, default=1.0)      # 0.0 (erratic/moving) to 1.0 (highly fixed)
    spatial_dispersion_radius_m = Column(Float, default=0.0)  # 95th percentile distance from centroid
    bounding_box = Column(JSON, nullable=True)               # [min_lon, min_lat, max_lon, max_lat]
    
    # Data Sufficiency & Governance
    data_sufficiency = Column(String, default="INSUFFICIENT_HISTORY", index=True)  # INSUFFICIENT_HISTORY, LIMITED_HISTORY, ESTABLISHED_BASELINE, STRONG_BASELINE
    fingerprint_version = Column(String, default="1.0")
    baseline_version = Column(String, default="v1.0")

    __table_args__ = (
        Index("idx_fp_fac_src", "facility_id", "thermal_source_id"),
        Index("idx_fp_sufficiency", "data_sufficiency", "observation_count"),
        Index("idx_fp_centroid", "centroid_lat", "centroid_lon"),
    )


class ThermalAbnormalityAssessmentModel(Base):
    """
    Thermal Abnormality Assessment Model.
    Stores multi-signal analytical assessments comparing current observations against empirical fingerprints.
    """
    __tablename__ = "thermal_abnormality_assessments"

    assessment_id = Column(String, primary_key=True, index=True)  # e.g., ABN-20260830-SRC-01
    source_id = Column(String, index=True, nullable=False)
    facility_id = Column(String, index=True, nullable=True)
    facility_name = Column(String, nullable=True)
    assessment_time = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    
    # Current Observation Snapshot
    current_frp_mw = Column(Float, nullable=False)
    current_temp_k = Column(Float, nullable=True)
    current_lat = Column(Float, nullable=False)
    current_lon = Column(Float, nullable=False)
    
    # Multi-Dimensional Deviation Features
    frp_deviation = Column(Float, default=1.0)       # Ratio: current_frp / baseline_median
    frp_robust_zscore = Column(Float, default=0.0)   # (current_frp - median) / (1.4826 * MAD)
    frp_standard_zscore = Column(Float, default=0.0) # (current_frp - mean) / std (where applicable)
    frp_percentile = Column(Float, default=50.0)     # Percentile position in historical distribution
    
    temperature_deviation = Column(Float, default=0.0)  # Delta Kelvin from baseline median
    temperature_percentile = Column(Float, nullable=True)
    
    frequency_deviation = Column(Float, default=1.0)    # Recent observation surge ratio
    spatial_change_score = Column(Float, default=0.0)   # Centroid displacement (m) / dispersion
    spatial_displacement_m = Column(Float, default=0.0)
    
    diurnal_deviation = Column(Float, default=0.0)      # Shift in day/night probability
    seasonal_deviation = Column(Float, default=1.0)     # Deviation adjusted for current season
    
    # Overall Synthetic Scores (Strictly Separated)
    overall_abnormality_score = Column(Float, default=0.0, index=True)  # 0.0 to 100.0 (Severity of deviation)
    confidence = Column(Float, default=0.5, index=True)                 # 0.0 to 1.0 (Evidence strength)
    
    # Status & Explainability
    status = Column(String, default="NORMAL_BASELINE", index=True)
    # Status values:
    # NORMAL_BASELINE, EXPECTED_PERSISTENT, RECURRING, WATCH, ABNORMAL_THERMAL_BEHAVIOUR, INSUFFICIENT_HISTORY, DATA_QUALITY_LIMITED
    
    evidence = Column(JSON, default=dict)  # List of reason bullets, statistical comparisons, observation tallies
    feature_vector = Column(JSON, default=dict)  # Normalized features prepared for Phase 7 ML Classifier
    
    # Governance & Provenance
    baseline_version = Column(String, default="v1.0")
    algorithm_version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_abn_status_score", "status", "overall_abnormality_score"),
        Index("idx_abn_fac_time", "facility_id", "assessment_time"),
        Index("idx_abn_source_time", "source_id", "assessment_time"),
    )
