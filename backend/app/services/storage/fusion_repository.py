import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.fusion_models import FusedHazardAssessmentRecord
from app.schemas.fusion import (
    FusedHazardAssessment, FusedHazardState, DempsterShaferMass,
    EvidenceAgreementMatrix, SynchronizedTimelineEvent, EvidenceItem
)

class FusionRepository:
    """
    DAO repository for multimodal fused hazard assessments.
    """

    def persist_assessment(self, db: Session, asm: FusedHazardAssessment) -> FusedHazardAssessmentRecord:
        rec = FusedHazardAssessmentRecord(
            assessment_id=asm.assessment_id or f"FUSED-{uuid.uuid4().hex[:10].upper()}",
            facility_id=asm.facility_id,
            asset_id=asm.asset_id,
            zone_id=asm.zone_id,
            created_at=asm.created_at,
            assessment_window_start=asm.assessment_window_start,
            assessment_window_end=asm.assessment_window_end,
            hazard_family=asm.hazard_family,
            fused_state=asm.fused_state.value if hasattr(asm.fused_state, "value") else str(asm.fused_state),
            confidence=asm.confidence,
            uncertainty_score=asm.uncertainty_score,
            conflict_mass_k=asm.conflict_mass_k,
            recommended_action=asm.recommended_action,
            recommended_action_detail=asm.recommended_action_detail,
            human_review_required=asm.human_review_required,
            is_live_data=asm.is_live_data,
            is_simulated=asm.is_simulated,
            fusion_engine_version=asm.fusion_engine_version,
            dempster_shafer_json=asm.dempster_shafer.model_dump(mode="json") if asm.dempster_shafer else {},
            agreement_matrix_json=asm.agreement_matrix.model_dump(mode="json") if asm.agreement_matrix else {},
            top_supporting_evidence_json=asm.top_supporting_evidence,
            timeline_events_json=[t.model_dump(mode="json") for t in asm.evidence_timeline] if asm.evidence_timeline else [],
            data_lineage_json=asm.data_lineage
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    def get_latest_assessment(self, db: Session, facility_id: str, asset_id: Optional[str] = None) -> Optional[FusedHazardAssessment]:
        q = db.query(FusedHazardAssessmentRecord).filter(FusedHazardAssessmentRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(FusedHazardAssessmentRecord.asset_id == asset_id)
        rec = q.order_by(desc(FusedHazardAssessmentRecord.created_at)).first()
        if not rec:
            return None
        return self._record_to_schema(rec)

    def query_history(
        self,
        db: Session,
        facility_id: str,
        asset_id: Optional[str] = None,
        limit: int = 50
    ) -> List[FusedHazardAssessment]:
        q = db.query(FusedHazardAssessmentRecord).filter(FusedHazardAssessmentRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(FusedHazardAssessmentRecord.asset_id == asset_id)
        records = q.order_by(desc(FusedHazardAssessmentRecord.created_at)).limit(limit).all()
        return [self._record_to_schema(r) for r in records]

    def _record_to_schema(self, rec: FusedHazardAssessmentRecord) -> FusedHazardAssessment:
        ds_data = rec.dempster_shafer_json or {}
        ag_data = rec.agreement_matrix_json or {}
        tl_data = rec.timeline_events_json or []

        ds_mass = DempsterShaferMass(**ds_data) if ds_data else DempsterShaferMass()
        ag_matrix = EvidenceAgreementMatrix(**ag_data) if ag_data else EvidenceAgreementMatrix()
        timeline = [SynchronizedTimelineEvent(**t) for t in tl_data]

        return FusedHazardAssessment(
            assessment_id=rec.assessment_id,
            facility_id=rec.facility_id,
            asset_id=rec.asset_id,
            zone_id=rec.zone_id,
            created_at=rec.created_at.replace(tzinfo=timezone.utc) if rec.created_at.tzinfo is None else rec.created_at,
            assessment_window_start=rec.assessment_window_start.replace(tzinfo=timezone.utc) if rec.assessment_window_start.tzinfo is None else rec.assessment_window_start,
            assessment_window_end=rec.assessment_window_end.replace(tzinfo=timezone.utc) if rec.assessment_window_end.tzinfo is None else rec.assessment_window_end,
            hazard_family=rec.hazard_family,
            fused_state=FusedHazardState(rec.fused_state) if rec.fused_state in FusedHazardState.__members__ else FusedHazardState.NORMAL,
            confidence=rec.confidence,
            uncertainty_score=rec.uncertainty_score,
            conflict_mass_k=rec.conflict_mass_k,
            dempster_shafer=ds_mass,
            agreement_matrix=ag_matrix,
            top_supporting_evidence=rec.top_supporting_evidence_json or [],
            recommended_action=rec.recommended_action,
            recommended_action_detail=rec.recommended_action_detail or "",
            human_review_required=rec.human_review_required,
            evidence_timeline=timeline,
            data_lineage=rec.data_lineage_json or {},
            is_live_data=rec.is_live_data,
            is_simulated=rec.is_simulated,
            fusion_engine_version=rec.fusion_engine_version
        )

fusion_repository = FusionRepository()
