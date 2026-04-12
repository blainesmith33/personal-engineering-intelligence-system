from typing import Any, Dict, Literal, TypedDict, Optional


class OrchestrationInput(TypedDict):
    planning_request: Dict[str, Any]
    session_snapshot: Dict[str, Any]


class ValidPlanResult(TypedDict):
    status: Literal["VALID"]
    plan: Dict[str, Any]


class EscalationResult(TypedDict):
    status: Literal["ESCALATED"]
    escalation_payload: Dict[str, Any]


OrchestrationResult = ValidPlanResult | EscalationResult