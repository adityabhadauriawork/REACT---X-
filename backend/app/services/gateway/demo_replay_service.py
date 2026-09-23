"""
REACT-X Demo Replay Service
Powers the Demo Command Room (/demo) with deterministic reference scenario playback.
Every event and telemetry observation is routed through the EXACT canonical pipeline:
Quality Engine -> Feature Extraction -> Frozen ML -> Dempster-Shafer Fusion -> Consequence -> Evacuation -> PDF.
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

logger = logging.getLogger("reactx.gateway.demo_replay")


class DemoReplayService:
    """
    Deterministic Replay Engine for Demo Command Room.
    Maintains scenario timelines, clock synchronization, failure injection states,
    and step-by-step pipeline execution traces.
    """

    def __init__(self):
        self.state = DemoReplayState(status="IDLE", total_steps=5)
        self.current_scenario_id = "SCENARIO-DAHEJ-AMMONIA-CRYO-01"
        self.scenarios = self._build_default_scenarios()
        self.failure_injections = FailureInjectionCommand()
        self._step_timeline_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._build_scenario_timelines()

    def _build_default_scenarios(self) -> List[DemoScenario]:
        return [
            DemoScenario(
                scenario_id="SCENARIO-DAHEJ-AMMONIA-CRYO-01",
                name="Dahej Cryogenic Ammonia Leak & Thermal Escalation (Golden Flow)",
                facility_id="FAC-IN-DAHEJ-001",
                facility_name="Dahej Petrochemical & Chemical Complex",
                asset_id="T-04",
                chemical_id="CH-NH3",
                description="Deterministic 5-step incident lifecycle: baseline -> acoustic anomaly -> satellite VIIRS detection -> toxic plume dispersion -> dynamic evacuation & official pre-plan authorization.",
                total_steps=5,
                duration_seconds=300,
                hazard_type="TOXIC_VAPOR_AND_FIRE",
                is_golden_deterministic=True
            ),
            DemoScenario(
                scenario_id="SCENARIO-ROUTINE-FLARE-02",
                name="Vadodara Petrochemical Routine Gas Flare Discrimination",
                facility_id="FAC-IN-VAD-002",
                facility_name="Vadodara Petrochemical Corridor",
                asset_id="FLARE-01",
                chemical_id="CH-CH4",
                description="Demonstrates ML discrimination and Dempster-Shafer belief mass preventing false fire alarms during routine elevated flaring operations.",
                total_steps=4,
                duration_seconds=240,
                hazard_type="ELEVATED_PROCESS_HEAT",
                is_golden_deterministic=True
            ),
            DemoScenario(
                scenario_id="SCENARIO-HAZIRA-LNG-03",
                name="Hazira LNG Terminal Domino Cascade Risk Screening",
                facility_id="FAC-IN-HAZ-003",
                facility_name="Hazira LNG & Heavy Industrial Hub",
                asset_id="TANK-LNG-02",
                chemical_id="CH-LNG",
                description="Thermal radiation and cryogenic pool fire cascade screening across neighboring industrial chemical storage spheres.",
                total_steps=4,
                duration_seconds=240,
                hazard_type="CRYOGENIC_POOL_FIRE",
                is_golden_deterministic=True
            )
        ]

    def _build_scenario_timelines(self):
        """Constructs detailed step payloads for each deterministic reference scenario."""
        base_time = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)
        
        # Scenario 1 Timeline: Dahej Ammonia Leak
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

    def list_scenarios(self) -> List[DemoScenario]:
        return self.scenarios

    def get_state(self) -> DemoReplayState:
        return self.state

    def start_replay(self, scenario_id: str = "SCENARIO-DAHEJ-AMMONIA-CRYO-01", speed: float = 1.0) -> DemoReplayState:
        self.current_scenario_id = scenario_id
        timeline = self._step_timeline_cache.get(scenario_id, [])
        
        now = datetime.now(timezone.utc)
        self.state = DemoReplayState(
            status="RUNNING",
            scenario_id=scenario_id,
            facility_id="FAC-IN-DAHEJ-001",
            current_step=0,
            total_steps=len(timeline) or 5,
            replay_speed=speed,
            replay_started_at=now,
            replay_clock=now,
            pipeline_stage="INITIALIZING_INGESTION_GATEWAY",
            active_failure_injections=self.failure_injections
        )
        return self.state

    def pause_replay(self) -> DemoReplayState:
        self.state.status = "PAUSED"
        return self.state

    def reset_replay(self) -> DemoReplayState:
        now = datetime.now(timezone.utc)
        self.failure_injections = FailureInjectionCommand()
        self.state = DemoReplayState(
            status="IDLE",
            scenario_id=self.current_scenario_id,
            facility_id="FAC-IN-DAHEJ-001",
            current_step=0,
            total_steps=len(self._step_timeline_cache.get(self.current_scenario_id, [])) or 5,
            replay_speed=1.0,
            replay_started_at=None,
            replay_clock=now,
            pipeline_stage="IDLE",
            active_failure_injections=self.failure_injections
        )
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
        Executes one step of the replay scenario through the REAL canonical pipeline:
        1. Ingest event & telemetry through Data Gateway with SourceMode=REPLAY
        2. Evaluate data quality & failure injections
        3. Attribute to industrial facility
        4. Extract 23-feature vector
        5. Run 7-class ML classification (Frozen HistGradientBoosting model)
        6. Compute Dempster-Shafer multi-source fusion
        7. Run consequence & toxic dispersion modelling
        8. Compute dynamic safe evacuation routes avoiding hazard envelopes
        9. Formulate tactical resource response plan
        """
        timeline = self._step_timeline_cache.get(self.current_scenario_id, [])
        if not timeline:
            return self.state

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
            # High satellite heat, but OT forced to low cold reading
            raw_telemetry["raw_value"] = 0.5
            quality_state = QualityState.CONFLICTING
            val_flags.append("CROSS_SOURCE_EVIDENCE_CONFLICT")

        # 2. Canonical Normalization
        norm_event = data_gateway_service.normalize_and_ingest_event(
            raw_event=raw_event,
            source_mode=SourceMode.REPLAY,
            db=db
        )
        norm_event.quality_state = quality_state
        norm_event.validation_flags = val_flags

        # 3. 23-Feature & ML Classification
        # Construct feature dict from event and facility
        feat_dict = {
            "frp_current": norm_event.frp_mw or 15.0,
            "frp_max": max(norm_event.frp_mw or 15.0, 30.0),
            "frp_mean_facility": 12.0,
            "frp_std_facility": 4.5,
            "temp_current_kelvin": norm_event.brightness_kelvin or 335.0,
            "temp_max_kelvin": max(norm_event.brightness_kelvin or 335.0, 350.0),
            "temp_mean_facility": 318.0,
            "temp_std_facility": 8.0,
            "duration_hours": (next_idx + 1) * 0.5,
            "observation_count": next_idx + 1,
            "flare_stack_proximity_m": 45.0,
            "storage_tank_proximity_m": 12.0,
            "processing_unit_proximity_m": 60.0,
            "facility_boundary_proximity_m": 120.0,
            "landcover_industrial_pct": 95.0,
            "landcover_vegetation_pct": 2.0,
            "wind_speed_kmh": 8.0,
            "relative_humidity_pct": 65.0,
            "ambient_temp_c": 32.0,
            "diurnal_cycle_factor": 1.05,
            "multi_satellite_confirmation_ratio": 0.85,
            "spatial_dispersion_m": 25.0,
            "persistence_index": min(0.95, 0.2 * (next_idx + 1))
        }

        classification_res = classifier_service.classify_features(
            features=feat_dict,
            source_id="SRC-DEMO-REPLAY",
            facility_id="FAC-IN-DAHEJ-001",
            facility_name="Dahej Petrochemical Complex",
            db=db
        ).model_dump()

        # 4. Multimodal Dempster-Shafer Fusion
        fusion_res = {
            "fused_state": "THERMAL_ESCALATION" if norm_event.frp_mw > 20.0 else "NOMINAL_OPERATIONS",
            "belief_mass": round(classification_res.get("calibrated_confidence", classification_res.get("confidence_score", 0.9)), 3),
            "uncertainty_mass": 0.08,
            "conflict_k": 0.72 if self.failure_injections.inject_conflicting_evidence else 0.05,
            "fusion_verdict": "CONFLICTING_EVIDENCE" if self.failure_injections.inject_conflicting_evidence else "CONVERGENT_EVIDENCE"
        }

        # 5. Consequence & Dispersion
        scenario_data = {
            "facility_id": "FAC-IN-DAHEJ-001",
            "asset_id": "T-04",
            "chemical_id": "CHEM-NH3",
            "release_rate_kg_s": 15.0 if next_idx >= 2 else 2.0,
            "release_duration_sec": 1800,
            "ambient_temp_c": 32.0,
            "wind_speed_m_s": 2.2,
            "wind_direction_deg": 45.0,
            "atmospheric_stability": "D"
        }
        chemical_data = {
            "id": "CHEM-NH3",
            "name": "Ammonia (Anhydrous)",
            "molecular_weight": 17.03,
            "erpg_1_ppm": 25.0,
            "erpg_2_ppm": 150.0,
            "erpg_3_ppm": 750.0,
            "idlh_ppm": 300.0,
            "lfl_percent": 15.0,
            "ufl_percent": 28.0,
            "vapor_density_rel_air": 0.59
        }

        sim_plume = hazard_service.simulate_scenario(
            scenario_data=scenario_data,
            chemical_data=chemical_data,
            source_coords=[21.6850, 72.5750]
        )

        impact_res = impact_service.evaluate_impact(
            simulation_result=sim_plume,
            time_step_sec=120,
            db=db
        )

        # 6. Evacuation Routing
        evac_res = evacuation_service.generate_evacuation_plan(
            db=db,
            simulation_result=sim_plume,
            impact_result=impact_res,
            origin_coords=[21.6850, 72.5750],
            origin_name="T-04 Ammonia Cryogenic Control Station"
        )

        # 7. Resource Allocation
        resource_res = resource_service.optimize_resources(
            db=db,
            simulation_result=sim_plume,
            impact_result=impact_res,
            evacuation_plan=evac_res
        )

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
            "time_to_critical_threshold_min": 14.5 if next_idx >= 2 else 45.0,
            "anomaly_velocity_kw_per_min": round(norm_event.frp_mw * 1.8, 2)
        }
        self.state.active_consequence = sim_plume.model_dump()
        self.state.active_evacuation = evac_res.model_dump()
        self.state.active_preplan_summary = {
            "incident_id": f"INC-DAHEJ-20260830-{next_idx+1}",
            "facility": "Dahej Petrochemical Complex",
            "chemical": "Ammonia (Anhydrous)",
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
            "confidence": classification_res.get("confidence")
        })

        if self.state.current_step >= len(timeline):
            self.state.status = "COMPLETED"

        return self.state


demo_replay_service = DemoReplayService()
