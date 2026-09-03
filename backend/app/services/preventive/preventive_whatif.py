from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from app.services.preventive.preventive_engine import preventive_engine

class PreventiveWhatIfRequest(BaseModel):
    asset_id: str = "T-04"
    chemical_id: str = "CHEM-NH3"
    base_risk_score: float = 82.0
    selected_action_ids: List[str] = ["ACT-T04-ISO", "ACT-T04-CURTAIN"]

class PreventiveWhatIfResponse(BaseModel):
    asset_id: str
    chemical_id: str
    base_state: Dict[str, Any]
    selected_interventions: List[Dict[str, Any]]
    mitigated_state: Dict[str, Any]
    deltas: Dict[str, Any]
    safety_summary: str
    model_metadata: Dict[str, Any]

class PreventiveWhatIfSimulator:
    """
    Simulates preventive interventions to quantify risk reduction prior to field execution.
    Fulfills the: PREDICT -> INTERVENE -> VERIFY engineering loop.
    """
    def simulate_intervention_outcome(self, req: PreventiveWhatIfRequest) -> PreventiveWhatIfResponse:
        asset_id = req.asset_id
        chem_id = req.chemical_id
        base_risk = req.base_risk_score

        # Get all possible options
        all_actions = preventive_engine.generate_ranked_interventions(asset_id, chem_id, base_risk, "Multi-Signal Overpressure & Vibration")
        action_map = {a.action_id: a for a in all_actions}

        selected = []
        cumulative_reduction = 0.0
        for act_id in req.selected_action_ids:
            act = action_map.get(act_id)
            if act:
                selected.append({
                    "action_id": act.action_id,
                    "title": act.title,
                    "type": act.action_type,
                    "risk_reduction_pts": act.expected_risk_reduction_pts,
                    "confidence_pct": act.confidence_pct,
                    "execution_time_min": act.estimated_execution_time_min
                })
                cumulative_reduction += act.expected_risk_reduction_pts

        # Apply diminishing returns formula for combined actions
        effective_reduction = round(cumulative_reduction * (1.0 - (cumulative_reduction / 200.0)), 1)
        mitigated_risk = max(12.0, round(base_risk - effective_reduction, 1))

        # Base vs Mitigated Metrics
        base_state = {
            "risk_score": base_risk,
            "risk_category": "CRITICAL" if base_risk >= 75 else ("PREVENTIVE" if base_risk >= 50 else "WATCH"),
            "max_plume_reach_m": 1749.6 if asset_id == "T-04" else 1420.0,
            "projected_threat_area_sq_m": 245000.0,
            "exposed_workers_count": 6 if asset_id == "T-04" else 4,
            "threatened_domino_assets": 3,
            "estimated_loss_rate_kg_s": 15.0
        }

        # Mitigation reduces loss rate and threat footprint
        plume_reduction_factor = max(0.2, 1.0 - (effective_reduction / 100.0) * 0.75)
        mitigated_state = {
            "risk_score": mitigated_risk,
            "risk_category": "CRITICAL" if mitigated_risk >= 75 else ("PREVENTIVE" if mitigated_risk >= 50 else "WATCH" if mitigated_risk >= 30 else "LOW"),
            "max_plume_reach_m": round(base_state["max_plume_reach_m"] * plume_reduction_factor, 1),
            "projected_threat_area_sq_m": round(base_state["projected_threat_area_sq_m"] * (plume_reduction_factor ** 2), 1),
            "exposed_workers_count": 0 if mitigated_risk < 45 else 1,
            "threatened_domino_assets": 0 if mitigated_risk < 45 else 1,
            "estimated_loss_rate_kg_s": round(base_state["estimated_loss_rate_kg_s"] * 0.25, 2)
        }

        deltas = {
            "risk_points_reduced": round(base_risk - mitigated_risk, 1),
            "risk_reduction_pct": round(((base_risk - mitigated_risk) / base_risk) * 100.0, 1),
            "plume_reach_reduction_m": round(base_state["max_plume_reach_m"] - mitigated_state["max_plume_reach_m"], 1),
            "area_reduction_pct": round((1.0 - (mitigated_state["projected_threat_area_sq_m"] / base_state["projected_threat_area_sq_m"])) * 100.0, 1),
            "workers_saved": base_state["exposed_workers_count"] - mitigated_state["exposed_workers_count"],
            "cascade_assets_protected": base_state["threatened_domino_assets"] - mitigated_state["threatened_domino_assets"]
        }

        summary = (
            f"Simulated intervention on {asset_id} successfully reduced overall risk score from "
            f"{base_risk} ({base_state['risk_category']}) to {mitigated_risk} ({mitigated_state['risk_category']}), "
            f"yielding a {deltas['risk_reduction_pct']}% risk reduction and preventing potential domino escalation "
            f"to {deltas['cascade_assets_protected']} adjacent industrial units."
        )

        return PreventiveWhatIfResponse(
            asset_id=asset_id,
            chemical_id=chem_id,
            base_state=base_state,
            selected_interventions=selected,
            mitigated_state=mitigated_state,
            deltas=deltas,
            safety_summary=summary,
            model_metadata={
                "simulation_type": "Multi-Parameter Preventive Consequence Recalculation",
                "verification_loop": "PREDICT -> INTERVENE -> VERIFY",
                "non_certified_notice": "Advisory Decision Support Model Output"
            }
        )

preventive_whatif = PreventiveWhatIfSimulator()
