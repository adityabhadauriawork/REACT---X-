import threading
from collections import deque
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from app.schemas.canonical import CanonicalEvent

class RollingBuffer:
    """
    High-performance in-memory circular window buffer:
    Maintains rolling telemetry windows (default 120 observations) per signal.
    Allows extracting exact pre-event, event, and post-event excursion windows for forensic/ML analysis.
    """
    def __init__(self, max_points_per_signal: int = 120):
        self.max_points = max_points_per_signal
        self.buffers: Dict[str, deque] = {}
        self.lock = threading.Lock()

    def append(self, event: Any):
        asset_id = getattr(event, "asset_id", "UNKNOWN")
        signal_id = getattr(event, "signal_id", getattr(event, "sensor_id", "UNKNOWN"))
        key = f"{asset_id}::{signal_id}"
        with self.lock:
            if key not in self.buffers:
                self.buffers[key] = deque(maxlen=self.max_points)
            self.buffers[key].append(event)

    def get_recent_points(self, asset_id: str, signal_id: str, count: Optional[int] = None) -> List[CanonicalEvent]:
        key = f"{asset_id}::{signal_id}"
        with self.lock:
            buf = self.buffers.get(key)
            if not buf:
                return []
            if count:
                return list(buf)[-count:]
            return list(buf)

    def get_asset_recent_telemetry(self, asset_id: str) -> Dict[str, List[CanonicalEvent]]:
        prefix = f"{asset_id}::"
        res = {}
        with self.lock:
            for k, buf in self.buffers.items():
                if k.startswith(prefix):
                    sig = k.split("::")[1]
                    res[sig] = list(buf)
        return res

    def extract_event_window(
        self,
        asset_id: str,
        signal_id: str,
        event_time: datetime,
        pre_window_sec: float = 60.0,
        post_window_sec: float = 60.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extracts pre-event window (-pre_window_sec), event window, and post-event window (+post_window_sec).
        """
        key = f"{asset_id}::{signal_id}"
        with self.lock:
            buf = self.buffers.get(key)
            if not buf:
                return {"pre_event": [], "event": [], "post_event": []}
            all_events = list(buf)

        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        pre_cutoff = event_time - timedelta(seconds=pre_window_sec)
        post_cutoff = event_time + timedelta(seconds=post_window_sec)

        pre_list = []
        event_list = []
        post_list = []

        for e in all_events:
            ts = e.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            item = {"timestamp": ts.isoformat(), "value": e.value, "quality": e.quality.value, "sequence": e.sequence}
            if ts < event_time and ts >= pre_cutoff:
                pre_list.append(item)
            elif abs((ts - event_time).total_seconds()) <= 5.0:
                event_list.append(item)
            elif ts > event_time and ts <= post_cutoff:
                post_list.append(item)

        return {
            "pre_event": pre_list,
            "event": event_list,
            "post_event": post_list
        }

rolling_buffer = RollingBuffer()
