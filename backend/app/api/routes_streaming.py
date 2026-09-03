from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.canonical import CanonicalEvent, IngestionMetrics
from app.services.industrial.telemetry_simulator import telemetry_simulator
from app.services.ingestion.stream_router import stream_router
from app.services.predictive.early_warning_engine import early_warning_engine
from app.services.preventive.preventive_engine import preventive_engine
from app.services.preventive.preventive_whatif import preventive_whatif, PreventiveWhatIfRequest, PreventiveWhatIfResponse
from app.services.preventive.control_boundary import safety_control_boundary
from app.services.graph.risk_graph_service import risk_graph_service
from app.services.scenarios.scenario_orchestrator import scenario_orchestrator
from app.services.observability.observability import system_observability

router = APIRouter(prefix="/streaming", tags=["Streaming & Pre-Incident Intelligence"])

# 1. STREAMING METRICS & PIPELINE HEALTH
@router.get("/metrics", response_model=IngestionMetrics)
def get_ingestion_metrics():
    """
    Fetch real-time industrial telemetry ingestion metrics (events/sec, P95/P99 latency, data quality).
    """
    return telemetry_simulator.get_metrics()

@router.get("/health-overview")
def get_health_overview():
    """
    Get full system observability and broker health status.
    """
    return system_observability.get_system_health()

# 2. STREAM GENERATION & SIMULATION CONTROLS
@router.post("/config")
def configure_stream_count(stream_count: int = Body(..., embed=True)):
    """
    Set active logical sensor stream multiplexing count (e.g. 100, 500, 1000 streams).
    """
    telemetry_simulator.set_stream_count(stream_count)
    return {"status": "SUCCESS", "active_streams_count": telemetry_simulator.stream_count}

@router.post("/inject-anomaly")
def inject_stream_anomaly(
    asset_id: str = Body("T-04"),
    signal_suffix: str = Body("PRESS_01"),
    target_value: float = Body(6.8),
    severity: str = Body("CRITICAL")
):
    """
    Inject a realistic sensor anomaly excursion for live testing.
    """
    telemetry_simulator.inject_anomaly(asset_id, signal_suffix, target_value, severity)
    return {"status": "ANOMALY_INJECTED", "asset_id": asset_id, "signal": f"{asset_id}_{signal_suffix}", "value": target_value}

@router.post("/clear-anomalies")
def clear_stream_anomalies():
    """
    Reset all simulated anomalies back to nominal baseline.
    """
    telemetry_simulator.clear_anomalies()
    return {"status": "ANOMALIES_CLEARED"}

@router.get("/tick", response_model=List[CanonicalEvent])
def fetch_stream_tick(count: Optional[int] = Query(None, description="Number of events to generate")):
    """
    Fetch one live multiplexed tick of normalized canonical sensor events.
    """
    events = telemetry_simulator.generate_tick_batch(count)
    # Route through decision-value router
    for e in events:
        stream_router.route_event(e)
    return events[:50] # Return preview to client

# 3. PRE-INCIDENT EARLY WARNING ROSTER
@router.get("/pre-incident/assets")
def get_all_assets_early_warning():
    """
    Evaluates multi-signal pre-incident risk across all plant assets.
    """
    assets = [
        ("T-04", "Ammonia Cryogenic Tank", "Ammonia (Anhydrous)", 5.2, -28.0, 4.8, 28.0, 280),
        ("T-03", "LPG Horton Sphere 01", "Liquefied Petroleum Gas", 12.0, 28.0, 3.5, 22.0, 210),
        ("T-01", "Benzene Storage Tank 01", "Benzene (Pure Grade)", 1.2, 32.0, 1.8, 16.0, 150),
        ("T-02", "Chlorine Bullet Tank", "Chlorine (Liquefied)", 6.5, 24.0, 2.1, 14.0, 120),
        ("PU-01", "Primary Catalytic Reformer", "Benzene", 28.0, 460.0, 2.2, 12.0, 80),
        ("PU-02", "Ammonia Synthesis Loop", "Ammonia", 145.0, 410.0, 2.5, 14.0, 95),
        ("SUB-01", "66kV Main High-Voltage Substation", "None", 1.0, 34.0, 4.2, 32.0, 320),
    ]
    results = []
    for a in assets:
        ew = early_warning_engine.evaluate_asset_pre_incident_state(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7])
        results.append(ew)
    
    results.sort(key=lambda x: x["early_warning_score"], reverse=True)
    return results

