import time
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone

from app.schemas.adaptive import MonitoringLevel

class StateHysteresisController:
    """
    Prevents rapid level oscillation / flapping during transient signal fluctuations.
    Enforces immediate upward escalation and disciplined cooldown dwell times for downward transitions.
    """

    COOLDOWN_DURATIONS_SEC = {
        MonitoringLevel.LEVEL_5_INCIDENT: 120.0,
        MonitoringLevel.LEVEL_4_CRITICAL: 60.0,
        MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING: 45.0,
        MonitoringLevel.LEVEL_2_ABNORMAL: 30.0,
        MonitoringLevel.LEVEL_1_WATCH: 15.0,
        MonitoringLevel.LEVEL_0_BASELINE: 0.0
    }

    LEVEL_RANKS = {
        MonitoringLevel.LEVEL_0_BASELINE: 0,
        MonitoringLevel.LEVEL_1_WATCH: 1,
        MonitoringLevel.LEVEL_2_ABNORMAL: 2,
        MonitoringLevel.LEVEL_3_HAZARD_DEVELOPING: 3,
        MonitoringLevel.LEVEL_4_CRITICAL: 4,
        MonitoringLevel.LEVEL_5_INCIDENT: 5
    }

    def __init__(self):
        # In-memory tracking per facility: {facility_id: {"level": MonitoringLevel, "timestamp": float, "peak_level": MonitoringLevel, "cooldown_until": float}}
        self._facility_states: Dict[str, Dict[str, Any]] = {}

    def process_level_transition(
        self,
        facility_id: str,
        target_level: MonitoringLevel,
        force_instant: bool = False
    ) -> Tuple[MonitoringLevel, MonitoringLevel, bool, float]:
        """
        Calculates the effective monitoring level after applying upward-instant and downward-cooldown rules.
        Returns: (effective_level, previous_level, is_in_cooldown, cooldown_remaining_sec)
        """
        now = time.time()
        curr_rec = self._facility_states.get(facility_id)

        if not curr_rec:
            # Initial state
            self._facility_states[facility_id] = {
                "level": target_level,
                "timestamp": now,
                "peak_level": target_level,
                "cooldown_until": now + self.COOLDOWN_DURATIONS_SEC.get(target_level, 0.0)
            }
            return target_level, MonitoringLevel.LEVEL_0_BASELINE, False, 0.0

        prev_level = curr_rec["level"]
        prev_rank = self.LEVEL_RANKS[prev_level]
        target_rank = self.LEVEL_RANKS[target_level]

        # Case 1: Upward Escalation (Immediate — zero delay)
        if target_rank > prev_rank:
            curr_rec["level"] = target_level
            curr_rec["timestamp"] = now
            curr_rec["peak_level"] = target_level
            curr_rec["cooldown_until"] = now + self.COOLDOWN_DURATIONS_SEC.get(target_level, 0.0)
            return target_level, prev_level, False, 0.0

        # Case 2: Steady State
        if target_rank == prev_rank:
            return target_level, prev_level, False, 0.0

        # Case 3: Downward Transition (Subject to Cooldown Dwell Time)
        if force_instant:
            curr_rec["level"] = target_level
            curr_rec["timestamp"] = now
            curr_rec["cooldown_until"] = now
            return target_level, prev_level, False, 0.0

        cooldown_until = curr_rec.get("cooldown_until", 0.0)
        remaining = max(0.0, cooldown_until - now)

        if remaining > 0.0:
            # Cooldown active: Hold current level to prevent flapping
            return prev_level, prev_level, True, round(remaining, 1)

        # Cooldown expired: Step down smoothly
        # For safety, step down at most 1 level per evaluation cycle rather than jumping Critical -> Baseline
        step_down_rank = max(target_rank, prev_rank - 1)
        step_down_level = next(k for k, v in self.LEVEL_RANKS.items() if v == step_down_rank)

        curr_rec["level"] = step_down_level
        curr_rec["timestamp"] = now
        curr_rec["cooldown_until"] = now + self.COOLDOWN_DURATIONS_SEC.get(step_down_level, 0.0)

        return step_down_level, prev_level, False, 0.0

    def reset_facility(self, facility_id: str):
        if facility_id in self._facility_states:
            del self._facility_states[facility_id]

hysteresis_controller = StateHysteresisController()
