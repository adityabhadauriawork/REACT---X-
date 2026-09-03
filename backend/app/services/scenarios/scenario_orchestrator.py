import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.schemas.incident_packet import IncidentPacket, IncidentEvidence
from app.services.predictive.early_warning_engine import early_warning_engine
from app.services.graph.risk_graph_service import risk_graph_service
from app.services.preventive.preventive_engine import preventive_engine
from app.services.preventive.preventive_whatif import preventive_whatif, PreventiveWhatIfRequest

class ScenarioOrchestrator:
    """
    Orchestrates the 19-Stage T-04 Ammonia End-to-End Demonstration Scenario:
    Demonstrates the complete lifecycle:
    PREDICT -> PREVENT -> PROTECT -> PREPARE -> RESPOND -> LEARN
    """
    STAGES = [
        {"stage": 1, "name": "Nominal Baseline", "phase": "PREDICT", "desc": "T-04 Ammonia Tank operating normally at 4.2 bar, 1.2 mm/s vibration, -33°C skin temperature."},
        {"stage": 2, "name": "Pressure Inception Drift", "phase": "PREDICT", "desc": "Operating pressure drifts upward to 5.2 bar due to header boil-off valve restriction."},
        {"stage": 3, "name": "Mechanical Vibration Anomaly", "phase": "PREDICT", "desc": "Compressor shaft & flange vibration rises to 5.4 mm/s indicating seal instability."},
        {"stage": 4, "name": "Thermal & Optical Anomaly", "phase": "PREDICT", "desc": "Thermal camera detects localized hotspot (88.4°C) on compressor bearing."},
        {"stage": 5, "name": "Multi-Signal Early Warning", "phase": "PREDICT", "desc": "Early Warning Engine detects combined excursion; state elevates to PREVENTIVE/CRITICAL (Score: 78.4)."},
        {"stage": 6, "name": "Risk Acceleration", "phase": "PREDICT", "desc": "Composite risk rises rapidly; acoustic ultrasonic leak detector registers 38 dB."},
        {"stage": 7, "name": "Root-Cause Identification", "phase": "PREDICT", "desc": "System isolates T-04 cryogenic transfer header as authoritative hazard epicenter."},
        {"stage": 8, "name": "Cascade & Domino Screening", "phase": "PREVENT", "desc": "Risk Graph reveals PU-02 Ammonia Loop (45m) and PL-101 header as threatened units."},
        {"stage": 9, "name": "Preventive Action Evaluation", "phase": "PREVENT", "desc": "Preventive Engine generates ranked interventions: ROSOV Isolation + Perimeter Water Curtain."},
        {"stage": 10, "name": "Simulated Preventive What-If", "phase": "PREVENT", "desc": "Simulating isolation confirms risk reduction from 82 to 34 (-58.5% drop), preventing breach."},
        {"stage": 11, "name": "Simulated Escalation (Loss of Containment)", "phase": "PROTECT", "desc": "Demonstrating unmitigated path: Flange seal ruptures releasing 15.0 kg/s anhydrous ammonia."},
        {"stage": 12, "name": "Atmospheric Plume Dispersion", "phase": "PROTECT", "desc": "Gaussian plume model projects Red (ERPG-3/IDLH) reach 1750m downwind along SSW wind vector."},
        {"stage": 13, "name": "Spatial Consequence & Worker Impact", "phase": "PROTECT", "desc": "Point-in-polygon identifies 6 workers in Red/Orange zones and 4 severed access road links."},
        {"stage": 14, "name": "Dynamic Evacuation Routing", "phase": "PREPARE", "desc": "Dijkstra safe graph engine diverts workers to Assembly Point 3 (West Perimeter) via Gate 2."},
        {"stage": 15, "name": "Tactical Resource Allocation", "phase": "RESPOND", "desc": "Dispatches Water Bowser for vapor knockdown, Level A Hazmat squad, and Medical triage."},
        {"stage": 16, "name": "Human-in-the-Loop Sign-Off", "phase": "RESPOND", "desc": "HSE Controller completes mandatory 5-point checklist and formally authorizes pre-plan v1.0."},
        {"stage": 17, "name": "Decision Audit Trail", "phase": "LEARN", "desc": "Every computational hypothesis and operator decision is committed to persistent immutable audit log."},
        {"stage": 18, "name": "Executive Situation Brief", "phase": "LEARN", "desc": "1-click 12-point executive brief synthesized answering the 6 core executive questions."},
        {"stage": 19, "name": "Post-Incident Forensic Learning", "phase": "LEARN", "desc": "Pre/post event telemetry windows, evidence clips, and timeline archived for turnaround audit."}
    ]

    def get_stages_roster(self) -> List[Dict[str, Any]]:
        return self.STAGES

    def execute_stage(self, stage_number: int) -> Dict[str, Any]:
        """
        Executes a specific stage of the 19-stage storyline and returns the authoritative state.
        """
        stage_num = max(1, min(19, stage_number))
        stage_meta = self.STAGES[stage_num - 1]

        # Stage specific state generation
        if stage_num == 1:
            ew = early_warning_engine.evaluate_asset_pre_incident_state("T-04", "Ammonia Tank", "Ammonia", 4.2, -33.0, 1.2, 14.0, 90)
        elif stage_num in [2, 3, 4]:
            ew = early_warning_engine.evaluate_asset_pre_incident_state("T-04", "Ammonia Tank", "Ammonia", 5.2, -28.0, 4.8, 28.0, 280, vision_thermal_anomaly=(stage_num == 4))
        elif stage_num in [5, 6, 7]:
            ew = early_warning_engine.evaluate_asset_pre_incident_state("T-04", "Ammonia Tank", "Ammonia", 5.8, -22.0, 6.8, 42.0, 310, vision_thermal_anomaly=True)
        elif stage_num in [8, 9, 10]:
            ew = early_warning_engine.evaluate_asset_pre_incident_state("T-04", "Ammonia Tank", "Ammonia", 5.8, -22.0, 6.8, 42.0, 310, vision_thermal_anomaly=True)
        else: # Stages 11-19 (Active Emergency & Resolution)
            ew = early_warning_engine.evaluate_asset_pre_incident_state("T-04", "Ammonia Tank", "Ammonia", 6.5, -15.0, 7.5, 48.0, 310, vision_thermal_anomaly=True)

        cascade = risk_graph_service.analyze_cascade_pathways("T-04")
        env = risk_graph_service.evaluate_environmental_consequence("T-04", 195.0)
        interventions = preventive_engine.generate_ranked_interventions("T-04", "CHEM-NH3", ew["early_warning_score"], ew["top_driver"])
        
        whatif_sim = None
        if stage_num >= 9:
            whatif_sim = preventive_whatif.simulate_intervention_outcome(PreventiveWhatIfRequest(
                asset_id="T-04", chemical_id="CHEM-NH3", base_risk_score=ew["early_warning_score"],
                selected_action_ids=["ACT-T04-ISO", "ACT-T04-CURTAIN"]
            ))

        packet = IncidentPacket(
            incident_id=f"INC-T04-DEMO-S{stage_num:02d}",
            title=f"Stage {stage_num}: {stage_meta['name']}",
            hazard_type="TOXIC_RELEASE" if stage_num >= 11 else "OVERPRESSURE_LEAK_WARNING",
            source_asset_id="T-04",
            chemical_id="CHEM-NH3",
            chemical_name="Ammonia (Anhydrous)",
            risk_score=ew["early_warning_score"],
            risk_category=ew["state"],
            confidence=ew["confidence_pct"] / 100.0,
            affected_zone="Sector D - Cryogenic Yard",
            status="OPEN" if stage_num < 16 else "ACKNOWLEDGED",
            leading_indicators=[d["driver"] for d in ew["drivers_breakdown"] if d["score"] > 8.0],
            evidence=IncidentEvidence(
                early_warning_drivers=ew["drivers_breakdown"],
                risk_graph_threats=cascade["threatened_nodes"]
            ),
            recommended_preventive_action=ew["recommended_preventive_action"],
            recommended_emergency_action="Deploy wide-angle fog curtains and evacuate to AP-3 via Gate 2" if stage_num >= 11 else None
        )

        return {
            "stage_number": stage_num,
            "stage_name": stage_meta["name"],
            "phase": stage_meta["phase"],
            "description": stage_meta["desc"],
            "incident_packet": packet.model_dump(),
            "early_warning_evaluation": ew,
            "cascade_pathways": cascade,
            "environmental_receptors": env,
            "preventive_options": [i.model_dump() for i in interventions],
            "preventive_whatif_outcome": whatif_sim.model_dump() if whatif_sim else None
        }

scenario_orchestrator = ScenarioOrchestrator()
