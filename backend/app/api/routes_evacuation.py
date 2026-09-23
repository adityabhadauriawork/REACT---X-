from fastapi import APIRouter, Depends, Body
from typing import Optional, List
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.evacuation.evacuation_service import evacuation_service
from app.schemas.hazard import HazardSimulationResult
from app.schemas.impact import ImpactAnalysisResult
from app.schemas.evacuation import EvacuationPlanResponse

router = APIRouter(prefix="/evacuation", tags=["Dynamic Evacuation Engine"])

class EvacAnalysisPayload:
    pass

@router.post("/route", response_model=EvacuationPlanResponse)
def calculate_safe_evacuation_route(
    simulation_result: HazardSimulationResult = Body(...),
    impact_result: ImpactAnalysisResult = Body(...),
    origin_coords: Optional[List[float]] = Body(None),
    origin_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Generate graph-based safe evacuation routes avoiding roads severed by lethal and injury hazard envelopes.
    """
    return evacuation_service.generate_evacuation_plan(
        db=db,
        simulation_result=simulation_result,
        impact_result=impact_result,
        origin_coords=origin_coords,
        origin_name=origin_name
    )
