from __future__ import annotations

from typing import Any, Dict


class PromptPackBuilder:
    """
    Builds deterministic prompt input with grounding context.
    """

    def __init__(self, prompt_version: str):
        self.prompt_version = prompt_version

    def build_prompt(
        self,
        objective: str,
        grounding: Dict[str, Any],
    ) -> str:
        """
        Construct full prompt string.
        """

        sections = []

        sections.append(self._system_header())
        sections.append(self._objective_block(objective))
        sections.append(self._grounding_block(grounding))
        sections.append(self._instruction_block())

        return "\n\n".join(sections)

    # -------------------------
    # SECTIONS
    # -------------------------

    def _system_header(self) -> str:
        return (
            f"[PROMPT_PACK_VERSION={self.prompt_version}]\n"
            "You are a deterministic planning model.\n"
            "Output STRICT JSON only."
        )

    def _objective_block(self, objective: str) -> str:
        return f"[OBJECTIVE]\n{objective}"

    def _grounding_block(self, grounding: Dict[str, Any]) -> str:
        return (
            "[GROUNDING_CONTEXT]\n"
            f"VALIDATED_EXAMPLES={grounding.get('validated_examples', [])}\n"
            f"FAILURE_EXAMPLES={grounding.get('failure_examples', [])}\n"
            f"CORRECTION_EXAMPLES={grounding.get('correction_examples', [])}"
        )

    def _instruction_block(self) -> str:
        return (
            "[INSTRUCTIONS]\n"
            "Return one JSON object:\n"
            "{\n"
            '  "objective": "...",\n'
            '  "steps": [{"action_type": "..."}]\n'
            "}\n"
            "Allowed action_type values:\n"
            "- run_pytest\n"
            "- identify_next_task\n"
            "- summarize_current_blocker\n"
            "- review_repo_state\n"
            "Routing:\n"
            "- tests -> run_pytest\n"
            "- vague/overloaded/next step -> identify_next_task\n"
            "- blocked/confused -> summarize_current_blocker\n"
            "- repo/project state -> review_repo_state\n"
            "One step only. No extra fields. No explanations."
        )