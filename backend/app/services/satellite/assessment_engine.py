import math
import uuid
import datetime
from datetime import timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.schemas.thermal_classification import TargetSourceClass as ThermalSourceClass
from app.schemas.thermal_fingerprint import AbnormalityStatus
from app.schemas.thermal_corroboration import EvidenceState, ObservationStatus, SatelliteSensorRole
from app.schemas.thermal_assessment import (
    IndustrialThermalAssessment,
    EvidenceItem,
    ReactXIncidentDraft,
    IndustrialRiskLevel,
    HandoffEligibility,
    AssessmentStatus,
    AssessmentRequest,
    IncidentPromotionRequest,
    IncidentRejectionRequest,
    AssessmentExecutiveBriefResponse
)
from app.schemas.data_quality import AssessmentLineage, DataQualityState
from app.models.thermal_assessment import IndustrialThermalAssessmentModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.models.facility import IndustrialFacilityModel
from app.models.audit import DecisionAuditModel

from app.services.satellite.abnormality_engine import abnormality_engine
from app.services.ml.thermal_classifier_service import classifier_service
from app.services.satellite.evidence_fusion_engine import evidence_fusion_engine


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class IndustrialThermalAssessmentEngine:
    """
    Core Phase 9 Multi-Factor Evidence Fusion & Industrial Risk Assessment Engine.
    Synthesizes Phase 3-8 outputs into an authoritative, reproducible IndustrialThermalAssessment.
    """

    def __init__(self):
        self.classification_model_version = "IHS_INDIA_HGB_v1.0"
        self.abnormality_algorithm_version = "TF-LEVEL5-v1.0"
        self.attribution_algorithm_version = "OSM-GEM-H3-v1.0"
        self.evidence_fusion_version = "EFE-4TIER-v1.0"
        self.risk_algorithm_version = "MFR-SCREENING-v1.0"

    def assess_thermal_source(
        self,
        source: ThermalSourceModel,
        db: Session,
        req: Optional[AssessmentRequest] = None
    ) -> IndustrialThermalAssessment:
        """
        Synthesize all multi-source intelligence layers into an authoritative assessment.
        """
        now = utcnow()

        # 1. Retrieve or evaluate Phase 6 Thermal Abnormality
        abn_result = abnormality_engine.assess_thermal_source(source=source, current_event=None, db=db)
        
        # 2. Retrieve or evaluate Phase 7 AI ML Classification
        clf_result = classifier_service.classify_source(source=source, db=db)

        # 3. Retrieve or evaluate Phase 8 Multi-Satellite Evidence Bundle
        evidence_bundle = evidence_fusion_engine.corroborate_thermal_source(source=source, db=db)

        # 4. Extract 4 SEPARATE & INDEPENDENT CONFIDENCES
        s_attr = self._calculate_attribution_confidence(source)
        s_class = getattr(clf_result, "model_confidence", 0.85)
        s_abn = getattr(abn_result, "confidence", 0.80)
        s_ev = evidence_bundle.overall_evidence_confidence

        abn_status = getattr(abn_result, "status", AbnormalityStatus.NORMAL_BASELINE)
        robust_z = getattr(abn_result, "frp_robust_zscore", 0.0)
        abn_score = getattr(abn_result, "overall_abnormality_score", 0.0)

        # 5. Determine Routine vs Abnormal Operational State
        is_routine, operational_summary = self._evaluate_operational_status(
            source=source,
            classification=clf_result.predicted_class,
            abnormality_status=abn_status,
            robust_z=robust_z,
            mean_frp=source.mean_frp_mw
        )

        # 6. Multi-Factor Screening-Level Industrial Risk Assessment
        risk_level, risk_score, risk_conf = self._calculate_multi_factor_risk(
            source=source,
            classification=clf_result.predicted_class,
            abnormality_status=abn_status,
            robust_z=robust_z,
            mean_frp=source.mean_frp_mw,
            s_attr=s_attr,
            s_ev=s_ev
        )

        # 7. Construct Explicit Evidence Graph / Items
        evidence_items, evidence_summary_text = self._build_evidence_package(
            source=source,
            abn_result=abn_result,
            clf_result=clf_result,
            evidence_bundle=evidence_bundle
        )

        # 8. Safe Satellite -> REACT-X Handoff Eligibility Gate
        handoff_eligibility = self._evaluate_handoff_eligibility(
            source=source,
            classification=clf_result.predicted_class,
            s_class=s_class,
            s_attr=s_attr,
            s_ev=s_ev,
            abnormality_status=abn_status,
            risk_level=risk_level
        )

        # 9. Build Pre-Configured Incident Scenario Draft (if eligible or review required)
        incident_draft = None
        if handoff_eligibility in [HandoffEligibility.INCIDENT_DRAFT_READY, HandoffEligibility.REVIEW_REQUIRED]:
            incident_draft = self._create_incident_draft(
                source=source,
                clf_result=clf_result,
                abn_result=abn_result,
                evidence_bundle=evidence_bundle,
                risk_level=risk_level,
                risk_score=risk_score
            )

        # 10. Check for previous version for reassessment lineage
        prev_assessment = db.query(IndustrialThermalAssessmentModel).filter(
            IndustrialThermalAssessmentModel.source_id == source.source_id
        ).order_by(IndustrialThermalAssessmentModel.version.desc()).first()

        version = (prev_assessment.version + 1) if prev_assessment else 1
        parent_id = prev_assessment.assessment_id if prev_assessment else None
        assessment_status = AssessmentStatus.UPDATED if prev_assessment else AssessmentStatus.INITIAL

        assessment_id = f"ASM-{source.source_id[-10:]}-v{version}"

        # 11. Populate data lineage (Phase 10 — full provenance)
        # Query events directly from DB (no ORM relationship assumed)
        try:
            source_events = db.query(ThermalSourceEventModel).filter(
                ThermalSourceEventModel.source_id == source.source_id
            ).all()
            event_ids = [e.event_id for e in source_events]
        except Exception:
            event_ids = []
        fingerprint_version = getattr(abn_result, "baseline_algorithm_version", self.abnormality_algorithm_version)
        lineage = AssessmentLineage(
            source_observation_ids=event_ids,
            thermal_source_id=source.source_id,
            facility_id=source.primary_attributed_facility_id,
            baseline_version=fingerprint_version,
            classification_model_version=self.classification_model_version,
            evidence_fusion_version=self.evidence_fusion_version,
            risk_algorithm_version=self.risk_algorithm_version,
            source_observation_start=ensure_utc(source.first_detected),
            source_observation_end=ensure_utc(source.last_detected),
            processing_timestamp=now
        )

        # Determine data quality state
        if len(event_ids) >= 3 and s_ev >= 0.70:
            dq_state = DataQualityState.GOOD
        elif len(event_ids) >= 1 and s_ev >= 0.40:
            dq_state = DataQualityState.WARNING
        elif s_ev > 0.0:
            dq_state = DataQualityState.DEGRADED
        else:
            dq_state = DataQualityState.INVALID

        return IndustrialThermalAssessment(
            assessment_id=assessment_id,
            source_id=source.source_id,
            facility_id=source.primary_attributed_facility_id,
            facility_name=source.primary_attributed_facility_name,
            centroid_lat=source.centroid_lat,
            centroid_lon=source.centroid_lon,
            attribution_confidence=round(s_attr, 3),
            classification_confidence=round(s_class, 3),
            abnormality_confidence=round(s_abn, 3),
            overall_evidence_confidence=round(s_ev, 3),
            classification=clf_result.predicted_class,
            classification_probabilities=getattr(clf_result, "class_probabilities", {}),
            abnormality_score=round(abn_score, 3),
            abnormality_status=abn_status,
            robust_zscore=round(robust_z, 2),
            attribution_status=source.attribution_status or "ATTRIBUTED_HIGH_CONFIDENCE",
            corroboration_status=evidence_bundle.evidence_status,
            industrial_risk_level=risk_level,
            industrial_risk_score=round(risk_score, 1),
            risk_confidence=round(risk_conf, 3),
            risk_label="SCREENING-LEVEL INDUSTRIAL RISK",
            is_routine_operation=is_routine,
            operational_concern_summary=operational_summary,
            evidence_summary=evidence_summary_text,
            evidence_items=evidence_items,
            handoff_eligibility=handoff_eligibility,
            incident_draft=incident_draft,
            assessment_status=assessment_status,
            version=version,
            parent_assessment_id=parent_id,
            classification_model_version=self.classification_model_version,
            abnormality_algorithm_version=self.abnormality_algorithm_version,
            attribution_algorithm_version=self.attribution_algorithm_version,
            evidence_fusion_version=self.evidence_fusion_version,
            risk_algorithm_version=self.risk_algorithm_version,
            created_at=now,
            updated_at=now,
            data_lineage=lineage,
            data_quality_state=dq_state
        )

    # =========================================================================
    # CONFIDENCE & RISK MATHEMATICAL FORMULATIONS
    # =========================================================================

    def _calculate_attribution_confidence(self, source: ThermalSourceModel) -> float:
        """Calculate spatial association confidence with industrial facility cadastre."""
        if source.facility_attribution_confidence is not None:
            return float(source.facility_attribution_confidence)
        if source.is_inside_facility_boundary:
            return 0.95
        if source.primary_attributed_facility_id and source.facility_distance_m is not None:
            d = source.facility_distance_m
            if d <= 250.0:
                return 0.85
            elif d <= 750.0:
                return 0.65
            elif d <= 1500.0:
                return 0.40
        return 0.10

    def _evaluate_operational_status(
        self,
        source: ThermalSourceModel,
        classification: Any,
        abnormality_status: Any,
        robust_z: float,
        mean_frp: float
    ) -> Tuple[bool, str]:
        """Distinguish normal routine industrial operations from unpredicted abnormal events."""
        cls_str = classification.value if hasattr(classification, "value") else str(classification)
        abn_str = abnormality_status.value if hasattr(abnormality_status, "value") else str(abnormality_status)

        is_routine_class = cls_str in [
            ThermalSourceClass.GAS_FLARE.value,
            ThermalSourceClass.ROUTINE_PROCESS_HEAT.value,
            ThermalSourceClass.MINING_PROCESS_HEAT.value,
            "GAS_FLARE", "ROUTINE_PROCESS_HEAT", "MINING_PROCESS_HEAT"
        ]
        is_baseline_normal = abn_str in [
            AbnormalityStatus.NORMAL_BASELINE.value,
            AbnormalityStatus.INSUFFICIENT_HISTORY.value,
            AbnormalityStatus.SPARSE_OBSERVATIONS.value,
            "NORMAL_BASELINE", "INSUFFICIENT_HISTORY", "SPARSE_OBSERVATIONS", "EXPECTED_RECURRING", "EXPECTED_PERSISTENT"
        ] and robust_z < 2.5

        if mean_frp >= 60.0:
            return False, f"Abnormal industrial event: High-intensity thermal output ({mean_frp:.1f} MW) exceeding routine operational limits."

        if is_routine_class and is_baseline_normal and source.active_days_count >= 5:
            return True, f"Routine industrial operation: Stable {cls_str.replace('_', ' ')} consistent with site baseline."
        
        if cls_str in [ThermalSourceClass.INDUSTRIAL_FIRE.value, "INDUSTRIAL_FIRE"]:
            return False, "Abnormal thermal event: Signature matches unpredicted industrial fire surge."
        
        if robust_z >= 3.0 or abn_str in [AbnormalityStatus.ABNORMAL_THERMAL_BEHAVIOUR.value, "ABNORMAL_THERMAL_BEHAVIOUR", "WATCH"]:
            return False, f"Abnormal industrial event: {cls_str.replace('_', ' ')} exhibiting severe thermal departure (+{robust_z:.1f} MAD)."
        
        if cls_str in [ThermalSourceClass.AGRICULTURAL_BURNING.value, ThermalSourceClass.WILDFIRE_NATURAL.value, "AGRICULTURAL_BURNING", "WILDFIRE_NATURAL"] or (not source.is_inside_facility_boundary and source.primary_attributed_facility_id is None):
            return True, f"Non-industrial surface burning: {cls_str.replace('_', ' ')} in regional rural zone."

        return False, "Elevated thermal activity requiring operational review."

    def _calculate_multi_factor_risk(
        self,
        source: ThermalSourceModel,
        classification: Any,
        abnormality_status: Any,
        robust_z: float,
        mean_frp: float,
        s_attr: float,
        s_ev: float
    ) -> Tuple[IndustrialRiskLevel, float, float]:
        """
        Evaluate multi-factor screening-level industrial risk:
        Risk = Q_gate * [ 0.35*H_class + 0.30*A_score + 0.20*I_frp + 0.15*P_prox ]
        """
        cls_str = classification.value if hasattr(classification, "value") else str(classification)

        # 1. Quality Gate: Penalize if evidence or attribution is sparse/unconfirmed
        q_gate = max(0.20, min(s_attr, s_ev))
        if not source.primary_attributed_facility_id and cls_str not in ["INDUSTRIAL_FIRE"]:
            q_gate = min(q_gate, 0.35)

        # 2. Hazard Potential (H_class [0 - 100])
        hazard_map = {
            "INDUSTRIAL_FIRE": 95.0,
            "GAS_FLARE": 30.0 if robust_z < 2.5 else 75.0,
            "ROUTINE_PROCESS_HEAT": 15.0 if robust_z < 2.5 else 65.0,
            "MINING_PROCESS_HEAT": 35.0,
            "AGRICULTURAL_BURNING": 10.0,
            "WILDFIRE_NATURAL": 12.0,
            "OTHER_UNKNOWN": 25.0
        }
        h_class = hazard_map.get(cls_str, 25.0)
        if source.is_inside_facility_boundary and (mean_frp >= 60.0 or robust_z >= 2.5):
            h_class = max(h_class, 75.0)
            if robust_z < 2.0:
                robust_z = max(robust_z, 3.5)

        # 3. Abnormality Magnitude (A_score [0 - 100])
        if robust_z >= 4.5:
            a_score = 100.0
        elif robust_z >= 3.0:
            a_score = 80.0
        elif robust_z >= 2.0:
            a_score = 55.0
        elif robust_z >= 1.0:
            a_score = 30.0
        else:
            a_score = 10.0

        # 4. Thermal Intensity (I_frp [0 - 100])
        i_frp = min(100.0, (mean_frp / 80.0) * 100.0)

        # 5. Proximity & Facility Containment (P_prox [0 - 100])
        if source.is_inside_facility_boundary:
            p_prox = 90.0
        elif source.facility_distance_m is not None and source.facility_distance_m <= 500.0:
            p_prox = 70.0
        elif source.facility_distance_m is not None and source.facility_distance_m <= 1500.0:
            p_prox = 45.0
        else:
            p_prox = 15.0

        # Multi-factor score
        raw_score = (0.35 * h_class) + (0.30 * a_score) + (0.20 * i_frp) + (0.15 * p_prox)
        final_score = raw_score * q_gate

        # Non-industrial override: Agricultural or Wildfire outside industrial facility cannot exceed LOW risk
        if cls_str in ["AGRICULTURAL_BURNING", "WILDFIRE_NATURAL"] and not source.is_inside_facility_boundary:
            final_score = min(final_score, 18.0)

        # Map to Risk Category
        if final_score >= 80.0:
            risk_level = IndustrialRiskLevel.CRITICAL
        elif final_score >= 60.0:
            risk_level = IndustrialRiskLevel.HIGH
        elif final_score >= 38.0:
            risk_level = IndustrialRiskLevel.MODERATE
        elif final_score >= 18.0:
            risk_level = IndustrialRiskLevel.LOW
        else:
            risk_level = IndustrialRiskLevel.NOMINAL

        risk_confidence = min(0.98, max(0.40, (s_attr * 0.40) + (s_ev * 0.40) + (q_gate * 0.20)))
        return risk_level, final_score, risk_confidence

    # =========================================================================
    # EVIDENCE PACKAGE GENERATION
    # =========================================================================

    def _build_evidence_package(
        self,
        source: ThermalSourceModel,
        abn_result: Any,
        clf_result: Any,
        evidence_bundle: Any
    ) -> Tuple[List[EvidenceItem], str]:
        """Construct a structured, transparent evidence graph for the assessment."""
        items: List[EvidenceItem] = []
        now = utcnow()
        source_ts = ensure_utc(source.last_detected) or now

        # 1. Tier 1 Detection Evidence
        items.append(EvidenceItem(
            source="NASA_FIRMS_VIIRS_MODIS",
            record_id=f"SRC-OBS-{source.source_id}",
            timestamp=source_ts,
            quality="HIGH",
            role="PRIMARY_TRIGGER",
            result=f"{source.observation_count} total detections recorded (Mean FRP: {source.mean_frp_mw:.1f} MW, Peak: {source.max_frp_mw:.1f} MW).",
            confidence=0.92,
            provenance={"satellite_count": source.unique_satellite_count, "active_days": source.active_days_count}
        ))

        # 2. Facility Attribution Cadastre
        if source.primary_attributed_facility_id:
            dist_str = f"~{source.facility_distance_m:.0f}m" if source.facility_distance_m is not None else "0m (Inside)"
            items.append(EvidenceItem(
                source="OSM_GEM_FACILITY_CADASTRE",
                record_id=source.primary_attributed_facility_id,
                timestamp=now,
                quality="HIGH" if source.is_inside_facility_boundary else "GOOD",
                role="SPATIAL_CONTEXT",
                result=f"Attributed to {source.primary_attributed_facility_name} (Distance: {dist_str}, Containment: {'INSIDE' if source.is_inside_facility_boundary else 'NEARBY'}).",
                confidence=float(source.facility_attribution_confidence or 0.85),
                provenance={"facility_id": source.primary_attributed_facility_id, "boundary_containment": source.is_inside_facility_boundary}
            ))

        # 3. Phase 6 Non-Parametric Empirical Baseline
        abn_status = getattr(abn_result, "status", "NORMAL_BASELINE")
        robust_z = getattr(abn_result, "frp_robust_zscore", 0.0)
        abn_conf = getattr(abn_result, "confidence", 0.80)
        clf_prob = getattr(clf_result, "model_confidence", 0.85)
        clf_sys_conf = getattr(clf_result, "system_confidence", 0.85)

        items.append(EvidenceItem(
            source="EMPIRICAL_THERMAL_BASELINE_ENGINE",
            record_id=f"BASE-{source.primary_attributed_facility_id or source.source_id}",
            timestamp=now,
            quality="GOOD" if abn_conf >= 0.70 else "MARGINAL",
            role="STATISTICAL_BASELINE",
            result=f"Departure Status: {abn_status} (Robust Z-Score: {robust_z:+.2f} MADs).",
            confidence=abn_conf,
            provenance={"confidence_level": abn_conf}
        ))

        # 4. Phase 7 Calibrated AI ML Classifier
        items.append(EvidenceItem(
            source="HIST_GRADIENT_BOOSTING_CLASSIFIER",
            record_id=f"ML-CLF-{source.source_id}",
            timestamp=now,
            quality="HIGH" if clf_prob >= 0.75 else "GOOD",
            role="AI_PREDICTION",
            result=f"Classified as {clf_result.predicted_class} with {clf_prob*100:.1f}% calibrated probability.",
            confidence=clf_prob,
            provenance={"system_confidence": clf_sys_conf}
        ))

        # 5. Phase 8 Multi-Satellite Evidence Bundle
        items.append(EvidenceItem(
            source="MULTI_SATELLITE_FUSION_ENGINE",
            record_id=evidence_bundle.bundle_id,
            timestamp=now,
            quality="HIGH" if evidence_bundle.evidence_status == EvidenceState.CORROBORATED else "GOOD",
            role="TEMPORAL_CONTINUITY",
            result=f"Evidence Status: {evidence_bundle.evidence_status} across {evidence_bundle.independent_satellite_count} independent satellite platforms.",
            confidence=evidence_bundle.overall_evidence_confidence,
            provenance={"satellites": evidence_bundle.independent_satellite_count, "supporting_reasons": getattr(evidence_bundle, "supporting_reasons", [])[:2]}
        ))

        summary = (
            f"Multi-source assessment synthesizes {len(items)} independent analytical items: "
            f"{clf_result.predicted_class} ({clf_prob*100:.0f}% confidence), "
            f"Abnormality {abn_status} (Z: {robust_z:+.1f}), "
            f"Corroboration: {evidence_bundle.evidence_status} ({evidence_bundle.overall_evidence_confidence*100:.0f}%)."
        )
        return items, summary

    # =========================================================================
    # SAFE SATELLITE -> REACT-X EMERGENCY HANDOFF GATEWAY
    # =========================================================================

    def _evaluate_handoff_eligibility(
        self,
        source: ThermalSourceModel,
        classification: Any,
        s_class: float,
        s_attr: float,
        s_ev: float,
        abnormality_status: Any,
        risk_level: IndustrialRiskLevel
    ) -> HandoffEligibility:
        """
        Evaluate explicit eligibility criteria for REACT-X incident draft generation.
        Enforces human-in-the-loop gating before emergency response activation.
        """
        cls_str = classification.value if hasattr(classification, "value") else str(classification)
        abn_str = abnormality_status.value if hasattr(abnormality_status, "value") else str(abnormality_status)

        # Non-industrial or routine operations are NOT eligible for emergency handoff
        if cls_str in ["AGRICULTURAL_BURNING", "WILDFIRE_NATURAL"] and not source.is_inside_facility_boundary:
            return HandoffEligibility.NOT_ELIGIBLE

        if cls_str in ["ROUTINE_PROCESS_HEAT", "GAS_FLARE"] and abn_str in ["NORMAL_BASELINE", "EXPECTED_RECURRING", "EXPECTED_PERSISTENT"] and risk_level in [IndustrialRiskLevel.NOMINAL, IndustrialRiskLevel.LOW]:
            return HandoffEligibility.NOT_ELIGIBLE

        # Clear high-consequence candidate: High Risk or High-Confidence Fire inside Facility
        if (risk_level in [IndustrialRiskLevel.HIGH, IndustrialRiskLevel.CRITICAL] and s_attr >= 0.50) or (cls_str == "INDUSTRIAL_FIRE" and s_attr >= 0.50):
            return HandoffEligibility.INCIDENT_DRAFT_READY

        # Moderate risk or borderline confidence requires human review
        if risk_level == IndustrialRiskLevel.MODERATE or abn_str in ["ABNORMAL_THERMAL_BEHAVIOUR", "WATCH"]:
            return HandoffEligibility.REVIEW_REQUIRED

        return HandoffEligibility.NOT_ELIGIBLE

    def _create_incident_draft(
        self,
        source: ThermalSourceModel,
        clf_result: Any,
        abn_result: Any,
        evidence_bundle: Any,
        risk_level: IndustrialRiskLevel,
        risk_score: float
    ) -> ReactXIncidentDraft:
        """Create structured REACT-X incident draft without triggering physical safety actions."""
        draft_id = f"DRAFT-INC-{source.source_id[-10:]}-{utcnow().strftime('%Y%m%d%H%M')}"
        fac_name = source.primary_attributed_facility_name or "Unattributed Industrial Facility"

        cls_str = clf_result.predicted_class.value if hasattr(clf_result.predicted_class, "value") else str(clf_result.predicted_class)
        suggested_type = "FIRE_EXPLOSION" if (cls_str in ["INDUSTRIAL_FIRE", "GAS_FLARE"] or source.max_frp_mw >= 80.0) else "PROCESS_OVERPRESSURE"
        clf_prob = getattr(clf_result, "model_confidence", 0.85)
        abn_status = getattr(abn_result, "status", "NORMAL_BASELINE")
        robust_z = getattr(abn_result, "frp_robust_zscore", 0.0)

        return ReactXIncidentDraft(
            draft_id=draft_id,
            source_id=source.source_id,
            facility_id=source.primary_attributed_facility_id,
            facility_name=fac_name,
            suggested_incident_type=suggested_type,
            suggested_severity=risk_level.value,
            coordinates=[source.centroid_lat, source.centroid_lon],
            thermal_summary=f"Mean FRP: {source.mean_frp_mw:.1f} MW, Peak: {source.max_frp_mw:.1f} MW, Brightness Temp: {source.mean_brightness_temp_k:.1f} K.",
            ml_classification=f"{clf_result.predicted_class} (Confidence: {clf_prob*100:.1f}%)",
            abnormality_summary=f"{abn_status} (Robust Z-Score: {robust_z:+.2f} MADs)",
            multi_satellite_summary=f"{evidence_bundle.evidence_status} across {evidence_bundle.independent_satellite_count} satellite platforms",
            chemical_consequence_status="CHEMICAL CONSEQUENCE MODEL: INSUFFICIENT DATA (Awaiting plant-provided hazardous material registry)",
            site_evacuation_status="SITE-LEVEL RESPONSE DATA UNAVAILABLE (Awaiting facility shift worker roster & on-site road telemetry)",
            suggested_next_actions=[
                "Review satellite evidence package and confirm facility sector coordinates.",
                "Initiate operator authorization to open active REACT-X Emergency Workspace.",
                "If plant chemical inventory is available, select hazardous substance in Hazard Dispersion Simulator.",
                "Inspect neighbouring assets for domino escalation risk in Domino Cascade Engine."
            ],
            created_at=utcnow()
        )

    # =========================================================================
    # PERSISTENCE, PROMOTION & AUDIT
    # =========================================================================

    def persist_assessment(self, assessment: IndustrialThermalAssessment, db: Session) -> IndustrialThermalAssessmentModel:
        """Persist assessment record to database."""
        def to_val(v):
            if v is None:
                return None
            return v.value if hasattr(v, "value") else str(v)

        model = IndustrialThermalAssessmentModel(
            assessment_id=assessment.assessment_id,
            source_id=assessment.source_id,
            facility_id=assessment.facility_id,
            facility_name=assessment.facility_name,
            centroid_lat=assessment.centroid_lat,
            centroid_lon=assessment.centroid_lon,
            attribution_confidence=assessment.attribution_confidence,
            classification_confidence=assessment.classification_confidence,
            abnormality_confidence=assessment.abnormality_confidence,
            overall_evidence_confidence=assessment.overall_evidence_confidence,
            classification=to_val(assessment.classification),
            classification_probabilities=assessment.classification_probabilities,
            abnormality_score=assessment.abnormality_score,
            abnormality_status=to_val(assessment.abnormality_status),
            robust_zscore=assessment.robust_zscore,
            attribution_status=assessment.attribution_status,
            corroboration_status=to_val(assessment.corroboration_status),
            industrial_risk_level=to_val(assessment.industrial_risk_level),
            industrial_risk_score=assessment.industrial_risk_score,
            risk_confidence=assessment.risk_confidence,
            risk_label=assessment.risk_label,
            is_routine_operation=assessment.is_routine_operation,
            operational_concern_summary=assessment.operational_concern_summary,
            evidence_summary=assessment.evidence_summary,
            evidence_items=[item.model_dump(mode="json") for item in assessment.evidence_items],
            handoff_eligibility=to_val(assessment.handoff_eligibility),
            incident_draft=assessment.incident_draft.model_dump(mode="json") if assessment.incident_draft else None,
            assessment_status=to_val(assessment.assessment_status),
            version=assessment.version,
            parent_assessment_id=assessment.parent_assessment_id,
            classification_model_version=assessment.classification_model_version,
            abnormality_algorithm_version=assessment.abnormality_algorithm_version,
            attribution_algorithm_version=assessment.attribution_algorithm_version,
            evidence_fusion_version=assessment.evidence_fusion_version,
            risk_algorithm_version=assessment.risk_algorithm_version,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    def promote_to_incident(
        self,
        assessment_id: str,
        req: IncidentPromotionRequest,
        db: Session
    ) -> Dict[str, Any]:
        """
        Authorize and promote a satellite assessment into an active REACT-X Incident.
        Enforces mandatory decision audit trail logging.
        """
        assessment_model = db.query(IndustrialThermalAssessmentModel).filter_by(assessment_id=assessment_id).first()
        if not assessment_model:
            raise ValueError(f"Assessment {assessment_id} not found.")

        # Update assessment status
        assessment_model.assessment_status = AssessmentStatus.CONFIRMED.value
        assessment_model.handoff_eligibility = HandoffEligibility.INCIDENT_ACTIVE.value
        assessment_model.updated_at = utcnow()

        # Create unique incident ID
        incident_id = f"INC-{assessment_model.source_id[-10:]}-{utcnow().strftime('%Y%m%d%H%M')}"

        # Record in DecisionAuditModel
        rec_id = f"AUD-{utcnow().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:6].upper()}"
        audit_entry = DecisionAuditModel(
            id=rec_id,
            incident_id=incident_id,
            timestamp=utcnow(),
            module="SATELLITE_ASSESSMENT_HANDOFF",
            input_summary=f"Thermal Assessment {assessment_id} for Source {assessment_model.source_id} at {assessment_model.facility_name or 'Industrial Zone'}",
            recommendation=f"Promote to active emergency incident (Risk: {assessment_model.industrial_risk_level}, Score: {assessment_model.industrial_risk_score})",
            reason=req.justification,
            human_action="PROMOTED_TO_ACTIVE_INCIDENT",
            actor_role=req.operator_role,
            actor_name=req.operator_id,
            result=f"Active REACT-X Incident {incident_id} activated.",
            status="AUTHORIZED",
            data_classification="OPERATIONAL_SAFETY_CRITICAL",
            created_at=utcnow()
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "INCIDENT_PROMOTED",
            "incident_id": incident_id,
            "assessment_id": assessment_id,
            "source_id": assessment_model.source_id,
            "facility_name": assessment_model.facility_name,
            "audit_record_id": rec_id,
            "authorized_by": req.operator_id,
            "authorized_role": req.operator_role,
            "activated_at": utcnow().isoformat() + "Z"
        }

    def reject_incident_draft(
        self,
        assessment_id: str,
        req: IncidentRejectionRequest,
        db: Session
    ) -> Dict[str, Any]:
        """
        Record operator rejection / de-escalation of an incident draft with audit trail.
        """
        assessment_model = db.query(IndustrialThermalAssessmentModel).filter_by(assessment_id=assessment_id).first()
        if not assessment_model:
            raise ValueError(f"Assessment {assessment_id} not found.")

        assessment_model.assessment_status = AssessmentStatus.DOWNGRADED.value
        assessment_model.handoff_eligibility = HandoffEligibility.NOT_ELIGIBLE.value
        assessment_model.updated_at = utcnow()

        rec_id = f"AUD-{utcnow().strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:6].upper()}"
        audit_entry = DecisionAuditModel(
            id=rec_id,
            incident_id=f"DRAFT-{assessment_model.source_id}",
            timestamp=utcnow(),
            module="SATELLITE_ASSESSMENT_HANDOFF",
            input_summary=f"Draft Incident for Assessment {assessment_id}",
            recommendation="Emergency activation rejected by human operator.",
            reason=f"Reason: {req.rejection_reason} | Notes: {req.notes or 'None'}",
            human_action="REJECTED_DRAFT_INCIDENT",
            actor_role=req.operator_role,
            actor_name=req.operator_id,
            result="De-escalated to routine monitoring.",
            status="REJECTED",
            data_classification="OPERATIONAL_AUDIT_LOG",
            created_at=utcnow()
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "INCIDENT_DRAFT_REJECTED",
            "assessment_id": assessment_id,
            "source_id": assessment_model.source_id,
            "audit_record_id": rec_id,
            "rejection_reason": req.rejection_reason,
            "rejected_by": req.operator_id,
            "timestamp": utcnow().isoformat() + "Z"
        }

    def generate_executive_brief(
        self,
        assessment: IndustrialThermalAssessment,
        db: Session
    ) -> AssessmentExecutiveBriefResponse:
        """
        Synthesize a unified, satellite-aware situation brief in Markdown format.
        """
        def to_val(v):
            if v is None:
                return ""
            return v.value if hasattr(v, "value") else str(v)

        fac_name = assessment.facility_name or "Industrial Facility (Unattributed)"
        status_val = to_val(assessment.assessment_status)
        cls_val = to_val(assessment.classification)
        abn_val = to_val(assessment.abnormality_status)
        corrob_val = to_val(assessment.corroboration_status)
        risk_val = to_val(assessment.industrial_risk_level)
        handoff_val = to_val(assessment.handoff_eligibility)

        brief_md = f"""# EXECUTIVE SITUATION BRIEF: THERMAL INTELLIGENCE ASSESSMENT
**ASSESSMENT ID:** `{assessment.assessment_id}` | **GENERATED:** {assessment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
**TARGET FACILITY:** {fac_name} | **STATUS:** {status_val}

---

### 1. WHAT WAS DETECTED?
- **Centroid Coordinates:** `{assessment.centroid_lat:.4f}° N, {assessment.centroid_lon:.4f}° E`
- **Predicted Source Identity:** **{cls_val.replace('_', ' ')}** (Calibrated Confidence: **{assessment.classification_confidence*100:.1f}%**)
- **Empirical Baseline Status:** **{abn_val}** (Robust Z-Score: **{assessment.robust_zscore:+.2f} MAD**)
- **Operational Classification:** **{'ROUTINE INDUSTRIAL OPERATION' if assessment.is_routine_operation else 'ABNORMAL INDUSTRIAL SURGE'}**

---

### 2. HOW STRONG IS THE EVIDENCE?
- **Multi-Satellite Corroboration:** **{corrob_val}** (Confidence: **{assessment.overall_evidence_confidence*100:.1f}%**)
- **Facility Cadastral Attribution:** **{assessment.attribution_status}** (Confidence: **{assessment.attribution_confidence*100:.1f}%**)
- **Supporting Evidence Items:** {len(assessment.evidence_items)} auditable sensor & model records verified.

---

### 3. INDUSTRIAL RISK ASSESSMENT (SCREENING-LEVEL)
- **Assessed Risk Level:** **{risk_val}** (Score: **{assessment.industrial_risk_score:.1f} / 100.0**)
- **Risk Evaluation Confidence:** **{assessment.risk_confidence*100:.1f}%**
- **Assessment Summary:** {assessment.operational_concern_summary}

---

### 4. RECOMMENDED ACTION & EMERGENCY HANDOFF
- **REACT-X Handoff Eligibility:** **{handoff_val}**
{'- **Recommended Next Step:** Authorize promotion to active REACT-X Incident Workspace for toxic dispersion & domino cascade simulation.' if handoff_val == 'INCIDENT_DRAFT_READY' else '- **Recommended Next Step:** Continue routine automated satellite monitoring; no immediate physical response required.'}

*Notice: This report is a screening-level thermal intelligence assessment generated under model version `{assessment.classification_model_version}` & baseline `{assessment.abnormality_algorithm_version}`. Autonomous physical safety actions are prohibited without authorized human review.*
"""
        return AssessmentExecutiveBriefResponse(
            assessment_id=assessment.assessment_id,
            source_id=assessment.source_id,
            facility_name=fac_name,
            brief_markdown=brief_md,
            generated_at=utcnow()
        )


assessment_engine = IndustrialThermalAssessmentEngine()
