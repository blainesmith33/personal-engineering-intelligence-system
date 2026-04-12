from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from peis.core.authority import AuthorityBinding
from peis.core.determinism import DeterminismEnvelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopDecision
from peis.core.validation import require_mapping, require_non_empty_str
from peis.plan_record import PlanStep
from peis.runtime.orchestrator import (
    OrchestrationInputs,
    OrchestrationResult,
    OrchestratorError,
    build_inputs,
    orchestrate,
)


class PipelineError(ValueError):
    """Raised when pipeline invariants are violated."""


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    """
    Serializable request surface for one deterministic PEIS pipeline run.

    This is the externalized request form that feeds the runtime orchestration
    layer. It is intentionally narrow and schema-like so it can later be used
    by CLI, API, tests, or batch runners without changing runtime semantics.
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
        require_non_empty_str(
            self.plan_type,
            field_name="plan_type",
        )
        require_non_empty_str(
            self.evaluation_summary,
            field_name="evaluation_summary",
        )
        require_non_empty_str(
            self.decision_summary,
            field_name="decision_summary",
        )
        require_non_empty_str(
            self.plan_summary,
            field_name="plan_summary",
        )

        if self.rationale is not None:
            require_non_empty_str(self.rationale, field_name="rationale")

        if self.emitted_by is not None:
            require_non_empty_str(self.emitted_by, field_name="emitted_by")

        if not isinstance(self.authority, AuthorityBinding):
            raise PipelineError("authority must be an AuthorityBinding")

        if not isinstance(self.evidence, EvidenceBinding):
            raise PipelineError("evidence must be an EvidenceBinding")

        if not isinstance(self.determinism, DeterminismEnvelope):
            raise PipelineError(
                "determinism must be a DeterminismEnvelope"
            )

        if not isinstance(self.stop_decision, StopDecision):
            raise PipelineError("stop_decision must be a StopDecision")

        if not isinstance(self.steps, tuple):
            raise PipelineError("steps must be a tuple[PlanStep, ...]")

        for index, step in enumerate(self.steps):
            if not isinstance(step, PlanStep):
                raise PipelineError(f"steps[{index}] must be a PlanStep")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "evaluation_type": self.evaluation_type,
            "decision_type": self.decision_type,
            "plan_type": self.plan_type,
            "authority": self.authority.to_dict(),
            "evidence": self.evidence.to_dict(),
            "determinism": self.determinism.to_dict(),
            "stop_decision": self.stop_decision.to_dict(),
            "evaluation_summary": self.evaluation_summary,
            "decision_summary": self.decision_summary,
            "plan_summary": self.plan_summary,
            "steps": [step.to_dict() for step in self.steps],
            "rationale": self.rationale,
            "emitted_by": self.emitted_by,
            "human_authorized": self.human_authorized,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PipelineRequest":
        require_mapping(data, field_name="data")

        authority_payload = require_mapping(
            data.get("authority"),
            field_name="authority",
        )
        evidence_payload = require_mapping(
            data.get("evidence"),
            field_name="evidence",
        )
        determinism_payload = require_mapping(
            data.get("determinism"),
            field_name="determinism",
        )
        stop_decision_payload = require_mapping(
            data.get("stop_decision"),
            field_name="stop_decision",
        )

        steps_raw = data.get("steps", [])
        if not isinstance(steps_raw, list):
            raise PipelineError("steps must be a list in serialized form")

        try:
            steps = tuple(
                PlanStep.from_dict(require_mapping(item, field_name="steps[]"))
                for item in steps_raw
            )

            return cls(
                subject_id=require_non_empty_str(
                    data.get("subject_id"),
                    field_name="subject_id",
                ),
                evaluation_type=require_non_empty_str(
                    data.get("evaluation_type"),
                    field_name="evaluation_type",
                ),
                decision_type=require_non_empty_str(
                    data.get("decision_type"),
                    field_name="decision_type",
                ),
                plan_type=require_non_empty_str(
                    data.get("plan_type"),
                    field_name="plan_type",
                ),
                authority=AuthorityBinding.from_dict(authority_payload),
                evidence=EvidenceBinding.from_dict(evidence_payload),
                determinism=DeterminismEnvelope.from_dict(determinism_payload),
                stop_decision=StopDecision.from_dict(stop_decision_payload),
                evaluation_summary=require_non_empty_str(
                    data.get("evaluation_summary"),
                    field_name="evaluation_summary",
                ),
                decision_summary=require_non_empty_str(
                    data.get("decision_summary"),
                    field_name="decision_summary",
                ),
                plan_summary=require_non_empty_str(
                    data.get("plan_summary"),
                    field_name="plan_summary",
                ),
                steps=steps,
                rationale=_coerce_optional_non_empty_str(
                    data.get("rationale"),
                    field_name="rationale",
                ),
                emitted_by=_coerce_optional_non_empty_str(
                    data.get("emitted_by"),
                    field_name="emitted_by",
                ),
                human_authorized=_coerce_bool(
                    data.get("human_authorized", False),
                    field_name="human_authorized",
                ),
            )
        except (TypeError, ValueError) as exc:
            raise PipelineError(f"invalid pipeline request payload: {exc}") from exc


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """
    Serializable output surface for one deterministic PEIS pipeline run.
    """

    request: PipelineRequest
    result: OrchestrationResult

    def __post_init__(self) -> None:
        if not isinstance(self.request, PipelineRequest):
            raise PipelineError("request must be a PipelineRequest")
        if not isinstance(self.result, OrchestrationResult):
            raise PipelineError("result must be an OrchestrationResult")

    @property
    def subject_id(self) -> str:
        return self.result.subject_id

    @property
    def stop_state(self):
        return self.result.stop_state

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
        }


def run_pipeline(request: PipelineRequest) -> PipelineResult:
    """
    Execute one fully deterministic PEIS pipeline cycle from request to result.

    This is the public runtime entrypoint for Phase 1.
    """
    if not isinstance(request, PipelineRequest):
        raise PipelineError("request must be a PipelineRequest")

    try:
        inputs = build_inputs(
            subject_id=request.subject_id,
            evaluation_type=request.evaluation_type,
            decision_type=request.decision_type,
            plan_type=request.plan_type,
            authority=request.authority,
            evidence=request.evidence,
            determinism=request.determinism,
            stop_decision=request.stop_decision,
            evaluation_summary=request.evaluation_summary,
            decision_summary=request.decision_summary,
            plan_summary=request.plan_summary,
            steps=request.steps,
            rationale=request.rationale,
            emitted_by=request.emitted_by,
            human_authorized=request.human_authorized,
        )

        result = orchestrate(inputs)
    except OrchestratorError as exc:
        raise PipelineError(f"pipeline orchestration failed: {exc}") from exc

    return PipelineResult(
        request=request,
        result=result,
    )


def build_pipeline_request(
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
) -> PipelineRequest:
    """
    Convenience constructor for pipeline requests.
    """
    return PipelineRequest(
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


def build_pipeline_inputs(request: PipelineRequest) -> OrchestrationInputs:
    """
    Normalize a pipeline request into orchestration inputs without executing.
    """
    if not isinstance(request, PipelineRequest):
        raise PipelineError("request must be a PipelineRequest")

    return build_inputs(
        subject_id=request.subject_id,
        evaluation_type=request.evaluation_type,
        decision_type=request.decision_type,
        plan_type=request.plan_type,
        authority=request.authority,
        evidence=request.evidence,
        determinism=request.determinism,
        stop_decision=request.stop_decision,
        evaluation_summary=request.evaluation_summary,
        decision_summary=request.decision_summary,
        plan_summary=request.plan_summary,
        steps=request.steps,
        rationale=request.rationale,
        emitted_by=request.emitted_by,
        human_authorized=request.human_authorized,
    )


def _coerce_optional_non_empty_str(
    value: Any,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return require_non_empty_str(value, field_name=field_name)


def _coerce_bool(
    value: Any,
    *,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise PipelineError(f"{field_name} must be a bool")
    return value