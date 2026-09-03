import math
from typing import Dict, Optional, Tuple
from datetime import datetime, timezone
from app.schemas.canonical import (
    CanonicalEvent, DataQualityFlag, SensorType, SignalRangeConfig
)

class DataQualityEngine:
    """
    Validates physical boundaries, checks stale data timeouts, suppresses duplicates,
    and assigns authoritative data quality flags to canonical observations.
    """
    def __init__(self):
        # Default tag engineering limits across facility assets
        self.signal_configs: Dict[str, SignalRangeConfig] = {}
        # Signal tracking state for stale/rate-of-change/duplicate detection
        self.last_seen_state: Dict[str, Dict] = {}
        self._initialize_default_ranges()

    def _initialize_default_ranges(self):
        # Default physical limits for typical refinery / petrochemical tags
        defaults = [
            # T-04 Ammonia Cryogenic Tank
            SignalRangeConfig(
                signal_id="T04_PRESS_01", sensor_type=SensorType.PRESSURE, unit="bar",
                nominal_min=3.5, nominal_max=5.2, warning_low=2.5, warning_high=6.5,
                critical_low=1.0, critical_high=8.0, max_rate_of_change_per_sec=0.8
            ),
            SignalRangeConfig(
                signal_id="T04_TEMP_SKIN", sensor_type=SensorType.TEMPERATURE, unit="degC",
                nominal_min=-35.0, nominal_max=-30.0, warning_low=-40.0, warning_high=-20.0,
                critical_low=-45.0, critical_high=0.0, max_rate_of_change_per_sec=2.0
            ),
            SignalRangeConfig(
                signal_id="T04_VIB_RMS", sensor_type=SensorType.VIBRATION, unit="mm/s",
                nominal_min=0.5, nominal_max=3.0, warning_low=0.0, warning_high=5.0,
                critical_low=0.0, critical_high=8.0, max_rate_of_change_per_sec=1.5
            ),
            SignalRangeConfig(
                signal_id="T04_ACOUSTIC_LEAK", sensor_type=SensorType.ACOUSTIC, unit="dB",
                nominal_min=10.0, nominal_max=22.0, warning_low=0.0, warning_high=35.0,
                critical_low=0.0, critical_high=50.0, max_rate_of_change_per_sec=5.0
            ),
            SignalRangeConfig(
                signal_id="T04_GAS_NH3", sensor_type=SensorType.GAS_CONCENTRATION, unit="ppm",
                nominal_min=0.0, nominal_max=5.0, warning_low=0.0, warning_high=25.0,
                critical_low=0.0, critical_high=150.0, max_rate_of_change_per_sec=20.0
            ),
            # T-03 LPG Horton Sphere
            SignalRangeConfig(
                signal_id="T03_PRESS_01", sensor_type=SensorType.PRESSURE, unit="bar",
                nominal_min=8.0, nominal_max=13.0, warning_low=5.0, warning_high=16.0,
                critical_low=2.0, critical_high=20.0, max_rate_of_change_per_sec=1.5
            ),
            SignalRangeConfig(
                signal_id="T03_TEMP_SKIN", sensor_type=SensorType.TEMPERATURE, unit="degC",
                nominal_min=15.0, nominal_max=35.0, warning_low=0.0, warning_high=50.0,
                critical_low=-10.0, critical_high=75.0, max_rate_of_change_per_sec=3.0
            ),
            SignalRangeConfig(
                signal_id="T03_VIB_RMS", sensor_type=SensorType.VIBRATION, unit="mm/s",
                nominal_min=0.5, nominal_max=3.2, warning_low=0.0, warning_high=5.5,
                critical_low=0.0, critical_high=8.5, max_rate_of_change_per_sec=1.5
            ),
            SignalRangeConfig(
                signal_id="T03_GAS_LPG", sensor_type=SensorType.GAS_CONCENTRATION, unit="ppm",
                nominal_min=0.0, nominal_max=100.0, warning_low=0.0, warning_high=1000.0,
                critical_low=0.0, critical_high=5000.0, max_rate_of_change_per_sec=250.0
            ),
            # Generic default patterns
            SignalRangeConfig(
                signal_id="GENERIC_PRESSURE", sensor_type=SensorType.PRESSURE, unit="bar",
                nominal_min=0.0, nominal_max=25.0, warning_low=-0.5, warning_high=30.0,
                critical_low=-1.0, critical_high=40.0, max_rate_of_change_per_sec=5.0
            ),
            SignalRangeConfig(
                signal_id="GENERIC_TEMPERATURE", sensor_type=SensorType.TEMPERATURE, unit="degC",
                nominal_min=-50.0, nominal_max=150.0, warning_low=-60.0, warning_high=180.0,
                critical_low=-70.0, critical_high=250.0, max_rate_of_change_per_sec=10.0
            ),
            SignalRangeConfig(
                signal_id="GENERIC_VIBRATION", sensor_type=SensorType.VIBRATION, unit="mm/s",
                nominal_min=0.0, nominal_max=4.0, warning_low=0.0, warning_high=6.5,
                critical_low=0.0, critical_high=10.0, max_rate_of_change_per_sec=3.0
            ),
            SignalRangeConfig(
                signal_id="GENERIC_GAS", sensor_type=SensorType.GAS_CONCENTRATION, unit="ppm",
                nominal_min=0.0, nominal_max=20.0, warning_low=0.0, warning_high=50.0,
                critical_low=0.0, critical_high=300.0, max_rate_of_change_per_sec=50.0
            )
        ]
        for cfg in defaults:
            self.signal_configs[cfg.signal_id] = cfg

    def register_signal_config(self, config: SignalRangeConfig):
        self.signal_configs[config.signal_id] = config

    def get_config_for_signal(self, signal_id: str, sensor_type: Optional[SensorType] = None) -> SignalRangeConfig:
        if signal_id in self.signal_configs:
            return self.signal_configs[signal_id]
        
        # Fallback to generic config by sensor type
        if sensor_type == SensorType.PRESSURE:
            return self.signal_configs["GENERIC_PRESSURE"]
        elif sensor_type == SensorType.TEMPERATURE:
            return self.signal_configs["GENERIC_TEMPERATURE"]
        elif sensor_type == SensorType.VIBRATION:
            return self.signal_configs["GENERIC_VIBRATION"]
        elif sensor_type == SensorType.GAS_CONCENTRATION:
            return self.signal_configs["GENERIC_GAS"]
        
        # Absolute fallback
        return SignalRangeConfig(
            signal_id=signal_id, sensor_type=sensor_type or SensorType.PRESSURE, unit="unit",
            nominal_min=-1000.0, nominal_max=10000.0, stale_timeout_sec=60.0
        )

    def validate_and_enrich(self, event: CanonicalEvent) -> CanonicalEvent:
        """
        Validates the incoming canonical event, checks boundaries, rate-of-change,
        timestamps, and assigns the appropriate quality flag and severity hint.
        """
        cfg = self.get_config_for_signal(event.signal_id, event.sensor_type)
        now = datetime.now(timezone.utc)
        event_time = event.timestamp
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        # 1. Stale / Future timestamp validation
        time_diff_sec = (now - event_time).total_seconds()
        if time_diff_sec < -30.0:  # >30s in the future (clock desync)
            event.quality = DataQualityFlag.UNCERTAIN
            event.severity_hint = "WATCH"
        elif time_diff_sec > cfg.stale_timeout_sec:
            event.quality = DataQualityFlag.STALE

        # 2. NaN / Infinite check
        if math.isnan(event.value) or math.isinf(event.value):
            event.quality = DataQualityFlag.BAD
            event.severity_hint = "CRITICAL"
            return event

        # 3. Duplicate detection
        state_key = f"{event.asset_id}::{event.signal_id}"
        prev_state = self.last_seen_state.get(state_key)
        
        if prev_state is not None:
            # Duplicate sequence or exact duplicate timestamp
            if event.sequence > 0 and event.sequence == prev_state.get("sequence"):
                event.quality = DataQualityFlag.UNCERTAIN
            
            # Rate of change check
            if cfg.max_rate_of_change_per_sec is not None:
                dt = (event_time - prev_state["timestamp"]).total_seconds()
                if dt > 0.001:
                    roc = abs(event.value - prev_state["value"]) / dt
                    if roc > cfg.max_rate_of_change_per_sec * 3.0: # Physical impossibility spike
                        event.quality = DataQualityFlag.BAD
                        event.severity_hint = "WATCH"

        # 4. Physical range boundary verification & severity evaluation
        val = event.value
        severity = "NORMAL"

        if cfg.critical_high is not None and val >= cfg.critical_high:
            severity = "CRITICAL"
            event.quality = DataQualityFlag.GOOD if event.quality != DataQualityFlag.BAD else event.quality
        elif cfg.critical_low is not None and val <= cfg.critical_low:
            severity = "CRITICAL"
        elif cfg.warning_high is not None and val >= cfg.warning_high:
            severity = "WARNING"
        elif cfg.warning_low is not None and val <= cfg.warning_low:
            severity = "WARNING"
        elif val > cfg.nominal_max or val < cfg.nominal_min:
            severity = "WATCH"

        event.severity_hint = severity

        # Update last seen state
        self.last_seen_state[state_key] = {
            "timestamp": event_time,
            "value": event.value,
            "sequence": event.sequence,
            "quality": event.quality
        }

        # Assign HOT/WARM/COLD classification
        from app.services.ingestion.stream_classifier import stream_classifier
        event.classification = stream_classifier.classify_event(event)

        return event

data_quality_engine = DataQualityEngine()
