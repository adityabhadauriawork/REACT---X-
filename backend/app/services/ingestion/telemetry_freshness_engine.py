from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.schemas.telemetry import FreshnessStatus, SensorMetadata

class TelemetryFreshnessEngine:
    """
    Dynamic Multi-Frequency Freshness Engine.
    Evaluates sensor observation age dynamically relative to each sensor's unique
    expected sampling interval (1s, 2s, 5s, 10s, 30s, 60s, or satellite 15m),
    preventing arbitrary global freshness thresholds.
    """

    def compute_freshness(
        self,
        observation_timestamp: datetime,
        expected_sampling_interval_sec: float = 1.0,
        current_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if current_time_utc is None:
            current_time_utc = datetime.now(timezone.utc)
        
        obs_time = observation_timestamp
        if obs_time.tzinfo is None:
            obs_time = obs_time.replace(tzinfo=timezone.utc)

        age_sec = max(0.0, (current_time_utc - obs_time).total_seconds())
        interval = max(0.1, expected_sampling_interval_sec)
        ratio = age_sec / interval

        if ratio < 1.5:
            status = FreshnessStatus.LIVE
        elif ratio < 3.0:
            status = FreshnessStatus.FRESH
        elif ratio < 6.0:
            status = FreshnessStatus.STALE
        elif ratio < 12.0:
            status = FreshnessStatus.DEGRADED
        else:
            status = FreshnessStatus.UNAVAILABLE

        return {
            "freshness_status": status,
            "age_sec": round(age_sec, 2),
            "expected_interval_sec": interval,
            "interval_ratio": round(ratio, 2)
        }

telemetry_freshness_engine = TelemetryFreshnessEngine()
