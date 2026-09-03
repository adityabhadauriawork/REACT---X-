from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.schemas.discrimination import (
    DiscriminationAssessment, LandCoverContextResult, EOVerificationResult
)
from app.services.satellite.source_discrimination_service import source_discrimination_service
from app.services.satellite.land_cover_service import land_cover_service
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.storage.discrimination_repository import discrimination_repository

router = APIRouter(prefix="/discrimination", tags=["Thermal Source Discrimination & EO Verification"])

@router.get("/sources/{source_id}", response_model=DiscriminationAssessment)
def get_source_discrimination(
    source_id: str = Path(..., description="Target thermal source ID"),
    lat: float = Query(21.6850, description="Centroid latitude"),
    lon: float = Query(72.5620, description="Centroid longitude"),
    frp: float = Query(24.5, description="Mean FRP in MW"),
    obs_count: int = Query(42, description="Observation count"),
    active_days: int = Query(28, description="Active days count"),
    facility_id: Optional[str] = Query("FAC-IN-DAHEJ-001", description="Attributed facility ID"),
    db: Session = Depends(get_db)
):
    """
    Returns full multimodal thermal source discrimination assessment,
    including land-cover context, observation quality, and EO structural alignment.
    """
    return source_discrimination_service.discriminate_source(
        source_id=source_id,
        latitude=lat,
        longitude=lon,
        mean_frp_mw=frp,
        max_frp_mw=frp * 1.5,
        observation_count=obs_count,
        active_days_count=active_days,
        diurnal_night_fraction=0.65,
        facility_id=facility_id,
        facility_name="Dahej Petrochemical Complex" if facility_id else None,
        facility_distance_m=35.0 if facility_id else 850.0,
        is_inside_facility=bool(facility_id),
        db=db
    )

@router.get("/sources/{source_id}/land-cover", response_model=LandCoverContextResult)
def get_source_land_cover_context(
    source_id: str,
    lat: float = Query(21.6850),
    lon: float = Query(72.5620),
    facility_id: Optional[str] = Query(None)
):
    """
    Resolves authoritative Copernicus / ESA WorldCover land-cover context for thermal source coordinates.
    """
    return land_cover_service.resolve_land_cover(latitude=lat, longitude=lon, facility_id=facility_id)

@router.get("/sources/{source_id}/eo-verification", response_model=EOVerificationResult)
def get_source_eo_verification(
    source_id: str,
    lat: float = Query(21.6850),
    lon: float = Query(72.5620),
    facility_id: Optional[str] = Query("FAC-IN-DAHEJ-001")
):
    """
    Returns high-resolution Earth Observation (Sentinel-2 / PlanetScope) structural verification footprint.
    """
    return eo_verification_service.verify_thermal_source(
        source_id=source_id,
        latitude=lat,
        longitude=lon,
        facility_id=facility_id,
        facility_distance_m=35.0 if facility_id else 850.0
    )

@router.get("/sources/{source_id}/explanation")
def get_source_discrimination_explanation(
    source_id: str,
    lat: float = Query(21.6850),
    lon: float = Query(72.5620),
    facility_id: Optional[str] = Query("FAC-IN-DAHEJ-001"),
    db: Session = Depends(get_db)
):
    """
    Returns structured explanation of why the source was classified,
    top supporting features, opposing evidence, and abstention criteria.
    """
    asm = source_discrimination_service.discriminate_source(
        source_id=source_id,
        latitude=lat,
        longitude=lon,
        facility_id=facility_id,
        db=db
    )
    return {
        "source_id": asm.source_id,
        "predicted_class": asm.predicted_class,
        "classification_state": asm.classification_state,
        "model_confidence": asm.model_confidence,
        "system_confidence": asm.system_confidence,
        "evidence_sufficiency": asm.evidence_sufficiency,
        "top_supporting_evidence": asm.top_supporting_evidence,
        "top_opposing_evidence": asm.top_opposing_evidence,
        "abstention_reason": asm.abstention_reason,
        "land_cover_class": asm.land_cover.land_cover_class,
        "eo_structural_match": asm.eo_verification.structural_match_status if asm.eo_verification else "UNAVAILABLE"
    }

@router.post("/sources/{source_id}/verify-eo", response_model=EOVerificationResult)
def trigger_selective_eo_verification(
    source_id: str,
    payload: Dict[str, Any] = Body(...)
):
    """
    Triggers selective on-demand high-resolution EO verification for a thermal source.
    """
    lat = float(payload.get("latitude", 21.6850))
    lon = float(payload.get("longitude", 72.5620))
    fac_id = payload.get("facility_id", "FAC-IN-DAHEJ-001")
    force_unavail = bool(payload.get("force_unavailable", False))

    return eo_verification_service.verify_thermal_source(
        source_id=source_id,
        latitude=lat,
        longitude=lon,
        facility_id=fac_id,
        force_unavailable=force_unavail
    )
