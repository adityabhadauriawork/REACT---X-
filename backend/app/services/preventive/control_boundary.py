import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

class ProposedControlAction(BaseModel):
    action_id: str
    target_asset_id: str
    action_type: str
    command_payload: Dict[str, Any]
    status: str = "PROPOSED" # PROPOSED, HUMAN_REVIEWED, AUTHORIZED, REJECTED, EXECUTED_IN_SIMULATION
    requested_by: str = "REACT-X AI Decision Support Engine"
    authorized_by: Optional[str] = None
    approver_role: Optional[str] = None
    checklist_verified: bool = False
    authorization_token: Optional[str] = None
    timestamp: datetime = datetime.now(timezone.utc)

class SafetyControlBoundary:
    """
    Non-Negotiable Safety-Control Boundary:
    Separates AI/ML analytics from safety-critical SIS/ESD/PLC execution.
    All control interventions are read-only proposals until authorized by a certified human operator.
    """
    def __init__(self):
        self.control_requests: Dict[str, ProposedControlAction] = {}

    def create_proposal(
        self,
        target_asset_id: str,
        action_type: str,
        title: str,
        command_params: Dict[str, Any]
    ) -> ProposedControlAction:
        act_id = f"REQ-CTRL-{uuid.uuid4().hex[:6].upper()}"
        prop = ProposedControlAction(
            action_id=act_id,
            target_asset_id=target_asset_id,
            action_type=action_type,
            command_payload={
                "title": title,
                "parameters": command_params,
                "mode": "PROPOSAL_ONLY_READ_ONLY"
            },
            status="PROPOSED",
            timestamp=datetime.now(timezone.utc)
        )
        self.control_requests[act_id] = prop
        return prop

    def authorize_control_action(
        self,
        action_id: str,
        approver_name: str,
        approver_role: str,
        checklist_confirmations: List[str]
    ) -> Dict[str, Any]:
        prop = self.control_requests.get(action_id)
        if not prop:
            return {"success": False, "error": f"Action ID {action_id} not found."}

        if len(checklist_confirmations) < 3:
            return {
                "success": False,
                "error": "Mandatory safety checklist incomplete. Minimum 3 engineering safety items required."
            }

        auth_token = f"AUTH-SIS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        prop.status = "AUTHORIZED"
        prop.authorized_by = approver_name
        prop.approver_role = approver_role
        prop.checklist_verified = True
        prop.authorization_token = auth_token

        return {
            "success": True,
            "action_id": action_id,
            "status": "AUTHORIZED",
            "authorization_token": auth_token,
            "approver_name": approver_name,
            "approver_role": approver_role,
            "notice": "Action authorized for DCS execution. Forwarded to Plant Control Room Interface."
        }

safety_control_boundary = SafetyControlBoundary()
