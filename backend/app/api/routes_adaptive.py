from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.adaptive import (
    AdaptiveMonitoringDecision, NationalPriorityItem,
    AdaptiveEvaluationRequest, AdaptiveAcknowledgementRequest
)
from app.services.adaptive.adaptive_orchestrator_service import adaptive_orchestrator_service
from app.services.storage.adaptive_repository import adaptive_repository

router = APIRouter(prefix="/adaptive", tags=["Adaptive Sensing & Surveillance Orchestration"])

@router.get("/facilities/{facility_id}/current", response_model=AdaptiveMonitoringDecision)
def get_current_adaptive_decision(
    facility_id: str,
    asset_id: str = "T-04",
    db: Session = Depends(get_db)
):
    """
    Returns the current adaptive monitoring decision, monitoring level (0-5),
    requested evidence, and active evaluation policy for the facility.
    """
    return adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id=facility_id,
        asset_id=asset_id,
        db=db
    )

@router.get("/facilities/{facility_id}/history", response_model=List[AdaptiveMonitoringDecision])
def get_adaptive_decision_history(
    facility_id: str,
    asset_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Returns historical adaptive monitoring decisions and level transitions.
    """
    history = adaptive_repository.query_history(db, facility_id, asset_id, limit=limit)
    if not history:
        # Fall back to live evaluation if no prior record
        dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
            facility_id=facility_id,
            asset_id=asset_id or "T-04",
            db=db
        )
        return [dec]
    return history

@router.get("/facilities/{facility_id}/explanation")
def get_adaptive_decision_explanation(
    facility_id: str,
    asset_id: str = "T-04",
    db: Session = Depends(get_db)
):
    """
    Returns structured explanation of why the current monitoring level was selected,
    what data is being prioritized, and what value of information is expected.
    """
    dec = adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id=facility_id,
        asset_id=asset_id,
        db=db
    )
    return {
        "facility_id": dec.facility_id,
        "monitoring_level": dec.monitoring_level,
        "hazard_state": dec.hazard_state,
        "reason": dec.reason,
        "confidence": dec.confidence,
        "uncertainty_score": dec.uncertainty_score,
        "conflict_mass_k": dec.conflict_mass_k,
        "requested_evidence": dec.requested_evidence,
        "value_of_information": dec.value_of_information,
        "applied_policy": dec.applied_policy,
        "is_in_cooldown": dec.is_in_cooldown,
        "cooldown_remaining_sec": dec.cooldown_remaining_sec,
        "expires_at": dec.expires_at
    }

@router.get("/priority", response_model=List[NationalPriorityItem])
def get_national_priority_queue(db: Session = Depends(get_db)):
    """
    Returns the national-scale ranked surveillance priority queue across all registered industrial clusters.
    Uses dynamic aging to guarantee baseline coverage while focusing attention on active risks.
    """
    return adaptive_orchestrator_service.get_national_priority_queue(db=db)

@router.post("/facilities/{facility_id}/evaluate", response_model=AdaptiveMonitoringDecision)
def evaluate_facility_adaptive_monitoring(
    facility_id: str,
    req: AdaptiveEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Runs deterministic evaluation of the adaptive monitoring policy.
    Supports simulation injection parameters (force state, force missing sources).
    """
    return adaptive_orchestrator_service.evaluate_facility_orchestration(
        facility_id=facility_id,
        asset_id=req.asset_id,
        force_hazard_state=req.force_hazard_state,
        force_uncertainty=req.force_uncertainty,
        force_missing_sources=req.force_missing_sources,
        db=db
    )

@router.post("/facilities/{facility_id}/acknowledge", response_model=AdaptiveMonitoringDecision)
def acknowledge_monitoring_recommendation(
    facility_id: str,
    req: AdaptiveAcknowledgementRequest,
    db: Session = Depends(get_db)
):
    """
    Logs human operator acknowledgement of the adaptive surveillance recommendation.
    NOTE: This acknowledges analytical awareness, NOT physical plant actuation.
    """
    # Ensure current decision exists in DB
    current_dec = adaptive_orchestrator_service.evaluate_facility_orchestration(facility_id=facility_id, db=db)
    
    ack = adaptive_repository.acknowledge_decision(
        db=db,
        facility_id=facility_id,
        operator_name=req.operator_name,
        notes=req.notes
    )
    if not ack:
        return current_dec
    return ack
