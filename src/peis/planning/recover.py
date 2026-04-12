from __future__ import annotations

from typing import Any, Callable, Dict

from peis.planning.artifact_store import ArtifactStore
from peis.planning.escalation import build_escalation_payload
from peis.planning.pipeline import run_draft_pipeline
from peis.planning.validate import (
    STATUS_INVALID,
    STATUS_REPAIRED_VALID,
    STATUS_VALID,
    validate_and_repair,
)


def run_recovery_pipeline(
    *,
    planning_request: Dict[str, Any],
    session_snapshot: Dict[str, Any],
    model_invoke_fn: Callable[[str], str],
    adjudicate_fn: Callable[[Dict[str, Any]], str],
    artifact_store: ArtifactStore,
) -> Dict[str, Any]:
    """
    Full planning recovery pipeline.

    Flow:
    1. Run the normal draft pipeline
    2. If valid, return immediately
    3. If invalid, build escalation payload
    4. Run a single adjudication pass
    5. Re-validate adjudicated output
    6. Persist correction artifact if repaired
    7. Hard-fail if still invalid

    No multi-pass repair loops are allowed.
    """

    pipeline_result = run_draft_pipeline(
        planning_request=planning_request,
        session_snapshot=session_snapshot,
        model_invoke_fn=model_invoke_fn,
        artifact_store=artifact_store,
    )

    if not pipeline_result["escalation_required"]:
        return {
            **pipeline_result,
            "adjudicated_output": None,
            "adjudicated_validation_result": None,
            "escalation_payload": None,
            "hard_fail": False,
        }

    escalation_payload = build_escalation_payload(
        planning_request=planning_request,
        session_snapshot=session_snapshot,
        raw_output=pipeline_result["raw_draft"],
        validation_result=pipeline_result["validation_result"],
        failure_case_id=None,
    )

    adjudicated_output = adjudicate_fn(escalation_payload)

    adjudicated_validation_result = validate_and_repair(
        adjudicated_output,
        session_snapshot=session_snapshot,
    )

    adjudicated_status = adjudicated_validation_result["status"]

    if adjudicated_status in {STATUS_VALID, STATUS_REPAIRED_VALID}:
        validated_plan = adjudicated_validation_result["plan"]

        validated_plan_id = artifact_store.write_validated_plan(
            {
                "plan": validated_plan,
                "validation_result": adjudicated_validation_result,
                "session_snapshot": session_snapshot,
                "determinism_envelope": _require_determinism_envelope(
                    session_snapshot
                ),
            }
        )

        correction_case_id = artifact_store.write_correction_case(
            {
                "original_failure_id": _extract_failure_case_id(escalation_payload),
                "original_output": pipeline_result["raw_draft"],
                "corrected_output": adjudicated_validation_result.get(
                    "normalized_output",
                    validated_plan,
                ),
                "correction_type": "CHATGPT_ADJUDICATION",
                "diff_summary": _build_diff_summary(
                    original_output=pipeline_result["raw_draft"],
                    corrected_output=adjudicated_validation_result.get(
                        "normalized_output",
                        validated_plan,
                    ),
                ),
                "validation_result": adjudicated_validation_result,
                "session_snapshot": session_snapshot,
                "determinism_envelope": _require_determinism_envelope(
                    session_snapshot
                ),
            }
        )

        return {
            "status": adjudicated_status,
            "raw_draft": pipeline_result["raw_draft"],
            "validated_plan": validated_plan,
            "validation_result": pipeline_result["validation_result"],
            "escalation_required": False,
            "escalation_payload": escalation_payload,
            "adjudicated_output": adjudicated_output,
            "adjudicated_validation_result": adjudicated_validation_result,
            "validated_plan_id": validated_plan_id,
            "correction_case_id": correction_case_id,
            "hard_fail": False,
        }

    if adjudicated_status == STATUS_INVALID:
        return {
            "status": STATUS_INVALID,
            "raw_draft": pipeline_result["raw_draft"],
            "validated_plan": None,
            "validation_result": pipeline_result["validation_result"],
            "escalation_required": True,
            "escalation_payload": escalation_payload,
            "adjudicated_output": adjudicated_output,
            "adjudicated_validation_result": adjudicated_validation_result,
            "hard_fail": True,
        }

    raise RuntimeError(f"unexpected adjudicated validation status: {adjudicated_status}")


def _require_determinism_envelope(session_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    envelope = session_snapshot.get("determinism_envelope")

    if not isinstance(envelope, dict):
        raise ValueError("session_snapshot must include determinism_envelope")

    return envelope


def _extract_failure_case_id(escalation_payload: Dict[str, Any]) -> str | None:
    value = escalation_payload.get("failure_case_id")

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _build_diff_summary(
    *,
    original_output: str,
    corrected_output: Any,
) -> str:
    corrected_repr = (
        corrected_output if isinstance(corrected_output, str) else str(corrected_output)
    )

    if original_output == corrected_repr:
        return "no structural change"

    return "adjudicated output differs from original failed draft"