from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.predictive import (
    HazardPrediction, HazardState, HazardFamily, ForecastHorizon,
    FacilityPredictiveTimelineResponse, PredictionExplanationResponse,
    PredictionEvaluationRequest
)
from app.services.predictive.hazard_prediction_service import hazard_prediction_service
from app.services.predictive.backtesting_framework import backtest_engine
from app.services.storage.predictive_repository import predictive_repository

router = APIRouter(prefix="/prediction", tags=["Real-Time Hazard Trajectory & Early-Warning Engine"])

@router.get("/facilities/{facility_id}/current", response_model=HazardPrediction)
def get_current_facility_hazard_prediction(
    facility_id: str = Path(..., description="Target facility ID"),
    asset_id: str = Query("T-04", description="Target equipment asset ID"),
    horizon: ForecastHorizon = Query(ForecastHorizon.HORIZON_10M),
    db: Session = Depends(get_db)
):
    """
    Retrieve live short-horizon hazard state prediction, trend trajectory, and feature explanations.
    """
    try:
        return hazard_prediction_service.evaluate_facility_hazard(
            facility_id=facility_id,
            asset_id=asset_id,
            forecast_horizon=horizon,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate hazard trajectory: {str(e)}")

@router.get("/facilities/{facility_id}/history", response_model=List[HazardPrediction])
def get_facility_prediction_history(
    facility_id: str = Path(...),
    asset_id: Optional[str] = Query(None),
    hazard_family: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Fetch historical hazard predictions and state transitions.
    """
    return predictive_repository.query_history(db, facility_id, asset_id, hazard_family, limit)

@router.get("/facilities/{facility_id}/timeline", response_model=FacilityPredictiveTimelineResponse)
def get_facility_predictive_timeline(
    facility_id: str = Path(...),
    asset_id: str = Query("T-04")
):
    """
    Retrieve sequential predictive timeline (t-10m -> t-5m -> NOW -> t+5m -> t+10m) with projected parameters.
    """
    return hazard_prediction_service.get_predictive_timeline(facility_id, asset_id)

@router.get("/facilities/{facility_id}/explanation", response_model=PredictionExplanationResponse)
def get_facility_prediction_explanation(
    facility_id: str = Path(...),
    asset_id: str = Query("T-04")
):
    """
    Retrieve feature contribution breakdown, calibrated confidence curve, and evidence narrative.
    """
    return hazard_prediction_service.get_prediction_explanation(facility_id, asset_id)

@router.post("/facilities/{facility_id}/evaluate", response_model=HazardPrediction)
def evaluate_facility_hazard_explicit(
    facility_id: str = Path(...),
    req: PredictionEvaluationRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Deterministic evaluation of a specific observation window, optionally simulating stale or missing sensors.
    """
    return hazard_prediction_service.evaluate_facility_hazard(
        facility_id=facility_id,
        asset_id=req.asset_id,
        forecast_horizon=req.forecast_horizon,
        force_stale=req.force_stale_telemetry,
        simulate_missing_sensors=req.simulate_missing_sensors,
        db=db
    )

@router.post("/backtest")
def run_predictive_backtest(
    scenario_name: str = Body("THERMAL_ESCALATION", embed=True),
    duration_minutes: int = Body(15, embed=True)
):
    """
    Run temporal walk-forward backtesting framework to calculate warning lead times, PR-AUC, and calibration.
    """
    return backtest_engine.run_walk_forward_backtest(
        scenario_name=scenario_name,
        duration_minutes=duration_minutes
    )
