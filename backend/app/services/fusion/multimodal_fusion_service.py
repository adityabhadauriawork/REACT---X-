import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.schemas.fusion import (
    FusedHazardAssessment, FusedHazardState, EvidenceItem,
    EvidenceSourceType, EvidenceSupportState, EvidenceAgreementMatrix,
    SynchronizedTimelineEvent, DempsterShaferMass
)
from app.services.fusion.dempster_shafer_engine import ds_combiner
from app.services.fusion.evidence_normalizer import evidence_normalizer
from app.services.industrial.telemetry_service import telemetry_service
from app.services.vision.vision_pipeline_service import vision_pipeline_service
from app.services.predictive.hazard_prediction_service import hazard_prediction_service
from app.services.storage.fusion_repository import fusion_repository

class MultimodalFusionService:
    """
    Central Multimodal Evidence Fusion Orchestrator.
    Combines Satellite, Industrial Telemetry, Thermal Vision, Optical CCTV,
    Hazard Predictions, and Environmental Context into explainable assessments.
    """

    def evaluate_facility_fusion(
        self,
        facility_id: str = "FAC-IN-DAHEJ-001",
        asset_id: str = "T-04",
        force_satellite_anomaly: bool = False,
        force_satellite_stale: bool = False,
        force_telemetry_stale: bool = False,
        simulate_missing_sources: Optional[List[str]] = None,
        db: Optional[Session] = None
    ) -> FusedHazardAssessment:
        now_utc = datetime.now(timezone.utc)
        missing_filter = [s.upper() for s in (simulate_missing_sources or [])]

        evidence_items: List[EvidenceItem] = []
        missing_modalities: List[str] = []

        # 1. Telemetry Evidence (Phase 12)
        if "TELEMETRY" in missing_filter:
            missing_modalities.append("TELEMETRY")
        else:
            tel_obs = telemetry_service.get_latest_facility_telemetry(facility_id)
            asset_tel = [t for t in tel_obs if t.asset_id == asset_id]
            for t in asset_tel:
                ev = evidence_normalizer.normalize_telemetry(t)
                if force_telemetry_stale:
                    ev.freshness_status = "STALE"
                    ev.support_state = EvidenceSupportState.STALE
                evidence_items.append(ev)

        # 2. Thermal Vision & CCTV Evidence (Phase 13)
        if "THERMAL_CAMERA" in missing_filter:
            missing_modalities.append("THERMAL_CAMERA")
        else:
            th_vis = vision_pipeline_service.get_latest_camera_vision("CAM-TH-T04-01")
            th_frame = th_vis.get("thermal")
            if th_frame:
                evidence_items.append(evidence_normalizer.normalize_thermal_vision(th_frame))

        if "CCTV" in missing_filter:
            missing_modalities.append("CCTV")
        else:
            cctv_vis = vision_pipeline_service.get_latest_camera_vision("CAM-CCTV-T04-01")
            cctv_frame = cctv_vis.get("cctv")
            if cctv_frame:
                evidence_items.append(evidence_normalizer.normalize_cctv(cctv_frame))

        # 3. Hazard Trajectory Prediction (Phase 14)
        if "PREDICTION" in missing_filter:
            missing_modalities.append("PREDICTION")
        else:
            try:
                pred = hazard_prediction_service.evaluate_facility_hazard(facility_id=facility_id, asset_id=asset_id)
                evidence_items.append(evidence_normalizer.normalize_prediction(pred))
            except Exception:
                pass

        # 4. Satellite Context (FIRMS)
        if "SATELLITE" in missing_filter:
            missing_modalities.append("SATELLITE")
        else:
            sat_ev = evidence_normalizer.generate_satellite_evidence(
                facility_id, asset_id, force_satellite_anomaly, force_satellite_stale
            )
            evidence_items.append(sat_ev)

        # 5. Execute Dempster-Shafer Evidence Combination
        ds_mass = ds_combiner.combine_evidence_items(evidence_items)

        # 6. Build Evidence Agreement Matrix
        matrix = self._build_agreement_matrix(evidence_items, missing_modalities)

        # 7. State Decision Logic & Conflict Detection
        fused_state, conf, uncert, conf_expl, rec_action, rec_detail, rev_req = self._resolve_fused_state(
            ds_mass, matrix, evidence_items, missing_modalities
        )

        # 8. Top Supporting Evidence Items
        top_supporting = [
            f"{e.source_type.value}: {e.evidence_type} ({e.raw_value} {e.unit}, score: {e.normalized_score})"
            for e in matrix.supporting_signals[:4]
        ]

        # 9. Synchronized Evidence Timeline
        timeline = self._generate_evidence_timeline(matrix, fused_state)

        # 10. Assemble Canonical Assessment
        assessment = FusedHazardAssessment(
            assessment_id=f"FUSED-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            facility_id=facility_id,
            asset_id=asset_id,
            zone_id="Sector D - Cryogenic Yard",
            created_at=now_utc,
            assessment_window_start=now_utc - timedelta(minutes=15),
            assessment_window_end=now_utc,
            hazard_family="THERMAL_ESCALATION",
            fused_state=fused_state,
            confidence=round(conf, 3),
            uncertainty_score=round(uncert, 3),
            conflict_mass_k=ds_mass.conflict_mass_k,
            dempster_shafer=ds_mass,
            agreement_matrix=matrix,
            top_supporting_evidence=top_supporting,
            conflict_explanation=conf_expl,
            missing_evidence_explanation=f"Missing modalities: {', '.join(missing_modalities)}" if missing_modalities else None,
            recommended_action=rec_action,
            recommended_action_detail=rec_detail,
            human_review_required=rev_req,
            evidence_timeline=timeline,
            data_lineage={
                "evidence_count": len(evidence_items),
                "supporting_count": len(matrix.supporting_signals),
                "contradicting_count": len(matrix.contradicting_signals),
                "stale_count": len(matrix.stale_signals),
                "conflict_k": ds_mass.conflict_mass_k
            },
            is_live_data=False,
            is_simulated=True
        )

        # Persist if DB session provided
        if db:
            try:
                fusion_repository.persist_assessment(db, assessment)
            except Exception:
                pass

        return assessment

    def _build_agreement_matrix(
        self,
        items: List[EvidenceItem],
        missing: List[str]
    ) -> EvidenceAgreementMatrix:
        supporting = [e for e in items if e.support_state == EvidenceSupportState.SUPPORTING and e.freshness_status != "STALE"]
        contradicting = [e for e in items if e.support_state == EvidenceSupportState.CONTRADICTING and e.freshness_status != "STALE"]
        conflicting = [e for e in items if e.support_state == EvidenceSupportState.CONFLICTING]
        stale = [e for e in items if e.freshness_status == "STALE" or e.support_state == EvidenceSupportState.STALE]

        return EvidenceAgreementMatrix(
            supporting_signals=supporting,
            contradicting_signals=contradicting,
            conflicting_signals=conflicting,
            stale_signals=stale,
            missing_modalities=missing
        )

    def _resolve_fused_state(
        self,
        ds: DempsterShaferMass,
        matrix: EvidenceAgreementMatrix,
        items: List[EvidenceItem],
        missing: List[str]
    ) -> tuple:
        """
        Determines the fused hazard state, confidence, uncertainty, and actions.
        """
        k = ds.conflict_mass_k
        bel_therm = ds.belief.get("THERMAL_ESCALATION", 0.0)
        bel_norm = ds.belief.get("NORMAL", 0.0)
        bel_inc = ds.belief.get("INCIDENT", 0.0)
        uncert = ds.uncertainty_mass

        # Case 1: Total Absence of Modalities
        if len(items) == 0:
            return (
                FusedHazardState.UNAVAILABLE, 0.0, 1.0,
                None, "SYSTEM_OFFLINE", "All sensor telemetry and vision feeds unavailable.", True
            )

        # Case 2: Critical Telemetry Missing -> INSUFFICIENT_EVIDENCE
        if "TELEMETRY" in missing and "THERMAL_CAMERA" in missing:
            return (
                FusedHazardState.INSUFFICIENT_EVIDENCE, 0.20, 0.85,
                None, "REQUEST_LOCAL_VERIFICATION", "Both process telemetry and thermal vision feeds are missing.", True
            )

        # Case 3: High Conflict (K >= 0.40) between positive escalation and nominal signals
        if len(matrix.supporting_signals) > 0 and len(matrix.contradicting_signals) > 0 and k >= 0.40:
            expl = "Significant cross-modal discrepancy: Satellite thermal anomaly detected, but local facility process sensors and thermal cameras indicate nominal baseline."
            return (
                FusedHazardState.CONFLICTING_EVIDENCE, 0.45, 0.60,
                expl, "INVESTIGATE_SENSOR_DISCREPANCY", "Inspect physical asset for localized flare or sensor miscalibration.", True
            )

        # Case 4: Strong Multi-Modal Agreement on Escalation
        if len(matrix.supporting_signals) >= 3 and (bel_therm > 0.60 or bel_inc > 0.60):
            return (
                FusedHazardState.CRITICAL, 0.94, 0.06,
                None, "INITIATE_EMERGENCY_STANDBY", "Multiple independent sensors confirm acute thermal/pressure escalation.", False
            )

        # Case 5: 2 Independent Signals on Developing Hazard
        if len(matrix.supporting_signals) >= 2 or bel_therm > 0.45:
            return (
                FusedHazardState.HAZARD_DEVELOPING, 0.88, 0.12,
                None, "ELEVATED_SURVEILLANCE", "Telemetry and thermal trends confirm upward excursion.", False
            )

        # Case 6: Single Source Anomaly -> WATCH
        if len(matrix.supporting_signals) == 1:
            return (
                FusedHazardState.WATCH, 0.75, 0.25,
                None, "MONITOR_ASSET_TREND", "Single sensor baseline departure detected; corroboration pending.", False
            )

        # Case 7: Nominal Consensus
        return (
            FusedHazardState.NORMAL, 0.95, 0.05,
            None, "ROUTINE_MONITORING", "All live process telemetry and thermal vision feeds within operating limits.", False
        )

    def _generate_evidence_timeline(
        self,
        matrix: EvidenceAgreementMatrix,
        state: FusedHazardState
    ) -> List[SynchronizedTimelineEvent]:
        now = datetime.now(timezone.utc)
        events = []

        for e in matrix.supporting_signals:
            events.append(SynchronizedTimelineEvent(
                timestamp_utc=e.observation_timestamp,
                relative_time=f"{(e.observation_timestamp - now).total_seconds():.0f}s",
                source_type=e.source_type,
                source_name=e.source_id,
                description=f"{e.evidence_type}: {e.raw_value} {e.unit} (excursion support)",
                state_impact="ESCALATION_SUPPORT"
            ))

        for e in matrix.stale_signals:
            events.append(SynchronizedTimelineEvent(
                timestamp_utc=e.observation_timestamp,
                relative_time=f"{(e.observation_timestamp - now).total_seconds() / 60.0:.0f}m",
                source_type=e.source_type,
                source_name=e.source_id,
                description=f"{e.source_type.value} observation aged > TTL (marked STALE)",
                state_impact="CONTEXT_ONLY"
            ))

        # Sort timeline chronologically
        events.sort(key=lambda x: x.timestamp_utc)
        return events

multimodal_fusion_service = MultimodalFusionService()
