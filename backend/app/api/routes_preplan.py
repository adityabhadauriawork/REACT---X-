from fastapi import APIRouter, Depends, Body, Response, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.services.site.site_service import site_service
from app.services.preplan.preplan_service import preplan_service
from app.services.preplan.authorization_service import authorization_service
from app.schemas.hazard import HazardSimulationResult
from app.schemas.impact import ImpactAnalysisResult
from app.schemas.evacuation import EvacuationPlanResponse
from app.schemas.resource import ResourceOptimizationPlan
from app.schemas.authorization import AuthorizationRequest, RejectionRequest, AuthorizationRecordResponse
from pydantic import BaseModel

router = APIRouter(prefix="/preplan", tags=["Fire Pre-Plan & Authorization"])

class PrePlanFullPayload(BaseModel):
    simulation_result: HazardSimulationResult
    impact_result: ImpactAnalysisResult
    evacuation_plan: EvacuationPlanResponse
    resource_plan: ResourceOptimizationPlan
    author_name: str = "REACT-X Decision Support Engine"
    facility_ref: str = "PCH-ALPHA-04 (Demo Facility — Non-Statutory Evaluation)"
    authorization_id: Optional[str] = None

@router.get("/authorization/{incident_id}", response_model=AuthorizationRecordResponse)
def get_authorization_status(
    incident_id: str,
    asset_id: str = "T-04",
    chemical_id: str = "CHEM-NH3",
    chemical_name: str = "Ammonia (Anhydrous)",
    scenario_hash: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get existing authorization record or initialize a PENDING_HUMAN_AUTHORIZATION record.
    """
    record = authorization_service.get_or_create_record(
        db=db,
        incident_id=incident_id,
        asset_id=asset_id,
        chemical_id=chemical_id,
        chemical_name=chemical_name,
        scenario_hash=scenario_hash
    )
    return AuthorizationRecordResponse(
        authorization_id=record.id,
        incident_id=record.incident_id,
        asset_id=record.asset_id,
        chemical_id=record.chemical_id,
        chemical_name=record.chemical_name,
        document_version=record.document_version,
        status=record.status,
        approver_name=record.approver_name,
        approver_role=record.approver_role,
        checklist_completed=record.checklist_completed,
        approval_notes=record.approval_notes,
        rejection_reason=record.rejection_reason,
        approval_timestamp=record.approval_timestamp,
        created_at=record.created_at
    )

@router.post("/authorize", response_model=AuthorizationRecordResponse)
def authorize_preplan_document(
    req: AuthorizationRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit human HSE review & authorization. Transitions state from PENDING -> AUTHORIZED.
    """
    try:
        record = authorization_service.authorize_preplan(db=db, req=req)
        return AuthorizationRecordResponse(
            authorization_id=record.id,
            incident_id=record.incident_id,
            asset_id=record.asset_id,
            chemical_id=record.chemical_id,
            chemical_name=record.chemical_name,
            document_version=record.document_version,
            status=record.status,
            approver_name=record.approver_name,
            approver_role=record.approver_role,
            checklist_completed=record.checklist_completed,
            approval_notes=record.approval_notes,
            rejection_reason=record.rejection_reason,
            approval_timestamp=record.approval_timestamp,
            created_at=record.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reject", response_model=AuthorizationRecordResponse)
def reject_preplan_document(
    req: RejectionRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Submit human rejection/revision request. Transitions state to REJECTED.
    """
    try:
        record = authorization_service.reject_preplan(db=db, req=req)
        return AuthorizationRecordResponse(
            authorization_id=record.id,
            incident_id=record.incident_id,
            asset_id=record.asset_id,
            chemical_id=record.chemical_id,
            chemical_name=record.chemical_name,
            document_version=record.document_version,
            status=record.status,
            approver_name=record.approver_name,
            approver_role=record.approver_role,
            checklist_completed=record.checklist_completed,
            approval_notes=record.approval_notes,
            rejection_reason=record.rejection_reason,
            approval_timestamp=record.approval_timestamp,
            created_at=record.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate-pdf")
def generate_fire_preplan_pdf(
    payload: PrePlanFullPayload = Body(...),
    db: Session = Depends(get_db)
):
    """
    Generate and stream a professional industrial Emergency Pre-Plan PDF document.
    Validates state consistency and embeds active human authorization governance records.
    """
    # 1. State Consistency Validation
    sim_asset = payload.simulation_result.source_asset_id
    res_incident = payload.resource_plan.incident_id
    sim_chem = payload.simulation_result.chemical_name
    res_chem = payload.resource_plan.chemical_name

    if sim_asset not in res_incident:
        raise HTTPException(
            status_code=400,
            detail=f"State Inconsistency Error: Simulation source asset '{sim_asset}' does not match Tactical Resource Plan incident '{res_incident}'. Please re-run simulation pipeline."
        )

    if sim_chem.strip().lower() != res_chem.strip().lower():
        raise HTTPException(
            status_code=400,
            detail=f"State Inconsistency Error: Simulation chemical '{sim_chem}' does not match Tactical Resource Plan chemical '{res_chem}'. Please re-run simulation pipeline."
        )

    if not payload.simulation_result.summary_zones or len(payload.simulation_result.summary_zones) < 3:
        raise HTTPException(
            status_code=400,
            detail="State Inconsistency Error: Simulation result does not contain complete threat zones (Red, Orange, Yellow)."
        )

    # 2. Retrieve active authorization record if exists
    auth_rec = authorization_service.get_or_create_record(
        db=db,
        incident_id=res_incident,
        asset_id=sim_asset,
        chemical_id=payload.simulation_result.chemical_id,
        chemical_name=sim_chem
    )

    # 3. Build Document
    site_data = site_service.get_full_site_data(db)
    pdf_bytes = preplan_service.generate_pdf_bytes(
        plant_info=site_data["plant"],
        simulation_result=payload.simulation_result,
        impact_result=payload.impact_result,
        evac_plan=payload.evacuation_plan,
        resource_plan=payload.resource_plan,
        auth_record=auth_rec,
        author_name=payload.author_name,
        facility_ref=payload.facility_ref
    )

    clean_chem = payload.simulation_result.chemical_name.split('(')[0].strip().replace(' ', '_')
    status_tag = "AUTHORIZED" if auth_rec and auth_rec.status == "AUTHORIZED" else "DRAFT"
    filename = f"Fire_PrePlan_{sim_asset}_{clean_chem}_{status_tag}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
