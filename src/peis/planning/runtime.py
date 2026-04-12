from __future__ import annotations

from typing import Any, Callable, Dict

from peis.planning.artifact_store import ArtifactStore
from peis.planning.recover import run_recovery_pipeline


class PEISRuntimeError(RuntimeError):
    pass


class PlanningRuntime:
    """
    Entry point for PEIS planning system.

    This is the ONLY interface that external systems (Open WebUI, local AI, etc.)
    should call.

    It enforces:
    - full pipeline execution
    - adjudication loop
    - artifact persistence
    - deterministic boundaries
    """

    def __init__(
        self,
        *,
        artifact_store: ArtifactStore,
        model_invoke_fn: Callable[[str], str],
        adjudicate_fn: Callable[[Dict[str, Any]], str],
    ):
        self.artifact_store = artifact_store
        self.model_invoke_fn = model_invoke_fn
        self.adjudicate_fn = adjudicate_fn

    # -------------------------
    # PUBLIC API
    # -------------------------

    def run(
        self,
        *,
        planning_request: Dict[str, Any],
        session_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute full planning lifecycle.

        This is what your UI calls.
        """

        self._validate_inputs(planning_request, session_snapshot)

        result = run_recovery_pipeline(
            planning_request=planning_request,
            session_snapshot=session_snapshot,
            model_invoke_fn=self.model_invoke_fn,
            adjudicate_fn=self.adjudicate_fn,
            artifact_store=self.artifact_store,
        )

        return self._normalize_output(result)

    # -------------------------
    # INTERNALS
    # -------------------------

    def _validate_inputs(
        self,
        planning_request: Dict[str, Any],
        session_snapshot: Dict[str, Any],
    ) -> None:
        if not isinstance(planning_request, dict):
            raise PEISRuntimeError("planning_request must be a dict")

        if not isinstance(session_snapshot, dict):
            raise PEISRuntimeError("session_snapshot must be a dict")

        if "objective" not in planning_request:
            raise PEISRuntimeError("planning_request must include 'objective'")

        if "determinism_envelope" not in session_snapshot:
            raise PEISRuntimeError(
                "session_snapshot must include determinism_envelope"
            )

    def _normalize_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize runtime output for UI consumption.

        This is the ONLY place allowed to reshape output.
        """

        had_adjudication = result.get("adjudicated_output") is not None

        if had_adjudication:
            final_validation_status = (
                result.get("adjudicated_validation_result", {}).get("status")
            )
        else:
            final_validation_status = (
                result.get("validation_result", {}).get("status")
            )

        return {
            "status": result["status"],
            "plan": result.get("validated_plan"),
            "escalation_required": result.get("escalation_required", False),
            "hard_fail": result.get("hard_fail", False),
            "meta": {
                "had_adjudication": had_adjudication,
                "validation_status": final_validation_status,
            },
        }