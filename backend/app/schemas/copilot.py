from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CopilotMessage(BaseModel):
    role: str  # user, assistant, system
    content: str
    timestamp: Optional[str] = None

class CopilotChatRequest(BaseModel):
    query: str
    user_role: Optional[str] = "HSE_COMMANDER"  # FIELD_RESPONDER, HSE_COMMANDER, PLANT_MANAGER, DISTRICT_AUTHORITY, EXECUTIVE_AUTHORITY
    history: List[CopilotMessage] = []
    simulation_result: Optional[Dict[str, Any]] = None
    impact_result: Optional[Dict[str, Any]] = None
    evacuation_plan: Optional[Dict[str, Any]] = None
    resource_plan: Optional[Dict[str, Any]] = None

class CopilotChatResponse(BaseModel):
    reply: str
    intent_detected: str
    grounded_metrics: Dict[str, Any] = {}
    suggested_followups: List[str] = []
    action_recommended: Optional[str] = None
    disclaimer: str = "AI EMERGENCY COPILOT — Grounded in active REACT-X simulation telemetry."
