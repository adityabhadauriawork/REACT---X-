import uuid
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.schemas.adaptive import (
    AdaptiveMonitoringDecision, MonitoringLevel, AnalyticalPriority,
    FacilityCriticalityTier, ValueOfInformationItem, MonitoringPolicy,
    NationalPriorityItem
)
from app.schemas.fusion import FusedHazardAssessment, FusedHazardState
from app.services.fusion.multimodal_fusion_service import multimodal_fusion_service
from app.services.adaptive.hysteresis_controller import hysteresis_controller
from app.services.adaptive.priority_queue_manager import priority_queue_manager, NationalPriorityQueueManager
from app.services.storage.adaptive_repository import adaptive_repository

class AdaptiveOrchestratorService:
    """
    Central Adaptive / Risk-Driven Sensing Orchestrator.
    Dynamically adjusts analytical processing intensity, feature extraction windows,
    and evidence requests without controlling physical plant instrumentation.
    """

    POLICY_CONFIGS = {
        MonitoringLevel.LEVEL_0_BASELINE: MonitoringPolicy(
            telemetry_evaluation_window_sec=60.0,
            telemetry_sampling_interval_sec=5.0,
            thermal_camera_tracking_mode="PERIODIC",
            cctv_frame_extraction_fps=1.0,
            satellite_query_priority="BACKGROUND",
            multi_modal_fusion_cadence_sec=30.0
        ),
        MonitoringLevel.LEVEL_1_WATCH: MonitoringPolicy(
            telemetry_evaluation_window_sec=30.0,
            telemetry_sampling_interval_sec=3.0,
            thermal_camera_tracking_mode="PERIODIC",
            cctv_frame_extraction_fps=2.0,
            satellite_query_priority="BACKGROUND",
            multi_modal_fusion_cadence_sec=15.0
        ),
        MonitoringLevel.LEVEL_2_ABNORMAL: MonitoringPolicy(
            telemetry_evaluation_window_sec=20.0,
            telemetry_sampling_interval_sec=2.0,
            thermal_camera_tracking_mode="CONTINUOUS_CONTOUR",
            cctv_frame_extraction_fps=3.0,
            satellite_query_priority="EXPEDITE_NEXT_OVERPASS",
            multi_modal_fusion_cadence_sec=10.0
        ),
        MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING: MonitoringPolicy(
            telemetry_evaluation_window_sec=10.0,
            telemetry_sampling_interval_sec=1.0,
            thermal_camera_tracking_mode="CONTINUOUS_CONTOUR",
            cctv_frame_extraction_fps=5.0,
            satellite_query_priority="EXPEDITE_NEXT_OVERPASS",
            multi_modal_fusion_cadence_sec=5.0
        ),
        MonitoringLevel.LEVEL_4_CRITICAL: MonitoringPolicy(
            telemetry_evaluation_window_sec=5.0,
            telemetry_sampling_interval_sec=0.5,
            thermal_camera_tracking_mode="MAXIMUM_FRAME_RATE",
            cctv_frame_extraction_fps=10.0,
            satellite_query_priority="HIGH_PRIORITY_REVISE",
            multi_modal_fusion_cadence_sec=2.0
        ),
        MonitoringLevel.LEVEL_5_INCIDENT: MonitoringPolicy(
            telemetry_evaluation_window_sec=5.0,
            telemetry_sampling_interval_sec=0.5,
            thermal_camera_tracking_mode="MAXIMUM_FRAME_RATE",
            cctv_frame_extraction_fps=10.0,
            satellite_query_priority="HIGH_PRIORITY_REVISE",
            multi_modal_fusion_cadence_sec=1.0
        )
    }

    def evaluate_facility_orchestration(
        self,
        facility_id: str = "FAC-IN-DAHEJ-001",
        asset_id: str = "T-04",
        force_hazard_state: Optional[str] = None,
        force_uncertainty: Optional[float] = None,
        force_missing_sources: Optional[List[str]] = None,
        force_instant_transition: bool = False,
        db: Optional[Session] = None
    ) -> AdaptiveMonitoringDecision:
        now_utc = datetime.now(timezone.utc)

        # 1. Ingest upstream Multimodal Fused Assessment (Phase 15)
        fused_asm = multimodal_fusion_service.evaluate_facility_fusion(
            facility_id=facility_id,
            asset_id=asset_id,
            simulate_missing_sources=force_missing_sources,
            db=db
        )

        fused_state = force_hazard_state or (
            fused_asm.fused_state.value if hasattr(fused_asm.fused_state, "value") else str(fused_asm.fused_state)
        )
        uncertainty = force_uncertainty if force_uncertainty is not None else fused_asm.uncertainty_score
        conflict_k = fused_asm.conflict_mass_k
        confidence = fused_asm.confidence

        # Criticality tier
        crit_tier = FacilityCriticalityTier.TIER_1_CRITICAL if "DAHEJ" in facility_id or asset_id == "T-04" else FacilityCriticalityTier.TIER_2_MAJOR

        # 2. Determine Raw Target Monitoring Level
        raw_level = self._map_state_to_level(fused_state, uncertainty, conflict_k)

        # 3. Apply State Hysteresis & Cooldown Dwell Times
        eff_level, prev_level, in_cooldown, cd_remaining = hysteresis_controller.process_level_transition(
            facility_id=facility_id,
            target_level=raw_level,
            force_instant=force_instant_transition
        )

        # 4. Generate Applied Monitoring Policy
        policy = self.POLICY_CONFIGS.get(eff_level, self.POLICY_CONFIGS[MonitoringLevel.LEVEL_0_BASELINE])

        # 5. Prioritize Evidence Requests & Value of Information
        requested_ev, voi_items = self._generate_evidence_requests(
            fused_state, eff_level, uncertainty, conflict_k, fused_asm
        )

        # 6. Formulate Explainable Human-Readable Reason
        reason = self._formulate_decision_reason(
            fused_state, eff_level, prev_level, in_cooldown, cd_remaining,
            uncertainty, conflict_k, requested_ev
        )

        # 7. Map Priority
        priority_score = self._compute_priority_score(fused_state, crit_tier, uncertainty)
        if eff_level in [MonitoringLevel.LEVEL_4_CRITICAL, MonitoringLevel.LEVEL_5_INCIDENT]:
            priority = AnalyticalPriority.URGENT
        elif eff_level == MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING or priority_score >= 65.0:
            priority = AnalyticalPriority.HIGH
        elif eff_level in [MonitoringLevel.LEVEL_2_ABNORMAL, MonitoringLevel.LEVEL_1_WATCH] or priority_score >= 35.0:
            priority = AnalyticalPriority.MEDIUM
        else:
            priority = AnalyticalPriority.LOW

        # Update last observation timestamp in queue manager
        priority_queue_manager.update_observation_timestamp(facility_id, time.time())

        # 8. Assemble Canonical Decision Contract
        decision = AdaptiveMonitoringDecision(
            decision_id=f"ADAPT-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            facility_id=facility_id,
            asset_id=asset_id,
            zone_id="Sector D - Cryogenic Yard",
            created_at=now_utc,
            expires_at=now_utc + timedelta(seconds=policy.multi_modal_fusion_cadence_sec * 2),
            monitoring_level=eff_level,
            previous_level=prev_level,
            hazard_state=fused_state,
            confidence=round(confidence, 3),
            uncertainty_score=round(uncertainty, 3),
            conflict_mass_k=round(conflict_k, 3),
            facility_criticality=crit_tier,
            priority=priority,
            priority_score=round(priority_score, 1),
            reason=reason,
            requested_evidence=requested_ev,
            value_of_information=voi_items,
            applied_policy=policy,
            is_in_cooldown=in_cooldown,
            cooldown_remaining_sec=cd_remaining,
            is_live_data=False,
            is_simulated=True
        )

        # Persist to database
        if db:
            try:
                adaptive_repository.persist_decision(db, decision)
            except Exception:
                pass

        return decision

    def get_national_priority_queue(self, db: Optional[Session] = None) -> List[NationalPriorityItem]:
        """
        Builds the national ranked surveillance queue across all registered industrial clusters.
        """
        facility_candidates = [
            {
                "facility_id": "FAC-IN-DAHEJ-001",
                "facility_name": "Dahej Petrochemical Complex",
                "criticality": FacilityCriticalityTier.TIER_1_CRITICAL,
                "asset_id": "T-04"
            },
            {
                "facility_id": "FAC-IN-HAZIRA-002",
                "facility_name": "Hazira Heavy Chemicals Hub",
                "criticality": FacilityCriticalityTier.TIER_1_CRITICAL,
                "asset_id": "T-01"
            },
            {
                "facility_id": "FAC-IN-VADODARA-003",
                "facility_name": "Vadodara Refining & Fertilizer",
                "criticality": FacilityCriticalityTier.TIER_2_MAJOR,
                "asset_id": "PU-01"
            },
            {
                "facility_id": "FAC-IN-MUNDRA-004",
                "facility_name": "Mundra Thermal Power & Port",
                "criticality": FacilityCriticalityTier.TIER_2_MAJOR,
                "asset_id": "SUB-01"
            },
            {
                "facility_id": "FAC-IN-JAMNAGAR-005",
                "facility_name": "Jamnagar Mega Petroleum Complex",
                "criticality": FacilityCriticalityTier.TIER_1_CRITICAL,
                "asset_id": "T-03"
            }
        ]

        snapshots = []
        for fc in facility_candidates:
            f_id = fc["facility_id"]
            # Evaluate latest decision
            dec = self.evaluate_facility_orchestration(facility_id=f_id, asset_id=fc["asset_id"], db=db)
            snapshots.append({
                "facility_id": f_id,
                "facility_name": fc["facility_name"],
                "monitoring_level": dec.monitoring_level,
                "hazard_state": dec.hazard_state,
                "uncertainty_score": dec.uncertainty_score,
                "criticality": fc["criticality"],
                "reason": dec.reason,
                "requested_evidence_count": len(dec.requested_evidence)
            })

        return priority_queue_manager.rank_facilities(snapshots)

    def _map_state_to_level(self, state: str, uncertainty: float, conflict_k: float) -> MonitoringLevel:
        if state == "INCIDENT":
            return MonitoringLevel.LEVEL_5_INCIDENT
        if state == "CRITICAL":
            return MonitoringLevel.LEVEL_4_CRITICAL
        if state == "HAZARD_DEVELOPING":
            return MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING
        if state in ["ABNORMAL", "CONFLICTING_EVIDENCE"]:
            return MonitoringLevel.LEVEL_2_ABNORMAL
        if state == "WATCH" or uncertainty > 0.35:
            return MonitoringLevel.LEVEL_1_WATCH
        return MonitoringLevel.LEVEL_0_BASELINE

    def _generate_evidence_requests(
        self,
        state: str,
        level: MonitoringLevel,
        uncertainty: float,
        conflict_k: float,
        asm: FusedHazardAssessment
    ) -> tuple:
        requested: List[str] = []
        voi_items: List[ValueOfInformationItem] = []

        if level in [MonitoringLevel.LEVEL_4_CRITICAL, MonitoringLevel.LEVEL_5_INCIDENT]:
            requested = ["THERMAL_CAMERA", "TELEMETRY_HIGH_FREQ", "CCTV_FLAME", "SATELLITE_CONTEXT"]
            voi_items.append(ValueOfInformationItem(
                target_modality="THERMAL_CAMERA",
                specific_signal="radiometric_hotspot_rate_of_rise",
                rationale="Continuous tracking of thermal plume boundary and heat release rate.",
                expected_uncertainty_reduction=0.35,
                urgency=AnalyticalPriority.URGENT
            ))
            voi_items.append(ValueOfInformationItem(
                target_modality="TELEMETRY",
                specific_signal="internal_vessel_pressure_slope",
                rationale="Evaluate mechanical containment margin before relief valve trigger.",
                expected_uncertainty_reduction=0.30,
                urgency=AnalyticalPriority.URGENT
            ))
        elif level == MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING:
            requested = ["THERMAL_CAMERA", "TELEMETRY_HIGH_FREQ", "HAZARD_PREDICTION"]
            voi_items.append(ValueOfInformationItem(
                target_modality="THERMAL_CAMERA",
                specific_signal="spatial_hotspot_growth",
                rationale="Confirm whether thermal anomaly is expanding across adjoining pipe racks.",
                expected_uncertainty_reduction=0.25,
                urgency=AnalyticalPriority.HIGH
            ))
        elif level == MonitoringLevel.LEVEL_2_ABNORMAL or conflict_k >= 0.40:
            requested = ["THERMAL_CAMERA", "GAS_SNIFFER"]
            voi_items.append(ValueOfInformationItem(
                target_modality="TELEMETRY",
                specific_signal="gas_sniffer_concentration",
                rationale="Validate whether localized excursion has resulted in vapor cloud dispersion.",
                expected_uncertainty_reduction=0.20,
                urgency=AnalyticalPriority.MEDIUM
            ))
        elif level == MonitoringLevel.LEVEL_1_WATCH:
            requested = ["TELEMETRY_DELTA_EVAL"]
        else:
            requested = ["BASELINE_TELEMETRY"]

        if uncertainty > 0.40:
            if "THERMAL_CAMERA" not in requested:
                requested.append("THERMAL_CAMERA")
            voi_items.append(ValueOfInformationItem(
                target_modality="THERMAL_CAMERA",
                specific_signal="spatial_thermal_distribution",
                rationale="Compensate for sensor uncertainty and eliminate information blind spots.",
                expected_uncertainty_reduction=round(min(0.40, uncertainty * 0.5), 2),
                urgency=AnalyticalPriority.MEDIUM
            ))

        return requested, voi_items

    def _formulate_decision_reason(
        self,
        state: str,
        eff_level: MonitoringLevel,
        prev_level: MonitoringLevel,
        in_cooldown: bool,
        cd_remaining: float,
        uncertainty: float,
        conflict_k: float,
        requested_ev: List[str]
    ) -> str:
        if in_cooldown:
            return f"Cooldown active ({cd_remaining:.0f}s remaining). Maintaining {eff_level.value} to prevent signal flapping."
        if eff_level == MonitoringLevel.LEVEL_4_CRITICAL:
            return f"Acute hazard state ({state}) confirmed across multiple independent streams. Maximizing analytical attention."
        if eff_level == MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING:
            return f"Persistent upward parameter trajectory detected. Accelerating multi-modal feature evaluation."
        if conflict_k >= 0.40:
            return f"High cross-modal conflict (K={conflict_k:.2f}). Intensifying local thermal camera and telemetry verification."
        if uncertainty > 0.40:
            return f"Elevated uncertainty ({uncertainty*100:.0f}%). Requesting additional data from: {', '.join(requested_ev)}."
        if eff_level == MonitoringLevel.LEVEL_1_WATCH:
            return f"Minor baseline departure observed. Increasing telemetry evaluation cadence."
        return "Operating within nominal design envelope. Maintaining baseline surveillance."

    def _compute_priority_score(self, state: str, crit: FacilityCriticalityTier, uncert: float) -> float:
        base = NationalPriorityQueueManager.BASE_RISK_SCORES.get(state, 5.0)
        bonus = NationalPriorityQueueManager.CRITICALITY_BONUS.get(crit, 0.0)
        return base + bonus + (uncert * 30.0)

adaptive_orchestrator_service = AdaptiveOrchestratorService()
