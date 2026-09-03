from fastapi import APIRouter, HTTPException, Depends, Query, Body, Path
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.fusion import (
    FusedHazardAssessment, EvidenceItem, FusionEvaluationRequest,
    MultimodalAblationResult
)
from app.services.fusion.multimodal_fusion_service import multimodal_fusion_service
from app.services.fusion.ablation_service import ablation_service
from app.services.storage.fusion_repository import fusion_repository

router = APIRouter(prefix="/fusion", tags=["Multimodal Evidence Fusion & Trusted Hazard Assessment"])

@router.get("/facilities/{facility_id}/current", response_model=FusedHazardAssessment)
def get_current_facility_fusion(
    facility_id: str = Path(..., description="Target facility ID"),
    asset_id: str = Query("T-04", description="Target equipment asset ID"),
    db: Session = Depends(get_db)
):
    """
    Retrieve live multimodal fused hazard assessment, Dempster-Shafer masses, conflict K, and evidence matrix.
    """
    try:
        return multimodal_fusion_service.evaluate_facility_fusion(
            facility_id=facility_id,
            asset_id=asset_id,
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate multimodal fusion: {str(e)}")

@router.get("/facilities/{facility_id}/history", response_model=List[FusedHazardAssessment])
def get_facility_fusion_history(
    facility_id: str = Path(...),
    asset_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Fetch historical fused hazard assessments.
    """
    return fusion_repository.query_history(db, facility_id, asset_id, limit)

@router.get("/facilities/{facility_id}/evidence", response_model=List[EvidenceItem])
def get_facility_current_evidence(
    facility_id: str = Path(...),
    asset_id: str = Query("T-04"),
    db: Session = Depends(get_db)
):
    """
    Retrieve normalized evidence items across all upstream sensory modalities (Telemetry, Thermal, CCTV, Satellite, Prediction).
    """
    asm = multimodal_fusion_service.evaluate_facility_fusion(facility_id, asset_id, db=db)
    items = []
    items.extend(asm.agreement_matrix.supporting_signals)
    items.extend(asm.agreement_matrix.contradicting_signals)
    items.extend(asm.agreement_matrix.conflicting_signals)
    items.extend(asm.agreement_matrix.stale_signals)
    return items

@router.get("/facilities/{facility_id}/explanation")
def get_facility_fusion_explanation(
    facility_id: str = Path(...),
    asset_id: str = Query("T-04"),
    db: Session = Depends(get_db)
):
    """
    Retrieve structured narrative explanation, conflict analysis, and recommended response action.
    """
    asm = multimodal_fusion_service.evaluate_facility_fusion(facility_id, asset_id, db=db)
    return {
        "assessment_id": asm.assessment_id,
        "facility_id": asm.facility_id,
        "asset_id": asm.asset_id,
        "fused_state": asm.fused_state,
        "confidence": asm.confidence,
        "uncertainty_score": asm.uncertainty_score,
        "conflict_mass_k": asm.conflict_mass_k,
        "top_supporting_evidence": asm.top_supporting_evidence,
        "conflict_explanation": asm.conflict_explanation,
        "missing_evidence_explanation": asm.missing_evidence_explanation,
        "recommended_action": asm.recommended_action,
        "recommended_action_detail": asm.recommended_action_detail,
        "human_review_required": asm.human_review_required
    }

@router.get("/facilities/{facility_id}/sources")
def get_registered_modality_sources(
    facility_id: str = Path(...)
):
    """
    List all upstream evidence sources with their calibrated reliabilities and expected freshness TTLs.
    """
    from app.services.fusion.evidence_normalizer import EvidenceNormalizer
    return {
        "facility_id": facility_id,
        "freshness_ttls_seconds": {k.value: v for k, v in EvidenceNormalizer.FRESHNESS_TTL_SEC.items()},
        "calibrated_source_reliabilities": {k.value: v for k, v in EvidenceNormalizer.SOURCE_RELIABILITIES.items()}
    }

@router.post("/facilities/{facility_id}/evaluate", response_model=FusedHazardAssessment)
def evaluate_facility_fusion_explicit(
    facility_id: str = Path(...),
    req: FusionEvaluationRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Deterministic evaluation of an explicit observation window with simulated anomalies, staleness, or missing modalities.
    """
    return multimodal_fusion_service.evaluate_facility_fusion(
        facility_id=facility_id,
        asset_id=req.asset_id,
        force_satellite_anomaly=req.force_satellite_anomaly,
        force_satellite_stale=req.force_satellite_stale,
        force_telemetry_stale=req.force_telemetry_stale,
        simulate_missing_sources=req.simulate_missing_sources,
        db=db
    )

@router.post("/ablation", response_model=List[MultimodalAblationResult])
def run_multimodal_ablation_benchmarks():
    """
    Execute systematic multimodal ablation evaluation comparing single vs combined modalities.
    """
    return ablation_service.run_ablation_suite()
