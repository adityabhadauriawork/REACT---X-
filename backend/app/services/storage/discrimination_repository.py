import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.discrimination_models import ThermalSourceDiscriminationRecord
from app.schemas.discrimination import (
    DiscriminationAssessment, LandCoverContextResult, LandCoverClass,
    ObservationQualityState, SourcePersistenceState, EOVerificationResult,
    EOStructuralMatchStatus, EOStructuralFeature, EvidenceExplanationItem
)

class DiscriminationRepository:
    """
    DAO repository for persisting and retrieving thermal source discrimination assessments.
    """

    def persist_assessment(self, db: Session, asm: DiscriminationAssessment) -> ThermalSourceDiscriminationRecord:
        rec = ThermalSourceDiscriminationRecord(
            assessment_id=asm.assessment_id or f"DISCRIM-{uuid.uuid4().hex[:10].upper()}",
            source_id=asm.source_id,
            centroid_lat=asm.centroid_lat,
            centroid_lon=asm.centroid_lon,
            h3_index=asm.h3_index,
            created_at=asm.created_at,
            predicted_class=asm.predicted_class,
            class_probabilities_json=asm.class_probabilities,
            classification_state=asm.classification_state,
            model_confidence=asm.model_confidence,
            system_confidence=asm.system_confidence,
            evidence_sufficiency=asm.evidence_sufficiency,
            persistence_state=asm.persistence_state.value if hasattr(asm.persistence_state, "value") else str(asm.persistence_state),
            observation_count=asm.observation_count,
            mean_frp_mw=asm.mean_frp_mw,
            max_frp_mw=asm.max_frp_mw,
            diurnal_night_fraction=asm.diurnal_night_fraction,
            spatial_dispersion_r95_m=asm.spatial_dispersion_r95_m,
            facility_attribution_status=asm.facility_attribution_status,
            attributed_facility_id=asm.attributed_facility_id,
            attributed_facility_name=asm.attributed_facility_name,
            facility_distance_m=asm.facility_distance_m,
            is_inside_facility=asm.is_inside_facility,
            land_cover_class=asm.land_cover.land_cover_class.value if hasattr(asm.land_cover.land_cover_class, "value") else str(asm.land_cover.land_cover_class),
            land_cover_dataset=asm.land_cover.dataset_source,
            land_cover_consistency=asm.land_cover.consistency_with_industrial,
            observation_quality=asm.observation_quality.value if hasattr(asm.observation_quality, "value") else str(asm.observation_quality),
            quality_explanation=asm.quality_explanation,
            is_potential_reflection=asm.is_potential_reflection,
            eo_verification_json=asm.eo_verification.model_dump(mode="json") if asm.eo_verification else None,
            eo_verification_required=asm.eo_verification_required,
            top_supporting_evidence_json=[e.model_dump(mode="json") for e in asm.top_supporting_evidence] if asm.top_supporting_evidence else [],
            top_opposing_evidence_json=[e.model_dump(mode="json") for e in asm.top_opposing_evidence] if asm.top_opposing_evidence else [],
            abstention_reason=asm.abstention_reason,
            is_live_data=asm.is_live_data,
            is_simulated=asm.is_simulated,
            discrimination_version=asm.discrimination_version
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    def get_latest_assessment(self, db: Session, source_id: str) -> Optional[DiscriminationAssessment]:
        rec = db.query(ThermalSourceDiscriminationRecord).filter(
            ThermalSourceDiscriminationRecord.source_id == source_id
        ).order_by(desc(ThermalSourceDiscriminationRecord.created_at)).first()
        if not rec:
            return None
        return self._record_to_schema(rec)

    def query_history(self, db: Session, source_id: str, limit: int = 50) -> List[DiscriminationAssessment]:
        records = db.query(ThermalSourceDiscriminationRecord).filter(
            ThermalSourceDiscriminationRecord.source_id == source_id
        ).order_by(desc(ThermalSourceDiscriminationRecord.created_at)).limit(limit).all()
        return [self._record_to_schema(r) for r in records]

    def _record_to_schema(self, rec: ThermalSourceDiscriminationRecord) -> DiscriminationAssessment:
        lc_class = LandCoverClass(rec.land_cover_class) if rec.land_cover_class in LandCoverClass.__members__ else LandCoverClass.INDUSTRIAL_BUILT_UP
        land_cover = LandCoverContextResult(
            land_cover_class=lc_class,
            dataset_source=rec.land_cover_dataset or "Copernicus Global Land Service / ESA WorldCover (10m)",
            dataset_version="2024-v1.2",
            spatial_confidence=0.95,
            consistency_with_industrial=rec.land_cover_consistency or 0.9,
            is_authoritative=True
        )

        eo_ver = None
        if rec.eo_verification_json:
            eo_ver = EOVerificationResult(**rec.eo_verification_json)

        sup_ev = [EvidenceExplanationItem(**e) for e in (rec.top_supporting_evidence_json or [])]
        opp_ev = [EvidenceExplanationItem(**e) for e in (rec.top_opposing_evidence_json or [])]

        return DiscriminationAssessment(
            assessment_id=rec.assessment_id,
            source_id=rec.source_id,
            centroid_lat=rec.centroid_lat,
            centroid_lon=rec.centroid_lon,
            h3_index=rec.h3_index,
            created_at=rec.created_at.replace(tzinfo=timezone.utc) if rec.created_at.tzinfo is None else rec.created_at,
            predicted_class=rec.predicted_class,
            class_probabilities=rec.class_probabilities_json or {},
            classification_state=rec.classification_state,
            model_confidence=rec.model_confidence,
            system_confidence=rec.system_confidence,
            evidence_sufficiency=rec.evidence_sufficiency,
            persistence_state=SourcePersistenceState(rec.persistence_state) if rec.persistence_state in SourcePersistenceState.__members__ else SourcePersistenceState.PERSISTENT,
            observation_count=rec.observation_count,
            mean_frp_mw=rec.mean_frp_mw,
            max_frp_mw=rec.max_frp_mw,
            diurnal_night_fraction=rec.diurnal_night_fraction,
            spatial_dispersion_r95_m=rec.spatial_dispersion_r95_m,
            facility_attribution_status=rec.facility_attribution_status,
            attributed_facility_id=rec.attributed_facility_id,
            attributed_facility_name=rec.attributed_facility_name,
            facility_distance_m=rec.facility_distance_m,
            is_inside_facility=rec.is_inside_facility,
            land_cover=land_cover,
            observation_quality=ObservationQualityState(rec.observation_quality) if rec.observation_quality in ObservationQualityState.__members__ else ObservationQualityState.GOOD,
            quality_explanation=rec.quality_explanation,
            is_potential_reflection=rec.is_potential_reflection,
            eo_verification=eo_ver,
            eo_verification_required=rec.eo_verification_required,
            top_supporting_evidence=sup_ev,
            top_opposing_evidence=opp_ev,
            abstention_reason=rec.abstention_reason,
            is_live_data=rec.is_live_data,
            is_simulated=rec.is_simulated,
            discrimination_version=rec.discrimination_version
        )

discrimination_repository = DiscriminationRepository()
