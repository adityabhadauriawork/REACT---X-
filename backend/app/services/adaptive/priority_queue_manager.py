import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.schemas.adaptive import (
    NationalPriorityItem, MonitoringLevel, AnalyticalPriority, FacilityCriticalityTier
)

class NationalPriorityQueueManager:
    """
    Manages the national facility surveillance queue using dynamic aging and risk-weighted prioritization.
    Ensures high-risk facilities receive intense compute while guaranteeing baseline coverage and preventing starvation.
    """

    BASE_RISK_SCORES = {
        "INCIDENT": 120.0,
        "CRITICAL": 100.0,
        "HAZARD_DEVELOPING": 75.0,
        "CONFLICTING_EVIDENCE": 60.0,
        "ABNORMAL": 50.0,
        "INSUFFICIENT_EVIDENCE": 45.0,
        "WATCH": 25.0,
        "NORMAL": 5.0,
        "UNAVAILABLE": 0.0
    }

    CRITICALITY_BONUS = {
        FacilityCriticalityTier.TIER_1_CRITICAL: 20.0,
        FacilityCriticalityTier.TIER_2_MAJOR: 10.0,
        FacilityCriticalityTier.TIER_3_STANDARD: 0.0
    }

    AGING_LAMBDA_PTS_PER_SEC = 0.25  # +15 pts per minute of elapsed unobserved time

    def __init__(self):
        # In-memory record of last observation timestamps: {facility_id: float}
        self._last_observation_times: Dict[str, float] = {}

    def update_observation_timestamp(self, facility_id: str, timestamp: Optional[float] = None):
        self._last_observation_times[facility_id] = timestamp or time.time()

    def rank_facilities(
        self,
        facility_snapshots: List[Dict[str, Any]]
    ) -> List[NationalPriorityItem]:
        """
        Ranks a list of facility surveillance snapshots by composite priority score.
        Each snapshot contains: facility_id, facility_name, monitoring_level, hazard_state,
        uncertainty_score, criticality, reason, requested_evidence_count.
        """
        now = time.time()
        scored_items: List[NationalPriorityItem] = []

        for s in facility_snapshots:
            f_id = s["facility_id"]
            state = s.get("hazard_state", "NORMAL")
            crit = s.get("criticality", FacilityCriticalityTier.TIER_1_CRITICAL)
            uncert = s.get("uncertainty_score", 0.05)
            level = s.get("monitoring_level", MonitoringLevel.LEVEL_0_BASELINE)
            name = s.get("facility_name", f_id)
            reason = s.get("reason", "Routine baseline surveillance.")
            req_count = s.get("requested_evidence_count", 0)

            last_obs = self._last_observation_times.get(f_id, now - 5.0)
            age_sec = max(0.0, now - last_obs)

            # Compute Composite Priority Score
            base_risk = self.BASE_RISK_SCORES.get(state, 5.0)
            crit_bonus = self.CRITICALITY_BONUS.get(crit, 0.0)
            uncert_bonus = uncert * 30.0
            aging_bonus = age_sec * self.AGING_LAMBDA_PTS_PER_SEC

            total_score = base_risk + crit_bonus + uncert_bonus + aging_bonus

            # Map total score to analytical priority bucket
            if total_score >= 100.0 or state in ["CRITICAL", "INCIDENT"]:
                priority = AnalyticalPriority.URGENT
            elif total_score >= 65.0 or state == "HAZARD_DEVELOPING":
                priority = AnalyticalPriority.HIGH
            elif total_score >= 35.0 or state in ["ABNORMAL", "WATCH", "CONFLICTING_EVIDENCE"]:
                priority = AnalyticalPriority.MEDIUM
            else:
                priority = AnalyticalPriority.LOW

            freshness = "LIVE" if age_sec < 15.0 else ("FRESH" if age_sec < 45.0 else "STALE")

            scored_items.append(NationalPriorityItem(
                rank=0, # will be populated after sorting
                facility_id=f_id,
                facility_name=name,
                monitoring_level=level,
                hazard_state=state,
                priority=priority,
                priority_score=round(total_score, 1),
                last_observation_age_sec=round(age_sec, 1),
                freshness_status=freshness,
                primary_reason=reason,
                requested_evidence_count=req_count
            ))

        # Sort descending by priority score
        scored_items.sort(key=lambda x: x.priority_score, reverse=True)

        # Assign 1-indexed ranks
        for idx, item in enumerate(scored_items, start=1):
            item.rank = idx

        return scored_items

priority_queue_manager = NationalPriorityQueueManager()
