from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.schemas.thermal_corroboration import (
    ThermalEvidenceBundle,
    SatelliteHealthStatus,
    OnDemandImageConfirmation,
    CorroborationRequest,
    EvidenceState
)
from app.models.thermal_corroboration import (
    ThermalEvidenceBundleModel,
    ThermalEvidenceMemberModel
)
from app.models.thermal_source import ThermalSourceModel
from app.models.thermal_event import ThermalEventModel
from app.services.satellite.evidence_fusion_engine import (
    evidence_fusion_engine,
    SATELLITE_REGISTRY
)

# Router for Satellite Health & Availability
satellite_router = APIRouter(prefix="/satellite", tags=["Satellite Systems & Health"])

# Router for Thermal Evidence & Corroboration
evidence_router = APIRouter(prefix="/thermal", tags=["Thermal Evidence & Multi-Satellite Fusion"])


# =============================================================================
# SATELLITE HEALTH & AVAILABILITY ENDPOINTS
# =============================================================================

@satellite_router.get("/health", response_model=List[SatelliteHealthStatus])
def get_satellite_constellation_health():
    """
    Get operational telemetry, nominal revisit schedule, and health status
    for all integrated multi-tier satellite platforms (VIIRS, MODIS, Nightfire, INSAT, Sentinel, Landsat).
    """
    return evidence_fusion_engine.get_satellite_health_status()


@satellite_router.get("/availability")
def get_satellite_availability_matrix():
    """
    Get geographic coverage, sensor capabilities, and access status matrix for satellite constellations.
    """
    matrix = []
    for sat_id, meta in SATELLITE_REGISTRY.items():
        matrix.append({
            "satellite_id": sat_id,
            "sensor": meta.get("sensor", "IMAGER"),
            "tier": meta["tier"],
            "role": meta["role"],
            "integration_status": "AVAILABLE_OPERATIONAL",
            "spatial_resolution": meta["resolution"],
            "temporal_revisit": meta["revisit"],
            "typical_latency": meta["latency"],
            "spectral_channels": meta["spectral_capabilities"],
            "is_on_demand_context": "TIER_4" in meta["tier"]
        })
    return {
        "constellation_count": len(matrix),
        "tiers_active": ["TIER_1_DETECTION", "TIER_2_CHARACTERIZATION", "TIER_3_TEMPORAL", "TIER_4_CONTEXT"],
        "matrix": matrix
    }


# =============================================================================
# THERMAL EVIDENCE BUNDLE & CORROBORATION ENDPOINTS
# =============================================================================

@evidence_router.get("/sources/{source_id}/evidence", response_model=ThermalEvidenceBundle)
def get_thermal_source_evidence_bundle(
    source_id: str,
    include_optical: bool = Query(True, description="Include on-demand Sentinel-2/Landsat context"),
    db: Session = Depends(get_db)
):
    """
    Get or compute the authoritative multi-satellite evidence bundle for a ThermalSourceObject.
    """
    # 1. Look up source in database
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal source {source_id} not found.")

    # 2. Check if a recent evidence bundle exists in database
    cached_bundle = db.query(ThermalEvidenceBundleModel).filter(
        ThermalEvidenceBundleModel.thermal_source_id == source_id
    ).first()

    if cached_bundle and not include_optical:
        return _bundle_model_to_schema(cached_bundle, db)

    # 3. Perform fresh fusion calculation & persist
    req = CorroborationRequest(
        source_id=source_id,
        include_on_demand_optical=include_optical
    )
    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db, req=req)
    evidence_fusion_engine.persist_evidence_bundle(bundle=bundle, db=db)
    return bundle


@evidence_router.get("/sources/{source_id}/corroboration")
def get_source_corroboration_summary(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a high-level summary of multi-satellite corroboration for a thermal source.
    """
    bundle = get_thermal_source_evidence_bundle(source_id=source_id, include_optical=True, db=db)
    return {
        "source_id": bundle.thermal_source_id,
        "facility_name": bundle.facility_name,
        "evidence_status": bundle.evidence_status,
        "overall_evidence_confidence": bundle.overall_evidence_confidence,
        "satellite_count": bundle.satellite_count,
        "independent_satellite_count": bundle.independent_satellite_count,
        "temporal_agreement": bundle.temporal_agreement.status,
        "spatial_agreement": bundle.spatial_agreement.status,
        "thermal_agreement": bundle.thermal_agreement.status,
        "image_confirmation_status": bundle.image_confirmation_status,
        "primary_summary": bundle.primary_corroboration_summary,
        "supporting_reasons": bundle.supporting_reasons,
        "conflicting_reasons": bundle.conflicting_reasons
    }


@evidence_router.post("/sources/{source_id}/corroborate", response_model=ThermalEvidenceBundle)
def force_recalculate_source_corroboration(
    source_id: str,
    req: Optional[CorroborationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Force re-execution of the multi-satellite evidence fusion pipeline for a thermal source.
    """
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal source {source_id} not found.")

    if req is None:
        req = CorroborationRequest(source_id=source_id)
    else:
        req.source_id = source_id

    bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db, req=req)
    evidence_fusion_engine.persist_evidence_bundle(bundle=bundle, db=db)
    return bundle


