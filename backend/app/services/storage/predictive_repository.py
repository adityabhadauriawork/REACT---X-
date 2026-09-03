import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.predictive_models import HazardPredictionRecord
from app.schemas.predictive import (
    HazardPrediction, HazardState, HazardFamily, TrendDirection,
    ForecastHorizon, UncertaintyState, FeatureContribution
)

class PredictiveRepository:
    """
    DAO repository for short-horizon hazard prediction events and time-series history.
    """

    def persist_prediction(self, db: Session, pred: HazardPrediction) -> HazardPredictionRecord:
        rec = HazardPredictionRecord(
            prediction_id=pred.prediction_id or f"PRED-{uuid.uuid4().hex[:10].upper()}",
            facility_id=pred.facility_id,
            asset_id=pred.asset_id,
            zone_id=pred.zone_id,
            hazard_family=pred.hazard_family.value if hasattr(pred.hazard_family, "value") else str(pred.hazard_family),
            created_at=pred.created_at,
            observation_window_start=pred.observation_window_start,
            observation_window_end=pred.observation_window_end,
            forecast_horizon=pred.forecast_horizon.value if hasattr(pred.forecast_horizon, "value") else str(pred.forecast_horizon),
            current_state=pred.current_state.value if hasattr(pred.current_state, "value") else str(pred.current_state),
            predicted_state=pred.predicted_state.value if hasattr(pred.predicted_state, "value") else str(pred.predicted_state),
            trend=pred.trend.value if hasattr(pred.trend, "value") else str(pred.trend),
            escalation_probability=pred.escalation_probability,
            calibrated_confidence=pred.calibrated_confidence,
            uncertainty_state=pred.uncertainty_state.value if hasattr(pred.uncertainty_state, "value") else str(pred.uncertainty_state),
            anomaly_score=pred.anomaly_score,
            change_point_detected=pred.change_point_detected,
            change_point_strength=pred.change_point_strength,
            recommended_monitoring_level=pred.recommended_monitoring_level,
            recommendation_reason=pred.recommendation_reason,
            data_sufficiency=pred.data_sufficiency,
            telemetry_freshness=pred.telemetry_freshness,
            thermal_vision_available=pred.thermal_vision_available,
            is_simulated_pipeline=pred.is_simulated_pipeline,
            model_version=pred.model_version,
            baseline_version=pred.baseline_version,
            top_contributing_features_json=[f.model_dump() for f in pred.top_contributing_features],
            raw_metrics_json={}
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    def get_latest_prediction(self, db: Session, facility_id: str, asset_id: Optional[str] = None) -> Optional[HazardPrediction]:
        q = db.query(HazardPredictionRecord).filter(HazardPredictionRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(HazardPredictionRecord.asset_id == asset_id)
        rec = q.order_by(desc(HazardPredictionRecord.created_at)).first()
        if not rec:
            return None
        return self._record_to_schema(rec)

    def query_history(
        self,
        db: Session,
        facility_id: str,
        asset_id: Optional[str] = None,
        hazard_family: Optional[str] = None,
        limit: int = 50
    ) -> List[HazardPrediction]:
        q = db.query(HazardPredictionRecord).filter(HazardPredictionRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(HazardPredictionRecord.asset_id == asset_id)
        if hazard_family:
            q = q.filter(HazardPredictionRecord.hazard_family == hazard_family)
        records = q.order_by(desc(HazardPredictionRecord.created_at)).limit(limit).all()
        return [self._record_to_schema(r) for r in records]

    def _record_to_schema(self, rec: HazardPredictionRecord) -> HazardPrediction:
        features = []
        if rec.top_contributing_features_json:
            for f in rec.top_contributing_features_json:
                features.append(FeatureContribution(**f))

        return HazardPrediction(
            prediction_id=rec.prediction_id,
            facility_id=rec.facility_id,
            asset_id=rec.asset_id,
            zone_id=rec.zone_id,
            hazard_family=HazardFamily(rec.hazard_family) if rec.hazard_family in HazardFamily.__members__ else HazardFamily.THERMAL_ESCALATION,
            created_at=rec.created_at.replace(tzinfo=timezone.utc) if rec.created_at.tzinfo is None else rec.created_at,
            observation_window_start=rec.observation_window_start.replace(tzinfo=timezone.utc) if rec.observation_window_start.tzinfo is None else rec.observation_window_start,
            observation_window_end=rec.observation_window_end.replace(tzinfo=timezone.utc) if rec.observation_window_end.tzinfo is None else rec.observation_window_end,
            forecast_horizon=ForecastHorizon(rec.forecast_horizon) if rec.forecast_horizon in ForecastHorizon.__members__ else ForecastHorizon.HORIZON_10M,
            current_state=HazardState(rec.current_state) if rec.current_state in HazardState.__members__ else HazardState.NORMAL,
            predicted_state=HazardState(rec.predicted_state) if rec.predicted_state in HazardState.__members__ else HazardState.WATCH,
            trend=TrendDirection(rec.trend) if rec.trend in TrendDirection.__members__ else TrendDirection.STABLE,
            escalation_probability=rec.escalation_probability,
            calibrated_confidence=rec.calibrated_confidence,
            uncertainty_state=UncertaintyState(rec.uncertainty_state) if rec.uncertainty_state in UncertaintyState.__members__ else UncertaintyState.CONFIRMED,
            top_contributing_features=features,
            anomaly_score=rec.anomaly_score,
            change_point_detected=rec.change_point_detected,
            change_point_strength=rec.change_point_strength,
            recommended_monitoring_level=rec.recommended_monitoring_level,
            recommendation_reason=rec.recommendation_reason or "",
            data_sufficiency=rec.data_sufficiency,
            telemetry_freshness=rec.telemetry_freshness,
            thermal_vision_available=rec.thermal_vision_available,
            is_simulated_pipeline=rec.is_simulated_pipeline,
            model_version=rec.model_version,
            baseline_version=rec.baseline_version
        )

predictive_repository = PredictiveRepository()
