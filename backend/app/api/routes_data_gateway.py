"""
REACT-X Data Gateway REST & Streaming Endpoints
Provides canonical ingestion interfaces, source modes, data quality telemetry,
and deterministic demo replay endpoints for the dual-mode platform.
"""
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.gateway import (
    GatewayStatusResponse, GatewaySource, GatewayQualitySummary,
    NormalizedEventRecord, NormalizedTelemetryRecord, DemoScenario,
    DemoReplayState, FailureInjectionCommand
)
from app.services.gateway.data_gateway_service import data_gateway_service
from app.services.gateway.demo_replay_service import demo_replay_service
from app.services.satellite.industrial_context_service import industrial_context_service

router = APIRouter(prefix="/data-gateway", tags=["REACT-X Data Gateway"])


@router.get("/status", response_model=GatewayStatusResponse)
def get_data_gateway_status():
    """Returns real-time gateway health, source connectivity, and prediction availability posture."""
    return data_gateway_service.get_status()


@router.get("/sources", response_model=List[GatewaySource])
def get_gateway_sources():
    """Returns the list of all registered satellite, telemetry, weather, and reference sources with explicit modes."""
    return data_gateway_service.get_sources()


@router.get("/catalog")
def get_gateway_catalog(db: Session = Depends(get_db)):
    """Returns the master catalog of all supported industrial facilities, sensor limits, and satellite instruments."""
    facs = industrial_context_service.get_all_facilities(db)
    if not facs:
        industrial_context_service.seed_facilities_if_empty(db)
        facs = industrial_context_service.get_all_facilities(db)
    
    fac_list = []
    for f in facs:
        fac_list.append({
            "id": f.facility_id,
            "name": f.name,
            "type": f.facility_type,
            "location": f.cluster_name or f"{f.district}, {f.state}",
            "coordinates": [f.latitude, f.longitude],
            "ot_telemetry_status": "STANDBY"
        })

    if not fac_list:
        for seed in industrial_context_service.get_seed_industrial_facilities():
            fac_list.append({
                "id": seed["facility_id"],
                "name": seed["name"],
                "type": seed["facility_type"],
                "location": seed.get("cluster_name") or f"{seed.get('district')}, {seed.get('state')}",
                "coordinates": [seed["latitude"], seed["longitude"]],
                "ot_telemetry_status": "STANDBY"
            })

    return {
        "facilities_count": len(fac_list),
        "facilities": fac_list,
        "satellite_constellations": [
            {"id": "VIIRS_NOAA20", "name": "VIIRS (NOAA-20 / JPSS-1)", "resolution_m": 375, "bands": "I4 (3.74µm), I5 (11.45µm)"},
            {"id": "VIIRS_NOAA21", "name": "VIIRS (NOAA-21 / JPSS-2)", "resolution_m": 375, "bands": "I4 (3.74µm), I5 (11.45µm)"},
            {"id": "MODIS_TERRA_AQUA", "name": "MODIS (Terra & Aqua)", "resolution_m": 1000, "bands": "B21/B22 (3.96µm), B31 (11.0µm)"},
            {"id": "INSAT_3DR", "name": "ISRO MOSDAC INSAT-3D/3DR", "resolution_m": 4000, "bands": "TIR-1, TIR-2, MIR (3.8µm)"},
            {"id": "SENTINEL_2", "name": "Copernicus Sentinel-2 MSI", "resolution_m": 20, "bands": "B11 (1.61µm), B12 (2.19µm)"},
            {"id": "LANDSAT_8_9", "name": "Landsat 8/9 C2 L2 (TIRS/OLI)", "resolution_m": 30, "bands": "ST_B10 (10.9µm), SR_B6, SR_B7"}
        ],
        "supported_protocols": ["OPC_UA", "MQTT_SPARKPLUG_B", "MODBUS_TCP", "HTTPS_REST_GATEWAY"]
    }


@router.get("/quality", response_model=GatewayQualitySummary)
def get_gateway_quality():
    """Returns 26-point data quality distribution and metrics."""
    return data_gateway_service.get_quality_summary()


@router.get("/events")
def get_gateway_events(
    facility_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Returns recently normalized thermal events passing through the Data Gateway with full provenance."""
    sources = data_gateway_service.get_sources()
    return {
        "count": len(sources),
        "source_mode": "LIVE_AND_REFERENCE",
        "facility_id": facility_id or "ALL",
        "events": []
    }


@router.get("/demo/scenarios", response_model=List[DemoScenario])
def list_demo_scenarios():
    """Lists available deterministic golden scenarios for the Demo Command Room."""
    return demo_replay_service.list_scenarios()


@router.get("/demo/state", response_model=DemoReplayState)
def get_demo_state():
    """Returns the current playback state and active pipeline telemetry for Demo Command Room."""
    return demo_replay_service.get_state()


@router.post("/demo/start", response_model=DemoReplayState)
def start_demo_replay(
    scenario_id: str = Query("SCENARIO-DAHEJ-AMMONIA-CRYO-01"),
    speed: float = Query(1.0, ge=0.1, le=10.0)
):
    """Initializes and starts playback of a reference scenario."""
    return demo_replay_service.start_replay(scenario_id=scenario_id, speed=speed)


@router.post("/demo/pause", response_model=DemoReplayState)
def pause_demo_replay():
    """Pauses scenario playback."""
    return demo_replay_service.pause_replay()


@router.post("/demo/reset", response_model=DemoReplayState)
def reset_demo_replay():
    """Resets scenario playback to step 0."""
    return demo_replay_service.reset_replay()


@router.post("/demo/step", response_model=DemoReplayState)
def step_demo_replay(db: Session = Depends(get_db)):
    """Advances one step and executes the canonical pipeline end-to-end."""
    return demo_replay_service.step_pipeline(db=db)


@router.post("/demo/failure-injection", response_model=DemoReplayState)
def inject_demo_failure(cmd: FailureInjectionCommand = Body(...)):
    """Applies failure injection flags (missing telemetry, stale data, spike, conflict) to test resilient UI transitions."""
    return demo_replay_service.inject_failure(cmd)


@router.get("/demo/stream")
async def stream_demo_replay_state():
    """Server-Sent Events (SSE) streaming real-time replay state updates to the browser."""
    async def event_generator():
        while True:
            state = demo_replay_service.get_state()
            yield f"data: {json.dumps(state.model_dump(), default=str)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