@evidence_router.post("/sources/{source_id}/request-image-confirmation", response_model=OnDemandImageConfirmation)
def request_on_demand_image_confirmation(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    Request on-demand high-resolution spatial context window (Sentinel-2 SWIR or Landsat TIRS).
    Results are cached by (source_id, overpass_date).
    """
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal source {source_id} not found.")

    confirmation = evidence_fusion_engine._get_or_fetch_image_confirmation(source)
    return confirmation


@evidence_router.get("/events/{event_id}/evidence")
def get_event_evidence_context(
    event_id: str,
    db: Session = Depends(get_db)
):
    """
    Get multi-satellite evidence context for a single CanonicalThermalEvent.
    """
    event = db.query(ThermalEventModel).filter(ThermalEventModel.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Thermal event {event_id} not found.")

    # If attached to a source, return source bundle
    if event.source_id:
        return get_thermal_source_evidence_bundle(source_id=event.source_id, db=db)

    # Standalone event context
    return {
        "event_id": event.event_id,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "frp_mw": event.frp_mw,
        "satellite": event.source_satellite,
        "sensor": event.sensor_name,
        "evidence_status": "SINGLE_SOURCE",
        "overall_evidence_confidence": 0.55,
        "note": "Standalone event not yet merged into a multi-pass ThermalSourceObject."
    }


@evidence_router.get("/evidence/bundles", response_model=List[ThermalEvidenceBundle])
def list_recent_evidence_bundles(
    limit: int = Query(25, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Query recent persisted evidence bundles from database.
    """
    q = db.query(ThermalEvidenceBundleModel)
    if status:
        q = q.filter(ThermalEvidenceBundleModel.evidence_status == status)
    
    rows = q.order_by(ThermalEvidenceBundleModel.updated_at.desc()).limit(limit).all()
    return [_bundle_model_to_schema(r, db) for r in rows]


# =============================================================================
# HELPER CONVERSION ROUTINE
# =============================================================================

def _bundle_model_to_schema(model: ThermalEvidenceBundleModel, db: Session) -> ThermalEvidenceBundle:
    members = db.query(ThermalEvidenceMemberModel).filter(
        ThermalEvidenceMemberModel.bundle_id == model.bundle_id
    ).all()

    member_schemas = [
        {
            "member_id": m.member_id,
            "satellite_name": m.satellite_name,
            "sensor_name": m.sensor_name,
            "source_product": m.source_product,
            "processing_version": m.processing_version,
            "role": m.role,
            "observation_status": m.observation_status,
            "acquisition_timestamp": m.acquisition_timestamp,
            "spatial_distance_m": m.spatial_distance_m,
            "temporal_offset_min": m.temporal_offset_min,
            "measured_values": m.measured_values or {},
            "data_quality": m.data_quality,
            "quality_flags": m.quality_flags or {},
            "is_dependent_on_member_id": m.is_dependent_on_member_id,
            "dependency_group_id": m.dependency_group_id,
            "evidence_weight": m.evidence_weight,
            "evidence_contribution_sign": m.evidence_contribution_sign,
            "explanation_text": m.explanation_text or ""
        }
        for m in members
    ]

    return ThermalEvidenceBundle(
        bundle_id=model.bundle_id,
        thermal_source_id=model.thermal_source_id or "SRC-UNKNOWN",
        facility_id=model.facility_id,
        facility_name=model.facility_name,
        centroid_lat=model.centroid_lat,
        centroid_lon=model.centroid_lon,
        evidence_status=EvidenceState(model.evidence_status),
        overall_evidence_confidence=model.overall_evidence_confidence,
        source_count=model.source_count,
        satellite_count=model.satellite_count,
        independent_satellite_count=model.independent_satellite_count,
        temporal_agreement=model.temporal_agreement,
        spatial_agreement=model.spatial_agreement,
        thermal_agreement=model.thermal_agreement,
        image_confirmation_status=model.image_confirmation_status,
        image_confirmation=model.image_confirmation,
        primary_corroboration_summary=model.primary_corroboration_summary or "",
        supporting_reasons=model.supporting_reasons or [],
        conflicting_reasons=model.conflicting_reasons or [],
        limitations_and_uncertainties=model.limitations_and_uncertainties or [],
        members=member_schemas,
        fusion_algorithm_version=model.fusion_algorithm_version,
        created_at=model.created_at,
        updated_at=model.updated_at
    )
