import math
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session


from app.models.thermal_event import ThermalEventModel
from app.models.thermal_source import ThermalSourceModel, ThermalSourceEventModel
from app.services.satellite.spatial_index import spatial_index

class SpatiotemporalClusteringEngine:
    """
    Spatiotemporal Clustering Engine for SIH26162.
    Groups discrete spaceborne thermal detections (NASA FIRMS VIIRS/MODIS) into
    first-class persistent, recurring, or active ThermalSourceObjects.
    
    Uses Uber H3 resolution 7 indexing for fast spatial candidate narrowing,
    followed by precise Haversine distance verification and temporal characterization.
    """

    def __init__(
        self,
        spatial_threshold_m: float = 750.0,
        h3_search_ring_k: int = 1,
        inactivity_threshold_days: int = 90
    ):
        self.spatial_threshold_m = spatial_threshold_m
        self.h3_search_ring_k = h3_search_ring_k
        self.inactivity_threshold_days = inactivity_threshold_days

    def haversine_distance_m(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates great-circle distance between two WGS84 coordinates in meters."""
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)

        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def get_candidate_h3_indices(self, lat: float, lon: float) -> Set[str]:
        """Returns the primary H3 Res 7 index plus its 1-ring neighbors."""
        center_h3 = spatial_index.lat_lng_to_h3(lat, lon)
        ring_cells = spatial_index.k_ring(center_h3, k=self.h3_search_ring_k)
        return set(ring_cells)

    def attach_or_create_source(
        self,
        event: ThermalEventModel,
        db: Session
    ) -> Tuple[ThermalSourceModel, bool]:
        """
        Incremental online clustering:
        1. Queries candidate ThermalSourceObjects within the H3 1-ring neighborhood.
        2. Checks exact spatial distance (d <= spatial_threshold_m).
        3. If candidate found, attaches observation and re-computes centroid & descriptive statistics.
        4. If no candidate found, instantiates a new ThermalSourceObject.
        """
        candidate_h3s = self.get_candidate_h3_indices(event.latitude, event.longitude)
        
        # Query active sources in H3 neighborhood
        candidates = db.query(ThermalSourceModel).filter(
            ThermalSourceModel.h3_index.in_(list(candidate_h3s))
        ).all()

        best_source = None
        min_distance = float('inf')

        for source in candidates:
            dist = self.haversine_distance_m(
                event.latitude, event.longitude,
                source.centroid_lat, source.centroid_lon
            )
            if dist <= self.spatial_threshold_m and dist < min_distance:
                min_distance = dist
                best_source = source

        if best_source:
            # Attach observation to existing source
            self._update_existing_source(best_source, event, db)
            return best_source, False
        else:
            # Instantiate new ThermalSourceObject
            new_source = self._create_new_source(event, db)
            return new_source, True

    def _create_new_source(
        self,
        event: ThermalEventModel,
        db: Session
    ) -> ThermalSourceModel:
        """Instantiates a new ThermalSourceObject from a solitary observation."""
        h3_idx = spatial_index.lat_lng_to_h3(event.latitude, event.longitude)
        now = datetime.utcnow()
        acq_time = event.acquisition_timestamp
        if hasattr(acq_time, "tzinfo") and acq_time.tzinfo is not None:
            acq_time = acq_time.replace(tzinfo=None)

        source_id = f"SRC-{h3_idx[-7:]}-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

        new_source = ThermalSourceModel(
            source_id=source_id,
            name=f"Thermal Source {h3_idx}",
            centroid_lat=event.latitude,
            centroid_lon=event.longitude,
            h3_index=h3_idx,
            bounding_box=[event.longitude - 0.005, event.latitude - 0.005, event.longitude + 0.005, event.latitude + 0.005],
            first_detected=acq_time,
            last_detected=acq_time,
            active_days_count=1,
            observation_count=1,
            unique_satellite_count=1,
            unique_sensor_count=1,
            satellites_seen=[event.source_satellite],
            sensors_seen=[event.sensor_name],
            mean_frp_mw=event.frp_mw,
            max_frp_mw=event.frp_mw,
            min_frp_mw=event.frp_mw,
            mean_brightness_temp_k=event.brightness_temp_k,
            max_brightness_temp_k=event.brightness_temp_k,
            day_detection_count=1 if event.day_night == 'D' else 0,
            night_detection_count=1 if event.day_night == 'N' else 0,
            diurnal_ratio=1.0,
            source_status="NEW_SOURCE",
            source_confidence=event.confidence or "NOMINAL",
            source_provenance="LIVE_FIRMS" if event.is_live_data else "BENCHMARK",
            created_at=now,
            updated_at=now
        )
        db.add(new_source)
        db.flush()

        # Add event attachment record
        source_event = ThermalSourceEventModel(
            source_id=new_source.source_id,
            event_id=event.event_id,
            acquisition_timestamp=acq_time,
            latitude=event.latitude,
            longitude=event.longitude,
            frp_mw=event.frp_mw,
            brightness_temp_k=event.brightness_temp_k,
            satellite=event.source_satellite,
            sensor=event.sensor_name,
            day_night=event.day_night,
            attached_at=now
        )
        db.add(source_event)
        return new_source

    def _update_existing_source(
        self,
        source: ThermalSourceModel,
        event: ThermalEventModel,
        db: Session
    ):
        """Attaches an observation, updates centroid, and re-computes descriptive statistics incrementally in O(1)."""
        now = datetime.utcnow()
        acq_time = event.acquisition_timestamp
        if hasattr(acq_time, "tzinfo") and acq_time.tzinfo is not None:
            acq_time = acq_time.replace(tzinfo=None)

        # Add junction record
        source_event = ThermalSourceEventModel(
            source_id=source.source_id,
            event_id=event.event_id,
            acquisition_timestamp=acq_time,
            latitude=event.latitude,
            longitude=event.longitude,
            frp_mw=event.frp_mw,
            brightness_temp_k=event.brightness_temp_k,
            satellite=event.source_satellite,
            sensor=event.sensor_name,
            day_night=event.day_night,
            attached_at=now
        )
        db.add(source_event)

        # Incremental descriptive statistics update
        old_n = source.observation_count or 1
        new_n = old_n + 1
        source.observation_count = new_n

        source.centroid_lat = round((source.centroid_lat * old_n + event.latitude) / new_n, 6)
        source.centroid_lon = round((source.centroid_lon * old_n + event.longitude) / new_n, 6)
        
        # Bounding box update
        if source.bounding_box and len(source.bounding_box) == 4:
            min_lon, min_lat, max_lon, max_lat = source.bounding_box
            source.bounding_box = [
                min(min_lon, event.longitude - 0.002),
                min(min_lat, event.latitude - 0.002),
                max(max_lon, event.longitude + 0.002),
                max(max_lat, event.latitude + 0.002)
            ]

        source.mean_frp_mw = round((source.mean_frp_mw * old_n + event.frp_mw) / new_n, 2)
        source.max_frp_mw = max(source.max_frp_mw, event.frp_mw)
        source.min_frp_mw = min(source.min_frp_mw, event.frp_mw)

        if event.brightness_temp_k is not None:
            if source.mean_brightness_temp_k is not None:
                source.mean_brightness_temp_k = round((source.mean_brightness_temp_k * old_n + event.brightness_temp_k) / new_n, 1)
                source.max_brightness_temp_k = max(source.max_brightness_temp_k, event.brightness_temp_k)
            else:
                source.mean_brightness_temp_k = event.brightness_temp_k
                source.max_brightness_temp_k = event.brightness_temp_k

        first_dt = source.first_detected.replace(tzinfo=None) if hasattr(source.first_detected, "tzinfo") and source.first_detected.tzinfo is not None else source.first_detected
        last_dt = source.last_detected.replace(tzinfo=None) if hasattr(source.last_detected, "tzinfo") and source.last_detected.tzinfo is not None else source.last_detected

        source.first_detected = min(first_dt, acq_time)
        source.last_detected = max(last_dt, acq_time)

        # Satellites & Sensors Tracking
        sats = set(source.satellites_seen or [])
        sats.add(event.source_satellite)
        source.satellites_seen = list(sats)
        source.unique_satellite_count = len(sats)

        sensors = set(source.sensors_seen or [])
        sensors.add(event.sensor_name)
        source.sensors_seen = list(sensors)
        source.unique_sensor_count = len(sensors)

        # Day/Night counts
        if event.day_night == 'D':
            source.day_detection_count = (source.day_detection_count or 0) + 1
        elif event.day_night == 'N':
            source.night_detection_count = (source.night_detection_count or 0) + 1

        day_c = source.day_detection_count or 0
        night_c = source.night_detection_count or 0
        source.diurnal_ratio = round((day_c + 0.1) / (night_c + 0.1), 2)

        # Active days calculation
        days_span = max(1, int((source.last_detected - source.first_detected).total_seconds() / 86400.0) + 1)
        source.active_days_count = min(new_n, days_span)

        # Lifecycle state
        days_since_last = (now - source.last_detected).total_seconds() / 86400.0
        if days_since_last > self.inactivity_threshold_days:
            source.source_status = "INACTIVE_SOURCE"
        elif new_n >= 10 and source.active_days_count >= 5:
            source.source_status = "PERSISTENT_SOURCE"
        elif new_n >= 3 and source.active_days_count >= 2:
            source.source_status = "RECURRING_SOURCE"
        else:
            source.source_status = "NEW_SOURCE"

        source.updated_at = now

    def run_batch_clustering(
        self,
        db: Session,
        events: Optional[List[ThermalEventModel]] = None
    ) -> Dict[str, Any]:
        """
        Executes batch clustering on all unclustered thermal events in the database.
        """
        start_time = time.time()
        if events is None:
            events = db.query(ThermalEventModel).order_by(ThermalEventModel.acquisition_timestamp.asc()).all()

        created_count = 0
        updated_count = 0

        for ev in events:
            _, is_new = self.attach_or_create_source(ev, db)
            if is_new:
                created_count += 1
            else:
                updated_count += 1

        db.commit()
        duration_ms = (time.time() - start_time) * 1000.0

        active_sources = db.query(ThermalSourceModel).count()
        status_dist = {}
        for s in db.query(ThermalSourceModel).all():
            status_dist[s.source_status] = status_dist.get(s.source_status, 0) + 1

        return {
            "total_events_evaluated": len(events),
            "sources_created": created_count,
            "sources_updated": updated_count,
            "total_active_sources": active_sources,
            "clustering_duration_ms": round(duration_ms, 2),
            "sources_by_status": status_dist
        }

clustering_engine = SpatiotemporalClusteringEngine()
