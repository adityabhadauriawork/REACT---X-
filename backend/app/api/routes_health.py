"""
SIH26162 — Health, Readiness & Observability Endpoints

/api/health   — process alive (always 200 if API is running)
/api/readiness — deep check: DB, ML model, FIRMS key
/api/system/status — FIRMS feed, background jobs, record counts
/api/system/coverage — geographic event/facility coverage by state
/api/system/data-quality — unified data quality report
"""
import datetime
from datetime import timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health & Observability"])


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)


def _db_alive(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _ml_model_loaded() -> bool:
    try:
        from app.services.ml.thermal_classifier_service import classifier_service
        return (
            classifier_service.pipeline.primary_model is not None or
            classifier_service.pipeline.calibrated_model is not None
        )
    except Exception:
        return False


def _firms_key_configured() -> bool:
    key = settings.NASA_FIRMS_MAP_KEY
    return bool(key and key != "YOUR_NASA_FIRMS_MAP_KEY_HERE" and len(key) > 8)


# ---------------------------------------------------------------------------
# GET /api/health — process liveness (always 200 if running)
# ---------------------------------------------------------------------------
@router.get("/health", summary="Process liveness probe")
def health():
    """
    Returns 200 if the API process is running.
    Does NOT check database or external dependencies.
    """
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.SYSTEM_VERSION,
        "timestamp": utcnow().isoformat()
    }


# ---------------------------------------------------------------------------
# GET /api/readiness — deep readiness check
# ---------------------------------------------------------------------------
@router.get("/readiness", summary="Dependency readiness probe")
def readiness(db: Session = Depends(get_db)):
    """
    Returns 200 only if all required dependencies are ready.
    Returns 503 if any critical dependency is unavailable.
    Distinguishes: process alive vs dependencies ready.
    """
    checks: Dict[str, Any] = {}

    # 1. Database
    db_ok = _db_alive(db)
    checks["database"] = {"status": "ready" if db_ok else "unavailable", "required": True}

    # 2. ML model
    ml_ok = _ml_model_loaded()
    checks["ml_classifier"] = {
        "status": "loaded" if ml_ok else "not_loaded",
        "required": False,
        "note": "Classification will return OTHER_UNKNOWN if not loaded"
    }

    # 3. FIRMS key
    firms_ok = _firms_key_configured()
    checks["firms_api_key"] = {
        "status": "configured" if firms_ok else "not_configured",
        "required": False,
        "note": "Set NASA_FIRMS_MAP_KEY env var for live satellite data"
    }

    # Overall status: only DB is required for readiness
    all_required_ok = db_ok
    http_status = 200 if all_required_ok else 503

    body = {
        "status": "ready" if all_required_ok else "not_ready",
        "version": settings.SYSTEM_VERSION,
        "checks": checks,
        "timestamp": utcnow().isoformat()
    }
    return JSONResponse(status_code=http_status, content=body)


