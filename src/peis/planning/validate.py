import json
import re
from typing import Any, Dict, List, Optional

from peis.planning.contracts import get_allowed_action_types


STATUS_VALID = "VALID"
STATUS_REPAIRED_VALID = "REPAIRED_VALID"
STATUS_INVALID = "INVALID"

_ALLOWED_TOP_LEVEL_KEYS = {"objective", "steps"}
_ALLOWED_STEP_KEYS = {"action_type"}


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()

    fenced_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        stripped,
        flags=re.DOTALL,
    )
    if fenced_match:
        return fenced_match.group(1).strip()

    return stripped


def _extract_first_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def _normalize_steps(value: Any) -> Optional[List[Dict[str, Any]]]:
    if value is None:
        return None
    if not isinstance(value, list):
        return None

    normalized: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(item)

    return normalized


def _basic_plan_shape_repair(plan: Dict[str, Any]) -> Dict[str, Any]:
    repaired = dict(plan)

    objective = repaired.get("objective")
    if isinstance(objective, str):
        repaired["objective"] = objective.strip()

    steps = _normalize_steps(repaired.get("steps"))
    if steps is not None:
        normalized_steps: List[Dict[str, Any]] = []
        for step in steps:
            normalized_step = dict(step)

            action_type = normalized_step.get("action_type")
            if isinstance(action_type, str):
                normalized_step["action_type"] = action_type.strip()

            normalized_steps.append(normalized_step)

        repaired["steps"] = normalized_steps

    return repaired


def _validate_plan_shape(
    plan: Dict[str, Any],
    session_snapshot: Optional[Dict[str, Any]] = None,
) -> List[str]:
    errors: List[str] = []

    if not isinstance(plan, dict):
        return ["parsed payload is not a JSON object"]

    if not plan:
        errors.append("plan object is empty")
        return errors

    unknown_top_level_keys = sorted(set(plan.keys()) - _ALLOWED_TOP_LEVEL_KEYS)
    if unknown_top_level_keys:
        errors.append(
            f"unknown top-level field(s): {', '.join(unknown_top_level_keys)}"
        )

    if "objective" not in plan:
        errors.append("missing required field: objective")
    elif not isinstance(plan["objective"], str) or not plan["objective"].strip():
        errors.append("objective must be a non-empty string")

    if "steps" not in plan:
        errors.append("missing required field: steps")
        return errors

    if not isinstance(plan["steps"], list):
        errors.append("steps must be a list")
        return errors

    if len(plan["steps"]) == 0:
        errors.append("steps must not be empty")
        return errors

    allowed_action_types = (
        get_allowed_action_types(session_snapshot)
        if session_snapshot is not None
        else set()
    )

    for index, step in enumerate(plan["steps"]):
        if not isinstance(step, dict):
            errors.append(f"steps[{index}] must be an object")
            continue

        unknown_step_keys = sorted(set(step.keys()) - _ALLOWED_STEP_KEYS)
        if unknown_step_keys:
            errors.append(
                f"steps[{index}] unknown field(s): {', '.join(unknown_step_keys)}"
            )

        if "action_type" not in step:
            errors.append(f"steps[{index}] missing required field: action_type")
            continue

        action_type = step["action_type"]
        if not isinstance(action_type, str) or not action_type.strip():
            errors.append(f"steps[{index}].action_type must be a non-empty string")
            continue

        if allowed_action_types and action_type not in allowed_action_types:
            errors.append(
                f"steps[{index}].action_type is not allowed in this session: {action_type}"
            )

    return errors


def validate_and_repair(
    raw_output: str,
    session_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate and lightly repair raw model output.

    If session_snapshot is provided, enforce capability legality using the
    allowed action types bound to that session.

    Returns:
        {
          "status": "VALID" | "REPAIRED_VALID" | "INVALID",
          "plan": dict | None,
          "errors": list[str],
          "raw_output": str,
          "normalized_output": str | None
        }
    """

    errors: List[str] = []
    repaired = False

    if not isinstance(raw_output, str):
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": ["raw_output must be a string"],
            "raw_output": raw_output,
            "normalized_output": None,
        }

    normalized = raw_output.strip()
    if not normalized:
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": ["raw_output is empty"],
            "raw_output": raw_output,
            "normalized_output": None,
        }

    stripped = _strip_code_fences(normalized)
    if stripped != normalized:
        repaired = True
    normalized = stripped

    candidate_json = _extract_first_json_object(normalized)
    if candidate_json is None:
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": ["no JSON object found in raw_output"],
            "raw_output": raw_output,
            "normalized_output": normalized,
        }

    if candidate_json != normalized:
        repaired = True
    normalized = candidate_json

    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError as exc:
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": [f"invalid JSON: {exc.msg}"],
            "raw_output": raw_output,
            "normalized_output": normalized,
        }

    if not isinstance(parsed, dict):
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": ["top-level JSON value must be an object"],
            "raw_output": raw_output,
            "normalized_output": normalized,
        }

    repaired_plan = _basic_plan_shape_repair(parsed)
    if repaired_plan != parsed:
        repaired = True

    shape_errors = _validate_plan_shape(
        repaired_plan,
        session_snapshot=session_snapshot,
    )
    if shape_errors:
        return {
            "status": STATUS_INVALID,
            "plan": None,
            "errors": shape_errors,
            "raw_output": raw_output,
            "normalized_output": normalized,
        }

    return {
        "status": STATUS_REPAIRED_VALID if repaired else STATUS_VALID,
        "plan": repaired_plan,
        "errors": errors,
        "raw_output": raw_output,
        "normalized_output": normalized,
    }