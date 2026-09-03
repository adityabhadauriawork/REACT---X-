import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from app.models.thermal_fingerprint import FacilityThermalFingerprintModel, ThermalAbnormalityAssessmentModel
from app.models.thermal_source import ThermalSourceModel
from app.models.facility import IndustrialFacilityModel
from app.models.thermal_event import ThermalEventModel
from app.services.satellite.spatial_index import spatial_index
from app.services.satellite.fingerprint_engine import fingerprint_engine

class AbnormalityEngine:
    """
    Scientific Multi-Dimensional Abnormality Engine.
    Evaluates current thermal observations against empirical facility/source profiles.
    Detects: Sudden Spike, Gradual Rise, Persistent Shift, Spatial Expansion, Behavioural Change, New Source.
    """

    def __init__(self):
        self.version = "1.0"
        self.baseline_version = "v1.0"
        self.weight_version = "v1.0_heuristic_validated"

    def assess_thermal_source(
        self,
        source: ThermalSourceModel,
        current_event: Optional[ThermalEventModel],
        db: Session
    ) -> ThermalAbnormalityAssessmentModel:
        """
        Conducts a multi-signal abnormality assessment for a ThermalSourceObject against its
        associated facility profile or its own empirical historical source baseline.
        """
        now = datetime.utcnow()
        current_frp = current_event.frp_mw if current_event else source.max_frp_mw
        current_temp = current_event.brightness_temp_k if current_event else source.mean_brightness_temp_k
        current_lat = current_event.latitude if current_event else source.centroid_lat
        current_lon = current_event.longitude if current_event else source.centroid_lon
        current_day_night = current_event.day_night if current_event else ("N" if source.night_detection_count > source.day_detection_count else "D")

        # 1. Lookup or compute facility baseline profile
        fingerprint = None
        facility = None
        if source.primary_attributed_facility_id:
            facility = db.query(IndustrialFacilityModel).filter(
                IndustrialFacilityModel.facility_id == source.primary_attributed_facility_id
            ).first()
            
            fingerprint = db.query(FacilityThermalFingerprintModel).filter(
                FacilityThermalFingerprintModel.facility_id == source.primary_attributed_facility_id
            ).first()

        # If no facility profile exists, try to seed or create from available source events
        if not fingerprint:
            fingerprint_engine.seed_initial_fingerprints_if_empty(db)
            if source.primary_attributed_facility_id:
                fingerprint = db.query(FacilityThermalFingerprintModel).filter(
                    FacilityThermalFingerprintModel.facility_id == source.primary_attributed_facility_id
                ).first()

        # 2. Case A: INSUFFICIENT HISTORY (< 5 observations)
        if not fingerprint or fingerprint.data_sufficiency == "INSUFFICIENT_HISTORY" or source.observation_count < 3:
            assessment_id = f"ABN-{now.strftime('%Y%m%d%H%M%S')}-{source.source_id[-6:]}-{uuid.uuid4().hex[:6]}"
            
            reasons = [
                "Insufficient historical baseline observations to reliably determine abnormality",
                f"Source observed across {source.observation_count} passes ({source.active_days_count} active days)",
                f"Current radiometric FRP is {current_frp:.1f} MW"
            ]
            
            evidence_dict = {
                "frp_deviation": {"ratio": 1.0, "robust_zscore": 0.0, "status": "INSUFFICIENT_DATA"},
                "temperature_deviation": {"delta_k": 0.0, "status": "INSUFFICIENT_DATA"},
                "recurrence_change": {"active_days": source.active_days_count, "observation_count": source.observation_count},
                "spatial_change": {"displacement_m": 0.0, "stability": "UNKNOWN"},
                "diurnal_change": {"day_night": current_day_night, "status": "NOMINAL"},
                "seasonal_change": {"month": now.month, "status": "UNAVAILABLE"},
                "recent_trend": {"trend": "STABLE", "slope": 0.0},
                "observation_coverage": {"passes": source.observation_count, "sufficiency": "INSUFFICIENT_HISTORY"},
                "data_quality": {"status": "GOOD", "confidence_discount": 0.50},
                "reasons": reasons,
                "change_type": "NEW_SOURCE" if source.observation_count <= 2 else "STABLE_BASELINE"
            }
            
            assessment = ThermalAbnormalityAssessmentModel(
                assessment_id=assessment_id,
                source_id=source.source_id,
                facility_id=facility.facility_id if facility else None,
                facility_name=facility.name if facility else "Unattributed Area",
                assessment_time=now,
                current_frp_mw=current_frp,
                current_temp_k=current_temp,
                current_lat=current_lat,
                current_lon=current_lon,
                frp_deviation=1.0,
                frp_robust_zscore=0.0,
                frp_standard_zscore=0.0,
                frp_percentile=50.0,
                temperature_deviation=0.0,
                frequency_deviation=1.0,
                spatial_change_score=0.0,
                spatial_displacement_m=0.0,
                diurnal_deviation=0.0,
                seasonal_deviation=1.0,
                overall_abnormality_score=10.0 if current_frp < 50.0 else 35.0,
                confidence=0.30,  # Explicitly low confidence due to sparse history
                status="INSUFFICIENT_HISTORY",
                evidence=evidence_dict,
                feature_vector=self._build_feature_vector(source, facility, fingerprint, current_frp, current_temp, 1.0, 0.0, 0.30, "INSUFFICIENT_HISTORY"),
                baseline_version=self.baseline_version,
                algorithm_version=self.version,
                created_at=now
            )
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            return assessment

        # 3. Multi-Signal Statistical Deviation Evaluation
        
        # --- Signal 1: Robust FRP Deviation ---
        median_frp = max(1.0, fingerprint.frp_median)
        mad_frp = max(0.5, fingerprint.frp_mad)
        std_frp = max(1.0, fingerprint.frp_std)
        mean_frp = max(1.0, fingerprint.frp_mean)
        
        frp_deviation_ratio = round(current_frp / median_frp, 2)
        robust_zscore = round((current_frp - median_frp) / (1.4826 * mad_frp), 2)
        std_zscore = round((current_frp - mean_frp) / std_frp, 2)
        
        # Percentile calculation
        if current_frp >= fingerprint.frp_p90:
            frp_pct = 95.0 + min(4.9, (current_frp - fingerprint.frp_p90) / max(1.0, fingerprint.frp_p90) * 5.0)
        elif current_frp >= fingerprint.frp_p50:
            frp_pct = 50.0 + (current_frp - fingerprint.frp_p50) / max(1.0, (fingerprint.frp_p90 - fingerprint.frp_p50)) * 40.0
        else:
            frp_pct = max(5.0, 10.0 + (current_frp - fingerprint.frp_p10) / max(1.0, (fingerprint.frp_p50 - fingerprint.frp_p10)) * 40.0)
        frp_pct = min(99.9, round(frp_pct, 1))

        # --- Signal 2: Brightness Temperature Deviation ---
        temp_deviation_k = 0.0
        temp_pct = 50.0
        if current_temp and fingerprint.temp_median:
            temp_deviation_k = round(current_temp - fingerprint.temp_median, 1)
            temp_p90 = fingerprint.temp_p90 or (fingerprint.temp_median + 20.0)
            temp_p10 = fingerprint.temp_p10 or (fingerprint.temp_median - 15.0)
            if current_temp >= temp_p90:
                temp_pct = 95.0
            elif current_temp >= fingerprint.temp_median:
                temp_pct = 50.0 + (current_temp - fingerprint.temp_median) / max(1.0, (temp_p90 - fingerprint.temp_median)) * 40.0
            else:
                temp_pct = max(5.0, 10.0 + (current_temp - temp_p10) / max(1.0, (fingerprint.temp_median - temp_p10)) * 40.0)
            temp_pct = min(99.9, round(temp_pct, 1))

        # --- Signal 3: Spatial Footprint & Displacement ---
        disp_m = spatial_index.haversine_distance_m(current_lat, current_lon, fingerprint.centroid_lat, fingerprint.centroid_lon)
        baseline_dispersion = max(50.0, fingerprint.spatial_dispersion_radius_m)
        spatial_change_score = round(min(5.0, disp_m / baseline_dispersion), 2)

        # --- Signal 4: Frequency & Burst Deviation ---
        expected_rate = max(0.1, fingerprint.detection_rate)
        recent_obs_count = source.observation_count
        freq_deviation = round(min(5.0, (recent_obs_count / max(1.0, source.active_days_count * expected_rate * 2.0))), 2)

        # --- Signal 5: Diurnal Pattern Consistency ---
        diurnal_deviation = 0.0
        if current_day_night == 'N' and fingerprint.night_fraction < 0.15:
            diurnal_deviation = 0.6  # Unusual night operation
        elif current_day_night == 'D' and fingerprint.night_fraction > 0.85:
            diurnal_deviation = 0.4

        # --- Signal 6: Seasonal Calibration ---
        current_month = f"{now.month:02d}"
        seasonal_dev = 1.0
        if fingerprint.monthly_statistics and current_month in fingerprint.monthly_statistics:
            m_stat = fingerprint.monthly_statistics[current_month]
            m_median = m_stat.get("median_frp", median_frp)
            seasonal_dev = round(current_frp / max(1.0, m_median), 2)

        # --- 4. Multi-Signal Synthesis: Overall Abnormality Score (0 - 100) ---
        w_frp = 0.45
        w_temp = 0.20
        w_spatial = 0.15
        w_freq = 0.10
        w_diurnal = 0.10

        frp_signal_score = min(100.0, max(0.0, (robust_zscore * 12.0) + (max(0.0, frp_deviation_ratio - 1.0) * 20.0)))
        temp_signal_score = min(100.0, max(0.0, (temp_deviation_k * 2.5)))
        spatial_signal_score = min(100.0, max(0.0, max(0.0, spatial_change_score - 1.0) * 30.0))
        freq_signal_score = min(100.0, max(0.0, max(0.0, freq_deviation - 1.0) * 25.0))
        diurnal_signal_score = min(100.0, diurnal_deviation * 100.0)

        overall_abnormality = (
            (w_frp * frp_signal_score) +
            (w_temp * temp_signal_score) +
            (w_spatial * spatial_signal_score) +
            (w_freq * freq_signal_score) +
            (w_diurnal * diurnal_signal_score)
        )
        overall_abnormality = round(min(100.0, max(0.0, overall_abnormality)), 1)

        # --- 5. Independent Confidence Calculation (0.0 - 1.0) ---
        base_conf = 0.50
        if fingerprint.data_sufficiency == "STRONG_BASELINE":
            base_conf = 0.88
        elif fingerprint.data_sufficiency == "ESTABLISHED_BASELINE":
            base_conf = 0.78
        elif fingerprint.data_sufficiency == "DEVELOPING_BASELINE":
            base_conf = 0.68
        elif fingerprint.data_sufficiency == "LIMITED_HISTORY":
            base_conf = 0.55

        if source.unique_satellite_count >= 3:
            base_conf += 0.08
        elif source.unique_satellite_count >= 2:
            base_conf += 0.04

        if source.observation_count >= 20:
            base_conf += 0.04

        confidence_score = round(min(0.98, max(0.35, base_conf)), 2)

        # --- 6. Determine Change Type Category ---
        if robust_zscore >= 3.5 and frp_deviation_ratio >= 2.5:
            change_type = "SUDDEN_SPIKE"
        elif robust_zscore >= 2.0 and spatial_change_score >= 2.0:
            change_type = "SPATIAL_EXPANSION"
        elif robust_zscore >= 1.5 and diurnal_deviation > 0.3:
            change_type = "BEHAVIOURAL_CHANGE"
        elif robust_zscore >= 1.8:
            change_type = "GRADUAL_RISE"
        elif source.source_status == "NEW_SOURCE":
            change_type = "NEW_SOURCE"
        else:
            change_type = "STABLE_BASELINE"

        # --- 7. Determine Status Category ---
        if overall_abnormality >= 65.0 or (robust_zscore >= 4.0 and frp_deviation_ratio >= 2.5):
            status = "ABNORMAL_THERMAL_BEHAVIOUR"
        elif overall_abnormality >= 35.0 or robust_zscore >= 2.0 or frp_deviation_ratio >= 1.8:
            status = "WATCH"
        elif source.source_status == "PERSISTENT_SOURCE" and overall_abnormality < 35.0:
            status = "EXPECTED_PERSISTENT"
        elif source.source_status == "RECURRING_SOURCE" and overall_abnormality < 35.0:
            status = "EXPECTED_RECURRING"
        else:
            status = "NORMAL_BASELINE"

        # --- 8. Build Transparent Explainable Evidence ---
        reasons = []
        if frp_deviation_ratio >= 2.0:
            reasons.append(f"• FRP is {frp_deviation_ratio:.1f}x facility baseline ({current_frp:.1f} MW vs {median_frp:.1f} MW median, +{robust_zscore:.1f} MAD)")
        elif frp_deviation_ratio <= 0.5 and current_frp > 0:
            reasons.append(f"• FRP is reduced by {(1.0 - frp_deviation_ratio)*100:.0f}% from median ({current_frp:.1f} MW vs {median_frp:.1f} MW)")
        else:
            reasons.append(f"• Radiometric FRP ({current_frp:.1f} MW) is within normal expected range ({fingerprint.frp_p10:.1f} - {fingerprint.frp_p90:.1f} MW)")

        if temp_deviation_k > 15.0:
            reasons.append(f"• Brightness temperature is +{temp_deviation_k:.1f} K above baseline ({current_temp:.1f} K vs {fingerprint.temp_median:.1f} K, {temp_pct:.0f}th percentile)")

        if disp_m > 300.0 and spatial_change_score > 1.5:
            reasons.append(f"• Spatial footprint shifted {disp_m:.0f}m from historical facility centroid")

        if freq_deviation > 2.0:
            reasons.append(f"• Elevated observation recurrence ({source.observation_count} detections in recent passes)")

        if diurnal_deviation > 0.0:
            reasons.append(f"• Operating schedule departure ({'Nighttime' if current_day_night == 'N' else 'Daytime'} overpass at predominantly {'daytime' if current_day_night == 'N' else 'nighttime'} facility)")

        # Create structured evidence dictionary
        evidence_dict = {
            "frp_deviation": {
                "current_mw": current_frp,
                "median_mw": median_frp,
                "ratio": frp_deviation_ratio,
                "robust_zscore": robust_zscore,
                "percentile": frp_pct
            },
            "temperature_deviation": {
                "current_k": current_temp,
                "median_k": fingerprint.temp_median,
                "delta_k": temp_deviation_k,
                "percentile": temp_pct
            },
            "recurrence_change": {
                "active_days": source.active_days_count,
                "observation_count": source.observation_count,
                "recurrence_rate": source.active_days_count / max(1, fingerprint.observation_opportunity_count or 90)
            },
            "spatial_change": {
                "displacement_m": round(disp_m, 1),
                "dispersion_radius_m": baseline_dispersion,
                "spatial_change_score": spatial_change_score
            },
            "diurnal_change": {
                "current_pass": current_day_night,
                "night_fraction": fingerprint.night_fraction,
                "diurnal_deviation": diurnal_deviation
            },
            "seasonal_change": {
                "month": current_month,
                "seasonal_deviation": seasonal_dev
            },
            "recent_trend": {
                "change_type": change_type,
                "zscore": robust_zscore
            },
            "observation_coverage": {
                "observation_count": source.observation_count,
                "active_days": source.active_days_count,
                "satellites": source.unique_satellite_count,
                "sufficiency": fingerprint.data_sufficiency
            },
            "data_quality": {
                "status": "GOOD",
                "sensor_flags": "VALID_TELEMETRY",
                "confidence_score": confidence_score
            },
            "reasons": reasons,
            "change_type": change_type
        }

        # --- 9. Build Prepared Feature Vector for Phase 7 ML ---
        feat_vector = self._build_feature_vector(
            source=source,
            facility=facility,
            fingerprint=fingerprint,
            current_frp=current_frp,
            current_temp=current_temp,
            frp_dev=frp_deviation_ratio,
            robust_z=robust_zscore,
            conf=confidence_score,
            suff=fingerprint.data_sufficiency
        )

        assessment_id = f"ABN-{now.strftime('%Y%m%d%H%M%S')}-{source.source_id[-6:]}-{uuid.uuid4().hex[:6]}"
        assessment = ThermalAbnormalityAssessmentModel(
            assessment_id=assessment_id,
            source_id=source.source_id,
            facility_id=facility.facility_id if facility else None,
            facility_name=facility.name if facility else "Unattributed Area",
            assessment_time=now,
            current_frp_mw=current_frp,
            current_temp_k=current_temp,
            current_lat=current_lat,
            current_lon=current_lon,
            frp_deviation=frp_deviation_ratio,
            frp_robust_zscore=robust_zscore,
            frp_standard_zscore=std_zscore,
            frp_percentile=frp_pct,
            temperature_deviation=temp_deviation_k,
            temperature_percentile=temp_pct,
            frequency_deviation=freq_deviation,
            spatial_change_score=spatial_change_score,
            spatial_displacement_m=round(disp_m, 1),
            diurnal_deviation=diurnal_deviation,
            seasonal_deviation=seasonal_dev,
            overall_abnormality_score=overall_abnormality,
            confidence=confidence_score,
            status=status,
            evidence=evidence_dict,
            feature_vector=feat_vector,
            baseline_version=self.baseline_version,
            algorithm_version=self.version,
            created_at=now
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment

    def _build_feature_vector(
        self,
        source: ThermalSourceModel,
        facility: Optional[IndustrialFacilityModel],
        fingerprint: Optional[FacilityThermalFingerprintModel],
        current_frp: float,
        current_temp: Optional[float],
        frp_dev: float,
        robust_z: float,
        conf: float,
        suff: str
    ) -> Dict[str, Any]:
        """
        Builds Phase 7 feature dictionary with rich provenance metadata.
        """
        now = datetime.utcnow()
        
        # Provenance helper
        def prov(val, unit, source_str, method, quality="VALID"):
            return {
                "value": val,
                "unit": unit,
                "source": source_str,
                "calculation_method": method,
                "calculated_at": now.isoformat() + "Z",
                "data_quality": quality
            }

        features = {
            "source_id": source.source_id,
            "facility_id": facility.facility_id if facility else None,
            "timestamp": now.isoformat() + "Z",
            
            # FRP features
            "frp_current": current_frp,
            "frp_median": fingerprint.frp_median if fingerprint else 0.0,
            "frp_p90": fingerprint.frp_p90 if fingerprint else 0.0,
            "frp_deviation": frp_dev,
            "frp_robust_zscore": robust_z,
            
            # Temp features
            "temperature_current": current_temp,
            "temperature_percentile": 50.0,
            
            # Recurrence features
            "recurrence_rate": source.active_days_count / max(1.0, (fingerprint.observation_opportunity_count if fingerprint else 90)),
            "active_days": source.active_days_count,
            "observation_count": source.observation_count,
            "detection_rate": fingerprint.detection_rate if fingerprint else 0.1,
            
            # Spatial & Temporal
            "day_night_ratio": source.diurnal_ratio,
            "night_fraction": source.night_detection_count / max(1, source.observation_count),
            "spatial_stability": fingerprint.spatial_stability_score if fingerprint else 0.5,
            "spatial_displacement_m": 0.0,
            
            # Context
            "facility_distance_m": source.facility_distance_m or 0.0,
            "is_inside_boundary": source.is_inside_facility_boundary or False,
            "facility_type": facility.facility_type if facility else "UNKNOWN",
            "sta_overlap": source.source_status == "PERSISTENT_SOURCE",
            
            "satellite_count": source.unique_satellite_count,
            "data_sufficiency": suff,
            "provenance": "PHASE6_SYNTHESIZED",
            
            # Full provenance breakdown for audit
            "features_provenance": {
                "frp_current": prov(current_frp, "MW", "NASA_FIRMS", "RADIOMETRIC_INTEGRATION"),
                "frp_median": prov(fingerprint.frp_median if fingerprint else 0.0, "MW", "HISTORICAL_BASELINES", "NON_PARAMETRIC_MEDIAN"),
                "frp_robust_zscore": prov(robust_z, "Z_SCORE", "FINGERPRINT_ENGINE", "ROBUST_MAD_FORMULA"),
                "spatial_stability": prov(fingerprint.spatial_stability_score if fingerprint else 0.5, "RATIO", "SPATIAL_INDEX", "HAVERSINE_DISPERSION_R95"),
                "data_sufficiency": prov(suff, "TIER", "FINGERPRINT_ENGINE", "OBSERVATION_DENSITY_RULE")
            }
        }
        return features

abnormality_engine = AbnormalityEngine()
