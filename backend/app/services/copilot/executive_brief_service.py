from datetime import datetime
from typing import Dict, Any, List, Optional
from app.schemas.executive_brief import (
    ExecutiveSituationBriefResponse, ExecutiveBriefRequest
)

class ExecutiveBriefService:
    def generate_brief(
        self,
        simulation_result: Optional[Dict[str, Any]] = None,
        impact_result: Optional[Dict[str, Any]] = None,
        evacuation_plan: Optional[Dict[str, Any]] = None,
        resource_plan: Optional[Dict[str, Any]] = None,
        authorization_record: Optional[Dict[str, Any]] = None
    ) -> ExecutiveSituationBriefResponse:
        """
        Synthesize the authoritative Executive Situation Brief from the active multi-engine state.
        """
        sim = simulation_result or {}
        imp = impact_result or {}
        evac = evacuation_plan or {}
        res = resource_plan or {}
        auth = authorization_record or {}

        asset_id = sim.get("source_asset_id", "T-04")
        chem_name = sim.get("chemical_name", "Ammonia (Anhydrous)")
        inc_type = sim.get("incident_type", "PIPELINE_LEAK")
        rel_rate = sim.get("effective_release_rate_kg_s", 15.0)
        facility = "PetroChem Complex Alpha - Unit 04"
        location = "Dahej Industrial Zone, Gujarat"
        sector = sim.get("source_sector", "Sector A (North Cryogenic Tank Farm)")
        
        # Severity
        risk = imp.get("risk_assessment") or {}
        score = float(risk.get("overall_score", 55.3))
        category = risk.get("risk_category", "HIGH")
        escalation_trend = "EVALUATING / STABILIZING" if score < 60 else ("ELEVATED / EXPANDING" if score > 75 else "ACTIVE CONTAINMENT")

        # People
        total_workers = imp.get("total_workers_at_site", 28)
        aff_workers = imp.get("affected_workers_count", 0)
        red_workers = imp.get("red_zone_workers_count", 0)
        org_workers = imp.get("orange_zone_workers_count", 0)
        yel_workers = imp.get("yellow_zone_workers_count", 0)
        evac_status = "ACTIVE EVACUATION IN PROGRESS" if aff_workers > 0 else "PRECAUTIONARY STANDBY"
        triage_sum = f"{aff_workers} exposed of {total_workers} total site personnel ({red_workers} Lethal Red Zone, {org_workers} Severe Orange Zone)."

        # Infrastructure & Roads
        aff_assets = imp.get("affected_assets_count", 0)
        crit_units = 1 if score > 50 else 0
        blocked_roads = imp.get("blocked_roads_count", 0)
        sectors_comp = [sector]
        if aff_assets > 1:
            sectors_comp.append("Sector B (Process Interconnection)")
        site_access = f"RESTRICTED ({blocked_roads} perimeter road segment(s) blocked; Egress active)" if blocked_roads > 0 else "ALL CORRIDORS CLEAR"

        # Hazard
        summary_zones = sim.get("summary_zones", [])
        red_reach = sim.get("max_red_reach_m") or (summary_zones[0].get("max_downwind_distance_m", 285.4) if len(summary_zones) > 0 else 285.4)
        org_reach = sim.get("max_orange_reach_m") or (summary_zones[1].get("max_downwind_distance_m", 542.1) if len(summary_zones) > 1 else 542.1)
        wind_spd = sim.get("wind_speed_kmh", 8.0)
        wind_deg = sim.get("wind_direction_deg", 45.0)
        wind_card = sim.get("wind_direction_cardinal", "NE")
        wind_summary = f"{wind_spd} km/h FROM {wind_card} ({wind_deg}°)"
        plume_bearing = f"Propagating TOWARD {(wind_deg + 180) % 360:.0f}°"

        # Evacuation
        prim_route = evac.get("primary_evacuation_route") or {}
        ap_name = prim_route.get("recommended_assembly_point_name", "Assembly Point 3 (AP-3)")
        gate_name = prim_route.get("recommended_gate_name", "Gate 2 (West Perimeter)")
        dist_m = prim_route.get("total_distance_m", 623.9)
        walk_min = prim_route.get("estimated_evac_time_min", 8.7)

        # Tactical
        fw = res.get("foam_water_requirements") or {}
        firewater = fw.get("firewater_demand_lpm", 5000.0)
        foam = fw.get("foam_concentrate_demand_liters", 0.0)
        ppe = fw.get("ppe_required", "Level A Encapsulated SCBA")
        rec_res = res.get("recommended_resources") or []
        lead_unit = rec_res[0].get("resource_name", "High-Volume Water Curtain Bowser") if rec_res else "High-Volume Water Curtain Bowser"
        lead_eta = rec_res[0].get("estimated_arrival_min", 2.5) if rec_res else 2.5
        standoff = res.get("standoff_upwind_m", 250.0)
        containment = "SUPPRESSION UNITS STAGING" if rec_res else "STANDBY"

        # Governance
        auth_status = auth.get("status", "PENDING_HUMAN_AUTHORIZATION")
        approver_name = auth.get("approver_name")
        approver_role = auth.get("approver_role")
        auth_id = auth.get("id")
        auth_timestamp = auth.get("approval_timestamp")

        # Decisions & Highlights
        pending_decisions = []
        if auth_status != "AUTHORIZED":
            pending_decisions.append("Human HSE Controller authorization required on Fire Pre-Plan document.")
        if score > 60:
            pending_decisions.append("Assess District Disaster Management Authority (DDMA) offsite mutual-aid escalation.")
        if blocked_roads > 0:
            pending_decisions.append("Confirm security roadblock enforcement at Northern Perimeter corridor.")
        if not pending_decisions:
            pending_decisions.append("None — All immediate emergency containment and evacuation directives are active.")

        timeline_highlights = [
            f"T+00:00 — Emission detected at {asset_id} ({chem_name} @ {rel_rate} kg/s)",
            f"T+00:30 — Gaussian hazard envelope calculated (Red zone reach: {red_reach:.0f}m)",
            f"T+01:00 — Evacuation ordered to {ap_name} via {gate_name}",
            f"T+01:20 — Tactical suppression dispatched ({lead_unit}, {firewater:,.0f} LPM)",
            f"Status — {auth_status}"
        ]

        # Generate Beautiful Markdown Output
        md = f"""# EXECUTIVE SITUATION BRIEF — INDUSTRIAL EMERGENCY
**FACILITY:** {facility} • {location}
**INCIDENT ID:** {sim.get('id', f'INC-{asset_id}')} | **DETECTED:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

---

### 1. WHAT HAPPENED?
- **Active Incident:** {asset_id} • {chem_name} ({inc_type.replace('_', ' ')})
- **Release Rate:** {rel_rate} kg/s | **Atmospheric Vector:** {wind_summary}
- **Plume Trajectory:** {plume_bearing}
- **Affected Sector:** {sector}

### 2. HOW SERIOUS IS IT?
- **Severity Score:** **{score}/100 — {category}**
- **Escalation Status:** {escalation_trend}
- **Threat Extent:** Lethal Red Zone reach **{red_reach:.0f}m** | Severe Orange Zone reach **{org_reach:.0f}m**

### 3. WHO & WHAT IS AFFECTED?
- **Personnel:** {triage_sum}
- **Infrastructure:** {aff_assets} compromised plant units, {blocked_roads} blocked road segment.
- **Site Accessibility:** {site_access}

### 4. IS IT UNDER CONTROL & WHAT IS BEING DONE?
- **Evacuation:** {evac_status} → Safe egress corridor to **{ap_name}** via **{gate_name}** ({dist_m}m, ~{walk_min} min walk).
- **Tactical Containment:** {containment}
  - **Lead Unit:** {lead_unit} (ETA: {lead_eta} min)
  - **Suppression Demand:** {firewater:,.0f} LPM Water | {foam:,.0f} L Foam | PPE: {ppe}
  - **Upwind Standoff:** {standoff}m

### 5. GOVERNANCE & PENDING DECISIONS
- **Fire Pre-Plan Authorization:** **{auth_status}** {f'by {approver_name} ({approver_role})' if approver_name else '(Requires Human HSE Approval)'}
- **Action Items Requiring Attention:**
"""
        for pd in pending_decisions:
            md += f"  - {pd}\n"

        md += "\n---\n*Industrial Decision Support System — REACT-X Decision Support Engine*"

        return ExecutiveSituationBriefResponse(
            incident_id=sim.get("id", f"INC-{asset_id}"),
            incident_title=f"{asset_id} {chem_name} Emergency",
            facility_name=facility,
            location=location,
            sector=sector,
            source_asset=asset_id,
            chemical=chem_name,
            incident_type=inc_type,
            detected_time_iso=datetime.utcnow().isoformat() + "Z",
            severity_score=score,
            severity_category=category,
            escalation_trend=escalation_trend,
            workforce_site_total=total_workers,
            exposed_workers_count=aff_workers,
            red_zone_lethal_count=red_workers,
            orange_zone_severe_count=org_workers,
            yellow_zone_caution_count=yel_workers,
            evacuation_status=evac_status,
            casualty_triage_summary=triage_sum,
            compromised_assets_count=aff_assets,
            critical_units_threatened=crit_units,
            blocked_road_segments_count=blocked_roads,
            compromised_sectors=sectors_comp,
            site_accessibility_status=site_access,
            max_red_reach_m=red_reach,
            max_orange_reach_m=org_reach,
            wind_vector_summary=wind_summary,
            plume_bearing_summary=plume_bearing,
            primary_assembly_point=ap_name,
            primary_exit_gate=gate_name,
            evacuation_distance_m=dist_m,
            estimated_walk_time_min=walk_min,
            lead_tactical_unit=lead_unit,
            lead_unit_eta_min=lead_eta,
            firewater_demand_lpm=firewater,
            foam_demand_liters=foam,
            mandatory_ppe=ppe,
            staging_standoff_m=standoff,
            containment_status=containment,
            human_authorization_status=auth_status,
            approver_name=approver_name,
            approver_role=approver_role,
            authorization_id=auth_id,
            authorization_timestamp=str(auth_timestamp) if auth_timestamp else None,
            pending_decisions=pending_decisions,
            timeline_highlights=timeline_highlights,
            formatted_brief_markdown=md,
            prototype_disclaimer="PROTOTYPE EXECUTIVE SITUATION BRIEF — Operational Decision Support"
        )

executive_brief_service = ExecutiveBriefService()
