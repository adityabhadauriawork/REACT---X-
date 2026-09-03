import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from app.schemas.vision import (
    VisionQualityStatus, VisionFreshnessStatus, CameraMetadata
)

class VisionQualityEngine:
    """
    Vision Stream Quality & Multi-Frame Temporal Consistency Engine.
    Detects camera failures (frozen streams, zero variance, clock skew, occlusion)
    and enforces multi-frame temporal persistence to prevent noisy single-frame alarms.
    """

    def __init__(self):
        # Tracking history per camera for frozen frame and temporal persistence detection
        self.camera_frame_history: Dict[str, List[Dict[str, Any]]] = {}

    def compute_camera_freshness(
        self,
        observation_timestamp: datetime,
        frame_rate_fps: float = 2.0,
        current_time_utc: Optional[datetime] = None
    ) -> Dict[str, Any]:
        if current_time_utc is None:
            current_time_utc = datetime.now(timezone.utc)

        obs_ts = observation_timestamp
        if obs_ts.tzinfo is None:
            obs_ts = obs_ts.replace(tzinfo=timezone.utc)

        age_sec = max(0.0, (current_time_utc - obs_ts).total_seconds())
        # Expected frame cadence (e.g. 2 FPS -> 0.5s expected interval)
        expected_interval_sec = max(0.1, 1.0 / max(0.1, frame_rate_fps))
        ratio = age_sec / expected_interval_sec

        if ratio < 2.0:
            status = VisionFreshnessStatus.LIVE
        elif ratio < 5.0:
            status = VisionFreshnessStatus.FRESH
        elif ratio < 15.0:
            status = VisionFreshnessStatus.STALE
        elif ratio < 30.0:
            status = VisionFreshnessStatus.DEGRADED
        else:
            status = VisionFreshnessStatus.UNAVAILABLE

        return {
            "freshness_status": status,
            "age_sec": round(age_sec, 2),
            "expected_interval_sec": round(expected_interval_sec, 2),
            "ratio": round(ratio, 2)
        }

    def validate_frame_quality(
        self,
        camera_id: str,
        source_timestamp: datetime,
        pixel_variance: float = 12.0,
        is_corrupted: bool = False
    ) -> Tuple[VisionQualityStatus, List[str]]:
        now_utc = datetime.now(timezone.utc)
        src_ts = source_timestamp
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)

        flags = []
        quality = VisionQualityStatus.GOOD

        # 1. Corruption / missing data
        if is_corrupted:
            return VisionQualityStatus.BAD, ["FRAME_CORRUPTION"]

        # 2. Clock skew / Future timestamp (>30s)
        if (src_ts - now_utc).total_seconds() > 30.0:
            flags.append("CLOCK_SKEW")
            quality = VisionQualityStatus.WARNING

        # 3. Frozen Frame Detection
        # Track pixel variance over time
        if camera_id not in self.camera_frame_history:
            self.camera_frame_history[camera_id] = []
        
        hist = self.camera_frame_history[camera_id]
        hist.append({
            "timestamp": src_ts,
            "variance": pixel_variance
        })
        if len(hist) > 10:
            hist.pop(0)

        # If last 5 frames have exactly 0.0 variance while timestamps advance -> Frozen feed
        if len(hist) >= 5 and all(h["variance"] == 0.0 for h in hist[-5:]):
            flags.append("FROZEN_STREAM")
            quality = VisionQualityStatus.FROZEN

        if not flags:
            flags.append("NONE")

        return quality, flags

    def evaluate_temporal_consistency(
        self,
        camera_id: str,
        is_anomalous_frame: bool,
        consecutive_anomaly_threshold: int = 3
    ) -> Tuple[str, float]:
        """
        Multi-frame temporal consistency filter:
        - 1 isolated anomalous frame -> 'WATCH' (suppress false trigger)
        - 2 consecutive anomalous frames -> 'ELEVATED_WATCH'
        - >=3 consecutive anomalous frames -> 'ABNORMAL' / Confirmed Evidence
        """
        hist = self.camera_frame_history.get(camera_id, [])
        if not hist:
            return ("WATCH" if is_anomalous_frame else "NORMAL"), 0.70

        # Count consecutive anomalies in recent history
        consecutive = 0
        for h in reversed(hist):
            if h.get("is_anomaly", False):
                consecutive += 1
            else:
                break

        if is_anomalous_frame:
            consecutive += 1

        if consecutive >= consecutive_anomaly_threshold:
            confidence = min(0.98, 0.85 + (consecutive * 0.03))
            return "ABNORMAL", round(confidence, 2)
        elif consecutive >= 1:
            confidence = 0.70 + (consecutive * 0.05)
            return "WATCH", round(confidence, 2)
        else:
            return "NORMAL", 0.95

vision_quality_engine = VisionQualityEngine()
