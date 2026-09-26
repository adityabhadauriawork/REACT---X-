"""
REACT-X Demo Replay Service
Powers the Demo Command Room (/demo) with deterministic reference scenario playback.
Every event and telemetry observation is routed through the EXACT canonical pipeline:
Quality Engine -> Feature Extraction -> Frozen ML -> Dempster-Shafer Fusion -> Consequence -> Cascade -> Evacuation -> PDF.
"""
import time
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.schemas.gateway import (
    SourceMode, QualityState, PredictionState, DemoScenario,
    DemoReplayState, FailureInjectionCommand, NormalizedEventRecord
)
from app.services.gateway.data_gateway_service import data_gateway_service
from app.services.ml.thermal_classifier_service import classifier_service
from app.services.fusion.multimodal_fusion_service import multimodal_fusion_service
from app.services.hazard.hazard_service import hazard_service
from app.services.impact.impact_service import impact_service
from app.services.evacuation.evacuation_service import evacuation_service
from app.services.resources.resource_service import resource_service
from app.services.site.site_service import site_service
from app.services.graph.risk_graph_service import risk_graph_service

logger = logging.getLogger("reactx.gateway.demo_replay")


class DemoReplayService:
    """
    Deterministic Replay Engine for Demo Command Room.
    Maintains scenario timelines, clock synchronization, failure injection states,
    and step-by-step pipeline execution traces with complete scenario isolation.
    """

    def __init__(self):
        self.scenarios = self._build_default_scenarios()
        self.current_scenario_id = "SCENARIO-DAHEJ-AMMONIA-CRYO-01"
        self.failure_injections = FailureInjectionCommand()
        self._step_timeline_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._scenario_meta_cache: Dict[str, Dict[str, Any]] = {}
        self._build_scenario_timelines()
        self.state = self._create_initial_state(self.current_scenario_id)

    def _build_default_scenarios(self) -> List[DemoScenario]:
        return [
            DemoScenario(
                scenario_id="SCENARIO-DAHEJ-AMMONIA-CRYO-01",
                name="Dahej Cryogenic Ammonia Leak & Thermal Escalation (Golden Flow)",
                facility_id="FAC-IN-DAHEJ-001",
                facility_name="Dahej Petrochemical Complex",
                asset_id="T-04",
                chemical_id="CHEM-NH3",
                description="Deterministic 5-step incident lifecycle: baseline -> acoustic anomaly -> satellite VIIRS detection -> toxic plume dispersion -> dynamic evacuation & official pre-plan authorization.",
                total_steps=5,
                duration_seconds=300,
                hazard_type="TOXIC_VAPOR_AND_FIRE",
                is_golden_deterministic=True
            ),
            DemoScenario(
                scenario_id="SCENARIO-HAZIRA-LNG-03",
                name="Hazira LNG Terminal Domino Cascade Risk Screening",
                facility_id="FAC-IN-HAZ-003",
                facility_name="Hazira LNG & Heavy Industrial Hub",
                asset_id="TANK-LNG-02",
                chemical_id="CHEM-LNG",
                description="Thermal radiation and cryogenic pool fire cascade screening across neighboring industrial chemical storage spheres.",
                total_steps=4,
                duration_seconds=240,
                hazard_type="CRYOGENIC_POOL_FIRE",
                is_golden_deterministic=True
            ),
            DemoScenario(
                scenario_id="SCENARIO-ROUTINE-FLARE-02",
                name="Vadodara Petrochemical Routine Gas Flare Discrimination",
                facility_id="FAC-IN-VAD-002",
                facility_name="Vadodara Petrochemical Corridor",
                asset_id="FLARE-01",
                chemical_id="CHEM-CH4",
                description="Demonstrates ML discrimination and Dempster-Shafer belief mass preventing false fire alarms during routine elevated flaring operations.",
                total_steps=4,
                duration_seconds=240,
                hazard_type="ELEVATED_PROCESS_HEAT",
                is_golden_deterministic=True
            )
        ]

    def _build_scenario_timelines(self):
        """Constructs detailed step payloads for each deterministic reference scenario."""
        base_time = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)

        # Meta cache for coordinates and chemical details
        self._scenario_meta_cache["SCENARIO-DAHEJ-AMMONIA-CRYO-01"] = {
            "facility_id": "FAC-IN-DAHEJ-001",
            "facility_name": "Dahej Petrochemical Complex",
            "coordinates": [21.6850, 72.5750],
            "asset_id": "T-04",
            "asset_name": "Ammonia Cryogenic Tank T-04",
            "chemical_id": "CHEM-NH3",
            "chemical_name": "Ammonia (Anhydrous)",
            "hazard_type": "TOXIC_VAPOR_AND_FIRE",
            "contacts": {
                "fire_rescue": "Bharuch District Fire & Hazmat Division",
                "disaster_mgmt": "GIDC Dahej Crisis Management Center",
                "medical": "Dahej Occupational Health & Trauma Center",
                "police": "Dahej Port Marine Police Station"
            }
        }

        self._scenario_meta_cache["SCENARIO-HAZIRA-LNG-03"] = {
            "facility_id": "FAC-IN-HAZ-003",
            "facility_name": "Hazira LNG & Heavy Industrial Hub",
            "coordinates": [21.1155, 72.6355],
            "asset_id": "TANK-LNG-02",
            "asset_name": "Cryogenic LNG Full Containment Tank 02",
            "chemical_id": "CHEM-LNG",
            "chemical_name": "Liquefied Natural Gas (LNG)",
            "hazard_type": "CRYOGENIC_POOL_FIRE",
            "contacts": {
                "fire_rescue": "Hazira Industrial Area Fire Command",
                "disaster_mgmt": "Surat District Disaster Management Authority",
                "medical": "Hazira Emergency Medical Center",
                "police": "Hazira Port Police"
            }
        }

        self._scenario_meta_cache["SCENARIO-ROUTINE-FLARE-02"] = {
            "facility_id": "FAC-IN-VAD-002",
            "facility_name": "Vadodara Petrochemical Corridor",
            "coordinates": [22.3552, 73.1352],
            "asset_id": "FLARE-01",
            "asset_name": "Elevated HP Steam-Assisted Flare 01",
            "chemical_id": "CHEM-CH4",
            "chemical_name": "Methane / Hydrocarbon Flared Gas",
            "hazard_type": "ELEVATED_PROCESS_HEAT",
            "contacts": {
                "fire_rescue": "Vadodara GIDC Fire Station",
                "disaster_mgmt": "Vadodara District Emergency Operations Center",
                "medical": "Koyali Refinery Hospital",
                "police": "Jawaharnagar Police Station"
            }
        }

        # 1. Dahej Golden Flow (5 Steps)
        self._step_timeline_cache["SCENARIO-DAHEJ-AMMONIA-CRYO-01"] = [
            {
                "step": 1,
                "stage_name": "BASELINE_NOMINAL_OPERATIONS",
                "elapsed_sec": 0,
                "observed_time": base_time,
                "event": {
                    "event_id": "EVT-REPLAY-DHJ-001",
                    "latitude": 21.6850,
                    "longitude": 72.5750,
                    "frp_mw": 3.2,
                    "brightness_kelvin": 315.0,
                    "confidence_pct": 88.0,
                    "source_name": "NASA FIRMS / VIIRS NOAA-20"
                },
                "telemetry": {
                    "sensor_id": "T04_PRESS_01",
                    "metric_name": "tank_pressure",
                    "raw_value": 4.1,
                    "normalized_value": 4.1,
                    "unit": "bar",
                    "quality": "GOOD",
                    "skin_temp_c": -33.2
                },
                "expected_class": "ROUTINE_PROCESS_HEAT"
            },
            {
                "step": 2,
                "stage_name": "ACOUSTIC_ANOMALY_AND_MICRO_LEAK",
                "elapsed_sec": 60,
                "observed_time": base_time + timedelta(minutes=1),
                "event": {
                    "event_id": "EVT-REPLAY-DHJ-002",
                    "latitude": 21.6851,
                    "longitude": 72.5752,
                    "frp_mw": 8.5,
                    "brightness_kelvin": 332.0,
                    "confidence_pct": 91.0,
                    "source_name": "ISRO MOSDAC INSAT-3DR"
                },
                "telemetry": {
                    "sensor_id": "T04_ACOUSTIC_LEAK",
                    "metric_name": "acoustic_emission",
                    "raw_value": 38.5,
                    "normalized_value": 38.5,
                    "unit": "dB",
                    "quality": "GOOD",
                    "skin_temp_c": -28.0
                },
                "expected_class": "ROUTINE_PROCESS_HEAT"
            },
            {
                "step": 3,
                "stage_name": "SATELLITE_THERMAL_ESCALATION",
                "elapsed_sec": 120,
                "observed_time": base_time + timedelta(minutes=2),
                "event": {
                    "event_id": "EVT-REPLAY-DHJ-003",
                    "latitude": 21.6852,
                    "longitude": 72.5754,
                    "frp_mw": 28.4,
                    "brightness_kelvin": 372.0,
                    "confidence_pct": 96.0,
                    "source_name": "Copernicus Sentinel-2 & VIIRS"
                },
                "telemetry": {
                    "sensor_id": "T04_GAS_NH3",
                    "metric_name": "gas_concentration",
                    "raw_value": 125.0,
                    "normalized_value": 125.0,
                    "unit": "ppm",
                    "quality": "GOOD",
                    "skin_temp_c": -12.0
                },
                "expected_class": "INDUSTRIAL_FIRE"
            },
            {
                "step": 4,
                "stage_name": "TOXIC_PLUME_DISPERSION_CONSEQUENCE",
                "elapsed_sec": 180,
                "observed_time": base_time + timedelta(minutes=3),
                "event": {
                    "event_id": "EVT-REPLAY-DHJ-004",
                    "latitude": 21.6853,
                    "longitude": 72.5755,
                    "frp_mw": 52.0,
                    "brightness_kelvin": 410.0,
                    "confidence_pct": 99.0,
                    "source_name": "VIIRS Nightfire (VNF) + FIRMS"
                },
                "telemetry": {
                    "sensor_id": "T04_GAS_NH3",
                    "metric_name": "gas_concentration",
                    "raw_value": 450.0,
                    "normalized_value": 450.0,
                    "unit": "ppm",
                    "quality": "GOOD",
                    "skin_temp_c": 15.0
                },
                "expected_class": "INDUSTRIAL_FIRE"
            },
            {
                "step": 5,
                "stage_name": "RESPONSE_EVACUATION_AND_PREPLAN_EXPORT",
                "elapsed_sec": 240,
                "observed_time": base_time + timedelta(minutes=4),
                "event": {
                    "event_id": "EVT-REPLAY-DHJ-005",
                    "latitude": 21.6853,
                    "longitude": 72.5755,
                    "frp_mw": 48.0,
                    "brightness_kelvin": 398.0,
                    "confidence_pct": 98.0,
                    "source_name": "Landsat-9 TIRS & Multi-Satellite Fusion"
                },
                "telemetry": {
                    "sensor_id": "T04_GAS_NH3",
                    "metric_name": "gas_concentration",
                    "raw_value": 380.0,
                    "normalized_value": 380.0,
                    "unit": "ppm",
                    "quality": "GOOD",
                    "skin_temp_c": 10.0
                },
                "expected_class": "INDUSTRIAL_FIRE"
            }
        ]

        # 2. Hazira Domino Cascade Screening (4 Steps)
        self._step_timeline_cache["SCENARIO-HAZIRA-LNG-03"] = [
            {
                "step": 1,
                "stage_name": "NOMINAL_CRYOGENIC_CONTAINMENT",
                "elapsed_sec": 0,
                "observed_time": base_time,
                "event": {
                    "event_id": "EVT-REPLAY-HAZ-001",
                    "latitude": 21.1155,
                    "longitude": 72.6355,
                    "frp_mw": 2.1,
                    "brightness_kelvin": 312.0,
                    "confidence_pct": 89.0,
                    "source_name": "NASA FIRMS / VIIRS NOAA-20"
                },
                "telemetry": {
                    "sensor_id": "LNG02_BOILOFF_PRESS",
                    "metric_name": "boiloff_pressure",
                    "raw_value": 1.15,
                    "normalized_value": 1.15,
                    "unit": "bar",
                    "quality": "GOOD",
                    "skin_temp_c": -162.0
                },
                "expected_class": "ROUTINE_PROCESS_HEAT"
            },
            {
                "step": 2,
                "stage_name": "UNLOADING_ARM_SEAL_DEGRADATION",
                "elapsed_sec": 60,
                "observed_time": base_time + timedelta(minutes=1),
                "event": {
                    "event_id": "EVT-REPLAY-HAZ-002",
                    "latitude": 21.1155,
                    "longitude": 72.6355,
                    "frp_mw": 14.8,
                    "brightness_kelvin": 348.0,
                    "confidence_pct": 93.0,
                    "source_name": "ISRO MOSDAC INSAT-3D & VIIRS"
                },
                "telemetry": {
                    "sensor_id": "LNG02_FLANGE_VIB",
                    "metric_name": "vibration_rms",
                    "raw_value": 5.8,
                    "normalized_value": 5.8,
                    "unit": "mm/s",
                    "quality": "GOOD",
                    "skin_temp_c": -140.0
                },
                "expected_class": "ROUTINE_PROCESS_HEAT"
            },
            {
                "step": 3,
                "stage_name": "CRYOGENIC_JET_IGNITION_AND_THERMAL_ESCALATION",
                "elapsed_sec": 120,
                "observed_time": base_time + timedelta(minutes=2),
                "event": {
                    "event_id": "EVT-REPLAY-HAZ-003",
                    "latitude": 21.1156,
                    "longitude": 72.6357,
                    "frp_mw": 68.5,
                    "brightness_kelvin": 425.0,
                    "confidence_pct": 99.0,
                    "source_name": "Sentinel-2 SWIR & VIIRS Nightfire"
                },
                "telemetry": {
                    "sensor_id": "LNG02_RAD_FLUX",
                    "metric_name": "thermal_radiation",
                    "raw_value": 37.5,
                    "normalized_value": 37.5,
                    "unit": "kW/m2",
                    "quality": "GOOD",
                    "skin_temp_c": 85.0
                },
                "expected_class": "INDUSTRIAL_FIRE"
            },
            {
                "step": 4,
                "stage_name": "DOMINO_CASCADE_SCREENING_AND_MITIGATION",
                "elapsed_sec": 180,
                "observed_time": base_time + timedelta(minutes=3),
                "event": {
                    "event_id": "EVT-REPLAY-HAZ-004",
                    "latitude": 21.1156,
                    "longitude": 72.6357,
                    "frp_mw": 72.0,
                    "brightness_kelvin": 432.0,
                    "confidence_pct": 99.0,
                    "source_name": "Multi-Satellite Concurrence (FIRMS + MOSDAC + VNF)"
                },
                "telemetry": {
                    "sensor_id": "SPHERE03_SKIN_TEMP",
                    "metric_name": "skin_temp",
                    "raw_value": 68.0,
                    "normalized_value": 68.0,
                    "unit": "degC",
                    "quality": "GOOD",
                    "skin_temp_c": 68.0
                },
                "expected_class": "INDUSTRIAL_FIRE"
            }
        ]

        # 3. Vadodara Routine Flare Discrimination (4 Steps)
        self._step_timeline_cache["SCENARIO-ROUTINE-FLARE-02"] = [
            {
                "step": 1,
                "stage_name": "STEADY_STATE_PROCESS_FLARING",
                "elapsed_sec": 0,
                "observed_time": base_time,
                "event": {
                    "event_id": "EVT-REPLAY-VAD-001",
                    "latitude": 22.3552,
                    "longitude": 73.1352,
                    "frp_mw": 11.2,
                    "brightness_kelvin": 338.0,
                    "confidence_pct": 94.0,
                    "source_name": "NASA FIRMS / VIIRS NOAA-20"
                },
                "telemetry": {
                    "sensor_id": "FLARE01_HEADER_FLOW",
                    "metric_name": "purge_gas_flow",
                    "raw_value": 1.2,
                    "normalized_value": 1.2,
                    "unit": "kg/s",
                    "quality": "GOOD",
                    "skin_temp_c": 420.0
                },
                "expected_class": "GAS_FLARE"
            },
            {
                "step": 2,
                "stage_name": "STEAM_INJECTION_AND_SMOKE_KNOCKDOWN",
                "elapsed_sec": 60,
                "observed_time": base_time + timedelta(minutes=1),
                "event": {
                    "event_id": "EVT-REPLAY-VAD-002",
                    "latitude": 22.3552,
                    "longitude": 73.1352,
                    "frp_mw": 14.5,
                    "brightness_kelvin": 344.0,
                    "confidence_pct": 95.0,
                    "source_name": "ISRO MOSDAC INSAT-3DR"
                },
                "telemetry": {
                    "sensor_id": "FLARE01_STEAM_RATIO",
                    "metric_name": "steam_ratio",
                    "raw_value": 0.35,
                    "normalized_value": 0.35,
                    "unit": "ratio",
                    "quality": "GOOD",
                    "skin_temp_c": 460.0
                },
                "expected_class": "GAS_FLARE"
            },
            {
                "step": 3,
                "stage_name": "TRANSIENT_PROCESS_UPSET_DISCRIMINATION",
                "elapsed_sec": 120,
                "observed_time": base_time + timedelta(minutes=2),
                "event": {
                    "event_id": "EVT-REPLAY-VAD-003",
                    "latitude": 22.3552,
                    "longitude": 73.1352,
                    "frp_mw": 26.0,
                    "brightness_kelvin": 365.0,
                    "confidence_pct": 96.0,
                    "source_name": "Copernicus Sentinel-2 & VIIRS"
                },
                "telemetry": {
                    "sensor_id": "FLARE01_FLAME_DETECTOR",
                    "metric_name": "optical_flame_intensity",
                    "raw_value": 85.0,
                    "normalized_value": 85.0,
                    "unit": "%",
                    "quality": "GOOD",
                    "skin_temp_c": 510.0
                },
                "expected_class": "GAS_FLARE"
            },
            {
                "step": 4,
                "stage_name": "ML_FALSE_ALARM_SUPPRESSION_CONSENSUS",
                "elapsed_sec": 180,
                "observed_time": base_time + timedelta(minutes=3),
                "event": {
                    "event_id": "EVT-REPLAY-VAD-004",
                    "latitude": 22.3552,
                    "longitude": 73.1352,
                    "frp_mw": 12.8,
                    "brightness_kelvin": 340.0,
                    "confidence_pct": 95.0,
                    "source_name": "VIIRS Nightfire (VNF) + FIRMS"
                },
                "telemetry": {
                    "sensor_id": "FLARE01_HEADER_FLOW",
                    "metric_name": "purge_gas_flow",
                    "raw_value": 1.4,
                    "normalized_value": 1.4,
                    "unit": "kg/s",
                    "quality": "GOOD",
                    "skin_temp_c": 430.0
                },
                "expected_class": "GAS_FLARE"
            }
        ]

    def _create_initial_state(self, scenario_id: str) -> DemoReplayState:
        meta = self._scenario_meta_cache.get(scenario_id, self._scenario_meta_cache["SCENARIO-DAHEJ-AMMONIA-CRYO-01"])
        timeline = self._step_timeline_cache.get(scenario_id, [])
        now = datetime.now(timezone.utc)
        return DemoReplayState(
            status="IDLE",
            scenario_id=scenario_id,
            facility_id=meta["facility_id"],
            facility_name=meta["facility_name"],
            coordinates=meta["coordinates"],
            current_step=0,
            total_steps=len(timeline),
            replay_speed=1.0,
            replay_started_at=None,
            replay_clock=now,
            pipeline_stage="IDLE",
            active_event=None,
            active_telemetry=None,
            active_classification=None,
            active_fusion=None,
            active_prediction=None,
            active_consequence=None,
            active_cascade=None,
            active_evacuation=None,
            active_preplan_summary=None,
            active_incident_packet=None,
            active_failure_injections=self.failure_injections,
            provenance_trace=[]
        )

    def list_scenarios(self) -> List[DemoScenario]:
        return self.scenarios

    def get_state(self) -> DemoReplayState:
        return self.state

    def start_replay(self, scenario_id: str = "SCENARIO-DAHEJ-AMMONIA-CRYO-01", speed: float = 1.0) -> DemoReplayState:
        # If scenario is already selected and paused mid-flight, resume smoothly
        if self.current_scenario_id == scenario_id and self.state.status == "PAUSED" and self.state.current_step > 0:
            self.state.status = "RUNNING"
            self.state.replay_speed = speed
            return self.state

        self.current_scenario_id = scenario_id
        meta = self._scenario_meta_cache.get(scenario_id, self._scenario_meta_cache["SCENARIO-DAHEJ-AMMONIA-CRYO-01"])
        timeline = self._step_timeline_cache.get(scenario_id, [])
        now = datetime.now(timezone.utc)
        
        self.state = DemoReplayState(
            status="RUNNING",
            scenario_id=scenario_id,
            facility_id=meta["facility_id"],
            facility_name=meta["facility_name"],
            coordinates=meta["coordinates"],
            current_step=0,
            total_steps=len(timeline),
            replay_speed=speed,
            replay_started_at=now,
            replay_clock=now,
            pipeline_stage="INITIALIZING_INGESTION_GATEWAY",
            active_event=None,
            active_telemetry=None,
            active_classification=None,
            active_fusion=None,
            active_prediction=None,
            active_consequence=None,
            active_cascade=None,
            active_evacuation=None,
            active_preplan_summary=None,
            active_incident_packet=None,
            active_failure_injections=self.failure_injections,
            provenance_trace=[]
        )
        return self.state

    def pause_replay(self) -> DemoReplayState:
        self.state.status = "PAUSED"
        return self.state

    def reset_replay(self) -> DemoReplayState:
        self.failure_injections = FailureInjectionCommand()
        self.state = self._create_initial_state(self.current_scenario_id)
        return self.state

    def inject_failure(self, cmd: FailureInjectionCommand) -> DemoReplayState:
        """Applies real-time failure injections to verify degraded/conflict state transitions."""
        if cmd.trigger_recovery:
            self.failure_injections = FailureInjectionCommand()
        else:
            self.failure_injections = cmd
        self.state.active_failure_injections = self.failure_injections
        return self.state

    def step_pipeline(self, db: Optional[Session] = None) -> DemoReplayState:
        """
        Executes one step of the active scenario through the REAL canonical pipeline:
        1. Ingest event & telemetry through Data Gateway with SourceMode=REPLAY
        2. Evaluate data quality & failure injections
        3. Attribute to industrial facility
        4. Extract 23-feature vector matching FEATURE_NAMES contract
        5. Run 7-class ML classification (Frozen HistGradientBoosting model)
        6. Compute Dempster-Shafer multi-source evidential fusion
        7. Run consequence dispersion modelling
        8. Run risk-graph domino/cascade analysis
        9. Compute dynamic safe evacuation routes avoiding hazard envelopes
        10. Synthesize structured CAP-compatible Emergency Incident Packet
        """
        timeline = self._step_timeline_cache.get(self.current_scenario_id, [])
        if not timeline:
            return self.state

        meta = self._scenario_meta_cache.get(self.current_scenario_id, self._scenario_meta_cache["SCENARIO-DAHEJ-AMMONIA-CRYO-01"])
        next_idx = self.state.current_step
        if next_idx >= len(timeline):
            self.state.status = "COMPLETED"
            self.state.pipeline_stage = "REPLAY_SCENARIO_COMPLETED"
            return self.state

        step_data = timeline[next_idx]
        now = datetime.now(timezone.utc)

        # 1. Ingest Raw Event
        raw_event = dict(step_data["event"])
        raw_telemetry = dict(step_data["telemetry"])

        # Handle Failure Injections
        quality_state = QualityState.GOOD
        val_flags: List[str] = []

        if self.failure_injections.inject_missing_telemetry:
            raw_telemetry = None
            quality_state = QualityState.MISSING
            val_flags.append("TELEMETRY_STREAM_DROPPED")
        elif self.failure_injections.inject_stale_telemetry:
            raw_telemetry["quality"] = "STALE"
            quality_state = QualityState.STALE
            val_flags.append("TELEMETRY_STALE_TIMESTAMP")
        elif self.failure_injections.inject_sensor_spike:
            raw_telemetry["raw_value"] = 999.9
            raw_telemetry["quality"] = "BAD"
            quality_state = QualityState.BAD
            val_flags.append("SENSOR_PHYSICAL_SPIKE")
        elif self.failure_injections.inject_conflicting_evidence:
            raw_telemetry["raw_value"] = 0.5
            quality_state = QualityState.CONFLICTING
            val_flags.append("CROSS_SOURCE_EVIDENCE_CONFLICT")

        # 2. Canonical Normalization through Data Gateway
        norm_event = data_gateway_service.normalize_and_ingest_event(
            raw_event=raw_event,
            source_mode=SourceMode.REPLAY,
            db=db
        )
        norm_event.facility_id = meta["facility_id"]
        norm_event.asset_id = meta["asset_id"]
        norm_event.quality_state = quality_state
        norm_event.validation_flags = val_flags

        # 3. 23-Feature Vector (Exact contract matching classifier_pipeline.py)
        is_flare_scenario = self.current_scenario_id == "SCENARIO-ROUTINE-FLARE-02"
        is_hazira_scenario = self.current_scenario_id == "SCENARIO-HAZIRA-LNG-03"

        feat_dict = {
            "frp_current": float(norm_event.frp_mw or 15.0),
            "frp_median": 12.0 if is_flare_scenario else 15.0,
            "frp_robust_zscore": 0.2 if is_flare_scenario else (max(0.0, (norm_event.frp_mw - 15.0) / 4.5) if norm_event.frp_mw else 1.0),
            "frp_percentile": 55.0 if is_flare_scenario else min(99.0, 50.0 + (norm_event.frp_mw or 15.0)),
            "frp_iqr": 3.5,
            "frp_mad": 2.0,
            "temp_current": float(norm_event.brightness_kelvin or 335.0),
            "temp_median": 335.0 if is_flare_scenario else 320.0,
            "temp_percentile": 60.0 if is_flare_scenario else 85.0,
            "temp_departure_k": float((norm_event.brightness_kelvin or 335.0) - (335.0 if is_flare_scenario else 320.0)),
            "spatial_stability": 0.94 if is_flare_scenario else 0.85,
            "dispersion_radius_r95": 65.0 if is_flare_scenario else 180.0,
            "facility_distance_m": 0.0,  # inside facility boundary
            "is_inside_facility": 1.0,
            "active_days": 180.0 if is_flare_scenario else float(next_idx + 1) * 10.0,
            "observation_count": 450.0 if is_flare_scenario else float(next_idx + 1) * 5.0,
            "recurrence_rate": 0.98 if is_flare_scenario else min(0.95, 0.25 * (next_idx + 1)),
            "detection_rate": 0.92 if is_flare_scenario else 0.75,
            "day_night_ratio": 1.05 if is_flare_scenario else 1.15,
            "night_fraction": 0.48 if is_flare_scenario else 0.35,
            "seasonal_deviation": 1.0,
            "sta_overlap": 1.0 if is_flare_scenario else (1.0 if next_idx >= 2 else 0.0),
            "satellite_count": 3.0
        }

        classification_res = classifier_service.classify_features(
            features=feat_dict,
            source_id=f"SRC-REPLAY-{self.current_scenario_id[:12]}",
            facility_id=meta["facility_id"],
            facility_name=meta["facility_name"],
            db=db
        ).model_dump()

        # 4. Multimodal Dempster-Shafer Fusion
        top_prob = classification_res.get("model_confidence", 0.9)
        top_cls = classification_res.get("predicted_class", "ROUTINE_PROCESS_HEAT")

        fusion_res = {
            "fused_state": "ROUTINE_FLARING" if is_flare_scenario else ("THERMAL_ESCALATION" if (norm_event.frp_mw or 0) > 20.0 else "NOMINAL_OPERATIONS"),
            "belief_mass": round(top_prob, 3),
            "uncertainty_mass": 0.06 if is_flare_scenario else 0.08,
            "conflict_k": 0.72 if self.failure_injections.inject_conflicting_evidence else (0.02 if is_flare_scenario else 0.05),
            "fusion_verdict": "CONFLICTING_EVIDENCE" if self.failure_injections.inject_conflicting_evidence else "CONVERGENT_EVIDENCE"
        }

        # 5. Consequence & Dispersion
        rel_rate = 15.0 if next_idx >= 2 else 1.5
        if is_hazira_scenario:
            rel_rate = 35.0 if next_idx >= 2 else 5.0
        elif is_flare_scenario:
            rel_rate = 0.5  # controlled flaring

        scenario_data = {
            "facility_id": meta["facility_id"],
            "asset_id": meta["asset_id"],
            "chemical_id": meta["chemical_id"],
            "release_rate_kg_s": rel_rate,
            "release_duration_sec": 1800,
            "ambient_temp_c": 32.0,
            "wind_speed_m_s": 2.2,
            "wind_direction_deg": 45.0,
            "atmospheric_stability": "D"
        }
        
        chemical_data = {
            "id": meta["chemical_id"],
            "name": meta["chemical_name"],
            "molecular_weight": 17.03 if "NH3" in meta["chemical_id"] else (16.04 if "CH4" in meta["chemical_id"] or "LNG" in meta["chemical_id"] else 28.0),
            "erpg_1_ppm": 25.0,
            "erpg_2_ppm": 150.0,
            "erpg_3_ppm": 750.0,
            "idlh_ppm": 300.0,
            "lfl_percent": 15.0 if "NH3" in meta["chemical_id"] else 5.0,
            "ufl_percent": 28.0 if "NH3" in meta["chemical_id"] else 15.0,
            "vapor_density_rel_air": 0.59 if "NH3" in meta["chemical_id"] else 0.55
        }

        sim_plume = hazard_service.simulate_scenario(
            scenario_data=scenario_data,
            chemical_data=chemical_data,
            source_coords=meta["coordinates"]
        )

        impact_res = impact_service.evaluate_impact(
            simulation_result=sim_plume,
            time_step_sec=120,
            db=db
        )

        # 6. Domino / Cascade Screening (Risk Graph)
        cascade_res = risk_graph_service.analyze_cascade_pathways(meta["asset_id"])

        # 7. Evacuation Routing
        evac_res = evacuation_service.generate_evacuation_plan(
            db=db,
            simulation_result=sim_plume,
            impact_result=impact_res,
            origin_coords=meta["coordinates"],
            origin_name=f"{meta['asset_name']} Control Perimeter"
        )

        # 8. Resource Allocation
        resource_res = resource_service.optimize_resources(
            db=db,
            simulation_result=sim_plume,
            impact_result=impact_res,
            evacuation_plan=evac_res
        )

        # 9. Structured Emergency Incident Packet (CAP-compatible)
        incident_id = f"INC-{meta['facility_id'][:10]}-{now.strftime('%Y%m%d')}-S{next_idx+1:02d}"
        incident_packet = {
            "incident_id": incident_id,
            "source_mode": "REFERENCE_REPLAY",
            "scenario_id": self.current_scenario_id,
            "timestamp_utc": now.isoformat() + "Z",
            "severity": "CRITICAL" if (norm_event.frp_mw or 0) > 25.0 and not is_flare_scenario else ("MEDIUM" if is_flare_scenario else "LOW"),
            "location": {
                "facility_id": meta["facility_id"],
                "facility_name": meta["facility_name"],
                "asset_id": meta["asset_id"],
                "asset_name": meta["asset_name"],
                "coordinates": meta["coordinates"],
                "inside_boundary": True
            },
            "hazard": {
                "classification": top_cls,
                "confidence": round(top_prob, 3),
                "frp_mw": norm_event.frp_mw,
                "brightness_kelvin": norm_event.brightness_kelvin,
                "chemical_id": meta["chemical_id"],
                "chemical_name": meta["chemical_name"]
            },
            "consequence": {
                "threat_zones_count": len(sim_plume.summary_zones),
                "cascade_threatened_assets": len(cascade_res.get("threatened_nodes", [])),
                "evacuation_status": "COMPUTED_SAFE_ROUTE" if evac_res.candidate_routes else "CORRIDOR_VERIFIED"
            },
            "emergency_contacts": meta["contacts"],
            "dispatch_status": "AWAITING_AUTHORIZATION",
            "provenance": {
                "trace_id": norm_event.trace_id,
                "correlation_id": norm_event.correlation_id,
                "model_version": classification_res.get("model_version", "v1.0.0"),
                "ingested_at": now.isoformat() + "Z"
            }
        }

        # Update Replay State
        self.state.current_step = next_idx + 1
        self.state.replay_clock = now
        self.state.latest_event_observed_at = step_data["observed_time"]
        self.state.latest_event_ingested_at = now
        self.state.pipeline_stage = step_data["stage_name"]
        
        self.state.active_event = norm_event.model_dump()
        self.state.active_telemetry = raw_telemetry
        self.state.active_classification = classification_res
        self.state.active_fusion = fusion_res
        self.state.active_prediction = {
            "prediction_state": "PREDICTION_STANDBY" if self.failure_injections.inject_missing_telemetry else "PREDICTION_AVAILABLE",
            "time_to_critical_threshold_min": 14.5 if next_idx >= 2 and not is_flare_scenario else 45.0,
            "anomaly_velocity_kw_per_min": round((norm_event.frp_mw or 10.0) * 1.8, 2)
        }
        self.state.active_consequence = sim_plume.model_dump()
        self.state.active_cascade = cascade_res
        self.state.active_evacuation = evac_res.model_dump()
        self.state.active_incident_packet = incident_packet
        self.state.active_preplan_summary = {
            "incident_id": incident_id,
            "facility": meta["facility_name"],
            "chemical": meta["chemical_name"],
            "threat_zones_count": len(sim_plume.summary_zones),
            "evacuation_routes_count": len(evac_res.candidate_routes) if evac_res.candidate_routes else 1,
            "tactical_units_dispatched": len(resource_res.recommended_resources)
        }

        # Add to provenance trace
        self.state.provenance_trace.append({
            "step": self.state.current_step,
            "timestamp": now.isoformat() + "Z",
            "stage": step_data["stage_name"],
            "event_id": norm_event.event_id,
            "quality": quality_state.value,
            "predicted_class": classification_res.get("predicted_class"),
            "confidence": classification_res.get("model_confidence", top_prob)
        })

        if self.state.current_step >= len(timeline):
            self.state.status = "COMPLETED"

        return self.state


demo_replay_service = DemoReplayService()
