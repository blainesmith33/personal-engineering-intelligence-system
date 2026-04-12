from __future__ import annotations

from typing import Any, Dict, List

from .artifact_store import ArtifactStore


class RetrievalError(ValueError):
    pass


class PlanningRetrieval:
    """
    Retrieval layer for planning grounding.

    Pulls prior artifacts and selects relevant examples
    to inject into prompt construction.
    """

    def __init__(self, store: ArtifactStore):
        self.store = store

    # -------------------------
    # PUBLIC API
    # -------------------------

    def build_grounding_context(
        self,
        objective: str,
        max_examples: int = 1,
    ) -> Dict[str, Any]:
        """
        Build structured grounding context for prompt injection.
        """

        validated = self.store.get_validated_plans()
        failures = self.store.get_failure_cases()
        corrections = self.store.get_correction_cases()

        selected_validated = self._select_validated(validated, objective, max_examples)
        selected_failures = self._select_failures(failures, max_examples)
        selected_corrections = self._select_corrections(corrections, max_examples)

        return {
            "validated_examples": [
                self._compact_validated_example(item) for item in selected_validated
            ],
            "failure_examples": [
                self._compact_failure_example(item) for item in selected_failures
            ],
            "correction_examples": [
                self._compact_correction_example(item) for item in selected_corrections
            ],
        }

    # -------------------------
    # SELECTION LOGIC
    # -------------------------

    def _select_validated(
        self,
        items: List[Dict[str, Any]],
        objective: str,
        k: int,
    ) -> List[Dict[str, Any]]:
        """
        Naive relevance: keyword overlap on objective.
        Deterministic.
        """

        scored = []

        for item in items:
            plan_obj = item.get("plan", {}).get("objective", "")
            score = self._overlap_score(objective, plan_obj)
            scored.append((score, item))

        scored.sort(key=lambda x: (-x[0], self._stable_id(x[1])))
        return [x[1] for x in scored[:k]]

    def _select_failures(
        self,
        items: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """
        Select most recent failures (deterministic ordering via ID).
        """

        items_sorted = sorted(items, key=self._stable_id)
        return items_sorted[-k:]

    def _select_corrections(
        self,
        items: List[Dict[str, Any]],
        k: int,
    ) -> List[Dict[str, Any]]:
        """
        Select corrections (prefer diversity via ID ordering).
        """

        items_sorted = sorted(items, key=self._stable_id)
        return items_sorted[:k]

    # -------------------------
    # COMPACTION
    # -------------------------

    def _compact_validated_example(self, item: Dict[str, Any]) -> Dict[str, Any]:
        plan = item.get("plan", {})
        return {
            "objective": plan.get("objective", ""),
            "steps": self._extract_steps(plan.get("steps", [])),
        }

    def _compact_failure_example(self, item: Dict[str, Any]) -> Dict[str, Any]:
        normalized_output = item.get("normalized_output", "")
        return {
            "failure_type": item.get("failure_type", ""),
            "validation_errors": item.get("validation_errors", []),
            "raw_output": normalized_output if isinstance(normalized_output, str) else "",
        }

    def _compact_correction_example(self, item: Dict[str, Any]) -> Dict[str, Any]:
        validation_result = item.get("validation_result", {})
        corrected_plan = validation_result.get("plan", {})

        return {
            "correction_type": item.get("correction_type", ""),
            "corrected_objective": corrected_plan.get("objective", ""),
            "corrected_steps": self._extract_steps(corrected_plan.get("steps", [])),
        }

    def _extract_steps(self, steps: Any) -> List[Dict[str, str]]:
        if not isinstance(steps, list):
            return []

        compact_steps: List[Dict[str, str]] = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            action_type = step.get("action_type")
            if isinstance(action_type, str) and action_type.strip():
                compact_steps.append({"action_type": action_type.strip()})

        return compact_steps

    # -------------------------
    # UTIL
    # -------------------------

    def _overlap_score(self, a: str, b: str) -> int:
        a_set = set(a.lower().split())
        b_set = set(b.lower().split())
        return len(a_set.intersection(b_set))

    def _stable_id(self, item: Dict[str, Any]) -> str:
        for key in [
            "validated_plan_id",
            "failure_case_id",
            "correction_case_id",
        ]:
            if key in item:
                return item[key]
        return ""