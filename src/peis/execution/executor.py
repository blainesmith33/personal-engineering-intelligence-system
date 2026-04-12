from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from peis.core.validation import require_bool, require_mapping, require_non_empty_str
from peis.execution.registry import (
    CapabilityRegistry,
    ExecutionRegistryError,
    execute_capability,
)
from peis.plan_record import PlanRecord, PlanStep


class ExecutionError(ValueError):
    """Raised when execution invariants are violated."""


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    step_id: str
    action_type: str
    status: str
    output: Mapping[str, Any]

    def __post_init__(self) -> None:
        require_non_empty_str(self.step_id, field_name="step_id")
        require_non_empty_str(self.action_type, field_name="action_type")
        require_non_empty_str(self.status, field_name="status")
        require_mapping(self.output, field_name="output")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action_type": self.action_type,
            "status": self.status,
            "output": dict(self.output),
        }


@dataclass(frozen=True, slots=True)
class PlanExecutionResult:
    plan_record_id: str
    subject_id: str
    executed: bool
    step_results: tuple[StepExecutionResult, ...]

    def __post_init__(self) -> None:
        require_non_empty_str(self.plan_record_id, field_name="plan_record_id")
        require_non_empty_str(self.subject_id, field_name="subject_id")
        require_bool(self.executed, field_name="executed")

        if not isinstance(self.step_results, tuple):
            raise ExecutionError("step_results must be a tuple")

        for i, result in enumerate(self.step_results):
            if not isinstance(result, StepExecutionResult):
                raise ExecutionError(f"step_results[{i}] must be StepExecutionResult")

    @property
    def is_noop_execution(self) -> bool:
        return len(self.step_results) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_record_id": self.plan_record_id,
            "subject_id": self.subject_id,
            "executed": self.executed,
            "step_results": [r.to_dict() for r in self.step_results],
        }


def execute_plan_record(
    *,
    registry: CapabilityRegistry,
    plan_record: PlanRecord,
) -> PlanExecutionResult:
    if not isinstance(registry, CapabilityRegistry):
        raise ExecutionError("registry must be a CapabilityRegistry")

    if not isinstance(plan_record, PlanRecord):
        raise ExecutionError("plan_record must be a PlanRecord")

    step_results: list[StepExecutionResult] = []

    for index, step in enumerate(plan_record.steps):
        if not isinstance(step, PlanStep):
            raise ExecutionError(f"plan_record.steps[{index}] must be PlanStep")

        payload = _build_step_payload(plan_record=plan_record, step=step)

        try:
            output = execute_capability(
                registry=registry,
                action_type=step.action_type,
                payload=payload,
                human_authorized=plan_record.human_authorized,
            )
        except ExecutionRegistryError as exc:
            raise ExecutionError(
                f"step execution failed for step_id={step.step_id}: {exc}"
            ) from exc

        step_results.append(
            StepExecutionResult(
                step_id=step.step_id,
                action_type=step.action_type,
                status=_extract_status(output),
                output=output,
            )
        )

    return PlanExecutionResult(
        plan_record_id=plan_record.plan_record_id,
        subject_id=plan_record.subject_id,
        executed=True,
        step_results=tuple(step_results),
    )


def _build_step_payload(
    *,
    plan_record: PlanRecord,
    step: PlanStep,
) -> dict[str, Any]:
    metadata: Mapping[str, Any]
    if step.metadata is None:
        metadata = {}
    else:
        require_mapping(step.metadata, field_name="step.metadata")
        metadata = step.metadata

    return {
        "plan_record_id": plan_record.plan_record_id,
        "subject_id": plan_record.subject_id,
        "plan_type": plan_record.plan_type,
        "basis_decision_record_id": plan_record.basis_decision_record_id,
        "basis_stop_state": plan_record.basis_stop_state.value,
        "step_id": step.step_id,
        "action_type": step.action_type,
        "description": step.description,
        "requires_human_authorization": step.requires_human_authorization,
        "metadata": dict(metadata),
    }


def _extract_status(output: Mapping[str, Any]) -> str:
    value = output.get("status")
    if not isinstance(value, str) or not value.strip():
        return "completed"
    return value.strip()