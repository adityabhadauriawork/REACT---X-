from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.thermal_source import (
    ThermalSourceObject,
    ThermalSourceGeoJSONCollection,
    ThermalSourceObservation,
    FacilityCandidate,
    ClusteringSummaryResponse
)
from app.services.satellite.thermal_source_service import thermal_source_service
from app.services.satellite.clustering_engine import clustering_engine
from app.services.satellite.source_attribution_engine import source_attribution_engine
from app.models.thermal_source import ThermalSourceModel

router = APIRouter(prefix="/thermal/sources", tags=["REACT-X Spatiotemporal Thermal Sources"])

@router.get("", response_model=List[ThermalSourceObject])
def get_thermal_sources(
    bbox: Optional[str] = Query(None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]"),
    source_status: Optional[str] = Query(None, description="NEW_SOURCE, RECURRING_SOURCE, PERSISTENT_SOURCE, INACTIVE_SOURCE"),
    facility_id: Optional[str] = Query(None, description="Filter by attributed facility ID"),
    min_frp: Optional[float] = Query(None, description="Minimum FRP magnitude in MW"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieve Spatiotemporal Thermal Source Objects constructed from multiple spaceborne observations.
    """
    return thermal_source_service.get_thermal_sources(
        db=db,
        bbox=bbox,
        source_status=source_status,
        facility_id=facility_id,
        min_frp=min_frp,
        limit=limit,
        offset=offset
    )

@router.get("/geojson", response_model=ThermalSourceGeoJSONCollection)
def get_thermal_sources_geojson(
    bbox: Optional[str] = Query(None, description="Bounding box filter"),
    source_status: Optional[str] = Query(None, description="Filter by source status"),
    db: Session = Depends(get_db)
):
    """
    Export map-ready RFC 7946 GeoJSON FeatureCollection of Thermal Source Objects.
    """
    return thermal_source_service.get_sources_geojson(db=db, source_status=source_status, bbox=bbox)

@router.post("/cluster", response_model=ClusteringSummaryResponse)
def trigger_batch_clustering(db: Session = Depends(get_db)):
    """
    Trigger spatiotemporal clustering across all stored observations and run industrial facility attribution.
    """
    summary = clustering_engine.run_batch_clustering(db=db)
    
    # Run attribution for all active sources
    sources = db.query(ThermalSourceModel).all()
    for s in sources:
        source_attribution_engine.attribute_source(s, db=db)
    db.commit()

    return ClusteringSummaryResponse(
        total_events_evaluated=summary["total_events_evaluated"],
        sources_created=summary["sources_created"],
        sources_updated=summary["sources_updated"],
        total_active_sources=summary["total_active_sources"],
        clustering_duration_ms=summary["clustering_duration_ms"],
        sources_by_status=summary["sources_by_status"]
    )

@router.get("/{source_id}", response_model=ThermalSourceObject)
def get_thermal_source_detail(source_id: str, db: Session = Depends(get_db)):
    """
    Retrieve deep-dive dossier for a specific ThermalSourceObject.
    """
    source = thermal_source_service.get_source_by_id(source_id, db=db)
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal Source '{source_id}' not found.")
    return source

@router.get("/{source_id}/events", response_model=List[ThermalSourceObservation])
def get_thermal_source_events(source_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all individual satellite observations that comprise this ThermalSourceObject.
    """
    return thermal_source_service.get_source_events(source_id, db=db)

@router.get("/{source_id}/facilities", response_model=List[FacilityCandidate])
def get_thermal_source_facilities(source_id: str, db: Session = Depends(get_db)):
    """
    Retrieve ranked industrial facility candidates with spatial distance and attribution confidence.
    """
    return thermal_source_service.get_source_facilities(source_id, db=db)