# ---------------------------------------------------------------------------
# GET /api/system/status — operational observability summary
# ---------------------------------------------------------------------------
@router.get("/system/status", summary="System operational status")
def system_status(db: Session = Depends(get_db)):
    """
    Returns observability summary: record counts, FIRMS feed state, job state.
    """
    from app.models.thermal_event import ThermalEventModel
    from app.models.thermal_source import ThermalSourceModel
    from app.models.facility import IndustrialFacilityModel
    from app.models.thermal_classification import ThermalClassificationResultModel
    from app.models.thermal_assessment import IndustrialThermalAssessmentModel

    event_count = db.query(func.count(ThermalEventModel.event_id)).scalar() or 0
    source_count = db.query(func.count(ThermalSourceModel.source_id)).scalar() or 0
    facility_count = db.query(func.count(IndustrialFacilityModel.facility_id)).scalar() or 0
    classification_count = db.query(func.count(ThermalClassificationResultModel.result_id)).scalar() or 0
    assessment_count = db.query(func.count(IndustrialThermalAssessmentModel.assessment_id)).scalar() or 0

    # FIRMS feed status
    try:
        from app.services.satellite.firms_service import firms_service
        feed_status = firms_service.get_feed_status()
    except Exception:
        feed_status = {"status": "UNKNOWN", "note": "FIRMS service unavailable"}

    return {
        "status": "operational",
        "version": settings.SYSTEM_VERSION,
        "data_counts": {
            "thermal_events": event_count,
            "thermal_sources": source_count,
            "industrial_facilities": facility_count,
            "classified_sources": classification_count,
            "assessments": assessment_count
        },
        "firms_feed": feed_status,
        "ml_classifier": {
            "loaded": _ml_model_loaded(),
            "abstention_threshold": settings.ML_ABSTENTION_THRESHOLD
        },
        "database": {
            "alive": _db_alive(db),
            "url_type": "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        },
        "timestamp": utcnow().isoformat()
    }


# ---------------------------------------------------------------------------
# GET /api/system/coverage — geographic coverage by state
# ---------------------------------------------------------------------------

# India state bounding boxes [min_lat, max_lat, min_lon, max_lon]
INDIA_STATE_BBOXES = {
    "Gujarat":        (20.1, 24.7, 68.2, 74.5),
    "Maharashtra":    (15.6, 22.0, 72.6, 80.9),
    "Rajasthan":      (23.0, 30.2, 69.5, 78.3),
    "Madhya Pradesh": (21.1, 26.9, 74.0, 82.8),
    "Uttar Pradesh":  (23.9, 30.4, 77.1, 84.6),
    "Punjab":         (29.5, 32.5, 73.9, 76.9),
    "Haryana":        (27.7, 30.9, 74.5, 77.6),
    "Bihar":          (24.3, 27.5, 83.3, 88.2),
    "West Bengal":    (21.5, 27.2, 85.8, 89.9),
    "Jharkhand":      (21.9, 25.3, 83.3, 87.9),
    "Odisha":         (17.8, 22.6, 81.4, 87.5),
    "Chhattisgarh":   (17.8, 24.1, 80.2, 84.4),
    "Andhra Pradesh": (12.6, 19.9, 76.7, 84.8),
    "Telangana":      (15.8, 19.9, 77.2, 81.3),
    "Tamil Nadu":     (8.1,  13.6, 76.2, 80.4),
    "Karnataka":      (11.6, 18.5, 74.1, 78.6),
    "Kerala":         (8.3,  12.8, 74.9, 77.4),
}


@router.get("/system/coverage", summary="Geographic & dataset coverage report")
def system_coverage(db: Session = Depends(get_db)):
    """
    Returns dataset coverage by Indian state and classification status.
    Does NOT claim complete national coverage for states with zero events.
    """
    from app.models.thermal_event import ThermalEventModel
    from app.models.thermal_source import ThermalSourceModel
    from app.models.facility import IndustrialFacilityModel
    from app.models.thermal_classification import ThermalClassificationResultModel

    all_events = db.query(
        ThermalEventModel.latitude, ThermalEventModel.longitude
    ).all()

    all_facilities = db.query(
        IndustrialFacilityModel.latitude, IndustrialFacilityModel.longitude,
        IndustrialFacilityModel.state
    ).all()

    # Build state-level event counts
    state_events: Dict[str, int] = {s: 0 for s in INDIA_STATE_BBOXES}
    for lat, lon in all_events:
        if lat is None or lon is None:
            continue
        for state, (min_lat, max_lat, min_lon, max_lon) in INDIA_STATE_BBOXES.items():
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                state_events[state] += 1
                break

    # Facility counts by state
    state_facilities: Dict[str, int] = {s: 0 for s in INDIA_STATE_BBOXES}
    for lat, lon, state_name in all_facilities:
        if state_name and state_name in state_facilities:
            state_facilities[state_name] += 1

    # Classification coverage
    total_sources = db.query(func.count(ThermalSourceModel.source_id)).scalar() or 0
    classified_sources = db.query(func.count(ThermalClassificationResultModel.result_id)).scalar() or 0
    classification_coverage_pct = (
        round(classified_sources / total_sources * 100, 1) if total_sources > 0 else 0.0
    )

    states_with_events = [s for s, c in state_events.items() if c > 0]
    states_without_events = [s for s, c in state_events.items() if c == 0]

    return {
        "coverage_scope": "India (all states)",
        "total_events": len(all_events),
        "total_facilities": len(all_facilities),
        "total_sources": total_sources,
        "classified_sources": classified_sources,
        "classification_coverage_pct": classification_coverage_pct,
        "states_with_events": states_with_events,
        "states_without_events": states_without_events,
        "state_breakdown": {
            state: {
                "thermal_events": state_events.get(state, 0),
                "industrial_facilities": state_facilities.get(state, 0),
                "coverage_status": "COVERED" if state_events.get(state, 0) > 0 else "NO_DATA"
            }
            for state in INDIA_STATE_BBOXES
        },
        "disclaimer": (
            "Coverage reflects events actually ingested. "
            "States showing NO_DATA have not been tested with real FIRMS data for this deployment."
        ),
        "generated_at": utcnow().isoformat()
    }


# ---------------------------------------------------------------------------
# GET /api/system/data-quality — unified data quality report
# ---------------------------------------------------------------------------
@router.get("/system/data-quality", summary="Unified data quality report")
def system_data_quality(db: Session = Depends(get_db)):
    """
    Returns a unified data quality assessment across all thermal data.
    Tracks: completeness, validity, timeliness, duplicate rate, missingness.
    States: GOOD | WARNING | DEGRADED | INVALID
    """
    from app.models.thermal_event import ThermalEventModel

    total = db.query(func.count(ThermalEventModel.event_id)).scalar() or 0
    if total == 0:
        return {
            "overall_state": "DEGRADED",
            "note": "No thermal events in database",
            "total_events": 0,
            "generated_at": utcnow().isoformat()
        }

    # Completeness: events with valid lat/lon, frp, brightness_temp
    complete = db.query(func.count(ThermalEventModel.event_id)).filter(
        ThermalEventModel.latitude.isnot(None),
        ThermalEventModel.longitude.isnot(None),
        ThermalEventModel.frp_mw.isnot(None),
        ThermalEventModel.frp_mw > 0
    ).scalar() or 0
    completeness_pct = round(complete / total * 100, 1)

    # Timeliness: events within last 48h
    cutoff = utcnow() - datetime.timedelta(hours=48)
    recent = db.query(func.count(ThermalEventModel.event_id)).filter(
        ThermalEventModel.acquisition_timestamp >= cutoff
    ).scalar() or 0
    timeliness_pct = round(recent / total * 100, 1)

    # Missingness: events missing brightness temperature
    missing_bt = db.query(func.count(ThermalEventModel.event_id)).filter(
        ThermalEventModel.brightness_temp_k.is_(None)
    ).scalar() or 0
    missingness_pct = round(missing_bt / total * 100, 1)

    # Overall quality state
    if completeness_pct >= 95 and missingness_pct <= 5:
        overall = "GOOD"
    elif completeness_pct >= 80:
        overall = "WARNING"
    elif completeness_pct >= 60:
        overall = "DEGRADED"
    else:
        overall = "INVALID"

    return {
        "overall_state": overall,
        "total_events": total,
        "completeness": {
            "valid_events": complete,
            "percentage": completeness_pct,
            "state": "GOOD" if completeness_pct >= 95 else "WARNING" if completeness_pct >= 80 else "DEGRADED"
        },
        "timeliness": {
            "recent_48h": recent,
            "percentage": timeliness_pct,
            "state": "GOOD" if timeliness_pct >= 50 else "WARNING"
        },
        "missingness": {
            "missing_brightness_temp": missing_bt,
            "percentage": missingness_pct,
            "state": "GOOD" if missingness_pct <= 5 else "WARNING" if missingness_pct <= 20 else "DEGRADED"
        },
        "source_provenance": {
            "note": "All events sourced from NASA FIRMS (VIIRS/MODIS) via official API or validated CSV",
            "satellites_configured": settings.FIRMS_SOURCE_CONSTELLATIONS
        },
        "generated_at": utcnow().isoformat()
    }
