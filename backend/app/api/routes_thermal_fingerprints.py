from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel, ThermalAbnormalityAssessmentModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.schemas.thermal_fingerprint import (
    FacilityThermalFingerprint,
    ThermalAbnormalityAssessment,
    ThermalHealthResponse,
    FingerprintFeatureVector,
    AbnormalityGeoJSONCollection,
    AbnormalityGeoJSONFeature,
    AbnormalityGeoJSONGeometry,
    AbnormalityGeoJSONProperties
)
from app.services.satellite.fingerprint_engine import fingerprint_engine
from app.services.satellite.abnormality_engine import abnormality_engine

router = APIRouter(prefix="/thermal", tags=["Thermal Fingerprints & Abnormality"])

@router.get("/fingerprints", response_model=List[Dict[str, Any]])
def get_thermal_fingerprints(
    facility_id: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    data_sufficiency: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns list of Facility and Source Thermal Fingerprints matching criteria.
    """
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    
    query = db.query(FacilityThermalFingerprintModel)
    if facility_id:
        query = query.filter(FacilityThermalFingerprintModel.facility_id == facility_id)
    if source_id:
        query = query.filter(FacilityThermalFingerprintModel.thermal_source_id == source_id)
    if data_sufficiency:
        query = query.filter(FacilityThermalFingerprintModel.data_sufficiency == data_sufficiency)

    fps = query.order_by(FacilityThermalFingerprintModel.observation_count.desc()).offset(offset).limit(limit).all()
    
    results = []
    for fp in fps:
        results.append({
            "fingerprint_id": fp.fingerprint_id,
            "facility_id": fp.facility_id,
            "facility_name": fp.facility_name,
            "thermal_source_id": fp.thermal_source_id,
            "baseline_start": fp.baseline_start.isoformat() if fp.baseline_start else None,
            "baseline_end": fp.baseline_end.isoformat() if fp.baseline_end else None,
            "observation_count": fp.observation_count,
            "active_days": fp.active_days,
            "recurrence_rate": fp.recurrence_rate,
            "detection_rate": fp.detection_rate,
            "frp_mean": fp.frp_mean,
            "frp_median": fp.frp_median,
            "frp_iqr": fp.frp_iqr,
            "frp_mad": fp.frp_mad,
            "frp_p10": fp.frp_p10,
            "frp_p50": fp.frp_p50,
            "frp_p90": fp.frp_p90,
            "frp_min": fp.frp_min,
            "frp_max": fp.frp_max,
            "temp_median": fp.temp_median,
            "temp_mean": fp.temp_mean,
            "diurnal_ratio": fp.diurnal_ratio,
            "night_fraction": fp.night_fraction,
            "spatial_stability_score": fp.spatial_stability_score,
            "spatial_dispersion_radius_m": fp.spatial_dispersion_radius_m,
            "centroid_lat": fp.centroid_lat,
            "centroid_lon": fp.centroid_lon,
            "data_sufficiency": fp.data_sufficiency,
            "baseline_version": fp.baseline_version,
            "last_updated": fp.last_updated.isoformat() if fp.last_updated else None
        })
    return results

@router.get("/fingerprints/{fingerprint_id}", response_model=Dict[str, Any])
def get_fingerprint_detail(
    fingerprint_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns deep-dive statistical fingerprint including hourly, seasonal, and sensor partitions.
    """
    fp = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.fingerprint_id == fingerprint_id
    ).first()
    if not fp:
        raise HTTPException(status_code=404, detail=f"Fingerprint {fingerprint_id} not found")

    return {
        "fingerprint_id": fp.fingerprint_id,
        "facility_id": fp.facility_id,
        "facility_name": fp.facility_name,
        "thermal_source_id": fp.thermal_source_id,
        "baseline_start": fp.baseline_start.isoformat() if fp.baseline_start else None,
        "baseline_end": fp.baseline_end.isoformat() if fp.baseline_end else None,
        "observation_count": fp.observation_count,
        "active_days": fp.active_days,
        "observation_opportunity_count": fp.observation_opportunity_count,
        "recurrence_rate": fp.recurrence_rate,
        "detection_rate": fp.detection_rate,
        "longest_active_run_days": fp.longest_active_run_days,
        "median_gap_days": fp.median_gap_days,
        "frp_statistics": {
            "mean": fp.frp_mean,
            "median": fp.frp_median,
            "std": fp.frp_std,
            "iqr": fp.frp_iqr,
            "mad": fp.frp_mad,
            "p10": fp.frp_p10,
            "p50": fp.frp_p50,
            "p90": fp.frp_p90,
            "min": fp.frp_min,
            "max": fp.frp_max
        },
        "temp_statistics": {
            "mean": fp.temp_mean,
            "median": fp.temp_median,
            "std": fp.temp_std,
            "p10": fp.temp_p10,
            "p50": fp.temp_p50,
            "p90": fp.temp_p90,
            "max": fp.temp_max
        },
        "day_count": fp.day_count,
        "night_count": fp.night_count,
        "diurnal_ratio": fp.diurnal_ratio,
        "night_fraction": fp.night_fraction,
        "hourly_distribution": fp.hourly_distribution or {},
        "monthly_statistics": fp.monthly_statistics or {},
        "seasonal_statistics": fp.seasonal_statistics or {},
        "sensor_statistics": fp.sensor_statistics or {},
        "satellite_coverage": fp.satellite_coverage or {},
        "centroid_lat": fp.centroid_lat,
        "centroid_lon": fp.centroid_lon,
        "spatial_stability_score": fp.spatial_stability_score,
        "spatial_dispersion_radius_m": fp.spatial_dispersion_radius_m,
        "bounding_box": fp.bounding_box,
        "data_sufficiency": fp.data_sufficiency,
        "fingerprint_version": fp.fingerprint_version,
        "baseline_version": fp.baseline_version,
        "last_updated": fp.last_updated.isoformat() if fp.last_updated else None
    }

