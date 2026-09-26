from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.thermal_source import (
    IndustrialFacilityDetail,
    FacilityGeoJSONCollection,
    ThermalSourceObject
)
from app.services.satellite.thermal_source_service import thermal_source_service

router = APIRouter(prefix="/facilities", tags=["REACT-X Industrial Facilities Registry"])

@router.get("", response_model=List[IndustrialFacilityDetail])
def get_industrial_facilities(
    state: Optional[str] = Query(None, description="State filter e.g. Gujarat, Jharkhand"),
    district: Optional[str] = Query(None, description="District filter e.g. Bharuch, Surat"),
    sector: Optional[str] = Query(None, description="PETROCHEMICAL, REFINERY, THERMAL_POWER, STEEL, MINING"),
    source: Optional[str] = Query(None, description="OSM, GEM, RECONCILED, BHUVAN"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieve registered industrial facilities normalized from OpenStreetMap (OSM) and Global Energy Monitor (GEM).
    """
    return thermal_source_service.get_facilities(
        db=db,
        state=state,
        district=district,
        sector=sector,
        source=source,
        limit=limit,
        offset=offset
    )

@router.get("/geojson", response_model=FacilityGeoJSONCollection)
def get_facilities_geojson(db: Session = Depends(get_db)):
    """
    Export map-ready RFC 7946 GeoJSON FeatureCollection of all industrial facility boundaries and points.
    """
    return thermal_source_service.get_facilities_geojson(db=db)

@router.get("/{facility_id}", response_model=IndustrialFacilityDetail)
def get_facility_profile(facility_id: str, db: Session = Depends(get_db)):
    """
    Retrieve deep-dive profile, boundary polygon, and operator info for a specific facility.
    """
    fac = thermal_source_service.get_facility_by_id(facility_id, db=db)
    if not fac:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found.")
    return fac

@router.get("/{facility_id}/thermal-sources", response_model=List[ThermalSourceObject])
def get_facility_thermal_sources(facility_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all ThermalSourceObjects attributed to this facility.
    """
    return thermal_source_service.get_facility_thermal_sources(facility_id, db=db)
