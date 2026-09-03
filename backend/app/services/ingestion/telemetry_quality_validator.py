import math
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, TelemetryQuality, DataQualityFlag, SensorType
)

class TelemetryQualityValidator:
    """
    Physical bounds validator, duplicate detector, clock-skew checker,
    and engineering unit normalizer.
    """

    def __init__(self):
        self._last_seen_by_sensor: Dict[str, Dict[str, Any]] = {}

    def normalize_and_validate(
        self,
        observation: FacilityTelemetryObservation,
        metadata: Optional[SensorMetadata] = None
    ) -> FacilityTelemetryObservation:
        now_utc = datetime.now(timezone.utc)
        obs_time = observation.timestamp_utc
        if obs_time.tzinfo is None:
            obs_time = obs_time.replace(tzinfo=timezone.utc)
            observation.timestamp_utc = obs_time

        flags: List[DataQualityFlag] = []

        # 1. NaN / Infinity check
        if math.isnan(observation.value) or math.isinf(observation.value):
            observation.quality = TelemetryQuality.BAD
            observation.data_quality_status = "REJECTED"
            observation.data_quality_flags = [DataQualityFlag.SENSOR_FAULT]
            return observation

        # 2. Clock Skew / Future Timestamp check (>30 seconds into future)
        time_delta_sec = (obs_time - now_utc).total_seconds()
        if time_delta_sec > 30.0:
            observation.quality = TelemetryQuality.WARNING
            flags.append(DataQualityFlag.CLOCK_SKEW)

        # 3. Duplicate and Out-of-Order sequence detection
        prev_state = self._last_seen_by_sensor.get(observation.sensor_id)
        if prev_state:
            prev_seq = prev_state.get("sequence_number", 0)
            prev_ts = prev_state.get("timestamp_utc", obs_time)
            
            # Duplicate sequence
            if observation.sequence_number > 0 and observation.sequence_number == prev_seq:
                flags.append(DataQualityFlag.DUPLICATE)
                observation.quality = TelemetryQuality.WARNING
            
            # Out-of-order arrival (older than previous reading)
            if obs_time < prev_ts:
                flags.append(DataQualityFlag.LATE)

        # 4. Hardware and Physical Bounds Check
        if metadata:
            val = observation.value
            # Out of physical hardware measurement limits
            if val < metadata.valid_range_min or val > metadata.valid_range_max:
                observation.quality = TelemetryQuality.BAD
                flags.append(DataQualityFlag.OUT_OF_RANGE)
            # Alarm range evaluation
            elif metadata.critical_max and val >= metadata.critical_max:
                if observation.quality != TelemetryQuality.BAD:
                    observation.quality = TelemetryQuality.WARNING
            elif metadata.critical_min and val <= metadata.critical_min:
                if observation.quality != TelemetryQuality.BAD:
                    observation.quality = TelemetryQuality.WARNING

        if not flags:
            flags.append(DataQualityFlag.NONE)

        observation.data_quality_flags = flags
        observation.data_quality_status = "VALID" if observation.quality == TelemetryQuality.GOOD else "ANOMALOUS"

        # Update last seen tracking
        self._last_seen_by_sensor[observation.sensor_id] = {
            "sequence_number": observation.sequence_number,
            "timestamp_utc": obs_time,
            "value": observation.value
        }

        return observation

    def convert_units_if_needed(self, value: float, from_unit: str, to_unit: str, sensor_type: SensorType) -> Tuple[float, str]:
        """Convert native sensor engineering units to standardized canonical units."""
        if from_unit == to_unit:
            return value, to_unit
        
        # Pressure conversions (kPa / psi -> bar)
        if sensor_type == SensorType.PRESSURE:
            if from_unit.lower() == "kpa" and to_unit == "bar":
                return value / 100.0, "bar"
            elif from_unit.lower() == "psi" and to_unit == "bar":
                return value * 0.0689476, "bar"
            elif from_unit.lower() == "bar" and to_unit == "kpa":
                return value * 100.0, "kPa"

        # Temperature conversions (K / degF -> °C)
        if sensor_type == SensorType.TEMPERATURE:
            if from_unit.upper() == "K" and to_unit in ("°C", "degC"):
                return value - 273.15, "°C"
            elif from_unit in ("°F", "degF") and to_unit in ("°C", "degC"):
                return (value - 32.0) * (5.0 / 9.0), "°C"

        # Flow conversions (l/min -> m3/h)
        if sensor_type == SensorType.FLOW:
            if from_unit in ("L/min", "lpm", "l/min") and to_unit in ("m³/h", "m3/h"):
                return value * 0.06, "m³/h"

        return value, from_unit

telemetry_quality_validator = TelemetryQualityValidator()