@router.get("/facilities/{facility_id}/thermal-health", response_model=ThermalHealthResponse)
def get_facility_thermal_health(
    facility_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns comprehensive Facility Thermal Health Dossier for the Facility Profile UI.
    """
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    
    facility = db.query(IndustrialFacilityModel).filter(
        IndustrialFacilityModel.facility_id == facility_id
    ).first()
    if not facility:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")

    fp = db.query(FacilityThermalFingerprintModel).filter(
        FacilityThermalFingerprintModel.facility_id == facility_id
    ).first()

    sources = db.query(ThermalSourceModel).filter(
        ThermalSourceModel.primary_attributed_facility_id == facility_id
    ).all()

    # Query latest assessment
    latest_assessment = db.query(ThermalAbnormalityAssessmentModel).filter(
        ThermalAbnormalityAssessmentModel.facility_id == facility_id
    ).order_by(ThermalAbnormalityAssessmentModel.assessment_time.desc()).first()

    # If no assessment yet, run one dynamically
    if not latest_assessment and sources:
        latest_assessment = abnormality_engine.assess_thermal_source(sources[0], None, db)

    # Compile Sparkline
    sparkline = []
    if sources:
        s_ids = [s.source_id for s in sources]
        recent_events = db.query(ThermalSourceEventModel).filter(
            ThermalSourceEventModel.source_id.in_(s_ids)
        ).order_by(ThermalSourceEventModel.acquisition_timestamp.asc()).limit(30).all()

        for ev in recent_events:
            sparkline.append({
                "timestamp": ev.acquisition_timestamp.isoformat(),
                "frp_mw": ev.frp_mw,
                "satellite": ev.satellite,
                "day_night": ev.day_night
            })

    # Determine status and metrics
    status = latest_assessment.status if latest_assessment else ("EXPECTED_PERSISTENT" if fp and fp.data_sufficiency != "INSUFFICIENT_HISTORY" else "INSUFFICIENT_HISTORY")
    score = latest_assessment.overall_abnormality_score if latest_assessment else (15.0 if fp else 5.0)
    conf = latest_assessment.confidence if latest_assessment else (0.80 if fp and fp.data_sufficiency != "INSUFFICIENT_HISTORY" else 0.35)
    
    current_frp = latest_assessment.current_frp_mw if latest_assessment else (fp.frp_p50 if fp else 0.0)
    median_frp = fp.frp_median if fp else 0.0
    iqr_frp = fp.frp_iqr if fp else 0.0
    p90_frp = fp.frp_p90 if fp else 0.0
    p10_frp = fp.frp_p10 if fp else 0.0
    
    dev_ratio = round(current_frp / max(1.0, median_frp), 2)
    
    trend = "STABLE"
    if dev_ratio >= 2.0:
        trend = "ELEVATED_SPIKE"
    elif dev_ratio >= 1.4:
        trend = "GRADUAL_INCREASE"
    elif dev_ratio <= 0.6 and current_frp > 0:
        trend = "COOLING_DECREASE"

    evidence_reasons = latest_assessment.evidence.get("reasons", []) if latest_assessment and latest_assessment.evidence else [
        f"Operating within historical baseline parameters ({p10_frp:.1f} - {p90_frp:.1f} MW)",
        f"Verified across {fp.observation_count if fp else 0} satellite passes"
    ]

    last_obs_time = sources[0].last_detected if sources else None

    return ThermalHealthResponse(
        facility_id=facility.facility_id,
        facility_name=facility.name,
        facility_type=facility.facility_type,
        state=facility.state,
        district=facility.district,
        thermal_health_status=status,
        overall_abnormality_score=score,
        confidence=conf,
        data_sufficiency=fp.data_sufficiency if fp else "INSUFFICIENT_HISTORY",
        current_frp_mw=current_frp,
        historical_median_frp_mw=median_frp,
        historical_iqr_frp_mw=iqr_frp,
        historical_p90_frp_mw=p90_frp,
        historical_range_mw=[p10_frp, p90_frp],
        frp_deviation_ratio=dev_ratio,
        recent_trend=trend,
        active_days_total=fp.active_days if fp else 0,
        recurrence_rate=fp.recurrence_rate if fp else 0.0,
        diurnal_ratio=fp.diurnal_ratio if fp else 1.0,
        night_fraction=fp.night_fraction if fp else 0.5,
        spatial_stability_score=fp.spatial_stability_score if fp else 1.0,
        last_observation_timestamp=last_obs_time,
        active_sources_count=len(sources),
        evidence_reasons=evidence_reasons,
        timeline_sparkline=sparkline,
        fingerprint_id=fp.fingerprint_id if fp else None,
        baseline_version=fp.baseline_version if fp else "v1.0"
    )

@router.get("/abnormalities", response_model=List[Dict[str, Any]])
def get_thermal_abnormalities(
    status: Optional[str] = Query(None),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    facility_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Lists active thermal abnormality assessments.
    """
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    
    query = db.query(ThermalAbnormalityAssessmentModel).filter(
        ThermalAbnormalityAssessmentModel.overall_abnormality_score >= min_score
    )
    if status:
        query = query.filter(ThermalAbnormalityAssessmentModel.status == status)
    if facility_id:
        query = query.filter(ThermalAbnormalityAssessmentModel.facility_id == facility_id)

    assessments = query.order_by(ThermalAbnormalityAssessmentModel.overall_abnormality_score.desc()).limit(limit).all()

    # If empty, generate assessments for all existing thermal sources
    if not assessments:
        sources = db.query(ThermalSourceModel).all()
        for src in sources:
            abnormality_engine.assess_thermal_source(src, None, db)
        assessments = query.order_by(ThermalAbnormalityAssessmentModel.overall_abnormality_score.desc()).limit(limit).all()

    results = []
    for a in assessments:
        results.append({
            "assessment_id": a.assessment_id,
            "source_id": a.source_id,
            "facility_id": a.facility_id,
            "facility_name": a.facility_name,
            "assessment_time": a.assessment_time.isoformat(),
            "current_frp_mw": a.current_frp_mw,
            "current_temp_k": a.current_temp_k,
            "current_lat": a.current_lat,
            "current_lon": a.current_lon,
            "frp_deviation": a.frp_deviation,
            "frp_robust_zscore": a.frp_robust_zscore,
            "overall_abnormality_score": a.overall_abnormality_score,
            "confidence": a.confidence,
            "status": a.status,
            "evidence": a.evidence or {},
            "baseline_version": a.baseline_version,
            "algorithm_version": a.algorithm_version
        })
    return results

@router.get("/abnormalities/geojson", response_model=AbnormalityGeoJSONCollection)
def get_abnormalities_geojson(
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    db: Session = Depends(get_db)
):
    """
    Returns RFC 7946 GeoJSON FeatureCollection of abnormality assessments for Leaflet GIS rendering.
    """
    fingerprint_engine.seed_initial_fingerprints_if_empty(db)
    
    assessments = db.query(ThermalAbnormalityAssessmentModel).filter(
        ThermalAbnormalityAssessmentModel.overall_abnormality_score >= min_score
    ).all()

    if not assessments:
        sources = db.query(ThermalSourceModel).all()
        for src in sources:
            abnormality_engine.assess_thermal_source(src, None, db)
        assessments = db.query(ThermalAbnormalityAssessmentModel).all()

    features = []
    for a in assessments:
        reasons = a.evidence.get("reasons", []) if a.evidence else []
        feat = AbnormalityGeoJSONFeature(
            type="Feature",
            geometry=AbnormalityGeoJSONGeometry(
                type="Point",
                coordinates=[a.current_lon, a.current_lat]
            ),
            properties=AbnormalityGeoJSONProperties(
                assessment_id=a.assessment_id,
                source_id=a.source_id,
                facility_id=a.facility_id,
                facility_name=a.facility_name,
                status=a.status,
                overall_abnormality_score=a.overall_abnormality_score,
                confidence=a.confidence,
                current_frp_mw=a.current_frp_mw,
                frp_deviation=a.frp_deviation,
                reasons=reasons,
                assessment_time=a.assessment_time.isoformat()
            )
        )
        features.append(feat)

    return AbnormalityGeoJSONCollection(
        type="FeatureCollection",
        features=features,
        metadata={
            "total_assessments": len(features),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "version": "1.0"
        }
    )

@router.get("/abnormalities/{assessment_id}", response_model=Dict[str, Any])
def get_abnormality_detail(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns single abnormality assessment dossier with complete evidence and metric breakdowns.
    """
    a = db.query(ThermalAbnormalityAssessmentModel).filter(
        ThermalAbnormalityAssessmentModel.assessment_id == assessment_id
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")

    return {
        "assessment_id": a.assessment_id,
        "source_id": a.source_id,
        "facility_id": a.facility_id,
        "facility_name": a.facility_name,
        "assessment_time": a.assessment_time.isoformat(),
        "current_frp_mw": a.current_frp_mw,
        "current_temp_k": a.current_temp_k,
        "current_lat": a.current_lat,
        "current_lon": a.current_lon,
        "frp_deviation": a.frp_deviation,
        "frp_robust_zscore": a.frp_robust_zscore,
        "frp_standard_zscore": a.frp_standard_zscore,
        "frp_percentile": a.frp_percentile,
        "temperature_deviation": a.temperature_deviation,
        "temperature_percentile": a.temperature_percentile,
        "frequency_deviation": a.frequency_deviation,
        "spatial_change_score": a.spatial_change_score,
        "spatial_displacement_m": a.spatial_displacement_m,
        "diurnal_deviation": a.diurnal_deviation,
        "seasonal_deviation": a.seasonal_deviation,
        "overall_abnormality_score": a.overall_abnormality_score,
        "confidence": a.confidence,
        "status": a.status,
        "evidence": a.evidence or {},
        "feature_vector": a.feature_vector or {},
        "baseline_version": a.baseline_version,
        "algorithm_version": a.algorithm_version,
        "created_at": a.created_at.isoformat()
    }

@router.get("/ml-features", response_model=List[Dict[str, Any]])
def get_ml_features(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Phase 7 ML Feature Export Interface.
    Returns normalized feature vectors prepared for ML classifier consumption.
    """
    assessments = db.query(ThermalAbnormalityAssessmentModel).order_by(
        ThermalAbnormalityAssessmentModel.assessment_time.desc()
    ).limit(limit).all()

    return [a.feature_vector for a in assessments if a.feature_vector]

@router.post("/fingerprints/recalculate", response_model=Dict[str, Any])
@router.post("/baselines/recalculate", response_model=Dict[str, Any])
def recalculate_all_fingerprints(
    db: Session = Depends(get_db)
):
    """
    Triggers batch recalculation of all facility baselines and assessments from database observations.
    """
    facilities = db.query(IndustrialFacilityModel).all()
    fp_updated = 0
    for fac in facilities:
        fp = fingerprint_engine.calculate_facility_fingerprint(fac.facility_id, db)
        if fp:
            fp_updated += 1

    sources = db.query(ThermalSourceModel).all()
    ass_updated = 0
    for src in sources:
        ass = abnormality_engine.assess_thermal_source(src, None, db)
        if ass:
            ass_updated += 1

    return {
        "status": "SUCCESS",
        "facilities_recalculated": fp_updated,
        "assessments_updated": ass_updated,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0"
    }

# Aliases for canonical nomenclature
@router.get("/baselines", response_model=List[Dict[str, Any]])
def get_thermal_baselines_alias(
    facility_id: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    data_sufficiency: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return get_thermal_fingerprints(facility_id, source_id, data_sufficiency, limit, offset, db)

@router.get("/baselines/{fingerprint_id}", response_model=Dict[str, Any])
def get_thermal_baseline_detail_alias(
    fingerprint_id: str,
    db: Session = Depends(get_db)
):
    return get_thermal_fingerprint_detail(fingerprint_id, db)

@router.get("/facilities/{facility_id}/profile", response_model=Dict[str, Any])
def get_facility_thermal_profile_alias(
    facility_id: str,
    db: Session = Depends(get_db)
):
    return get_facility_thermal_health(facility_id, db)

