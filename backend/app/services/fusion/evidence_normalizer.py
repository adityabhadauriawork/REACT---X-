import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

from app.schemas.fusion import (
    EvidenceItem, EvidenceSourceType, EvidenceSupportState
)
from app.schemas.telemetry import FacilityTelemetryObservation
from app.schemas.vision import ThermalFrameEvidence, CCTVFrameEvidence
from app.schemas.predictive import HazardPrediction

class EvidenceNormalizer:
    """
    Normalizes heterogeneous raw observations from Satellite, Telemetry, Thermal, CCTV,
    Prediction, and Weather into canonical, calibrated EvidenceItem contracts.
    """

    # Source-Specific Freshness TTL Thresholds
    FRESHNESS_TTL_SEC = {
        EvidenceSourceType.TELEMETRY: 15.0,        # 1-5s cadence -> 15s TTL
        EvidenceSourceType.THERMAL_CAMERA: 10.0,   # 2 FPS -> 10s TTL
        EvidenceSourceType.CCTV: 10.0,             # 5 FPS -> 10s TTL
        EvidenceSourceType.PREDICTION: 60.0,       # 1m cadence -> 60s TTL
        EvidenceSourceType.WEATHER: 1800.0,        # 30m cadence -> 30m TTL
        EvidenceSourceType.SATELLITE: 7200.0,      # Multi-hour overpass -> 2hr TTL
        EvidenceSourceType.FACILITY_CONTEXT: 86400.0
    }

    # Baseline Calibrated Source Reliabilities
    SOURCE_RELIABILITIES = {
        EvidenceSourceType.TELEMETRY: 0.95,
        EvidenceSourceType.THERMAL_CAMERA: 0.92,
        EvidenceSourceType.CCTV: 0.85,
        EvidenceSourceType.SATELLITE: 0.88,
        EvidenceSourceType.PREDICTION: 0.80,
        EvidenceSourceType.WEATHER: 0.90,
        EvidenceSourceType.FACILITY_CONTEXT: 0.98
    }

    def normalize_telemetry(self, obs: FacilityTelemetryObservation) -> EvidenceItem:
        now_utc = datetime.now(timezone.utc)
        src_ts = obs.source_timestamp
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)
        
        age_sec = max(0.0, (now_utc - src_ts).total_seconds())
        ttl = self.FRESHNESS_TTL_SEC[EvidenceSourceType.TELEMETRY]
        
        freshness = "LIVE" if age_sec < ttl else ("STALE" if age_sec < (ttl * 3) else "UNAVAILABLE")

        # Normalize score based on sensor type
        norm_score = 0.0
        support = EvidenceSupportState.NEUTRAL

        if "AMB_TEMP" in obs.sensor_id:
            # Ambient temperature is weather context (nominal 20-45°C)
            norm_score = min(1.0, max(0.0, (obs.value - 40.0) / 15.0))
            support = EvidenceSupportState.NEUTRAL if norm_score < 0.30 else EvidenceSupportState.SUPPORTING
        elif "TEMP" in obs.sensor_id:
            # T-04 baseline is -33°C. Critical is > 0°C.
            delta = obs.value - (-33.0)
            norm_score = min(1.0, max(0.0, delta / 35.0))
            if norm_score > 0.40:
                support = EvidenceSupportState.SUPPORTING
            elif delta < 2.0:
                support = EvidenceSupportState.CONTRADICTING
            else:
                support = EvidenceSupportState.NEUTRAL
        elif "PRESS" in obs.sensor_id:
            # T-04 baseline 4.2 bar. Critical > 6.0 bar.
            delta = obs.value - 4.2
            norm_score = min(1.0, max(0.0, delta / 2.5))
            if norm_score > 0.40:
                support = EvidenceSupportState.SUPPORTING
            elif abs(delta) < 0.3:
                support = EvidenceSupportState.CONTRADICTING
            else:
                support = EvidenceSupportState.NEUTRAL
        elif "GAS" in obs.sensor_id:
            # Gas warning threshold is > 25 ppm, critical is > 150 ppm
            norm_score = min(1.0, max(0.0, (obs.value - 5.0) / 45.0)) if obs.value > 5.0 else 0.0
            support = EvidenceSupportState.SUPPORTING if obs.value > 20.0 else EvidenceSupportState.CONTRADICTING
        else:
            norm_score = 0.05
            support = EvidenceSupportState.NEUTRAL

        return EvidenceItem(
            evidence_id=f"EV-TEL-{uuid.uuid4().hex[:6].upper()}",
            facility_id=obs.facility_id,
            asset_id=obs.asset_id,
            zone_id=obs.plant_area or "Sector D - Cryogenic Yard",
            source_id=obs.sensor_id,
            source_type=EvidenceSourceType.TELEMETRY,
            evidence_type=obs.sensor_type.value.lower(),
            observation_timestamp=src_ts,
            ingestion_timestamp=now_utc,
            raw_value=round(obs.value, 2),
            unit=obs.unit,
            normalized_score=round(norm_score, 3),
            quality=obs.quality.value,
            freshness_status=freshness,
            freshness_age_sec=round(age_sec, 1),
            reliability_score=self.SOURCE_RELIABILITIES[EvidenceSourceType.TELEMETRY],
            confidence=0.92,
            support_state=support,
            is_live_data=obs.is_live_data,
            is_simulated=True,
            metadata={"tag": obs.tag_name, "trend": obs.trend}
        )

    def normalize_thermal_vision(self, th: ThermalFrameEvidence) -> EvidenceItem:
        now_utc = datetime.now(timezone.utc)
        src_ts = th.source_timestamp
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)
        
        age_sec = max(0.0, (now_utc - src_ts).total_seconds())
        ttl = self.FRESHNESS_TTL_SEC[EvidenceSourceType.THERMAL_CAMERA]
        freshness = "LIVE" if age_sec < ttl else "STALE"

        norm_score = min(1.0, max(0.0, (th.max_temperature - 25.0) / 60.0))
        if th.hotspot_count > 0 or norm_score > 0.40:
            support = EvidenceSupportState.SUPPORTING
        else:
            support = EvidenceSupportState.CONTRADICTING

        return EvidenceItem(
            evidence_id=f"EV-TH-{uuid.uuid4().hex[:6].upper()}",
            facility_id=th.facility_id,
            asset_id=th.asset_id,
            zone_id=th.zone_id,
            source_id=th.camera_id,
            source_type=EvidenceSourceType.THERMAL_CAMERA,
            evidence_type="thermal_hotspot_radiometric",
            observation_timestamp=src_ts,
            ingestion_timestamp=now_utc,
            raw_value=round(th.max_temperature, 1),
            unit="°C",
            normalized_score=round(norm_score, 3),
            quality=th.quality_status.value,
            freshness_status=freshness,
            freshness_age_sec=round(age_sec, 1),
            reliability_score=self.SOURCE_RELIABILITIES[EvidenceSourceType.THERMAL_CAMERA],
            confidence=0.94,
            support_state=support,
            is_live_data=th.is_live_data,
            is_simulated=True,
            evidence_uri=th.evidence_uri,
            metadata={"hotspots": th.hotspot_count, "p95": th.percentile_95_temperature}
        )

    def normalize_cctv(self, cctv: CCTVFrameEvidence) -> EvidenceItem:
        now_utc = datetime.now(timezone.utc)
        src_ts = cctv.source_timestamp
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)

        age_sec = max(0.0, (now_utc - src_ts).total_seconds())
        norm_score = max(cctv.flame_confidence, cctv.smoke_confidence)
        support = EvidenceSupportState.SUPPORTING if norm_score > 0.50 else EvidenceSupportState.CONTRADICTING

        return EvidenceItem(
            evidence_id=f"EV-CCTV-{uuid.uuid4().hex[:6].upper()}",
            facility_id=cctv.facility_id,
            asset_id=cctv.asset_id,
            zone_id=cctv.zone_id,
            source_id=cctv.camera_id,
            source_type=EvidenceSourceType.CCTV,
            evidence_type="optical_flame_smoke_cctv",
            observation_timestamp=src_ts,
            ingestion_timestamp=now_utc,
            raw_value=round(norm_score * 100.0, 1),
            unit="%",
            normalized_score=round(norm_score, 3),
            quality=cctv.quality_status.value,
            freshness_status="LIVE" if age_sec < 10.0 else "STALE",
            freshness_age_sec=round(age_sec, 1),
            reliability_score=self.SOURCE_RELIABILITIES[EvidenceSourceType.CCTV],
            confidence=norm_score,
            support_state=support,
            is_live_data=cctv.is_live_data,
            is_simulated=True,
            metadata={"scene_status": cctv.scene_status}
        )

    def normalize_prediction(self, pred: HazardPrediction) -> EvidenceItem:
        now_utc = datetime.now(timezone.utc)
        norm_score = pred.escalation_probability
        support = EvidenceSupportState.SUPPORTING if norm_score > 0.40 else EvidenceSupportState.CONTRADICTING

        return EvidenceItem(
            evidence_id=f"EV-PRED-{uuid.uuid4().hex[:6].upper()}",
            facility_id=pred.facility_id,
            asset_id=pred.asset_id,
            zone_id=pred.zone_id,
            source_id=pred.prediction_id,
            source_type=EvidenceSourceType.PREDICTION,
            evidence_type="hazard_trajectory_prediction",
            observation_timestamp=pred.created_at,
            ingestion_timestamp=now_utc,
            raw_value=round(pred.escalation_probability * 100.0, 1),
            unit="%",
            normalized_score=round(norm_score, 3),
            quality="GOOD" if pred.uncertainty_state.value == "CONFIRMED" else "DEGRADED",
            freshness_status="LIVE",
            freshness_age_sec=0.0,
            reliability_score=self.SOURCE_RELIABILITIES[EvidenceSourceType.PREDICTION],
            confidence=pred.calibrated_confidence,
            support_state=support,
            is_live_data=False,
            is_simulated=True,
            metadata={"trend": pred.trend.value, "hazard_family": pred.hazard_family.value}
        )

    def generate_satellite_evidence(
        self,
        facility_id: str,
        asset_id: str,
        force_anomaly: bool = False,
        force_stale: bool = False
    ) -> EvidenceItem:
        now_utc = datetime.now(timezone.utc)
        obs_time = now_utc - (timedelta(hours=3) if force_stale else timedelta(minutes=15))
        frp_mw = 35.0 if force_anomaly else 0.5
        norm_score = min(1.0, frp_mw / 40.0)
        support = EvidenceSupportState.SUPPORTING if force_anomaly else EvidenceSupportState.CONTRADICTING
        freshness = "STALE" if force_stale else "FRESH"

        return EvidenceItem(
            evidence_id=f"EV-SAT-{uuid.uuid4().hex[:6].upper()}",
            facility_id=facility_id,
            asset_id=asset_id,
            zone_id="Sector D - Cryogenic Yard",
            source_id="NASA-FIRMS-VIIRS-NOAA20",
            source_type=EvidenceSourceType.SATELLITE,
            evidence_type="satellite_thermal_frp",
            observation_timestamp=obs_time,
            ingestion_timestamp=now_utc,
            raw_value=round(frp_mw, 1),
            unit="MW",
            normalized_score=round(norm_score, 3),
            quality="GOOD",
            freshness_status=freshness,
            freshness_age_sec=round((now_utc - obs_time).total_seconds(), 1),
            reliability_score=self.SOURCE_RELIABILITIES[EvidenceSourceType.SATELLITE],
            confidence=0.88,
            support_state=support,
            is_live_data=False,
            is_simulated=True,
            metadata={"satellite": "NOAA-20", "instrument": "VIIRS", "frp": frp_mw}
        )

evidence_normalizer = EvidenceNormalizer()
