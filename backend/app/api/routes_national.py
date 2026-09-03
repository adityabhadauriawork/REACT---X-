from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple

from app.core.database import get_db
from app.schemas.facility_config import (
    FacilityConfig, FacilityBaselineStage, FacilityType,
    FacilityConnectivityStatus, NationalCoverageSummary,
    RegionFreshnessSummary, FacilityConfigExport, FacilityConfigImportRequest
)
from app.services.national.facility_registry_service import facility_registry_service

router = APIRouter(prefix="/national", tags=["National Facility Registry & Geographic Coverage"])

@router.get("/facilities", response_model=List[FacilityConfig])
def list_national_facilities(
    state: Optional[str] = Query(None, description="Filter by Indian state"),
    district: Optional[str] = Query(None, description="Filter by district"),
    facility_type: Optional[str] = Query(None, description="Filter by industrial category"),
    connectivity_status: Optional[str] = Query(None, description="Filter by connectivity"),
    baseline_stage: Optional[str] = Query(None, description="Filter by baseline stage"),
    min_lat: Optional[float] = Query(None, description="Bounding box min latitude"),
    min_lon: Optional[float] = Query(None, description="Bounding box min longitude"),
    max_lat: Optional[float] = Query(None, description="Bounding box max latitude"),
    max_lon: Optional[float] = Query(None, description="Bounding box max longitude"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Returns registered industrial facilities across India with spatial and attribute filtering.
    """
    bbox = None
    if min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None:
        bbox = (min_lat, min_lon, max_lat, max_lon)

    return facility_registry_service.list_facilities(
        db=db,
        state=state,
        district=district,
        facility_type=facility_type,
        connectivity_status=connectivity_status,
        baseline_stage=baseline_stage,
        bbox=bbox,
        limit=limit,
        offset=offset
    )

@router.get("/facilities/{facility_id}", response_model=FacilityConfig)
def get_facility_configuration(
    facility_id: str = Path(..., description="Target facility ID"),
    db: Session = Depends(get_db)
):
    """
    Returns complete generic configuration, hierarchy, hazard profile, and capabilities for a facility.
    """
    fac = facility_registry_service.get_facility(db, facility_id)
    if not fac:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found in national registry")
    return fac

@router.post("/facilities/onboard", response_model=FacilityConfig)
def onboard_new_facility(
    config: FacilityConfig = Body(...),
    db: Session = Depends(get_db)
):
    """
    Registers a new industrial facility into the national platform.
    """
    return facility_registry_service.onboard_facility(db, config)

@router.post("/facilities/import", response_model=FacilityConfig)
def import_facility_configuration(
    payload: FacilityConfigImportRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Securely imports a facility JSON configuration, rejecting any embedded secrets or credentials.
    """
    try:
        return facility_registry_service.import_facility_config(
            db=db,
            config_json=payload.configuration_json,
            dry_run=payload.dry_run
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/facilities/{facility_id}/export", response_model=FacilityConfigExport)
def export_facility_configuration(
    facility_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    Exports a clean, sanitized facility configuration JSON without credentials.
    """
    try:
        return facility_registry_service.export_facility_config(db, facility_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/coverage", response_model=NationalCoverageSummary)
def get_national_coverage_statistics(
    db: Session = Depends(get_db)
):
    """
    Returns real-time calculated national coverage across Indian states and industrial sectors.
    """
    return facility_registry_service.get_national_coverage_summary(db)

@router.get("/freshness", response_model=RegionFreshnessSummary)
def get_regional_data_freshness(
    region: str = Query("National", description="Target region or state name"),
    db: Session = Depends(get_db)
):
    """
    Computes data freshness metrics across monitored facilities in a region.
    """
    return facility_registry_service.get_regional_freshness_summary(db, region)

@router.post("/facilities/{facility_id}/baseline-stage", response_model=FacilityConfig)
def update_facility_baseline_stage(
    facility_id: str = Path(...),
    new_stage: FacilityBaselineStage = Query(..., description="Target lifecycle stage"),
    db: Session = Depends(get_db)
):
    """
    Updates the cold-start baseline lifecycle stage for a facility.
    """
    try:
        return facility_registry_service.transition_baseline_stage(db, facility_id, new_stage)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
