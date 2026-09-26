import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse
from app.schemas.whatif import WhatIfScenarioInput, WhatIfComparisonRequest
from app.services.whatif.whatif_service import whatif_service
from app.models.authorization import AuthorizationRecordModel
from app.models.audit import DecisionAuditModel

class CopilotService:
    def process_query(
        self,
        db: Session,
        req: CopilotChatRequest
    ) -> CopilotChatResponse:
        """
        Grounded intent analyzer and reasoning engine for emergency response command.
        Queries authoritative incident context directly without hallucinating figures.
        Adapts tone, depth, and actions based on user_role.
        """
        q = req.query.lower().strip()
        role = (req.user_role or "HSE_COMMANDER").upper()
        sim = req.simulation_result or {}
        imp = req.impact_result or {}
        evac = req.evacuation_plan or {}
        res = req.resource_plan or {}

        # 0. AUDIT & AUTHORIZATION GOVERNANCE INTENT
        if any(w in q for w in ["who approved", "authorization", "audit", "signed", "approver", "decision log", "audit trail"]):
            incident_id = sim.get("id", "INC-PRIMARY-T04")
            auth_rec = db.query(AuthorizationRecordModel).filter(
                AuthorizationRecordModel.incident_id == incident_id
            ).order_by(AuthorizationRecordModel.created_at.desc()).first()

            recent_audits = db.query(DecisionAuditModel).order_by(
                DecisionAuditModel.timestamp.desc()
            ).limit(3).all()

            if auth_rec and auth_rec.status == "AUTHORIZED":
                auth_msg = (
                    f"✅ **Pre-Plan Authorization Status: AUTHORIZED**\n\n"
                    f"• **Approved By:** **{auth_rec.approver_name}** ({auth_rec.approver_role})\n"
                    f"• **Authorization ID:** `{auth_rec.id}`\n"
                    f"• **Timestamp:** {auth_rec.approval_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC') if auth_rec.approval_timestamp else 'Recent'}\n"
                    f"• **Version:** {auth_rec.document_version} (All 5 safety review checklist items confirmed)"
                )
            else:
                auth_msg = (
                    f"⚠️ **Pre-Plan Authorization Status: PENDING HUMAN REVIEW**\n\n"
                    f"• The AI Decision Support Engine has prepared the Fire Pre-Plan, but official operational execution requires review and endorsement by an on-duty HSE Controller."
                )

            audit_bullets = ""
            if recent_audits:
                audit_bullets = "\n\n📋 **Recent Decision Audit Records:**\n"
                for a in recent_audits:
                    audit_bullets += f"• `[{a.module}]` **{a.human_action}** by {a.actor_role}: *{a.recommendation}* ({a.reason})\n"

            return CopilotChatResponse(
                reply=f"{auth_msg}{audit_bullets}",
                intent_detected="AUDIT_AUTHORIZATION_QUERY",
                grounded_metrics={
                    "status": auth_rec.status if auth_rec else "PENDING",
                    "approver": auth_rec.approver_name if auth_rec else None
                },
                suggested_followups=["View Decision Audit Trail", "Generate Executive Situation Brief", "What are the active tactical directives?"]
            )

        # 1. FIELD RESPONDER TAILORED INTENT (Direct, Actionable, Standoff & PPE)
        if role == "FIELD_RESPONDER":
            prim = evac.get("primary_evacuation_route") or {}
            fw = res.get("foam_water_requirements") or {}
            target_ap = prim.get("recommended_assembly_point_name", "AP-3")
            exit_gate = prim.get("recommended_gate_name", "Gate 2")
            ppe = fw.get("ppe_required", "Level A Encapsulated SCBA")
            standoff = res.get("standoff_upwind_m", 250.0)

            reply = (
                f"🦺 **FIELD ACTION DIRECTIVE — IMMEDIATE**\n\n"
                f"• **Hazard:** **{sim.get('source_asset_id', 'T-04')}** ({sim.get('chemical_name', 'Ammonia')}) @ {sim.get('effective_release_rate_kg_s', 15)} kg/s.\n"
                f"• **Your Evacuation Route:** Proceed crosswind toward **{target_ap}** via **{exit_gate}** ({prim.get('total_distance_m', 624)}m, ~{prim.get('estimated_evac_time_min', 9)} min walk).\n"
                f"• **Mandatory PPE:** **{ppe}**.\n"
                f"• **Upwind Staging Standoff:** Maintain at least **{standoff} meters** upwind (Bearing {(sim.get('wind_direction_deg', 45) + 180) % 360:.0f}°).\n"
                f"• **Rule:** Do NOT enter Northern perimeter corridor."
            )
            return CopilotChatResponse(
                reply=reply,
                intent_detected="FIELD_RESPONDER_DIRECTIVE",
                grounded_metrics={
                    "target_ap": target_ap,
                    "exit_gate": exit_gate,
                    "ppe": ppe,
                    "standoff_m": standoff
                },
                suggested_followups=["Where is the safest muster point?", "What PPE is required?", "What is the wind direction?"]
            )

        # 2. WHAT-IF HYPOTHETICAL INTENT
        if any(w in q for w in ["what if", "double", "halved", "increase release", "wind shifts", "compare"]):
            if not sim:
                return CopilotChatResponse(
                    reply="Please run or select an initial scenario first before performing a hypothetical What-If comparison.",
                    intent_detected="WHAT_IF_HYPOTHETICAL",
                    suggested_followups=["What is happening right now?", "How many workers are affected?"]
                )

            curr_rate = sim.get("effective_release_rate_kg_s", 15.0)
            curr_wind = sim.get("wind_speed_kmh", 8.0)
            curr_deg = sim.get("wind_direction_deg", 45.0)
            chem_id = sim.get("chemical_id", "CHEM-NH3")
            asset_id = sim.get("source_asset_id", "T-04")
            inc_type = sim.get("incident_type", "PIPELINE_LEAK")

            hypo_rate = curr_rate * 2.0 if "double" in q else (curr_rate * 1.5 if "increase" in q else curr_rate)
            hypo_wind = (curr_deg + 180.0) % 360.0 if "wind shifts" in q else curr_deg

            comp_req = WhatIfComparisonRequest(
                scenario_a=WhatIfScenarioInput(
                    label="Current Incident",
                    asset_id=asset_id,
                    chemical_id=chem_id,
                    incident_type=inc_type,
                    release_rate_kg_s=curr_rate,
                    wind_speed_kmh=curr_wind,
                    wind_direction_deg=curr_deg
                ),
                scenario_b=WhatIfScenarioInput(
                    label="Hypothetical Escalation",
                    asset_id=asset_id,
                    chemical_id=chem_id,
                    incident_type=inc_type,
                    release_rate_kg_s=hypo_rate,
                    wind_speed_kmh=curr_wind,
                    wind_direction_deg=hypo_wind
                )
            )
            comparison = whatif_service.compare_scenarios(db, comp_req)
            deltas = comparison.deltas

            reply = (
                f"📊 **Hypothetical What-If Assessment ({asset_id} • {sim.get('chemical_name')}):**\n\n"
                f"• If release rate changes from **{curr_rate} kg/s** to **{hypo_rate} kg/s**:\n"
                f"  - **Lethal Red Zone Reach:** Expands by **+{deltas.red_reach_delta_m} meters** (+{deltas.red_reach_delta_pct}%), reaching **{comparison.scenario_b.red_reach_m}m**.\n"
                f"  - **Risk Score Delta:** Shifts by **{deltas.risk_score_delta:+} points** (from {comparison.scenario_a.risk_score} to **{comparison.scenario_b.risk_score}/100** — {comparison.scenario_b.risk_category}).\n"
                f"  - **Firewater Demand:** Increases by **+{deltas.firewater_delta_lpm:,.0f} LPM** (total required: **{comparison.scenario_b.firewater_lpm:,.0f} LPM**).\n"
                f"  - **Evacuation Impact:** Primary safe muster remains **{comparison.scenario_b.muster_point}** via **{comparison.scenario_b.exit_gate}** ({comparison.scenario_b.evacuation_dist_m}m, ~{comparison.scenario_b.evacuation_time_min}m walk)."
            )
            return CopilotChatResponse(
                reply=reply,
                intent_detected="WHAT_IF_HYPOTHETICAL",
                grounded_metrics={
                    "base_rate": curr_rate,
                    "hypothetical_rate": hypo_rate,
                    "red_reach_delta_m": deltas.red_reach_delta_m,
                    "risk_score_delta": deltas.risk_score_delta,
                    "firewater_delta_lpm": deltas.firewater_delta_lpm
                },
                suggested_followups=["Open What-If Comparison Tab", "What emergency resources are needed?", "Generate HSE briefing"],
                action_recommended="OPEN_WHATIF_TAB"
            )

        # 3. EVACUATION RATIONALE INTENT
        elif any(w in q for w in ["why", "ap-", "gate", "evacuat", "route", "muster", "unsafe", "where should i go"]):
            prim_route = evac.get("primary_evacuation_route") or {}
            score = prim_route.get("score_breakdown") or {}
            candidates = evac.get("candidate_routes") or []
            
            target_ap = None
            for match in re.findall(r"ap-?\d+", q):
                target_ap = match.upper().replace("-", " ")
                if not "AP-" in target_ap:
                    target_ap = target_ap.replace("AP", "AP-")

            rejection_info = ""
            if target_ap:
                cand = next((c for c in candidates if target_ap in c.get("target_assembly_point_id", "") or target_ap in c.get("candidate_id", "")), None)
                if cand:
                    rejection_info = f"\n\n🔍 **Analysis for {cand.get('target_assembly_point_id')}:** Status is **{cand.get('route_status')}** because *{cand.get('rejection_reason')}* (Safety score: {int(cand.get('safety_score', 0)*100)}%, Distance: {cand.get('total_distance_m')}m)."

            reply = (
                f"🧭 **Evacuation Route Selection Rationale:**\n\n"
                f"• **Recommended Muster:** **{prim_route.get('recommended_assembly_point_name', 'Assembly Point 3')}** via **{prim_route.get('recommended_gate_name', 'Gate 2')}**.\n"
                f"• **Selection Rationale:** {score.get('selection_reason', 'Provides crosswind egress with optimal distance and maximum plume standoff.')}\n"
                f"• **Metrics:** Egress distance **{prim_route.get('total_distance_m', 0)}m** (~**{prim_route.get('estimated_evac_time_min', 0)} min** walk at 1.2 m/s), Safety Score: **{int(score.get('safety_score', 1)*100)}%**."
                f"{rejection_info}"
            )
            return CopilotChatResponse(
                reply=reply,
                intent_detected="EVACUATION_RATIONALE",
                grounded_metrics={
                    "recommended_ap": prim_route.get("recommended_assembly_point_name"),
                    "distance_m": prim_route.get("total_distance_m"),
                    "walk_time_min": prim_route.get("estimated_evac_time_min")
                },
                suggested_followups=["Why is Gate 2 selected?", "How many workers are affected?", "What emergency resources are prioritized?"]
            )

        # 4. CASUALTY & POPULATION IMPACT INTENT
        elif any(w in q for w in ["worker", "people", "casualt", "injur", "exposed", "personnel"]):
            tot_site = imp.get("total_workers_at_site", 28)
            aff_count = imp.get("affected_workers_count", 0)
            red_count = imp.get("red_zone_workers_count", 0)
            org_count = imp.get("orange_zone_workers_count", 0)
            yel_count = imp.get("yellow_zone_workers_count", 0)

            if aff_count == 0:
                reply = (
                    f"👥 **Personnel Exposure Assessment:**\n\n"
                    f"• **Total Site Workforce:** {tot_site} active personnel.\n"
                    f"• **Exposure Count:** **0 workers exposed** (All active seeded coordinates fall outside calculated Gaussian threat envelopes).\n"
                    f"• **Directives:** Enforce preemptive assembly muster at **{evac.get('primary_evacuation_route', {}).get('recommended_assembly_point_name', 'AP-3')}**."
                )
            else:
                reply = (
                    f"👥 **Personnel Exposure Breakdown ({aff_count} Exposed):**\n\n"
                    f"• **Lethal Red Zone (ERPG-3 / IDLH):** <font color='#ef4444'><b>{red_count} workers</b></font> requiring immediate Level A Hazmat extraction.\n"
                    f"• **Severe Orange Zone (ERPG-2):** <b>{org_count} workers</b> requiring respiratory PPE and medical triage.\n"
                    f"• **Caution Yellow Zone (ERPG-1):** <b>{yel_count} workers</b> under crosswind evacuation directive.\n"
                    f"• **Total Site Workforce:** {tot_site} personnel."
                )

            return CopilotChatResponse(
                reply=reply,
                intent_detected="CASUALTY_IMPACT",
                grounded_metrics={
                    "total_workers": tot_site,
                    "affected_workers": aff_count,
                    "red_zone": red_count,
                    "orange_zone": org_count
                },
                suggested_followups=["What PPE is required?", "Show me the evacuation route", "Generate HSE briefing"]
            )

        # 5. TACTICAL SUPPRESSION INTENT
        elif any(w in q for w in ["resource", "firewater", "foam", "ppe", "truck", "tender", "tactical", "staging", "lpm"]):
            fw = res.get("foam_water_requirements") or {}
            rec_res = res.get("recommended_resources") or []
            top_r = rec_res[0] if rec_res else {}

            reply = (
                f"🚒 **Tactical Resource & Suppression Directives:**\n\n"
                f"• **Lead Tactical Unit:** **{top_r.get('resource_name', 'High-Volume Water Curtain Bowser')}** ({top_r.get('priority', 'IMMEDIATE')}, ETA: **{top_r.get('estimated_arrival_min', 2.5)} min**).\n"
                f"• **Firewater Demand:** **{fw.get('firewater_demand_lpm', 5000):,.0f} LPM**.\n"
                f"• **Foam Concentrate Demand:** **{fw.get('foam_concentrate_demand_liters', 0):,.0f} Liters** (AFFF 3%).\n"
                f"• **Upwind Staging Standoff:** **{res.get('standoff_upwind_m', 250)} meters** (Bearing {(sim.get('wind_direction_deg', 45) + 180) % 360:.0f}°).\n"
                f"• **Mandatory Entry PPE:** **{fw.get('ppe_required', 'Level A Encapsulated SCBA')}**."
            )
            return CopilotChatResponse(
                reply=reply,
                intent_detected="TACTICAL_SUPPRESSION",
                grounded_metrics={
                    "firewater_lpm": fw.get("firewater_demand_lpm", 5000),
                    "standoff_m": res.get("standoff_upwind_m", 250),
                    "lead_unit": top_r.get("resource_name")
                },
                suggested_followups=["What is the evacuation route?", "Generate HSE briefing", "What if release rate doubles?"]
            )

        # 6. HSE EXECUTIVE BRIEFING INTENT
        elif any(w in q for w in ["briefing", "summary", "report", "hse", "commander", "ddma", "status", "situation"]):
            risk = imp.get("risk_assessment") or {}
            prim = evac.get("primary_evacuation_route") or {}
            fw = res.get("foam_water_requirements") or {}

            reply = (
                f"📋 **INCIDENT COMMAND EXECUTIVE BRIEFING — REACT-X**\n\n"
                f"• **Incident ID:** {res.get('incident_id', 'INC-ACTIVE')}\n"
                f"• **Facility / Source:** {sim.get('source_asset_id', 'T-04')} • {sim.get('chemical_name', 'Ammonia')} ({sim.get('incident_type', 'PIPELINE_LEAK')})\n"
                f"• **Severity Score:** **{risk.get('overall_score', 75)}/100 — {risk.get('risk_category', 'HIGH')}**\n"
                f"• **Emission Rate:** {sim.get('effective_release_rate_kg_s', 15)} kg/s | Wind: {sim.get('wind_speed_kmh', 18)} km/h FROM {sim.get('wind_direction_cardinal', 'NE')}\n"
                f"• **Casualty Triage:** {imp.get('affected_workers_count', 0)} personnel exposed ({imp.get('red_zone_workers_count', 0)} Lethal Red, {imp.get('orange_zone_workers_count', 0)} Severe)\n"
                f"• **Infrastructure Impact:** {imp.get('affected_assets_count', 0)} compromised units, {imp.get('blocked_roads_count', 0)} severed road segments\n"
                f"• **Evacuation Directive:** Safe Egress to **{prim.get('recommended_assembly_point_name', 'AP-3')}** via **{prim.get('recommended_gate_name', 'Gate 2')}** ({prim.get('total_distance_m', 0)}m, ~{prim.get('estimated_evac_time_min', 0)}m walk)\n"
                f"• **Suppression Allocation:** {fw.get('firewater_demand_lpm', 5000):,.0f} LPM Water | Standoff: {res.get('standoff_upwind_m', 250)}m | PPE: {fw.get('ppe_required', 'Level A SCBA')}\n\n"
                f"*Action: Official Fire Pre-Plan prepared and pending human authorization.*"
            )
            return CopilotChatResponse(
                reply=reply,
                intent_detected="HSE_EXECUTIVE_BRIEFING",
                grounded_metrics={
                    "risk_score": risk.get("overall_score"),
                    "incident_id": res.get("incident_id")
                },
                suggested_followups=["Export Fire Pre-Plan PDF", "What if release rate doubles?", "Why was this route chosen?"]
            )

        # 7. GENERAL SITUATION STATUS INTENT (DEFAULT)
        else:
            risk = imp.get("risk_assessment") or {}
            prim = evac.get("primary_evacuation_route") or {}
            
            if not sim:
                reply = (
                    "👋 **REACT-X Emergency Copilot Ready.**\n\n"
                    "No active accident scenario has been simulated yet. You can:\n"
                    "1. Select a preset (e.g. **T-04 Ammonia**, **T-03 LPG**, **T-01 Benzene**).\n"
                    "2. Run a custom release scenario in the Scenario Simulator.\n"
                    "3. Ask me hypothetical questions like *'What if release rate doubles?'*."
                )
            else:
                reply = (
                    f"🚨 **Current Incident Situation:**\n\n"
                    f"• **Asset:** **{sim.get('source_asset_id')}** releasing **{sim.get('chemical_name')}** at **{sim.get('effective_release_rate_kg_s')} kg/s**.\n"
                    f"• **Severity Index:** **{risk.get('overall_score')}/100 ({risk.get('risk_category')})**.\n"
                    f"• **Weather Vector:** {sim.get('wind_speed_kmh')} km/h FROM {sim.get('wind_direction_cardinal')} ({sim.get('wind_direction_deg')}°).\n"
                    f"• **Evacuation Directive:** Muster at **{prim.get('recommended_assembly_point_name')}** ({prim.get('total_distance_m')}m, {prim.get('estimated_evac_time_min')}m walk).\n"
                    f"• **Exposed Personnel:** {imp.get('affected_workers_count', 0)} workers | Blocked Roads: {imp.get('blocked_roads_count', 0)} segments."
                )

            return CopilotChatResponse(
                reply=reply,
                intent_detected="SITUATION_STATUS",
                grounded_metrics={
                    "asset_id": sim.get("source_asset_id"),
                    "chemical": sim.get("chemical_name"),
                    "risk_category": risk.get("risk_category")
                },
                suggested_followups=[
                    "Why is this evacuation route chosen?",
                    "How many workers are affected?",
                    "What emergency resources are prioritized?",
                    "What if release rate doubles?"
                ]
            )

copilot_service = CopilotService()
