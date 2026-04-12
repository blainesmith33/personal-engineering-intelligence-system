from __future__ import annotations

from typing import Any, Dict


def build_escalation_payload(
    *,
    planning_request: Dict[str, Any],
    session_snapshot: Dict[str, Any],
    raw_output: str,
    validation_result: Dict[str, Any],
    failure_case_id: str | None = None,
) -> Dict[str, Any]:
    """
    Build deterministic escalation payload for adjudication.

    This payload is the ONLY input boundary between:
    - local model (draft generator)
    - adjudicator (ChatGPT)

    It must be:
    - complete
    - explicit
    - deterministic
    """

    return {
        "artifact_type": "planning_escalation_payload",

        # Link to persisted failure artifact (if available)
        "failure_case_id": failure_case_id,

        # Original request context
        "planning_request": planning_request,

        # Session binding (authoritative)
        "session_snapshot": session_snapshot,

        # Raw model output (untrusted)
        "raw_output": raw_output,

        # Normalized output (if parser produced one)
        "normalized_output": validation_result.get("normalized_output"),

        # Explicit validation errors (REQUIRED for repair)
        "validation_errors": validation_result.get("errors", []),

        # Validation classification
        "validation_status": validation_result.get("status"),

        # Determinism binding
        "determinism_envelope": _require_determinism_envelope(session_snapshot),
    }


def _require_determinism_envelope(session_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    envelope = session_snapshot.get("determinism_envelope")

    if not isinstance(envelope, dict):
        raise ValueError("session_snapshot must include determinism_envelope")

    return envelope