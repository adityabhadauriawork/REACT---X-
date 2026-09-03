import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.schemas.discrimination import (
    DiscriminationAssessment, LandCoverClass, LandCoverContextResult,
    ObservationQualityState, SourcePersistenceState, EOVerificationResult,
    EOStructuralMatchStatus, EvidenceExplanationItem
)
from app.services.satellite.land_cover_service import land_cover_service
from app.services.satellite.observation_quality_engine import observation_quality_engine
from app.services.satellite.eo_verification_service import eo_verification_service
from app.services.storage.discrimination_repository import discrimination_repository

class ThermalSourceDiscriminationService:
    """
    Advanced Multimodal Thermal Source Discrimination & Evidence Synthesis Engine.
    Combines spatiotemporal source dynamics, geometric facility context, authoritative land-cover,
    observation geometry quality filters, and selective Earth Observation (EO) verification.
    """

    def discriminate_source(
        self,
        source_id: str = "SRC-IN-DAHEJ-FLARE-01",
        latitude: float = 21.6850,
        longitude: float = 72.5620,
        mean_frp_mw: float = 24.5,
        max_frp_mw: float = 38.0,
        observation_count: int = 42,
        active_days_count: int = 28,
        diurnal_night_fraction: float = 0.65,
        facility_id: Optional[str] = "FAC-IN-DAHEJ-001",
        facility_name: Optional[str] = "Dahej Petrochemical Complex",
        facility_distance_m: float = 35.0,
        is_inside_facility: bool = True,
        solar_zenith_deg: float = 45.0,
        sensor_scan_angle_deg: float = 18.0,
        cloud_cover_fraction: float = 0.05,
        force_eo_unavailable: bool = False,
        db: Optional[Session] = None
    ) -> DiscriminationAssessment:
        now_utc = datetime.now(timezone.utc)

        # 1. Spatiotemporal Persistence State
        if active_days_count >= 7:
            persistence = SourcePersistenceState.PERSISTENT
        elif active_days_count >= 2:
            persistence = SourcePersistenceState.INTERMITTENT
        elif observation_count == 1:
            persistence = SourcePersistenceState.TRANSIENT
        else:
            persistence = SourcePersistenceState.NEW

        # 2. Authoritative Land-Cover Resolution
        land_cover = land_cover_service.resolve_land_cover(latitude, longitude, facility_id=facility_id)

        # 3. Observation Geometry & Solar Glint Quality Filter
        has_night = diurnal_night_fraction > 0.15 or active_days_count > 3
        quality_state, quality_expl, is_reflection = observation_quality_engine.evaluate_observation_quality(
            solar_zenith_deg=solar_zenith_deg,
            sensor_scan_angle_deg=sensor_scan_angle_deg,
            cloud_cover_fraction=cloud_cover_fraction,
            day_night="D" if diurnal_night_fraction < 0.1 else "N",
            frp_mw=mean_frp_mw,
            has_night_recurrence=has_night
        )

        # 4. Selective High-Resolution Earth Observation (EO) Verification
        eo_warranted = eo_verification_service.is_verification_warranted(
            facility_id=facility_id,
            facility_distance_m=facility_distance_m,
            uncertainty_score=0.15 if is_inside_facility else 0.45,
            frp_mw=max_frp_mw
        )
        
        eo_result = None
        if eo_warranted:
            eo_result = eo_verification_service.verify_thermal_source(
                source_id=source_id,
                latitude=latitude,
                longitude=longitude,
                facility_id=facility_id,
                facility_distance_m=facility_distance_m,
                force_unavailable=force_eo_unavailable
            )

        # 5. Multimodal Classification Decision Logic
        probs, predicted_class, class_state, abstention_reason = self._classify_multimodal(
            mean_frp_mw=mean_frp_mw,
            max_frp_mw=max_frp_mw,
            observation_count=observation_count,
            active_days_count=active_days_count,
            night_fraction=diurnal_night_fraction,
            is_inside_facility=is_inside_facility,
            facility_distance_m=facility_distance_m,
            land_cover_class=land_cover.land_cover_class,
            quality_state=quality_state,
            is_reflection=is_reflection,
            eo_result=eo_result
        )

        # 6. Dual-Confidence Governance
        model_conf = max(probs.values()) if probs else 0.50
        system_conf = self._compute_system_confidence(model_conf, observation_count, quality_state, eo_result)
        sufficiency = "SUFFICIENT" if observation_count >= 3 and quality_state == ObservationQualityState.GOOD else ("DEGRADED" if observation_count >= 1 else "INSUFFICIENT")

        # 7. Evidence Decomposition (Top Supporting & Opposing)
        sup_ev, opp_ev = self._generate_evidence_breakdown(
            predicted_class, persistence, is_inside_facility, land_cover,
            diurnal_night_fraction, quality_state, eo_result, is_reflection
        )

        assessment = DiscriminationAssessment(
            assessment_id=f"DISCRIM-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            source_id=source_id,
            centroid_lat=round(latitude, 5),
            centroid_lon=round(longitude, 5),
            h3_index="872d8a28affffff",
            created_at=now_utc,
            predicted_class=predicted_class,
            class_probabilities=probs,
            classification_state=class_state,
            model_confidence=round(model_conf, 3),
            system_confidence=round(system_conf, 3),
            evidence_sufficiency=sufficiency,
            persistence_state=persistence,
            observation_count=observation_count,
            mean_frp_mw=round(mean_frp_mw, 2),
            max_frp_mw=round(max_frp_mw, 2),
            diurnal_night_fraction=round(diurnal_night_fraction, 2),
            spatial_dispersion_r95_m=42.0 if is_inside_facility else 380.0,
            facility_attribution_status="ATTRIBUTED_INSIDE_BOUNDARY" if is_inside_facility else ("PROXIMATE_FACILITY" if facility_distance_m < 500.0 else "UNATTRIBUTED"),
            attributed_facility_id=facility_id,
            attributed_facility_name=facility_name,
            facility_distance_m=round(facility_distance_m, 1),
            is_inside_facility=is_inside_facility,
            land_cover=land_cover,
            observation_quality=quality_state,
            quality_explanation=quality_expl,
            is_potential_reflection=is_reflection,
            eo_verification=eo_result,
            eo_verification_required=eo_warranted,
            top_supporting_evidence=sup_ev,
            top_opposing_evidence=opp_ev,
            abstention_reason=abstention_reason,
            is_live_data=False,
            is_simulated=True
        )

        # Persist to database
        if db:
            try:
                discrimination_repository.persist_assessment(db, assessment)
            except Exception:
                pass

        return assessment

    def _classify_multimodal(
        self,
        mean_frp_mw: float,
        max_frp_mw: float,
        observation_count: int,
        active_days_count: int,
        night_fraction: float,
        is_inside_facility: bool,
        facility_distance_m: float,
        land_cover_class: LandCoverClass,
        quality_state: ObservationQualityState,
        is_reflection: bool,
        eo_result: Optional[EOVerificationResult]
    ) -> tuple:
        """
        Multimodal classification logic over target classes.
        Returns: (class_probabilities, predicted_class, classification_state, abstention_reason)
        """
        # Case 1: Potential Specular Reflection Confound -> Abstain with NEEDS_REVIEW
        if is_reflection or quality_state == ObservationQualityState.POTENTIAL_REFLECTION:
            probs = {"OTHER_UNKNOWN": 0.70, "ROUTINE_PROCESS_HEAT": 0.15, "GAS_FLARE": 0.15}
            return probs, "OTHER_UNKNOWN", "NEEDS_REVIEW", "Observation geometry exhibits high specular reflection probability during daytime without historical recurrence."

        # Case 2: Insufficient Observations
        if observation_count == 0:
            return {}, "OTHER_UNKNOWN", "INSUFFICIENT_EVIDENCE", "Zero confirmed satellite observations."

        # Case 3: Industrial Flare (High night persistence, inside petrochemical/refinery, high FRP)
        if (is_inside_facility or facility_distance_m < 80.0) and active_days_count >= 5 and night_fraction > 0.40 and mean_frp_mw > 10.0:
            probs = {
                "GAS_FLARE": 0.88,
                "ROUTINE_PROCESS_HEAT": 0.08,
                "INDUSTRIAL_FIRE": 0.03,
                "AGRICULTURAL_BURNING": 0.005,
                "WILDFIRE_NATURAL": 0.005
            }
            return probs, "GAS_FLARE", "CLASSIFIED", None

        # Case 4: Routine Industrial Process Heat (Inside facility, moderate FRP, persistent)
        if (is_inside_facility or facility_distance_m < 120.0) and active_days_count >= 3:
            probs = {
                "ROUTINE_PROCESS_HEAT": 0.84,
                "GAS_FLARE": 0.10,
                "INDUSTRIAL_FIRE": 0.04,
                "AGRICULTURAL_BURNING": 0.01,
                "WILDFIRE_NATURAL": 0.01
            }
            return probs, "ROUTINE_PROCESS_HEAT", "CLASSIFIED", None

        # Case 5: Mining / Quarry Process Heat
        if land_cover_class == LandCoverClass.MINING_QUARRY:
            probs = {
                "MINING_PROCESS_HEAT": 0.85,
                "ROUTINE_PROCESS_HEAT": 0.08,
                "WILDFIRE_NATURAL": 0.04,
                "AGRICULTURAL_BURNING": 0.03
            }
            return probs, "MINING_PROCESS_HEAT", "CLASSIFIED", None

        # Case 6: Agricultural Burning (Cropland land-cover, transient/seasonal, low night persistence)
        if land_cover_class == LandCoverClass.AGRICULTURE_CROPLAND and not is_inside_facility and night_fraction < 0.25:
            probs = {
                "AGRICULTURAL_BURNING": 0.86,
                "WILDFIRE_NATURAL": 0.09,
                "ROUTINE_PROCESS_HEAT": 0.03,
                "OTHER_UNKNOWN": 0.02
            }
            return probs, "AGRICULTURAL_BURNING", "CLASSIFIED", None

        # Case 7: Wildfire / Natural Vegetative Fire (Forest / Shrubland land-cover, moving/large footprint)
        if land_cover_class in [LandCoverClass.FOREST, LandCoverClass.SHRUBLAND_GRASSLAND] and not is_inside_facility:
            probs = {
                "WILDFIRE_NATURAL": 0.89,
                "AGRICULTURAL_BURNING": 0.07,
                "OTHER_UNKNOWN": 0.04
            }
            return probs, "WILDFIRE_NATURAL", "CLASSIFIED", None

        # Case 8: Transient Unattributed Anomaly -> NEEDS_REVIEW
        probs = {
            "OTHER_UNKNOWN": 0.45,
            "AGRICULTURAL_BURNING": 0.25,
            "WILDFIRE_NATURAL": 0.20,
            "ROUTINE_PROCESS_HEAT": 0.10
        }
        return probs, "OTHER_UNKNOWN", "NEEDS_REVIEW", "Transient spatial anomaly without authoritative facility linkage or decisive land-cover signature."

    def _compute_system_confidence(
        self,
        model_conf: float,
        obs_count: int,
        quality: ObservationQualityState,
        eo_result: Optional[EOVerificationResult]
    ) -> float:
        penalty = 0.0
        if obs_count < 3:
            penalty += 0.15
        if quality != ObservationQualityState.GOOD:
            penalty += 0.20
        if eo_result and eo_result.structural_match_status == EOStructuralMatchStatus.STRONG_SPATIAL_MATCH:
            penalty -= 0.05
        return round(max(0.20, min(0.98, model_conf - penalty)), 3)

    def _generate_evidence_breakdown(
        self,
        predicted_class: str,
        persistence: SourcePersistenceState,
        is_inside_facility: bool,
        land_cover: LandCoverContextResult,
        night_fraction: float,
        quality: ObservationQualityState,
        eo_result: Optional[EOVerificationResult],
        is_reflection: bool
    ) -> tuple:
        supporting: List[EvidenceExplanationItem] = []
        opposing: List[EvidenceExplanationItem] = []

        if is_inside_facility:
            supporting.append(EvidenceExplanationItem(
                evidence_type="FACILITY_GEOMETRY",
                description="Thermal centroid contained inside verified industrial facility boundary polygon.",
                support_state="SUPPORTING",
                weight=0.92
            ))
        else:
            opposing.append(EvidenceExplanationItem(
                evidence_type="FACILITY_GEOMETRY",
                description="Thermal centroid located outside established industrial infrastructure fence line.",
                support_state="CONTRADICTING",
                weight=0.60
            ))

        if land_cover.consistency_with_industrial > 0.70:
            supporting.append(EvidenceExplanationItem(
                evidence_type="LAND_COVER",
                description=f"Copernicus Land Cover confirmed {land_cover.land_cover_class.value} with 10m resolution.",
                support_state="SUPPORTING",
                weight=0.85
            ))

        if persistence in [SourcePersistenceState.PERSISTENT, SourcePersistenceState.INTERMITTENT]:
            supporting.append(EvidenceExplanationItem(
                evidence_type="FINGERPRINT",
                description=f"Source exhibits historical persistence across multi-week observation baselines.",
                support_state="SUPPORTING",
                weight=0.88
            ))

        if eo_result and eo_result.structural_match_status == EOStructuralMatchStatus.STRONG_SPATIAL_MATCH:
            scene_info = f" ({eo_result.copernicus_scene_id[:24]}...)" if getattr(eo_result, "copernicus_scene_id", None) else ""
            supporting.append(EvidenceExplanationItem(
                evidence_type="EO_VERIFICATION",
                description=f"High-resolution Copernicus Sentinel-2 optical imagery{scene_info} confirms structural alignment with flare stack/tank.",
                support_state="SUPPORTING",
                weight=0.90
            ))
        elif eo_result and eo_result.structural_match_status == EOStructuralMatchStatus.IMAGERY_UNAVAILABLE:
            cloud_info = f" ({eo_result.cloud_cover_percent:.0f}% clouds)" if getattr(eo_result, "cloud_cover_percent", None) else ""
            opposing.append(EvidenceExplanationItem(
                evidence_type="EO_VERIFICATION",
                description=f"High-resolution Sentinel-2 optical imagery currently obscured by local cloud cover{cloud_info}.",
                support_state="CONTRADICTING",
                weight=0.30
            ))

        if is_reflection:
            opposing.append(EvidenceExplanationItem(
                evidence_type="QUALITY",
                description="High solar elevation angle and low FRP indicates possible specular reflection.",
                support_state="CONTRADICTING",
                weight=0.85
            ))

        return supporting, opposing

source_discrimination_service = ThermalSourceDiscriminationService()
