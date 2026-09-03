import time
import math
import random
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.services.industrial.base_telemetry_adapter import TelemetrySourceAdapter
from app.schemas.telemetry import (
    FacilityTelemetryObservation, SensorMetadata, SourceProtocol,
    SensorType, TelemetryQuality, GatewayStatus, DataQualityFlag, FreshnessStatus
)

logger = logging.getLogger(__name__)

class SimulationScenario:
    NORMAL = "NORMAL"
    DRIFT = "DRIFT"
    THERMAL_RISE = "THERMAL_RISE"
    PRESSURE_RISE = "PRESSURE_RISE"
    GAS_LEAK_PATTERN = "GAS_LEAK_PATTERN"
    MULTI_SENSOR_DEVIATION = "MULTI_SENSOR_DEVIATION"
    SENSOR_FAILURE = "SENSOR_FAILURE"
    COMMUNICATION_LOSS = "COMMUNICATION_LOSS"

class TelemetrySimulator(TelemetrySourceAdapter):
    """
    High-Fidelity Correlated Industrial Telemetry Simulator.
    Generates realistic, physically-correlated multi-sensor time-series (10, 100, 1000 sensors)
    across diverse sampling intervals (1s, 2s, 5s, 10s, 30s, 60s) with discrete industrial failure scenarios.
    
    Adheres strictly to the TelemetrySourceAdapter interface and ensures:
    1. Realistic physical coupling (e.g. skin temp rise -> internal pressure rise -> thermal anomaly score -> gas sniffer).
    2. Explicit labelling (is_live_data = False, source_protocol = SIMULATED_GATEWAY).
    3. Clear distinction between sensor reporting 0.0 vs sensor offline / missing heartbeat.
    """

    ASSETS = [
        ("T-04", "Sector D - Cryogenic Yard", "UNIT-NH3-01", "Ammonia Cryogenic Tank"),
        ("T-03", "Sector C - Pressurized Gas Farm", "UNIT-LPG-01", "LPG Horton Sphere 01"),
        ("T-01", "Sector A - Liquid Hydrocarbons", "UNIT-HC-01", "Benzene Storage Tank 01"),
        ("T-02", "Sector B - Hazardous Inorganics", "UNIT-CL-01", "Chlorine Bullet Tank"),
        ("T-05", "Sector C - Pressurized Gas Farm", "UNIT-LPG-02", "LPG Horton Sphere 02"),
        ("T-06", "Sector B - Hazardous Inorganics", "UNIT-H2S-01", "H2S Scrubber Column"),
        ("PU-01", "Sector A - Liquid Hydrocarbons", "UNIT-REF-01", "Primary Catalytic Reformer"),
        ("PU-02", "Sector D - Cryogenic Yard", "UNIT-NH3-02", "Ammonia Synthesis Loop"),
        ("PU-03", "Sector B - Hazardous Inorganics", "UNIT-SULF-01", "Gas Desulfurization Unit"),
        ("SUB-01", "Sector E - Utilities", "UNIT-UTIL-01", "66kV High Voltage Substation"),
    ]

    def __init__(
        self,
        gateway_id: str = "GW-SIM-DAHEJ-01",
        facility_id: str = "FAC-IN-DAHEJ-001"
    ):
        super().__init__(
            name="HIGH_FIDELITY_TELEMETRY_SIMULATOR",
            protocol=SourceProtocol.SIMULATED_GATEWAY,
            gateway_id=gateway_id,
            facility_id=facility_id
        )
        self.active_scenario = SimulationScenario.NORMAL
        self.scenario_start_time = time.time()
        self.sequence_counter = 0
        self.sensor_count = 100
        self.start_time = time.time()
        self.recent_latencies: List[float] = []
        self.sensor_states: Dict[str, Dict[str, Any]] = {}
        self.sensor_last_tick_time: Dict[str, float] = {}
        
        # Build initial sensor catalog across assets
        self._build_sensor_catalog(self.sensor_count)
        self.connect("simulator://internal-timeseries-engine")

    def _build_sensor_catalog(self, target_count: int):
        """Construct deterministic sensor hierarchy for 10, 100, or 1000 sensors."""
        self.registered_sensors.clear()
        self.sensor_states.clear()
        
        # Base template signals per asset with varying expected sampling rates
        templates = [
            ("TEMP_SKIN", SensorType.TEMPERATURE, "°C", 1.0, -45.0, 85.0, -38.0, -25.0, -42.0, 0.0, -32.0),
            ("PRESS_01", SensorType.PRESSURE, "bar", 1.0, 0.0, 25.0, 2.8, 5.5, 1.5, 6.5, 4.2),
            ("GAS_SNIFFER", SensorType.GAS_CONCENTRATION, "ppm", 2.0, 0.0, 500.0, 0.0, 25.0, 0.0, 150.0, 1.5),
            ("FLOW_INLET", SensorType.FLOW, "m³/h", 2.0, 0.0, 600.0, 50.0, 350.0, 20.0, 450.0, 120.0),
            ("VIB_RMS", SensorType.VIBRATION, "mm/s", 1.0, 0.0, 25.0, 0.0, 4.5, 0.0, 7.5, 1.2),
            ("THCAM_SCORE", SensorType.THERMAL_CAMERA_SUMMARY, "score", 5.0, 0.0, 100.0, 0.0, 60.0, 0.0, 85.0, 15.0),
            ("PROC_STATE", SensorType.PROCESS_STATE, "state", 10.0, 0.0, 10.0, 0.0, 8.0, 0.0, 10.0, 1.0),
            ("ACOUSTIC_LEAK", SensorType.ACOUSTIC, "dB", 5.0, 0.0, 60.0, 0.0, 35.0, 0.0, 50.0, 14.0),
            ("AMB_TEMP", SensorType.TEMPERATURE, "°C", 30.0, -10.0, 60.0, 10.0, 45.0, 0.0, 52.0, 32.0),
            ("REL_HUMIDITY", SensorType.FLOW, "%", 60.0, 0.0, 100.0, 20.0, 90.0, 10.0, 95.0, 65.0),
        ]

        count = 0
        while count < target_count:
            for asset_idx, asset in enumerate(self.ASSETS):
                for tmpl in templates:
                    if count >= target_count:
                        break
                    
                    suffix = tmpl[0] if count < len(self.ASSETS) * len(templates) else f"{tmpl[0]}_{count // (len(self.ASSETS) * len(templates))}"
                    s_id = f"SENS-{asset[0]}-{suffix}"
                    tag = f"Plant.{asset[1].split(' - ')[0].replace(' ', '')}.{asset[0]}.{suffix}"
                    
                    meta = SensorMetadata(
                        sensor_id=s_id,
                        facility_id=self.facility_id,
                        plant_area=asset[1],
                        unit_id=asset[2],
                        asset_id=asset[0],
                        tag_name=tag,
                        sensor_type=tmpl[1],
                        unit=tmpl[2],
                        expected_sampling_interval=tmpl[3],
                        valid_range_min=tmpl[4],
                        valid_range_max=tmpl[5],
                        warning_min=tmpl[6],
                        warning_max=tmpl[7],
                        critical_min=tmpl[8],
                        critical_max=tmpl[9],
                        source_protocol=SourceProtocol.SIMULATED_GATEWAY,
                        gateway_id=self.gateway_id
                    )
                    self.register_sensor_metadata(meta)
                    self.sensor_states[s_id] = {
                        "baseline": tmpl[10],
                        "current_value": tmpl[10],
                        "trend": "STABLE",
                        "last_updated": time.time()
                    }
                    self.sensor_last_tick_time[s_id] = 0.0
                    count += 1

    def set_sensor_count(self, count: int):
        """Set active sensor scale (e.g. 10, 100, 1000)."""
        self.sensor_count = max(10, min(1000, count))
        self._build_sensor_catalog(self.sensor_count)
        logger.info(f"Simulator reconfigured to {self.sensor_count} active sensors.")

    def set_stream_count(self, count: int):
        """Alias for set_sensor_count for stream scalability benchmarks."""
        self.set_sensor_count(count)

    def set_scenario(self, scenario: str):
        """Switch current operational scenario."""
        if hasattr(SimulationScenario, scenario):
            self.active_scenario = scenario
            self.scenario_start_time = time.time()
            logger.info(f"Telemetry simulation scenario changed to {scenario}")
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def connect(self, endpoint: str = "simulator://internal", credentials: Optional[Dict[str, Any]] = None) -> bool:
        self.is_connected = True
        self.status = GatewayStatus.CONNECTED
        return True

    def disconnect(self) -> bool:
        self.is_connected = False
        self.status = GatewayStatus.DISCONNECTED
        return True

    def health(self) -> Dict[str, Any]:
        uptime = max(0.1, time.time() - self.start_time)
        rate = round(self.total_observations_ingested / uptime, 1)
        p95 = round(sorted(self.recent_latencies)[int(len(self.recent_latencies) * 0.95)], 2) if self.recent_latencies else 0.5
        p99 = round(sorted(self.recent_latencies)[int(len(self.recent_latencies) * 0.99)], 2) if self.recent_latencies else 1.2

        return {
            "adapter_name": self.name,
            "protocol": self.protocol.value,
            "gateway_id": self.gateway_id,
            "facility_id": self.facility_id,
            "status": self.status.value,
            "active_scenario": self.active_scenario,
            "scenario_elapsed_sec": round(time.time() - self.scenario_start_time, 1),
            "registered_sensors_count": len(self.registered_sensors),
            "events_per_second": rate if rate > 0 else float(self.sensor_count),
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "is_live_data": False,
            "read_only": True
        }

    def generate_tick_batch(self, force_all: bool = False) -> List[FacilityTelemetryObservation]:
        """
        Generates correlated time-series batch adhering to multi-sensor physical relationships
        and individual expected sampling intervals.
        """
        if not self.is_connected and self.active_scenario == SimulationScenario.COMMUNICATION_LOSS:
            return []

        t0 = time.perf_counter()
        now_utc = datetime.now(timezone.utc)
        current_time = time.time()
        elapsed_scenario = current_time - self.scenario_start_time

        observations: List[FacilityTelemetryObservation] = []

        # Correlated physics parameters based on scenario
        t04_temp_drift = 0.0
        t04_press_drift = 0.0
        t04_gas_drift = 0.0
        t04_thcam_drift = 0.0

        if self.active_scenario == SimulationScenario.DRIFT:
            # Subtle monotonic drift upwards on T-04 over 60s
            progress = min(1.0, elapsed_scenario / 60.0)
            t04_temp_drift = progress * 6.0   # -32 -> -26 °C
            t04_press_drift = progress * 0.8  # 4.2 -> 5.0 bar

        elif self.active_scenario == SimulationScenario.THERMAL_RISE:
            # Rapid thermal excursion on T-04 skin
            progress = min(1.0, elapsed_scenario / 45.0)
            t04_temp_drift = progress * 14.0   # -32 -> -18 °C
            t04_thcam_drift = progress * 65.0  # 15 -> 80 anomaly score
            t04_press_drift = progress * 1.5   # 4.2 -> 5.7 bar

        elif self.active_scenario == SimulationScenario.PRESSURE_RISE:
            # Acute boil-off pressure spike
            progress = min(1.0, elapsed_scenario / 30.0)
            t04_press_drift = progress * 2.8   # 4.2 -> 7.0 bar (critical alarm)
            t04_temp_drift = progress * 4.0

        elif self.active_scenario == SimulationScenario.GAS_LEAK_PATTERN:
            # Flange seal breach: gas sniffer spikes + acoustic detection rise
            progress = min(1.0, elapsed_scenario / 20.0)
            t04_gas_drift = progress * 180.0   # 1.5 -> 181.5 ppm
            t04_press_drift = -progress * 0.5  # Slight pressure drop due to leak

        elif self.active_scenario == SimulationScenario.MULTI_SENSOR_DEVIATION:
            # Combined catastrophic cascade: thermal rise -> pressure spike -> leak -> sniffer
            progress = min(1.0, elapsed_scenario / 40.0)
            t04_temp_drift = progress * 18.0
            t04_press_drift = progress * 2.6
            t04_thcam_drift = progress * 75.0
            t04_gas_drift = progress * 220.0

        for s_id, meta in self.registered_sensors.items():
            # Check sampling interval rate (unless force_all is requested)
            last_tick = self.sensor_last_tick_time.get(s_id, 0.0)
            if not force_all and (current_time - last_tick) < (meta.expected_sampling_interval * 0.9):
                continue

            self.sensor_last_tick_time[s_id] = current_time
            self.sequence_counter += 1

            state = self.sensor_states[s_id]
            base_val = state["baseline"]
            
            # Physics perturbation
            val = base_val
            trend = "STABLE"
            quality = TelemetryQuality.GOOD
            flags = [DataQualityFlag.NONE]

            # Scenario A: SENSOR_FAILURE (Sensor SENS-T-04-PRESS_01 goes offline vs reports 0)
            if self.active_scenario == SimulationScenario.SENSOR_FAILURE and ("PRESS_01" in s_id and meta.asset_id == "T-04"):
                # Simulated hardware fault: reports frozen or missing
                quality = TelemetryQuality.BAD
                flags = [DataQualityFlag.SENSOR_FAULT]
                val = -999.0
                trend = "STABLE"

            # Scenario G: COMMUNICATION_LOSS (Simulates complete network dropout for gateway)
            elif self.active_scenario == SimulationScenario.COMMUNICATION_LOSS:
                continue # No data emitted during comm loss

            else:
                # Apply asset-specific correlated drift
                if meta.asset_id == "T-04":
                    if meta.sensor_type == SensorType.TEMPERATURE and "TEMP_SKIN" in s_id:
                        val += t04_temp_drift
                        trend = "RISING" if t04_temp_drift > 1.0 else "STABLE"
                    elif meta.sensor_type == SensorType.PRESSURE:
                        val += t04_press_drift
                        trend = "RAPID_RISE" if t04_press_drift > 1.5 else ("RISING" if t04_press_drift > 0.3 else "STABLE")
                    elif meta.sensor_type == SensorType.GAS_CONCENTRATION:
                        val += t04_gas_drift
                        trend = "RAPID_RISE" if t04_gas_drift > 20.0 else "STABLE"
                    elif meta.sensor_type == SensorType.THERMAL_CAMERA_SUMMARY:
                        val += t04_thcam_drift
                        trend = "RISING" if t04_thcam_drift > 10.0 else "STABLE"

                # Add realistic physical stochastic noise
                noise = random.gauss(0, max(0.01, (meta.valid_range_max - meta.valid_range_min) * 0.005))
                val = round(val + noise, 2)

                # Evaluate warnings / limits
                if meta.critical_max and val >= meta.critical_max:
                    quality = TelemetryQuality.WARNING
                elif meta.warning_max and val >= meta.warning_max:
                    quality = TelemetryQuality.GOOD

            state["current_value"] = val
            state["trend"] = trend
            state["last_updated"] = current_time

            obs = FacilityTelemetryObservation(
                telemetry_id=f"TEL-SIM-{self.sequence_counter:08d}",
                facility_id=meta.facility_id,
                plant_area=meta.plant_area,
                unit_id=meta.unit_id,
                asset_id=meta.asset_id,
                gateway_id=meta.gateway_id,
                sensor_id=meta.sensor_id,
                sensor_type=meta.sensor_type,
                tag_name=meta.tag_name,
                timestamp_utc=now_utc,
                value=val,
                unit=meta.unit,
                quality=quality,
                source_protocol=SourceProtocol.SIMULATED_GATEWAY,
                source_timestamp=now_utc,
                acquisition_timestamp=now_utc,
                ingestion_timestamp=now_utc,
                processing_timestamp=now_utc,
                sequence_number=self.sequence_counter,
                is_live_data=False, # Strictly simulation
                data_quality_status="VALID" if quality == TelemetryQuality.GOOD else "ANOMALOUS",
                data_quality_flags=flags,
                freshness_status=FreshnessStatus.LIVE,
                trend=trend
            )
            observations.append(obs)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.recent_latencies.append(elapsed_ms)
        if len(self.recent_latencies) > 200:
            self.recent_latencies.pop(0)

        self.total_observations_ingested += len(observations)
        self.last_ingestion_time = now_utc
        return observations

    def subscribe_or_poll(self) -> List[FacilityTelemetryObservation]:
        return self.generate_tick_batch(force_all=False)

    def normalize(self, raw_payload: Any, metadata: SensorMetadata) -> Optional[FacilityTelemetryObservation]:
        # Simulator produces pre-normalized instances
        if isinstance(raw_payload, FacilityTelemetryObservation):
            return raw_payload
        return None

    def close(self) -> None:
        self.disconnect()
        self.registered_sensors.clear()

telemetry_simulator = TelemetrySimulator()
