from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class PreventiveActionOption(BaseModel):
    action_id: str
    action_type: str # ISOLATION, DEPRESSURIZATION, WATER_CURTAIN, LOAD_REDUCTION, PRE_POSITION_RESOURCES, EXCLUSION_ZONE
    title: str
    target_equipment: str
    description: str
    expected_risk_reduction_pts: float
    urgency: str # IMMEDIATE, HIGH, MODERATE
    confidence_pct: float
    estimated_execution_time_min: float
    operational_throughput_impact: str # LOW, MODERATE, HIGH_SHUTDOWN
    resource_requirements: List[str]
    safety_prerequisites: List[str]

class PreventiveEngine:
    """
    Industrial Preventive Action Recommendation Engine:
    Ranks physics-grounded engineering interventions by expected risk reduction (Delta R),
    operational feasibility, and safety priorities.
    """
    def generate_ranked_interventions(
        self,
        asset_id: str,
        chemical_id: str,
        current_risk_score: float,
        top_driver: str
    ) -> List[PreventiveActionOption]:
        
        actions: List[PreventiveActionOption] = []

        if asset_id == "T-04":
            actions = [
                PreventiveActionOption(
                    action_id="ACT-T04-ISO",
                    action_type="ISOLATION",
                    title="Remotely Actuate Remote-Operated Shut-Off Valves (ROSOV-04A/B)",
                    target_equipment="T-04 Liquid Ammonia Feed & Discharge Headers",
                    description="Isolate primary cryogenic ammonia liquid transfer headers to prevent inventory escalation into downstream process loop.",
                    expected_risk_reduction_pts=32.0,
                    urgency="IMMEDIATE",
                    confidence_pct=94.5,
                    estimated_execution_time_min=1.5,
                    operational_throughput_impact="MODERATE",
                    resource_requirements=["DCS Console Operator Authorization", "Field ERT Tag-out Verification"],
                    safety_prerequisites=["Confirm relief flare path is clear before header lock-in"]
                ),
                PreventiveActionOption(
                    action_id="ACT-T04-CURTAIN",
                    action_type="WATER_CURTAIN",
                    title="Activate Sector D Automated High-Density Water Fog Deluge Curtain",
                    target_equipment="Sector D Ammonia Tank Battery Limit Perimeter",
                    description="Deploy fixed vapor knockdown water curtains (4500 LPM) to absorb airborne ammonia aerosol prior to perimeter breach.",
                    expected_risk_reduction_pts=24.0,
                    urgency="IMMEDIATE",
                    confidence_pct=91.0,
                    estimated_execution_time_min=0.5,
                    operational_throughput_impact="LOW",
                    resource_requirements=["Dedicated Industrial Firewater Header Ring (min 7.5 bar pressure)"],
                    safety_prerequisites=["Ensure drainage retention basin sluice gates are closed to prevent sewer contamination"]
                ),
                PreventiveActionOption(
                    action_id="ACT-T04-DEPRESS",
                    action_type="DEPRESSURIZATION",
                    title="Controlled Flare Routing & Depressurization to Flare Header 02",
                    target_equipment="T-04 Cryogenic Relief Vent Loop",
                    description="Vent excess vapor to catalytic ammonia flare stack to depressurize tank vapor space from 5.8 bar down to 3.8 bar.",
                    expected_risk_reduction_pts=18.0,
                    urgency="HIGH",
                    confidence_pct=88.0,
                    estimated_execution_time_min=4.0,
                    operational_throughput_impact="LOW",
                    resource_requirements=["Flare pilot ignition active verification"],
                    safety_prerequisites=["Monitor flare stack exit temperature and thermal radiation boundary"]
                ),
                PreventiveActionOption(
                    action_id="ACT-T04-PREPOS",
                    action_type="PRE_POSITION_RESOURCES",
                    title="Pre-Position Fire Tender Alpha & Hazmat Squad at Upwind Staging Post 01",
                    target_equipment="Upwind Perimeter Sector D",
                    description="Stage Hazmat rapid response unit with Level A suits and mobile fog monitors ready for immediate flange clamp deployment.",
                    expected_risk_reduction_pts=12.0,
                    urgency="HIGH",
                    confidence_pct=96.0,
                    estimated_execution_time_min=3.0,
                    operational_throughput_impact="LOW",
                    resource_requirements=["Fire Tender Alpha", "Hazmat Squad 01", "Ambulance 01"],
                    safety_prerequisites=["Verify live wind bearing to ensure upwind standoff"]
                )
            ]
        elif asset_id == "T-03":
            actions = [
                PreventiveActionOption(
                    action_id="ACT-T03-DELUGE",
                    action_type="WATER_CURTAIN",
                    title="Activate Medium-Velocity Water Deluge Cooling Ring (10.2 L/min/m2)",
                    target_equipment="T-03 LPG Horton Sphere Shell",
                    description="Flood vessel top hemisphere and equator with continuous deluge cooling to prevent thermal skin stress and BLEVE escalation.",
                    expected_risk_reduction_pts=38.0,
                    urgency="IMMEDIATE",
                    confidence_pct=95.0,
                    estimated_execution_time_min=0.5,
                    operational_throughput_impact="LOW",
                    resource_requirements=["Firewater Ring Main (8500 LPM demand)"],
                    safety_prerequisites=["Check deluge nozzle orientation and strainer differential pressure"]
                ),
                PreventiveActionOption(
                    action_id="ACT-T03-ISO",
                    action_type="ISOLATION",
                    title="Emergency ESD Trip & Subsurface Interconnect Isolation",
                    target_equipment="PL-202 LPG Interconnect Pipeline",
                    description="Actuate subsurface double-block and bleed valves to isolate sphere inventory from Sector A units.",
                    expected_risk_reduction_pts=28.0,
                    urgency="IMMEDIATE",
                    confidence_pct=92.0,
                    estimated_execution_time_min=1.0,
                    operational_throughput_impact="HIGH_SHUTDOWN",
                    resource_requirements=["Shift Supervisor Sign-off"],
                    safety_prerequisites=["Verify pipeline thermal relief bypass valves remain functional"]
                )
            ]
        else:
            actions = [
                PreventiveActionOption(
                    action_id=f"ACT-{asset_id}-SHUT",
                    action_type="LOAD_REDUCTION",
                    title=f"Ramp Down {asset_id} Operational Throughput by 50%",
                    target_equipment=f"{asset_id} Unit Battery Limit",
                    description="Reduce process operating severity to stabilize thermal and pressure baseline parameters.",
                    expected_risk_reduction_pts=15.0,
                    urgency="MODERATE",
                    confidence_pct=85.0,
                    estimated_execution_time_min=10.0,
                    operational_throughput_impact="MODERATE",
                    resource_requirements=["Panel Operator"],
                    safety_prerequisites=["Verify balance across adjacent process units"]
                )
            ]

        # Rank actions by expected risk reduction
        actions.sort(key=lambda x: x.expected_risk_reduction_pts, reverse=True)
        return actions

preventive_engine = PreventiveEngine()
