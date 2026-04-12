from __future__ import annotations

from typing import Any, Callable, Dict

from peis.planning.artifact_store import ArtifactStore
from peis.planning.draft import generate_draft_plan
from peis.planning.validate import (
    STATUS_INVALID,
    STATUS_REPAIRED_VALID,
    STATUS_VALID,
    validate_and_repair,
)


def run_draft_pipeline(
    *,
    planning_request: Dict[str, Any],
    session_snapshot: Dict[str, Any],
    model_invoke_fn: Callable[[str], str],
    artifact_store: ArtifactStore,
) -> Dict[str, Any]:
    """
    Final planning pipeline:

    1. Generate grounded draft (retrieval + prompt pack)
    2. Validate / repair
    3. Persist artifacts (validated or failure)
    4. Return structured result

    This function does NOT perform ChatGPT adjudication.
    """

    # -------------------------
    # STEP 1 — GENERATE DRAFT
    # -------------------------

    raw_draft = generate_draft_plan(
        planning_request=planning_request,
        session_snapshot=session_snapshot,
        model_invoke_fn=model_invoke_fn,
        artifact_store=artifact_store,
    )

    # -------------------------
    # STEP 2 — VALIDATE
    # -------------------------

    validation_result = validate_and_repair(
        raw_draft,
        session_snapshot=session_snapshot,
    )

    status = validation_result["status"]

    # -------------------------
    # STEP 3A — SUCCESS
    # -------------------------

    if status in {STATUS_VALID, STATUS_REPAIRED_VALID}:
        validated_plan = validation_result["plan"]

        artifact_store.write_validated_plan(
            {
                "plan": validated_plan,
                "validation_result": validation_result,
                "session_snapshot": session_snapshot,
                "determinism_envelope": _require_determinism_envelope(
                    session_snapshot
                ),
            }
        )

        return {
            "status": status,
            "raw_draft": raw_draft,
            "validated_plan": validated_plan,
            "validation_result": validation_result,
            "escalation_required": False,
        }

    # -------------------------
    # STEP 3B — FAILURE
    # -------------------------

    if status == STATUS_INVALID:
        artifact_store.write_failure_case(
            {
                "raw_output": raw_draft,
                "normalized_output": validation_result.get("normalized_output"),
                "validation_errors": validation_result.get("errors", []),
                "failure_type": _classify_failure(validation_result),
                "session_snapshot": session_snapshot,
                "determinism_envelope": _require_determinism_envelope(
                    session_snapshot
                ),
            }
        )

        return {
            "status": STATUS_INVALID,
            "raw_draft": raw_draft,
            "validated_plan": None,
            "validation_result": validation_result,
            "escalation_required": True,
        }

    # -------------------------
    # UNEXPECTED STATE
    # -------------------------

    raise RuntimeError(f"unexpected validation status: {status}")


# -------------------------
# INTERNAL HELPERS
# -------------------------


def _require_determinism_envelope(session_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    envelope = session_snapshot.get("determinism_envelope")

    if not isinstance(envelope, dict):
        raise ValueError("session_snapshot must include determinism_envelope")

    return envelope


def _classify_failure(validation_result: Dict[str, Any]) -> str:
    errors = validation_result.get("errors", [])

    if not errors:
        return "UNKNOWN"

    err_text = " ".join(errors).lower()

    if "action_type" in err_text:
        return "UNKNOWN_ACTION"

    if "schema" in err_text:
        return "SCHEMA"

    if "json" in err_text:
        return "STRUCTURAL"

    return "LEGALITY"