import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.adaptive_models import AdaptiveMonitoringDecisionRecord
from app.schemas.adaptive import (
    AdaptiveMonitoringDecision, MonitoringLevel, AnalyticalPriority,
    FacilityCriticalityTier, ValueOfInformationItem, MonitoringPolicy
)

class AdaptiveRepository:
    """
    DAO repository for adaptive surveillance decisions and operator acknowledgements.
    """

    def persist_decision(self, db: Session, dec: AdaptiveMonitoringDecision) -> AdaptiveMonitoringDecisionRecord:
        rec = AdaptiveMonitoringDecisionRecord(
            decision_id=dec.decision_id or f"ADAPT-{uuid.uuid4().hex[:10].upper()}",
            facility_id=dec.facility_id,
            asset_id=dec.asset_id,
            zone_id=dec.zone_id,
            created_at=dec.created_at,
            expires_at=dec.expires_at,
            monitoring_level=dec.monitoring_level.value if hasattr(dec.monitoring_level, "value") else str(dec.monitoring_level),
            previous_level=dec.previous_level.value if hasattr(dec.previous_level, "value") else str(dec.previous_level),
            hazard_state=dec.hazard_state,
            confidence=dec.confidence,
            uncertainty_score=dec.uncertainty_score,
            conflict_mass_k=dec.conflict_mass_k,
            facility_criticality=dec.facility_criticality.value if hasattr(dec.facility_criticality, "value") else str(dec.facility_criticality),
            priority=dec.priority.value if hasattr(dec.priority, "value") else str(dec.priority),
            priority_score=dec.priority_score,
            reason=dec.reason,
            requested_evidence_json=dec.requested_evidence,
            value_of_information_json=[v.model_dump(mode="json") for v in dec.value_of_information] if dec.value_of_information else [],
            applied_policy_json=dec.applied_policy.model_dump(mode="json") if dec.applied_policy else {},
            is_in_cooldown=dec.is_in_cooldown,
            cooldown_remaining_sec=dec.cooldown_remaining_sec,
            acknowledged=dec.acknowledged,
            acknowledged_by=dec.acknowledged_by,
            acknowledged_at=dec.acknowledged_at,
            is_live_data=dec.is_live_data,
            is_simulated=dec.is_simulated,
            orchestration_version=dec.orchestration_version
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec

    def get_latest_decision(self, db: Session, facility_id: str, asset_id: Optional[str] = None) -> Optional[AdaptiveMonitoringDecision]:
        q = db.query(AdaptiveMonitoringDecisionRecord).filter(AdaptiveMonitoringDecisionRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(AdaptiveMonitoringDecisionRecord.asset_id == asset_id)
        rec = q.order_by(desc(AdaptiveMonitoringDecisionRecord.created_at)).first()
        if not rec:
            return None
        return self._record_to_schema(rec)

    def query_history(
        self,
        db: Session,
        facility_id: str,
        asset_id: Optional[str] = None,
        limit: int = 50
    ) -> List[AdaptiveMonitoringDecision]:
        q = db.query(AdaptiveMonitoringDecisionRecord).filter(AdaptiveMonitoringDecisionRecord.facility_id == facility_id)
        if asset_id:
            q = q.filter(AdaptiveMonitoringDecisionRecord.asset_id == asset_id)
        records = q.order_by(desc(AdaptiveMonitoringDecisionRecord.created_at)).limit(limit).all()
        return [self._record_to_schema(r) for r in records]

    def acknowledge_decision(
        self,
        db: Session,
        facility_id: str,
        operator_name: str,
        notes: Optional[str] = None
    ) -> Optional[AdaptiveMonitoringDecision]:
        rec = db.query(AdaptiveMonitoringDecisionRecord).filter(
            AdaptiveMonitoringDecisionRecord.facility_id == facility_id
        ).order_by(desc(AdaptiveMonitoringDecisionRecord.created_at)).first()
        
        if not rec:
            return None

        rec.acknowledged = True
        rec.acknowledged_by = operator_name
        rec.acknowledged_at = datetime.now(timezone.utc)
        if notes:
            rec.reason = f"{rec.reason} [Acknowledged Note: {notes}]"
        
        db.commit()
        db.refresh(rec)
        return self._record_to_schema(rec)

    def _record_to_schema(self, rec: AdaptiveMonitoringDecisionRecord) -> AdaptiveMonitoringDecision:
        voi_raw = rec.value_of_information_json or []
        policy_raw = rec.applied_policy_json or {}

        voi_list = [ValueOfInformationItem(**v) for v in voi_raw]
        policy = MonitoringPolicy(**policy_raw) if policy_raw else MonitoringPolicy()

        return AdaptiveMonitoringDecision(
            decision_id=rec.decision_id,
            facility_id=rec.facility_id,
            asset_id=rec.asset_id,
            zone_id=rec.zone_id,
            created_at=rec.created_at.replace(tzinfo=timezone.utc) if rec.created_at.tzinfo is None else rec.created_at,
            expires_at=rec.expires_at.replace(tzinfo=timezone.utc) if rec.expires_at.tzinfo is None else rec.expires_at,
            monitoring_level=MonitoringLevel(rec.monitoring_level) if rec.monitoring_level in MonitoringLevel.__members__ else MonitoringLevel.LEVEL_0_BASELINE,
            previous_level=MonitoringLevel(rec.previous_level) if rec.previous_level in MonitoringLevel.__members__ else MonitoringLevel.LEVEL_0_BASELINE,
            hazard_state=rec.hazard_state,
            confidence=rec.confidence,
            uncertainty_score=rec.uncertainty_score,
            conflict_mass_k=rec.conflict_mass_k,
            facility_criticality=FacilityCriticalityTier(rec.facility_criticality) if rec.facility_criticality in FacilityCriticalityTier.__members__ else FacilityCriticalityTier.TIER_1_CRITICAL,
            priority=AnalyticalPriority(rec.priority) if rec.priority in AnalyticalPriority.__members__ else AnalyticalPriority.LOW,
            priority_score=rec.priority_score,
            reason=rec.reason,
            requested_evidence=rec.requested_evidence_json or [],
            value_of_information=voi_list,
            applied_policy=policy,
            is_in_cooldown=rec.is_in_cooldown,
            cooldown_remaining_sec=rec.cooldown_remaining_sec,
            acknowledged=rec.acknowledged,
            acknowledged_by=rec.acknowledged_by,
            acknowledged_at=rec.acknowledged_at.replace(tzinfo=timezone.utc) if rec.acknowledged_at and rec.acknowledged_at.tzinfo is None else rec.acknowledged_at,
            is_live_data=rec.is_live_data,
            is_simulated=rec.is_simulated,
            orchestration_version=rec.orchestration_version
        )

adaptive_repository = AdaptiveRepository()