@router.post("/pre-incident/evaluate")
def evaluate_asset_state(
    asset_id: str = Body("T-04"),
    asset_name: str = Body("Ammonia Cryogenic Tank"),
    chemical_name: str = Body("Ammonia"),
    pressure_bar: float = Body(5.4),
    temperature_c: float = Body(-28.0),
    vibration_mm_s: float = Body(4.5),
    acoustic_db: float = Body(32.0),
    maintenance_age_days: int = Body(280)
):
    """
    Evaluates multi-signal fusion and ML isolation forest probability for a specific asset configuration.
    """
    return early_warning_engine.evaluate_asset_pre_incident_state(
        asset_id, asset_name, chemical_name, pressure_bar, temperature_c, vibration_mm_s, acoustic_db, maintenance_age_days
    )

# 4. PREVENTIVE INTERVENTIONS & WHAT-IF SIMULATOR
@router.get("/preventive/interventions/{asset_id}")
def get_preventive_interventions(
    asset_id: str,
    chemical_id: str = Query("CHEM-NH3"),
    current_risk_score: float = Query(75.0)
):
    """
    Returns prioritized preventive engineering actions ranked by expected risk reduction.
    """
    actions = preventive_engine.generate_ranked_interventions(asset_id, chemical_id, current_risk_score, "Overpressure Drift")
    return [a.model_dump() for a in actions]

@router.post("/preventive/whatif", response_model=PreventiveWhatIfResponse)
def simulate_preventive_whatif(req: PreventiveWhatIfRequest):
    """
    Simulates preventive interventions to quantify risk reduction prior to field execution (PREDICT -> INTERVENE -> VERIFY).
    """
    return preventive_whatif.simulate_intervention_outcome(req)

@router.post("/preventive/authorize-control")
def authorize_control_action(
    action_id: str = Body(...),
    approver_name: str = Body("Lead HSE Controller"),
    approver_role: str = Body("HSE_COMMANDER"),
    checklist_confirmations: List[str] = Body(...)
):
    """
    Formally authorize a proposed DCS/SIS control action through the safety-control boundary.
    """
    return safety_control_boundary.authorize_control_action(
        action_id, approver_name, approver_role, checklist_confirmations
    )

# 5. MULTI-RELATIONAL RISK GRAPH & ENVIRONMENTAL CONTEXT
@router.get("/risk-graph/cascade/{asset_id}")
def get_cascade_pathways(asset_id: str):
    """
    Traverse multi-relational risk graph for domino/cascade propagation.
    """
    return risk_graph_service.analyze_cascade_pathways(asset_id)

@router.get("/risk-graph/environmental/{asset_id}")
def get_environmental_receptors(asset_id: str, wind_direction_deg: float = Query(195.0)):
    """
    Evaluate consequence intersections with water bodies, drainages, and nearby settlements.
    """
    return risk_graph_service.evaluate_environmental_consequence(asset_id, wind_direction_deg)

# 6. 19-STAGE END-TO-END DEMONSTRATION STORYLINE
@router.get("/scenarios/19-stage/roster")
def get_19_stage_roster():
    """
    Retrieve metadata for all 19 stages of the T-04 Ammonia demonstration journey.
    """
    return scenario_orchestrator.get_stages_roster()

@router.get("/scenarios/19-stage/{stage_num}")
def execute_19_stage(stage_num: int):
    """
    Execute and fetch the authoritative state for a specific stage of the 19-stage scenario.
    """
    return scenario_orchestrator.execute_stage(stage_num)
