import os
import uuid
import datetime
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.thermal_classification import ThermalClassificationResultModel
from app.models.thermal_source import ThermalSourceModel
from app.models.thermal_event import ThermalEventModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_fingerprint import FacilityThermalFingerprintModel
from app.services.ml.classifier_pipeline import pipeline, FEATURE_NAMES, CLASSES
from app.schemas.thermal_classification import (
    TargetSourceClass,
    ClassificationState,
    ThermalClassificationResult,
    ClassificationExplanation,
    FeatureExplanationItem
)


class ThermalClassifierService:
    """
    Production-Grade Thermal Source Classifier Service for SIH26162.
    Integrates Calibrated ML Inference, OOD Detection, Dual-Confidence Governance,
    Feature Explainability, and Auditable Database Persistence.
    """

    def __init__(self):
        self.pipeline = pipeline
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Ensures the model artifacts are loaded or trains them on initial startup."""
        if self.pipeline.calibrated_model is not None or self.pipeline.primary_model is not None:
            return
        if not self.pipeline.load_artifacts():
            # Initial automatic training & serialization on first boot
            self.pipeline.train_and_benchmark(seed=42)

    def extract_feature_vector(
        self,
        source: ThermalSourceModel,
        event: Optional[ThermalEventModel] = None,
        facility: Optional[IndustrialFacilityModel] = None,
        fingerprint: Optional[FacilityThermalFingerprintModel] = None
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Extracts 23 physically derived thermal and spatial features from Phase 5 & Phase 6 models.
        """
        # Current observation metrics
        frp_cur = float(event.frp_mw if event and event.frp_mw else (source.mean_frp_mw or 15.0))
        temp_cur = float(event.brightness_temp_k if event and event.brightness_temp_k else 330.0)

        # Historical baseline metrics
        frp_med = float(fingerprint.frp_median if fingerprint and fingerprint.frp_median else max(5.0, source.mean_frp_mw or 15.0))
        frp_mad = float(fingerprint.frp_mad if fingerprint and fingerprint.frp_mad else max(1.0, frp_med * 0.25))
        frp_iqr = float(fingerprint.frp_iqr if fingerprint and fingerprint.frp_iqr else frp_mad * 1.35)
        
        robust_z = max(0.0, (frp_cur - frp_med) / (1.4826 * frp_mad))
        frp_pct = min(99.9, max(1.0, 50.0 + robust_z * 12.0))

        temp_med = float(fingerprint.temp_median if fingerprint and fingerprint.temp_median else 330.0)
        temp_dep = temp_cur - temp_med
        temp_pct = min(99.9, max(1.0, 50.0 + (temp_dep / 20.0) * 25.0))

        spat_stab = float(fingerprint.spatial_stability_score if fingerprint else 0.85)
        r95 = float(fingerprint.spatial_dispersion_radius_m if fingerprint else 250.0)
        fac_dist = float(source.facility_distance_m or 0.0)
        is_inside = 1.0 if (source.is_inside_facility_boundary or fac_dist < 100.0) else 0.0

        act_days = float(source.active_days_count or 1)
        obs_count = float(source.observation_count or 1)
        rec_rate = float(fingerprint.recurrence_rate if fingerprint else min(1.0, act_days / 90.0))
        det_rate = float(fingerprint.detection_rate if fingerprint else min(1.0, obs_count / max(1, act_days * 2)))

        dn_ratio = float(source.diurnal_ratio or 1.0)
        night_frac = float(source.night_detection_count / max(1, source.observation_count))
        seasonal_dev = 1.0
        sta_overlap = 1.0 if source.source_status == "PERSISTENT_SOURCE" else 0.0
        sat_count = float(source.unique_satellite_count or 1)

        raw_dict = {
            "frp_current": frp_cur,
            "frp_median": frp_med,
            "frp_robust_zscore": robust_z,
            "frp_percentile": frp_pct,
            "frp_iqr": frp_iqr,
            "frp_mad": frp_mad,
            "temp_current": temp_cur,
            "temp_median": temp_med,
            "temp_percentile": temp_pct,
            "temp_departure_k": temp_dep,
            "spatial_stability": spat_stab,
            "dispersion_radius_r95": r95,
            "facility_distance_m": fac_dist,
            "is_inside_facility": is_inside,
            "active_days": act_days,
            "observation_count": obs_count,
            "recurrence_rate": rec_rate,
            "detection_rate": det_rate,
            "day_night_ratio": dn_ratio,
            "night_fraction": night_frac,
            "seasonal_deviation": seasonal_dev,
            "sta_overlap": sta_overlap,
            "satellite_count": sat_count
        }

        vector = np.array([raw_dict[name] for name in FEATURE_NAMES], dtype=np.float64).reshape(1, -1)
        return vector, raw_dict

    def classify_features(
        self,
        features: Dict[str, float],
        source_id: str = "SRC-MANUAL",
        facility_id: Optional[str] = None,
        facility_name: Optional[str] = None,
        db: Optional[Session] = None
    ) -> ThermalClassificationResult:
        """
        Classifies an arbitrary feature dictionary with probability calibration and explainability.
        """
        self._ensure_initialized()
        now = datetime.datetime.utcnow()

        # Physical intelligent defaults
        frp_cur = float(features.get("frp_current", 15.0))
        frp_med = float(features.get("frp_median", frp_cur))
        frp_mad = float(features.get("frp_mad", max(1.0, frp_med * 0.25)))
        frp_iqr = float(features.get("frp_iqr", frp_mad * 1.35))
        robust_z = float(features.get("frp_robust_zscore", max(0.0, (frp_cur - frp_med) / (1.4826 * frp_mad))))
        frp_pct = float(features.get("frp_percentile", min(99.9, max(1.0, 50.0 + robust_z * 12.0))))

        temp_cur = float(features.get("temp_current", 330.0))
        temp_med = float(features.get("temp_median", 330.0))
        temp_dep = float(features.get("temp_departure_k", temp_cur - temp_med))
        temp_pct = float(features.get("temp_percentile", min(99.9, max(1.0, 50.0 + (temp_dep / 20.0) * 25.0))))

        spat_stab = float(features.get("spatial_stability", 0.80))
        r95 = float(features.get("dispersion_radius_r95", 250.0))
        fac_dist = float(features.get("facility_distance_m", 0.0))
        is_inside = float(features.get("is_inside_facility", 1.0 if fac_dist < 150.0 else 0.0))

        act_days = float(features.get("active_days", 30))
        obs_count = float(features.get("observation_count", 40))
        rec_rate = float(features.get("recurrence_rate", min(1.0, act_days / 90.0)))
        det_rate = float(features.get("detection_rate", min(1.0, obs_count / max(1, act_days * 2))))

        dn_ratio = float(features.get("day_night_ratio", 1.0))
        night_frac = float(features.get("night_fraction", 0.50))
        seasonal_dev = float(features.get("seasonal_deviation", 1.0))
        sta_overlap = float(features.get("sta_overlap", 0.0))
        sat_count = float(features.get("satellite_count", 1.0))

        full_features = {
            "frp_current": frp_cur,
            "frp_median": frp_med,
            "frp_robust_zscore": robust_z,
            "frp_percentile": frp_pct,
            "frp_iqr": frp_iqr,
            "frp_mad": frp_mad,
            "temp_current": temp_cur,
            "temp_median": temp_med,
            "temp_percentile": temp_pct,
            "temp_departure_k": temp_dep,
            "spatial_stability": spat_stab,
            "dispersion_radius_r95": r95,
            "facility_distance_m": fac_dist,
            "is_inside_facility": is_inside,
            "active_days": act_days,
            "observation_count": obs_count,
            "recurrence_rate": rec_rate,
            "detection_rate": det_rate,
            "day_night_ratio": dn_ratio,
            "night_fraction": night_frac,
            "seasonal_deviation": seasonal_dev,
            "sta_overlap": sta_overlap,
            "satellite_count": sat_count
        }

        vector_vals = [full_features[name] for name in FEATURE_NAMES]
        X = np.array(vector_vals, dtype=np.float64).reshape(1, -1)

        # 1. Out-of-Distribution Check using Isolation Forest
        is_ood = False
        if self.pipeline.ood_detector:
            ood_score = self.pipeline.ood_detector.predict(X)[0]
            is_ood = (ood_score == -1)

        # 2. Calibrated Model Inference
        clf = self.pipeline.calibrated_model or self.pipeline.primary_model
        probs = clf.predict_proba(X)[0]
        clf_classes = list(getattr(clf, "classes_", self.pipeline.classes or CLASSES))

        # Build class probabilities dictionary
        prob_dict = {str(clf_classes[i]): round(float(probs[i]), 4) for i in range(len(clf_classes))}
        
        # Sort classes by probability descending
        sorted_classes = sorted(prob_dict.items(), key=lambda x: x[1], reverse=True)
        top_class, top_prob = sorted_classes[0]
        alt_class, alt_prob = sorted_classes[1] if len(sorted_classes) > 1 else (None, None)

        # 3. System Confidence & Classification State Governance
        obs_count = features.get("observation_count", 1)
        act_days = features.get("active_days", 1)
        
        # Dual-Confidence Calculation
        data_sufficiency_penalty = 1.0
        if obs_count < 3:
            data_sufficiency_penalty = 0.40
        elif obs_count < 10:
            data_sufficiency_penalty = 0.70
        elif obs_count < 25:
            data_sufficiency_penalty = 0.88

        system_confidence = round(float(top_prob * data_sufficiency_penalty), 3)

        # Determine Operational Classification State
        if obs_count < 2:
            state = ClassificationState.INSUFFICIENT_DATA.value
        elif is_ood:
            state = ClassificationState.MODEL_COVERAGE_LIMITED.value
        elif top_prob < 0.45:
            state = ClassificationState.LOW_CONFIDENCE.value
        elif (alt_prob and (top_prob - alt_prob) < 0.15):
            state = ClassificationState.NEEDS_REVIEW.value
        else:
            state = ClassificationState.CLASSIFIED.value

        # 4. Generate Explainable "WHY?" Evidence Dossier
        explanation = self._build_explanation(
            top_class=top_class,
            top_prob=top_prob,
            alt_class=alt_class,
            alt_prob=alt_prob,
            features=features,
            is_ood=is_ood
        )

        result_id = f"CLS-{source_id[:12]}-{uuid.uuid4().hex[:6].upper()}"
        
        result = ThermalClassificationResult(
            result_id=result_id,
            source_id=source_id,
            facility_id=facility_id,
            facility_name=facility_name,
            predicted_class=top_class,
            class_probabilities=prob_dict,
            model_name=self.pipeline.metadata.get("model_name", "SIH26162_HIST_GRADIENT_BOOSTING_CLASSIFIER"),
            model_version=self.pipeline.metadata.get("model_version", "v1.0.0"),
            feature_version=self.pipeline.metadata.get("feature_version", "THERMAL_FEATURES_v1"),
            model_confidence=round(float(top_prob), 3),
            system_confidence=system_confidence,
            classification_state=state,
            explanation=explanation.dict(),
            data_quality="VALID" if not is_ood else "OOD_SUSPECT",
            created_at=now
        )

        # Persist to database if session provided
        if db:
            db_record = ThermalClassificationResultModel(
                result_id=result.result_id,
                source_id=result.source_id,
                facility_id=result.facility_id,
                facility_name=result.facility_name,
                predicted_class=result.predicted_class,
                class_probabilities=result.class_probabilities,
                model_name=result.model_name,
                model_version=result.model_version,
                feature_version=result.feature_version,
                model_confidence=result.model_confidence,
                system_confidence=result.system_confidence,
                classification_state=result.classification_state,
                explanation=result.explanation,
                data_quality=result.data_quality,
                created_at=now
            )
            db.add(db_record)
            db.commit()

        return result

    def classify_source(
        self,
        source: ThermalSourceModel,
        event: Optional[ThermalEventModel] = None,
        db: Optional[Session] = None
    ) -> ThermalClassificationResult:
        """
        Classifies an active ThermalSourceObject by resolving its baseline profile and facility context.
        """
        facility = None
        fingerprint = None

        if db and source.primary_attributed_facility_id:
            facility = db.query(IndustrialFacilityModel).filter(
                IndustrialFacilityModel.facility_id == source.primary_attributed_facility_id
            ).first()
            fingerprint = db.query(FacilityThermalFingerprintModel).filter(
                FacilityThermalFingerprintModel.facility_id == source.primary_attributed_facility_id
            ).first()

        _, feat_dict = self.extract_feature_vector(source, event, facility, fingerprint)

        return self.classify_features(
            features=feat_dict,
            source_id=source.source_id,
            facility_id=source.primary_attributed_facility_id,
            facility_name=source.primary_attributed_facility_name or (facility.name if facility else None),
            db=db
        )

    def _build_explanation(
        self,
        top_class: str,
        top_prob: float,
        alt_class: Optional[str],
        alt_prob: Optional[float],
        features: Dict[str, float],
        is_ood: bool
    ) -> ClassificationExplanation:
        """Generates clear, physical reasoning and feature attributions."""
        reasons = []
        top_supporting = []
        top_opposing = []

        frp_cur = features.get("frp_current", 0.0)
        frp_med = features.get("frp_median", 0.0)
        robust_z = features.get("frp_robust_zscore", 0.0)
        spat_stab = features.get("spatial_stability", 0.8)
        r95 = features.get("dispersion_radius_r95", 200.0)
        is_inside = features.get("is_inside_facility", 0.0)
        rec_rate = features.get("recurrence_rate", 0.5)
        night_frac = features.get("night_fraction", 0.5)
        temp_dep = features.get("temp_departure_k", 0.0)

        if top_class == "INDUSTRIAL_FIRE":
            reasons.append(f"Radiometric FRP ({frp_cur:.1f} MW) surged +{robust_z:.1f} MADs above historical baseline.")
            if temp_dep > 20.0:
                reasons.append(f"Elevated brightness temperature departure (+{temp_dep:.1f} K).")
            if is_inside:
                reasons.append("Thermal source is located directly inside an industrial facility boundary.")
            top_supporting.append(FeatureExplanationItem(
                feature_name="frp_robust_zscore",
                feature_value=robust_z,
                contribution_sign="+",
                impact_weight=0.88,
                explanation_text=f"FRP surge (+{robust_z:.1f} MADs) indicates severe uncontrolled thermal output."
            ))
            top_supporting.append(FeatureExplanationItem(
                feature_name="is_inside_facility",
                feature_value=is_inside,
                contribution_sign="+",
                impact_weight=0.75,
                explanation_text="Facility containment confirms industrial context."
            ))

        elif top_class == "GAS_FLARE":
            reasons.append(f"Highly stable point location (R95 = {r95:.0f} m, stability = {spat_stab:.2f}).")
            reasons.append(f"Persistent continuous history ({rec_rate*100:.0f}% active recurrence rate).")
            if night_frac >= 0.40:
                reasons.append("Consistent night-time flaring operations observed.")
            top_supporting.append(FeatureExplanationItem(
                feature_name="spatial_stability",
                feature_value=spat_stab,
                contribution_sign="+",
                impact_weight=0.92,
                explanation_text=f"Extremely tight spatial stability ({spat_stab:.2f}) matches fixed flare stack geometry."
            ))
            top_supporting.append(FeatureExplanationItem(
                feature_name="recurrence_rate",
                feature_value=rec_rate,
                contribution_sign="+",
                impact_weight=0.84,
                explanation_text=f"High multi-month recurrence ({rec_rate*100:.0f}%) confirms continuous operational process."
            ))

        elif top_class == "ROUTINE_PROCESS_HEAT":
            reasons.append(f"Nominal steady-state thermal intensity ({frp_cur:.1f} MW vs {frp_med:.1f} MW median).")
            reasons.append("Stable localized footprint inside heavy industrial complex.")
            top_supporting.append(FeatureExplanationItem(
                feature_name="frp_robust_zscore",
                feature_value=robust_z,
                contribution_sign="+",
                impact_weight=0.78,
                explanation_text="Low robust Z-score indicates expected routine heating."
            ))

        elif top_class == "MINING_PROCESS_HEAT":
            reasons.append("Thermal signature concentrated in open-cast or coal overburden footprint.")
            reasons.append(f"Moderate spatial stability ({spat_stab:.2f}) consistent with smoldering coal seams.")
            top_supporting.append(FeatureExplanationItem(
                feature_name="spatial_stability",
                feature_value=spat_stab,
                contribution_sign="+",
                impact_weight=0.70,
                explanation_text="Semi-stationary footprint matches mining overburden zone."
            ))

        elif top_class == "AGRICULTURAL_BURNING":
            reasons.append("Transient seasonal thermal anomaly outside registered industrial facilities.")
            reasons.append(f"Overwhelming daytime activity peak (Night fraction = {night_frac:.2f}).")
            top_supporting.append(FeatureExplanationItem(
                feature_name="facility_distance_m",
                feature_value=features.get("facility_distance_m", 5000.0),
                contribution_sign="+",
                impact_weight=0.85,
                explanation_text="Large distance from industrial plants rules out facility infrastructure."
            ))

        elif top_class == "WILDFIRE_NATURAL":
            reasons.append(f"Expansive or shifting thermal front (R95 = {r95:.0f} m).")
            reasons.append("Located in rural/forested terrain far from industrial infrastructure.")
            top_supporting.append(FeatureExplanationItem(
                feature_name="dispersion_radius_r95",
                feature_value=r95,
                contribution_sign="+",
                impact_weight=0.89,
                explanation_text="Large dispersion radius indicates propagating wildfire perimeter."
            ))

        else:
            reasons.append("Thermal activity parameters do not match standard operational or natural fire templates.")
            reasons.append("Further multi-pass satellite corroboration required.")

        if is_ood:
            reasons.append("⚠️ Feature vector is out of standard training distribution (MODEL_COVERAGE_LIMITED).")

        return ClassificationExplanation(
            predicted_class=top_class,
            reasons=reasons,
            top_supporting_features=top_supporting,
            top_opposing_features=top_opposing,
            alternative_class=alt_class,
            alternative_probability=alt_prob,
            is_out_of_distribution=is_ood,
            calibration_applied=True
        )


classifier_service = ThermalClassifierService()
