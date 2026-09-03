from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.vision import (
    VisionHealthResponse, VisualEvidence, CameraMetadata, VisionEventsQuery,
    ThermalFrameEvidence, CCTVFrameEvidence, VisualEvidenceType
)
from app.services.vision.vision_pipeline_service import vision_pipeline_service

router = APIRouter(prefix="/vision", tags=["Facility Thermal Vision & CCTV Intelligence"])

@router.get("/health", response_model=VisionHealthResponse)
def get_vision_pipeline_health(db: Session = Depends(get_db)):
    """
    Retrieve computer vision & thermal surveillance ingestion health, active cameras, and inference FPS.
    """
    return vision_pipeline_service.get_health(db)

@router.get("/facilities/{facility_id}/latest")
def get_facility_latest_vision(facility_id: str = Path(..., description="Target facility ID")):
    """
    Fetch the latest radiometric thermal distributions and optical CCTV evidence across all cameras in a facility.
    """
    return vision_pipeline_service.get_latest_facility_vision(facility_id)

@router.get("/facilities/{facility_id}/events", response_model=List[VisualEvidence])
def get_facility_vision_events(
    facility_id: str = Path(...),
    camera_id: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    zone_id: Optional[str] = Query(None),
    evidence_type: Optional[VisualEvidenceType] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    min_confidence: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Query paginated historical visual and thermal evidence events within a specified time window.
    """
    query = VisionEventsQuery(
        facility_id=facility_id,
        camera_id=camera_id,
        asset_id=asset_id,
        zone_id=zone_id,
        evidence_type=evidence_type,
        start_time=start_time,
        end_time=end_time,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset
    )
    return vision_pipeline_service.query_events(db, query)

@router.get("/cameras/{camera_id}/latest")
def get_camera_latest_vision(camera_id: str = Path(...)):
    """
    Fetch the latest frame evidence for a specific thermal or optical camera.
    """
    return vision_pipeline_service.get_latest_camera_vision(camera_id)

@router.get("/cameras", response_model=List[CameraMetadata])
def get_registered_cameras():
    """
    List all registered facility thermal and optical cameras.
    """
    return vision_pipeline_service.get_all_registered_cameras()

@router.get("/correlated/{asset_id}")
def get_correlated_visual_and_telemetry(asset_id: str = Path(..., description="Target equipment ID (e.g. T-04)")):
    """
    Multi-modal cross-correlation linking visual evidence (hotspots, flame, smoke)
    with Phase 12 process telemetry (temperature transmitters, vessel pressure, gas sniffer).
    """
    return vision_pipeline_service.get_linked_telemetry_for_visual_evidence(asset_id)

@router.post("/simulator/scenario")
def set_vision_simulator_scenario(scenario_name: str = Body(..., embed=True, description="NORMAL, GRADUAL_HEATING, LOCAL_HOTSPOT, RAPID_HEATING, HOTSPOT_GROWTH, MULTIPLE_HOTSPOTS, SMOKE_LIKE_EVENT, FLAME_LIKE_EVENT, OBSCURED_SCENE, CAMERA_FAILURE")):
    """
    Switch active camera simulator scenario.
    """
    return vision_pipeline_service.set_simulator_scenario(scenario_name)

@router.post("/simulator/tick")
def trigger_vision_simulator_tick(db: Session = Depends(get_db)):
    """
    Manually trigger one tick of radiometric thermal and optical CCTV simulation.
    """
    return vision_pipeline_service.generate_simulator_tick(db)

@router.post("/ingest")
def ingest_edge_camera_evidence(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Read-only push endpoint for edge camera gateways to ingest structured visual or thermal evidence.
    """
    # Accept either thermal frame or optical frame payload
    if "min_temperature" in payload or "hotspot_regions" in payload:
        evidence = ThermalFrameEvidence(**payload)
        res = vision_pipeline_service.ingest_thermal_evidence(evidence, db)
        return {"status": "SUCCESS", "type": "THERMAL", "frame_id": res.frame_id}
    else:
        evidence = CCTVFrameEvidence(**payload)
        res = vision_pipeline_service.ingest_cctv_evidence(evidence, db)
        return {"status": "SUCCESS", "type": "CCTV", "frame_id": res.frame_id}
