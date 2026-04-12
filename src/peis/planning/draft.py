from __future__ import annotations

from typing import Any, Callable, Dict

from peis.planning.artifact_store import ArtifactStore
from peis.planning.prompt_pack import PromptPackBuilder
from peis.planning.retrieval import PlanningRetrieval


def generate_draft_plan(
    *,
    planning_request: Dict[str, Any],
    session_snapshot: Dict[str, Any],
    model_invoke_fn: Callable[[str], str],
    artifact_store: ArtifactStore,
) -> str:
    """
    Generate a draft plan using the local model with deterministic grounding.

    model_invoke_fn must be a callable:
        fn(prompt: str) -> str

    This function:
    - retrieves relevant prior planning artifacts
    - builds a deterministic prompt pack
    - invokes the model
    - returns raw model output unchanged
    """

    objective = _extract_objective(planning_request)

    retrieval = PlanningRetrieval(store=artifact_store)
    grounding = retrieval.build_grounding_context(objective=objective)

    prompt_pack_version = _extract_prompt_pack_version(session_snapshot)
    prompt_builder = PromptPackBuilder(prompt_version=prompt_pack_version)

    prompt = prompt_builder.build_prompt(
        objective=objective,
        grounding=grounding,
    )

    raw_output = model_invoke_fn(prompt)
    return raw_output


def _extract_objective(planning_request: Dict[str, Any]) -> str:
    """
    Extract the planning objective from the normalized planning request.
    """
    objective = planning_request.get("objective")

    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("planning_request.objective must be a non-empty string")

    return objective.strip()


def _extract_prompt_pack_version(session_snapshot: Dict[str, Any]) -> str:
    """
    Extract the prompt pack version from the session snapshot.
    """
    prompt_pack_version = session_snapshot.get("prompt_pack_version")

    if not isinstance(prompt_pack_version, str) or not prompt_pack_version.strip():
        raise ValueError("session_snapshot.prompt_pack_version must be a non-empty string")

    return prompt_pack_version.strip()