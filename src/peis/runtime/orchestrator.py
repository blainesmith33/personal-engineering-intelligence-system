from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from peis.builders import (
    build_decision_record,
    build_evaluation_record,
    build_plan_record,
)
from peis.core.authority import AuthorityBinding
from peis.core.determinism import DeterminismEnvelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopDecision, StopState
from peis.core.validation import require_non_empty_str
from peis.decision_record import DecisionRecord
from peis.evaluation_record import EvaluationRecord
from peis.plan_record import PlanRecord, PlanStep


class OrchestratorError(ValueError):
    """Raised when runtime orchestration invariants are violated."""


@dataclass(frozen=True, slots=True)
class OrchestrationInputs:
    """
    Normalized runtime input set for a single PEIS orchestration cycle.

    This is intentionally strict and narrow:
    - one subject
    - one evaluation type
    - one decision type
    - one plan type
    - one authoritative context
    - one evidence/determinism context
    """

    subject_id: str
    evaluation_type: str
    decision_type: str
    plan_type: str

    authority: AuthorityBinding
    evidence: EvidenceBinding
    determinism: DeterminismEnvelope

    stop_decision: StopDecision
    evaluation_summary: str
    decision_summary: str
    plan_summary: str

    steps: tuple[PlanStep, ...] = ()
    rationale: str | None = None
    emitted_by: str | None = None
    human_authorized: bool = False

    def __post_init__(self) -> None:
        require_non_empty_str(self.subject_id, field_name="subject_id")
        require_non_empty_str(
            self.evaluation_type,
            field_name="evaluation_type",
        )
        require_non_empty_str(
            self.decision_type,
            field_name="decision_type",
        )
        require_non_empty_str(self.plan_type, field_name="plan_type")
        require_non_empty_str(
            self.evaluation_summary,
            field_name="evaluation_summary",
        )
        require_non_empty_str(
            self.decision_summary,
            field_name="decision_summary",
        )
        require_non_empty_str(self.plan_summary, field_name="plan_summary")

        if self.rationale is not None:
            require_non_empty_str(self.rationale, field_name="rationale")

        if self.emitted_by is not None:
            require_non_empty_str(self.emitted_by, field_name="emitted_by")

        if not isinstance(self.authority, AuthorityBinding):
            raise OrchestratorError("authority must be an AuthorityBinding")

        if not isinstance(self.evidence, EvidenceBinding):
            raise OrchestratorError("evidence must be an EvidenceBinding")

        if not isinstance(self.determinism, DeterminismEnvelope):
            raise OrchestratorError(
                "determinism must be a DeterminismEnvelope"
            )

        if not isinstance(self.stop_decision, StopDecision):
            raise OrchestratorError("stop_decision must be a StopDecision")

        if not isinstance(self.steps, tuple):
            raise OrchestratorError("steps must be a tuple[PlanStep, ...]")

        for index, step in enumerate(self.steps):
            if not isinstance(step, PlanStep):
                raise OrchestratorError(f"steps[{index}] must be a PlanStep")


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    """
    Materialized outputs from one orchestration cycle.
    """

    evaluation_record: EvaluationRecord
    decision_record: DecisionRecord
    plan_record: PlanRecord

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_record, EvaluationRecord):
            raise OrchestratorError(
                "evaluation_record must be an EvaluationRecord"
            )
        if not isinstance(self.decision_record, DecisionRecord):
            raise OrchestratorError(
                "decision_record must be a DecisionRecord"
            )
        if not isinstance(self.plan_record, PlanRecord):
            raise OrchestratorError("plan_record must be a PlanRecord")

    @property
    def subject_id(self) -> str:
        return self.decision_record.subject_id

    @property
    def stop_state(self) -> StopState:
        return self.decision_record.stop_state

    @property
    def evidence_snapshot_id(self) -> str:
        return self.decision_record.evidence_snapshot_id

    @property
    def policy_snapshot_id(self) -> str:
        return self.decision_record.policy_snapshot_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_record": self.evaluation_record.to_dict(),
            "decision_record": self.decision_record.to_dict(),
            "plan_record": self.plan_record.to_dict(),
        }


def orchestrate(inputs: OrchestrationInputs) -> OrchestrationResult:
    """
    Execute one deterministic PEIS orchestration cycle.

    Runtime order:
    1. Build decision artifact from authoritative context
    2. Build evaluation artifact referencing the decision
    3. Build plan artifact referencing the decision and basis stop-state

    This function is intentionally simple and deterministic. It performs no
    hidden routing, no retries, no adaptive branching, and no mutation of the
    supplied inputs.
    """
    if not isinstance(inputs, OrchestrationInputs):
        raise OrchestratorError("inputs must be an OrchestrationInputs")

    decision_record = build_decision_record(
        subject_id=inputs.subject_id,
        decision_type=inputs.decision_type,
        authority=inputs.authority,
        evidence=inputs.evidence,
        determinism=inputs.determinism,
        stop_decision=inputs.stop_decision,
        summary=inputs.decision_summary,
        rationale=inputs.rationale,
        emitted_by=inputs.emitted_by,
    )

    evaluation_record = build_evaluation_record(
        subject_id=inputs.subject_id,
        evaluation_type=inputs.evaluation_type,
        input_authorities=(inputs.authority,),
        input_evidence_bindings=(inputs.evidence,),
        input_determinism_envelopes=(inputs.determinism,),
        decision_record_id=decision_record.decision_record_id,
        result_stop_state=decision_record.stop_state,
        summary=inputs.evaluation_summary,
        rationale=inputs.rationale,
        emitted_by=inputs.emitted_by,
    )

    plan_record = build_plan_record(
        subject_id=inputs.subject_id,
        plan_type=inputs.plan_type,
        authority=inputs.authority,
        evidence=inputs.evidence,
        determinism=inputs.determinism,
        basis_decision_record_id=decision_record.decision_record_id,
        basis_stop_state=decision_record.stop_state,
        steps=inputs.steps,
        summary=inputs.plan_summary,
        rationale=inputs.rationale,
        emitted_by=inputs.emitted_by,
        human_authorized=inputs.human_authorized,
    )

    return OrchestrationResult(
        evaluation_record=evaluation_record,
        decision_record=decision_record,
        plan_record=plan_record,
    )


def build_inputs(
    *,
    subject_id: str,
    evaluation_type: str,
    decision_type: str,
    plan_type: str,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    stop_decision: StopDecision,
    evaluation_summary: str,
    decision_summary: str,
    plan_summary: str,
    steps: tuple[PlanStep, ...] = (),
    rationale: str | None = None,
    emitted_by: str | None = None,
    human_authorized: bool = False,
) -> OrchestrationInputs:
    """
    Convenience constructor for orchestration inputs.
    """
    return OrchestrationInputs(
        subject_id=subject_id,
        evaluation_type=evaluation_type,
        decision_type=decision_type,
        plan_type=plan_type,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary=evaluation_summary,
        decision_summary=decision_summary,
        plan_summary=plan_summary,
        steps=steps,
        rationale=rationale,
        emitted_by=emitted_by,
        human_authorized=human_authorized,
    )