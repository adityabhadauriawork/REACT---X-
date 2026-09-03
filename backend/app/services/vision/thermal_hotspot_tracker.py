import math
import uuid
import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.schemas.vision import ThermalHotspot

class TrackedHotspotState:
    def __init__(self, hotspot: ThermalHotspot, first_seen_time: float):
        self.hotspot_id = hotspot.hotspot_id or f"HS-TRK-{uuid.uuid4().hex[:6].upper()}"
        self.camera_id = hotspot.camera_id
        self.zone_id = hotspot.zone_id
        self.asset_id = hotspot.asset_id
        self.centroid_x = hotspot.centroid_x_pct
        self.centroid_y = hotspot.centroid_y_pct
        self.bbox_xywh = hotspot.bbox_xywh
        self.area_pixels = hotspot.area_pixels
        self.area_m2 = hotspot.area_estimated_m2
        self.max_temp = hotspot.max_temperature_c
        self.mean_temp = hotspot.mean_temperature_c
        self.baseline_temp = hotspot.baseline_temp_c
        self.first_seen_time = first_seen_time
        self.last_updated_time = first_seen_time
        self.prev_temp = hotspot.max_temperature_c
        self.prev_area = hotspot.area_pixels
        self.rate_of_rise = 0.0
        self.growth_rate = 0.0
        self.frames_seen = 1

class ThermalHotspotTracker:
    """
    Multi-Frame Spatial Hotspot Tracking Engine.
    Associates heat signatures across sequential frames to track physical persistence,
    spatial growth rate (%/sec), and temperature velocity (dT/dt in °C/min).
    """

    def __init__(self, match_distance_threshold: float = 0.15, stale_timeout_sec: float = 10.0):
        self.match_dist_thresh = match_distance_threshold
        self.stale_timeout_sec = stale_timeout_sec
        self.active_hotspots: Dict[str, TrackedHotspotState] = {}
        self._lock = threading.Lock()

    def update_hotspots(
        self,
        camera_id: str,
        incoming_hotspots: List[ThermalHotspot],
        timestamp: Optional[datetime] = None
    ) -> List[ThermalHotspot]:
        with self._lock:
            now_sec = timestamp.timestamp() if timestamp else datetime.now(timezone.utc).timestamp()
            updated_results: List[ThermalHotspot] = []

            # 1. Clean up stale untracked hotspots for this camera
            to_delete = []
            for h_id, state in self.active_hotspots.items():
                if state.camera_id == camera_id and (now_sec - state.last_updated_time) > self.stale_timeout_sec:
                    to_delete.append(h_id)
            for h_id in to_delete:
                del self.active_hotspots[h_id]

            # 2. Match incoming hotspots to active tracked hotspots by centroid distance
            matched_active_ids = set()

            for inc in incoming_hotspots:
                best_match_id = None
                best_dist = 999.0

                for h_id, state in self.active_hotspots.items():
                    if state.camera_id != camera_id or h_id in matched_active_ids:
                        continue
                    dist = math.hypot(inc.centroid_x_pct - state.centroid_x, inc.centroid_y_pct - state.centroid_y)
                    if dist < self.match_dist_thresh and dist < best_dist:
                        best_dist = dist
                        best_match_id = h_id

                if best_match_id is not None:
                    # Update existing tracked hotspot
                    state = self.active_hotspots[best_match_id]
                    dt = max(0.1, now_sec - state.last_updated_time)
                    
                    # Compute dT/dt and growth rate
                    dT_dt = ((inc.max_temperature_c - state.prev_temp) / dt) * 60.0
                    growth_rate = ((inc.area_pixels - state.prev_area) / max(1, state.prev_area)) / dt * 100.0
                    
                    state.centroid_x = inc.centroid_x_pct
                    state.centroid_y = inc.centroid_y_pct
                    state.bbox_xywh = inc.bbox_xywh
                    state.area_pixels = inc.area_pixels
                    state.area_m2 = inc.area_estimated_m2
                    state.prev_temp = state.max_temp
                    state.prev_area = state.area_pixels
                    state.max_temp = inc.max_temperature_c
                    state.mean_temp = inc.mean_temperature_c
                    state.rate_of_rise = round(dT_dt, 1)
                    state.growth_rate = round(growth_rate, 1)
                    state.last_updated_time = now_sec
                    state.frames_seen += 1
                    persistence = now_sec - state.first_seen_time

                    matched_active_ids.add(best_match_id)

                    sev = "WATCH"
                    if state.max_temp >= 80.0 or dT_dt >= 15.0 or persistence > 30.0:
                        sev = "CRITICAL"
                    elif state.max_temp >= 50.0 or dT_dt >= 5.0 or persistence > 10.0:
                        sev = "ABNORMAL"

                    hs = ThermalHotspot(
                        hotspot_id=state.hotspot_id,
                        camera_id=camera_id,
                        zone_id=state.zone_id,
                        asset_id=state.asset_id,
                        centroid_x_pct=state.centroid_x,
                        centroid_y_pct=state.centroid_y,
                        bbox_xywh=state.bbox_xywh,
                        area_pixels=state.area_pixels,
                        area_estimated_m2=state.area_m2,
                        max_temperature_c=state.max_temp,
                        mean_temperature_c=state.mean_temp,
                        baseline_temp_c=state.baseline_temp,
                        delta_t_baseline_c=round(state.max_temp - state.baseline_temp, 1),
                        rate_of_rise_c_min=state.rate_of_rise,
                        persistence_sec=round(persistence, 1),
                        growth_rate_pct_sec=state.growth_rate,
                        severity=sev
                    )
                    updated_results.append(hs)

                else:
                    # Create new tracked hotspot state
                    new_state = TrackedHotspotState(inc, now_sec)
                    self.active_hotspots[new_state.hotspot_id] = new_state
                    matched_active_ids.add(new_state.hotspot_id)

                    inc_copy = inc.model_copy()
                    inc_copy.hotspot_id = new_state.hotspot_id
                    inc_copy.persistence_sec = 0.5
                    updated_results.append(inc_copy)

            return updated_results

    def get_tracked_count(self) -> int:
        with self._lock:
            return len(self.active_hotspots)

    def clear(self):
        with self._lock:
            self.active_hotspots.clear()

thermal_hotspot_tracker = ThermalHotspotTracker()
