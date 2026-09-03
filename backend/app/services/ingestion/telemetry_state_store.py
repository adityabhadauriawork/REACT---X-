import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from app.schemas.telemetry import (
    FacilityTelemetryObservation, FreshnessStatus, SensorMetadata
)
from app.services.ingestion.telemetry_freshness_engine import telemetry_freshness_engine

class TelemetryStateStore:
    """
    Thread-Safe In-Memory Latest-Value State Store.
    Provides sub-millisecond latest-value lookups for all active plant sensors and assets.
    Designed with a decoupled interface enabling drop-in Redis cache backend support.
    """

    def __init__(self):
        self._state_by_sensor: Dict[str, FacilityTelemetryObservation] = {}
        self._sensors_by_facility: Dict[str, List[str]] = {}
        self._sensors_by_asset: Dict[str, List[str]] = {}
        self._sensor_metadata_map: Dict[str, SensorMetadata] = {}
        self._lock = threading.RLock()

    def register_sensor_metadata(self, metadata: SensorMetadata):
        with self._lock:
            self._sensor_metadata_map[metadata.sensor_id] = metadata
            if metadata.facility_id not in self._sensors_by_facility:
                self._sensors_by_facility[metadata.facility_id] = []
            if metadata.sensor_id not in self._sensors_by_facility[metadata.facility_id]:
                self._sensors_by_facility[metadata.facility_id].append(metadata.sensor_id)

            if metadata.asset_id not in self._sensors_by_asset:
                self._sensors_by_asset[metadata.asset_id] = []
            if metadata.sensor_id not in self._sensors_by_asset[metadata.asset_id]:
                self._sensors_by_asset[metadata.asset_id].append(metadata.sensor_id)

    def update_latest_observation(self, observation: FacilityTelemetryObservation):
        with self._lock:
            s_id = observation.sensor_id
            self._state_by_sensor[s_id] = observation
            
            # Ensure facility and asset index mappings exist
            fac_id = observation.facility_id
            if fac_id not in self._sensors_by_facility:
                self._sensors_by_facility[fac_id] = []
            if s_id not in self._sensors_by_facility[fac_id]:
                self._sensors_by_facility[fac_id].append(s_id)

            asset_id = observation.asset_id
            if asset_id not in self._sensors_by_asset:
                self._sensors_by_asset[asset_id] = []
            if s_id not in self._sensors_by_asset[asset_id]:
                self._sensors_by_asset[asset_id].append(s_id)

    def get_latest_for_sensor(self, sensor_id: str) -> Optional[FacilityTelemetryObservation]:
        with self._lock:
            obs = self._state_by_sensor.get(sensor_id)
            if not obs:
                return None
            
            # Recompute dynamic freshness upon retrieval
            meta = self._sensor_metadata_map.get(sensor_id)
            interval = meta.expected_sampling_interval if meta else 1.0
            freshness_res = telemetry_freshness_engine.compute_freshness(obs.timestamp_utc, interval)
            
            # Return fresh copy with updated status and age
            obs_copy = obs.model_copy()
            obs_copy.freshness_status = freshness_res["freshness_status"]
            obs_copy.freshness_age_sec = freshness_res["age_sec"]
            return obs_copy

    def get_latest_for_facility(self, facility_id: str) -> List[FacilityTelemetryObservation]:
        with self._lock:
            sensor_ids = self._sensors_by_facility.get(facility_id, [])
            results = []
            now = datetime.now(timezone.utc)
            for s_id in sensor_ids:
                obs = self._state_by_sensor.get(s_id)
                if obs:
                    meta = self._sensor_metadata_map.get(s_id)
                    interval = meta.expected_sampling_interval if meta else 1.0
                    freshness_res = telemetry_freshness_engine.compute_freshness(obs.timestamp_utc, interval, now)
                    obs_copy = obs.model_copy()
                    obs_copy.freshness_status = freshness_res["freshness_status"]
                    obs_copy.freshness_age_sec = freshness_res["age_sec"]
                    results.append(obs_copy)
            return results

    def get_latest_for_asset(self, asset_id: str) -> List[FacilityTelemetryObservation]:
        with self._lock:
            sensor_ids = self._sensors_by_asset.get(asset_id, [])
            results = []
            for s_id in sensor_ids:
                latest = self.get_latest_for_sensor(s_id)
                if latest:
                    results.append(latest)
            return results

    def clear(self):
        with self._lock:
            self._state_by_sensor.clear()
            self._sensors_by_facility.clear()
            self._sensors_by_asset.clear()
            self._sensor_metadata_map.clear()

telemetry_state_store = TelemetryStateStore()
