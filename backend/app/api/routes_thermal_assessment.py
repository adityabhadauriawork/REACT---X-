from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.thermal_assessment import (
    IndustrialThermalAssessment,
    ReactXIncidentDraft,
    AssessmentRequest,
    IncidentPromotionRequest,
    IncidentRejectionRequest,
    AssessmentExecutiveBriefResponse,
    IndustrialRiskLevel,
    HandoffEligibility,
    AssessmentStatus
)
from app.models.thermal_assessment import IndustrialThermalAssessmentModel
from app.models.thermal_source import ThermalSourceModel
from app.services.satellite.assessment_engine import assessment_engine

assessment_router = APIRouter(prefix="/thermal", tags=["Industrial Thermal Assessment & Risk"])


@assessment_router.get("/sources/{source_id}/assessment", response_model=IndustrialThermalAssessment)
def get_source_assessment(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve active assessment for a thermal source, evaluating on-the-fly if not already computed.
    """
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal source {source_id} not found.")

    # Check for existing latest assessment
    latest = db.query(IndustrialThermalAssessmentModel).filter(
        IndustrialThermalAssessmentModel.source_id == source_id
    ).order_by(IndustrialThermalAssessmentModel.version.desc()).first()

    if latest:
        # Reconstruct Pydantic schema from persisted record
        return IndustrialThermalAssessment(
            assessment_id=latest.assessment_id,
            source_id=latest.source_id,
            facility_id=latest.facility_id,
            facility_name=latest.facility_name,
            centroid_lat=latest.centroid_lat,
            centroid_lon=latest.centroid_lon,
            attribution_confidence=latest.attribution_confidence,
            classification_confidence=latest.classification_confidence,
            abnormality_confidence=latest.abnormality_confidence,
            overall_evidence_confidence=latest.overall_evidence_confidence,
            classification=latest.classification,
            classification_probabilities=latest.classification_probabilities,
            abnormality_score=latest.abnormality_score,
            abnormality_status=latest.abnormality_status,
            robust_zscore=latest.robust_zscore,
            attribution_status=latest.attribution_status,
            corroboration_status=latest.corroboration_status,
            industrial_risk_level=latest.industrial_risk_level,
            industrial_risk_score=latest.industrial_risk_score,
            risk_confidence=latest.risk_confidence,
            risk_label=latest.risk_label,
            is_routine_operation=latest.is_routine_operation,
            operational_concern_summary=latest.operational_concern_summary,
            evidence_summary=latest.evidence_summary,
            evidence_items=latest.evidence_items,
            handoff_eligibility=latest.handoff_eligibility,
            incident_draft=latest.incident_draft,
            assessment_status=latest.assessment_status,
            version=latest.version,
            parent_assessment_id=latest.parent_assessment_id,
            classification_model_version=latest.classification_model_version,
            abnormality_algorithm_version=latest.abnormality_algorithm_version,
            attribution_algorithm_version=latest.attribution_algorithm_version,
            evidence_fusion_version=latest.evidence_fusion_version,
            risk_algorithm_version=latest.risk_algorithm_version,
            created_at=latest.created_at,
            updated_at=latest.updated_at
        )

    # Compute fresh assessment and persist
    assessment = assessment_engine.assess_thermal_source(source=source, db=db)
    assessment_engine.persist_assessment(assessment=assessment, db=db)
    return assessment


@assessment_router.post("/sources/{source_id}/assess", response_model=IndustrialThermalAssessment)
def force_reassess_thermal_source(
    source_id: str,
    req: Optional[AssessmentRequest] = Body(default=None),
    db: Session = Depends(get_db)
):
    """
    Force re-evaluation of the multi-factor assessment pipeline for a thermal source.
    """
    source = db.query(ThermalSourceModel).filter(ThermalSourceModel.source_id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Thermal source {source_id} not found.")

    assessment = assessment_engine.assess_thermal_source(source=source, db=db, req=req)
    assessment_engine.persist_assessment(assessment=assessment, db=db)
    return assessment


@assessment_router.get("/assessments", response_model=List[IndustrialThermalAssessment])
def list_assessments(
    risk_level: Optional[str] = Query(None, description="NOMINAL, LOW, MODERATE, HIGH, CRITICAL"),
    handoff_eligibility: Optional[str] = Query(None, description="NOT_ELIGIBLE, REVIEW_REQUIRED, INCIDENT_DRAFT_READY, INCIDENT_ACTIVE"),
    status: Optional[str] = Query(None, description="INITIAL, UPDATED, CONFIRMED, DOWNGRADED, CLOSED"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    List recent industrial thermal assessments with optional filtering.
    """
    q = db.query(IndustrialThermalAssessmentModel)
    if risk_level:
        q = q.filter(IndustrialThermalAssessmentModel.industrial_risk_level == risk_level)
    if handoff_eligibility:
        q = q.filter(IndustrialThermalAssessmentModel.handoff_eligibility == handoff_eligibility)
    if status:
        q = q.filter(IndustrialThermalAssessmentModel.assessment_status == status)

    records = q.order_by(IndustrialThermalAssessmentModel.created_at.desc()).limit(limit).all()
    results = []
    for r in records:
        results.append(IndustrialThermalAssessment(
            assessment_id=r.assessment_id,
            source_id=r.source_id,
            facility_id=r.facility_id,
            facility_name=r.facility_name,
            centroid_lat=r.centroid_lat,
            centroid_lon=r.centroid_lon,
            attribution_confidence=r.attribution_confidence,
            classification_confidence=r.classification_confidence,
            abnormality_confidence=r.abnormality_confidence,
            overall_evidence_confidence=r.overall_evidence_confidence,
            classification=r.classification,
            classification_probabilities=r.classification_probabilities,
            abnormality_score=r.abnormality_score,
            abnormality_status=r.abnormality_status,
            robust_zscore=r.robust_zscore,
            attribution_status=r.attribution_status,
            corroboration_status=r.corroboration_status,
            industrial_risk_level=r.industrial_risk_level,
            industrial_risk_score=r.industrial_risk_score,
            risk_confidence=r.risk_confidence,
            risk_label=r.risk_label,
            is_routine_operation=r.is_routine_operation,
            operational_concern_summary=r.operational_concern_summary,
            evidence_summary=r.evidence_summary,
            evidence_items=r.evidence_items,
            handoff_eligibility=r.handoff_eligibility,
            incident_draft=r.incident_draft,
            assessment_status=r.assessment_status,
            version=r.version,
            parent_assessment_id=r.parent_assessment_id,
            classification_model_version=r.classification_model_version,
            abnormality_algorithm_version=r.abnormality_algorithm_version,
            attribution_algorithm_version=r.attribution_algorithm_version,
            evidence_fusion_version=r.evidence_fusion_version,
            risk_algorithm_version=r.risk_algorithm_version,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))
    return results


@assessment_router.get("/assessments/{assessment_id}", response_model=IndustrialThermalAssessment)
def get_assessment_by_id(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific assessment by ID.
    """
    r = db.query(IndustrialThermalAssessmentModel).filter(IndustrialThermalAssessmentModel.assessment_id == assessment_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")

    return IndustrialThermalAssessment(
        assessment_id=r.assessment_id,
        source_id=r.source_id,
        facility_id=r.facility_id,
        facility_name=r.facility_name,
        centroid_lat=r.centroid_lat,
        centroid_lon=r.centroid_lon,
        attribution_confidence=r.attribution_confidence,
        classification_confidence=r.classification_confidence,
        abnormality_confidence=r.abnormality_confidence,
        overall_evidence_confidence=r.overall_evidence_confidence,
        classification=r.classification,
        classification_probabilities=r.classification_probabilities,
        abnormality_score=r.abnormality_score,
        abnormality_status=r.abnormality_status,
        robust_zscore=r.robust_zscore,
        attribution_status=r.attribution_status,
        corroboration_status=r.corroboration_status,
        industrial_risk_level=r.industrial_risk_level,
        industrial_risk_score=r.industrial_risk_score,
        risk_confidence=r.risk_confidence,
        risk_label=r.risk_label,
        is_routine_operation=r.is_routine_operation,
        operational_concern_summary=r.operational_concern_summary,
        evidence_summary=r.evidence_summary,
        evidence_items=r.evidence_items,
        handoff_eligibility=r.handoff_eligibility,
        incident_draft=r.incident_draft,
        assessment_status=r.assessment_status,
        version=r.version,
        parent_assessment_id=r.parent_assessment_id,
        classification_model_version=r.classification_model_version,
        abnormality_algorithm_version=r.abnormality_algorithm_version,
        attribution_algorithm_version=r.attribution_algorithm_version,
        evidence_fusion_version=r.evidence_fusion_version,
        risk_algorithm_version=r.risk_algorithm_version,
        created_at=r.created_at,
        updated_at=r.updated_at
    )


@assessment_router.get("/assessments/{assessment_id}/history", response_model=List[IndustrialThermalAssessment])
def get_assessment_history(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve full historical version tree for a thermal assessment.
    """
    base = db.query(IndustrialThermalAssessmentModel).filter(IndustrialThermalAssessmentModel.assessment_id == assessment_id).first()
    if not base:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")

    records = db.query(IndustrialThermalAssessmentModel).filter(
        IndustrialThermalAssessmentModel.source_id == base.source_id
    ).order_by(IndustrialThermalAssessmentModel.version.asc()).all()

    return [
        IndustrialThermalAssessment(
            assessment_id=r.assessment_id,
            source_id=r.source_id,
            facility_id=r.facility_id,
            facility_name=r.facility_name,
            centroid_lat=r.centroid_lat,
            centroid_lon=r.centroid_lon,
            attribution_confidence=r.attribution_confidence,
            classification_confidence=r.classification_confidence,
            abnormality_confidence=r.abnormality_confidence,
            overall_evidence_confidence=r.overall_evidence_confidence,
            classification=r.classification,
            classification_probabilities=r.classification_probabilities,
            abnormality_score=r.abnormality_score,
            abnormality_status=r.abnormality_status,
            robust_zscore=r.robust_zscore,
            attribution_status=r.attribution_status,
            corroboration_status=r.corroboration_status,
            industrial_risk_level=r.industrial_risk_level,
            industrial_risk_score=r.industrial_risk_score,
            risk_confidence=r.risk_confidence,
            risk_label=r.risk_label,
            is_routine_operation=r.is_routine_operation,
            operational_concern_summary=r.operational_concern_summary,
            evidence_summary=r.evidence_summary,
            evidence_items=r.evidence_items,
            handoff_eligibility=r.handoff_eligibility,
            incident_draft=r.incident_draft,
            assessment_status=r.assessment_status,
            version=r.version,
            parent_assessment_id=r.parent_assessment_id,
            classification_model_version=r.classification_model_version,
            abnormality_algorithm_version=r.abnormality_algorithm_version,
            attribution_algorithm_version=r.attribution_algorithm_version,
            evidence_fusion_version=r.evidence_fusion_version,
            risk_algorithm_version=r.risk_algorithm_version,
            created_at=r.created_at,
            updated_at=r.updated_at
        ) for r in records
    ]


@assessment_router.post("/assessments/{assessment_id}/promote-incident", response_model=Dict[str, Any])
def promote_assessment_to_incident(
    assessment_id: str,
    req: IncidentPromotionRequest,
    db: Session = Depends(get_db)
):
    """
    Operator action: Authorize promotion of satellite assessment to active REACT-X emergency incident.
    """
    try:
        res = assessment_engine.promote_to_incident(assessment_id=assessment_id, req=req, db=db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@assessment_router.post("/assessments/{assessment_id}/reject-draft", response_model=Dict[str, Any])
def reject_assessment_incident_draft(
    assessment_id: str,
    req: IncidentRejectionRequest,
    db: Session = Depends(get_db)
):
    """
    Operator action: Reject emergency activation and mark as routine operation or false alarm.
    """
    try:
        res = assessment_engine.reject_incident_draft(assessment_id=assessment_id, req=req, db=db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@assessment_router.get("/assessments/{assessment_id}/executive-brief", response_model=AssessmentExecutiveBriefResponse)
def get_assessment_executive_brief(
    assessment_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate unified satellite situation brief in Markdown for executive briefings.
    """
    r = db.query(IndustrialThermalAssessmentModel).filter(IndustrialThermalAssessmentModel.assessment_id == assessment_id).first()
    if not r:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found.")

    assessment = IndustrialThermalAssessment(
        assessment_id=r.assessment_id,
        source_id=r.source_id,
        facility_id=r.facility_id,
        facility_name=r.facility_name,
        centroid_lat=r.centroid_lat,
        centroid_lon=r.centroid_lon,
        attribution_confidence=r.attribution_confidence,
        classification_confidence=r.classification_confidence,
        abnormality_confidence=r.abnormality_confidence,
        overall_evidence_confidence=r.overall_evidence_confidence,
        classification=r.classification,
        classification_probabilities=r.classification_probabilities,
        abnormality_score=r.abnormality_score,
        abnormality_status=r.abnormality_status,
        robust_zscore=r.robust_zscore,
        attribution_status=r.attribution_status,
        corroboration_status=r.corroboration_status,
        industrial_risk_level=r.industrial_risk_level,
        industrial_risk_score=r.industrial_risk_score,
        risk_confidence=r.risk_confidence,
        risk_label=r.risk_label,
        is_routine_operation=r.is_routine_operation,
        operational_concern_summary=r.operational_concern_summary,
        evidence_summary=r.evidence_summary,
        evidence_items=r.evidence_items,
        handoff_eligibility=r.handoff_eligibility,
        incident_draft=r.incident_draft,
        assessment_status=r.assessment_status,
        version=r.version,
        parent_assessment_id=r.parent_assessment_id,
        classification_model_version=r.classification_model_version,
        abnormality_algorithm_version=r.abnormality_algorithm_version,
        attribution_algorithm_version=r.attribution_algorithm_version,
        evidence_fusion_version=r.evidence_fusion_version,
        risk_algorithm_version=r.risk_algorithm_version,
        created_at=r.created_at,
        updated_at=r.updated_at
    )
    return assessment_engine.generate_executive_brief(assessment=assessment, db=db)
