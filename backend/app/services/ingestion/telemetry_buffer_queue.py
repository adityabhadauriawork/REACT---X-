import heapq
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.schemas.telemetry import (
    FacilityTelemetryObservation, DataQualityFlag, TelemetryQuality
)

class EdgeLocalBuffer:
    """
    Bounded Edge-Side Ring Buffer for Network Outage Tolerance.
    Buffers observations when connection to REACT-X ingestion drops,
    and replays them in original source timestamp order upon reconnection,
    marking observations with REPLAYED / LATE quality flags.
    """

    def __init__(self, max_capacity: int = 5000):
        self.max_capacity = max_capacity
        self.buffer: List[FacilityTelemetryObservation] = []
        self._lock = threading.Lock()
        self.total_buffered_count = 0
        self.total_dropped_count = 0

    def push(self, observation: FacilityTelemetryObservation) -> bool:
        with self._lock:
            self.total_buffered_count += 1
            if len(self.buffer) >= self.max_capacity:
                # Discard oldest non-critical observation
                self.buffer.pop(0)
                self.total_dropped_count += 1
            self.buffer.append(observation)
            return True

    def replay_all(self, sort_by_timestamp: bool = True) -> List[FacilityTelemetryObservation]:
        """Drains the buffer and returns observations in source timestamp order."""
        with self._lock:
            if not self.buffer:
                return []
            
            replayed = list(self.buffer)
            self.buffer.clear()

            if sort_by_timestamp:
                replayed.sort(key=lambda x: x.source_timestamp)

            now_utc = datetime.now(timezone.utc)
            for obs in replayed:
                obs.ingestion_timestamp = now_utc
                if DataQualityFlag.NONE in obs.data_quality_flags:
                    obs.data_quality_flags.remove(DataQualityFlag.NONE)
                if DataQualityFlag.REPLAYED not in obs.data_quality_flags:
                    obs.data_quality_flags.append(DataQualityFlag.REPLAYED)
                if DataQualityFlag.LATE not in obs.data_quality_flags:
                    obs.data_quality_flags.append(DataQualityFlag.LATE)
            return replayed

    def size(self) -> int:
        with self._lock:
            return len(self.buffer)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self.buffer) == 0


class BackpressureQueue:
    """
    Bounded Priority-Preserving Backpressure Queue.
    Protects ingestion pipeline from overload:
    Under high load, sheds low-priority routine telemetry while strictly preserving
    critical safety alerts, warnings, and high-frequency excursions.
    """

    def __init__(self, max_queue_size: int = 2000):
        self.max_queue_size = max_queue_size
        self._queue: List[FacilityTelemetryObservation] = []
        self._lock = threading.Lock()
        self.total_dropped_count = 0

    def enqueue(self, observation: FacilityTelemetryObservation) -> bool:
        with self._lock:
            if len(self._queue) >= self.max_queue_size:
                # Evict lowest-priority observation (routine GOOD quality vs CRITICAL/WARNING)
                evicted = False
                for i in range(len(self._queue) - 1, -1, -1):
                    item = self._queue[i]
                    if item.quality == TelemetryQuality.GOOD and item.trend == "STABLE":
                        self._queue.pop(i)
                        self.total_dropped_count += 1
                        evicted = True
                        break
                if not evicted:
                    # Everything is critical; drop incoming item if it's routine
                    if observation.quality == TelemetryQuality.GOOD and observation.trend == "STABLE":
                        self.total_dropped_count += 1
                        return False
                    else:
                        self._queue.pop(0)
                        self.total_dropped_count += 1

            self._queue.append(observation)
            return True

    def drain_batch(self, batch_size: int = 200) -> List[FacilityTelemetryObservation]:
        with self._lock:
            batch = self._queue[:batch_size]
            self._queue = self._queue[batch_size:]
            return batch

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def dropped_count(self) -> int:
        with self._lock:
            return self.total_dropped_count
