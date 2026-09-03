from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.telemetry import (
    FacilityTelemetryObservation, TelemetryHealthResponse, TelemetryHistoryQuery,
    SensorMetadata, EdgeGateway, SensorType, TelemetryQuality
)
from app.services.industrial.telemetry_service import telemetry_service
from app.services.storage.telemetry_repository import telemetry_repository

router = APIRouter(prefix="/telemetry", tags=["Industrial Telemetry & Edge Gateway Ingestion"])

@router.get("/health", response_model=TelemetryHealthResponse)
def get_telemetry_health(db: Session = Depends(get_db)):
    """
    Get industrial telemetry ingestion health, gateway statuses, sample rates, and latency.
    """
    return telemetry_service.get_health(db)

@router.get("/facilities/{facility_id}/latest", response_model=List[FacilityTelemetryObservation])
def get_facility_latest_telemetry(facility_id: str = Path(..., description="Target facility identifier")):
    """
    Fetch the latest telemetry readings across all active sensors for a specific industrial facility.
    Includes dynamic freshness indicators based on each sensor's unique sampling interval.
    """
    results = telemetry_service.get_latest_facility_telemetry(facility_id)
    return results

@router.get("/facilities/{facility_id}/history", response_model=List[FacilityTelemetryObservation])
def get_facility_telemetry_history(
    facility_id: str = Path(...),
    asset_id: Optional[str] = Query(None, description="Optional filter by asset ID"),
    sensor_type: Optional[SensorType] = Query(None, description="Optional filter by sensor modality"),
    start_time: Optional[datetime] = Query(None, description="ISO UTC start timestamp"),
    end_time: Optional[datetime] = Query(None, description="ISO UTC end timestamp"),
    quality: Optional[TelemetryQuality] = Query(None, description="Filter by quality status"),
    limit: int = Query(100, ge=1, le=1000, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    """
    Query paginated historical telemetry observations for a facility within a specified time window.
    """
    query = TelemetryHistoryQuery(
        facility_id=facility_id,
        asset_id=asset_id,
        sensor_type=sensor_type,
        start_time=start_time,
        end_time=end_time,
        quality=quality,
        limit=limit,
        offset=offset
    )
    return telemetry_service.query_history(db, query)

@router.get("/sensors/{sensor_id}/latest", response_model=FacilityTelemetryObservation)
def get_sensor_latest_telemetry(sensor_id: str = Path(..., description="Unique sensor identifier")):
    """
    Fetch the most recent telemetry observation for a specific sensor.
    """
    obs = telemetry_service.get_latest_sensor_telemetry(sensor_id)
    if not obs:
        raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found or has no readings.")
    return obs

@router.get("/sensors/{sensor_id}/history", response_model=List[FacilityTelemetryObservation])
def get_sensor_telemetry_history(
    sensor_id: str = Path(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Query paginated historical observations for a single sensor.
    """
    query = TelemetryHistoryQuery(
        sensor_id=sensor_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    return telemetry_service.query_history(db, query)

@router.get("/gateways", response_model=List[EdgeGateway])
def get_registered_gateways(db: Session = Depends(get_db)):
    """
    List all registered edge gateways and their connection / buffer statuses.
    """
    gateways = telemetry_repository.get_gateways(db)
    return [
        EdgeGateway(
            gateway_id=gw.gateway_id,
            facility_id=gw.facility_id,
            protocol=gw.protocol,
            endpoint=gw.endpoint,
            status=gw.status,
            last_heartbeat=gw.last_heartbeat,
            firmware_version=gw.firmware_version,
            time_sync_status=gw.time_sync_status,
            buffer_count=gw.buffer_count,
            dropped_count=gw.dropped_count,
            active_sensors_count=gw.active_sensors_count
        ) for gw in gateways
    ]

@router.post("/simulator/scenario")
def set_simulator_scenario(scenario_name: str = Body(..., embed=True, description="NORMAL, DRIFT, THERMAL_RISE, PRESSURE_RISE, GAS_LEAK_PATTERN, MULTI_SENSOR_DEVIATION, SENSOR_FAILURE, COMMUNICATION_LOSS")):
    """
    Switch active telemetry simulation scenario to generate correlated multi-sensor test time-series.
    """
    return telemetry_service.set_simulator_scenario(scenario_name)

@router.post("/simulator/tick", response_model=List[FacilityTelemetryObservation])
def generate_simulator_tick(db: Session = Depends(get_db)):
    """
    Manually trigger one tick of correlated telemetry generation from the simulator.
    """
    return telemetry_service.generate_simulator_tick(db)

@router.post("/ingest", response_model=Dict[str, Any])
def ingest_edge_webhook(
    observations: List[FacilityTelemetryObservation],
    db: Session = Depends(get_db)
):
    """
    Push-based read-only telemetry webhook for plant edge gateways.
    Validates quality, updates latest-value store, and persists observations.
    """
    processed = telemetry_service.ingest_observations(observations, db)
    return {
        "status": "SUCCESS",
        "ingested_count": len(processed),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
