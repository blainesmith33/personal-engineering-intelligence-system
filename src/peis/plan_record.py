from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from peis.core.authority import (
    AuthorityBinding,
    AuthorityError,
    assert_decision_authority,
)
from peis.core.determinism import (
    DeterminismEnvelope,
    DeterminismError,
)
from peis.core.enforcement import (
    enforce_human_gate,
    enforce_no_halt_progression,
    enforce_stop_state_actionability,
)
from peis.core.evidence import (
    EvidenceBinding,
    EvidenceError,
)
from peis.core.stop_states import (
    StopState,
    StopStateError,
)
from peis.core.validation import (
    ValidationError,
    require_bool,
    require_mapping,
    require_non_empty_list,
    require_non_empty_str,
)


class PlanRecordError(ValueError):
    """Raised when PlanRecord invariants are violated."""


@dataclass(frozen=True, slots=True)
class PlanStep:
    """
    Immutable executable plan step.

    This is intentionally minimal for Phase 1. It captures only the controlled
    execution intent, not arbitrary runtime behavior.
    """

    step_id: str
    action_type: str
    description: str
    requires_human_authorization: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        require_non_empty_str(self.step_id, field_name="step_id")
        require_non_empty_str(self.action_type, field_name="action_type")
        require_non_empty_str(self.description, field_name="description")

        require_bool(
            self.requires_human_authorization,
            field_name="requires_human_authorization",
        )

        if self.metadata is not None:
            require_mapping(self.metadata, field_name="metadata")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action_type": self.action_type,
            "description": self.description,
            "requires_human_authorization": self.requires_human_authorization,
            "metadata": dict(self.metadata) if self.metadata is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanStep":
        require_mapping(data, field_name="data")

        metadata = data.get("metadata")
        if metadata is not None:
            metadata = require_mapping(metadata, field_name="metadata")

        return cls(
            step_id=require_non_empty_str(
                data.get("step_id"),
                field_name="step_id",
            ),
            action_type=require_non_empty_str(
                data.get("action_type"),
                field_name="action_type",
            ),
            description=require_non_empty_str(
                data.get("description"),
                field_name="description",
            ),
            requires_human_authorization=require_bool(
                data.get("requires_human_authorization", False),
                field_name="requires_human_authorization",
            ),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class PlanRecord:
    """
    Canonical forward-action artifact for PEIS.

    Required invariants:
    - plan_record_id is present and non-empty
    - subject_id is present and non-empty
    - plan_type is present and non-empty
    - authority binding is decision-authoritative
    - evidence binding is present
    - determinism envelope is present
    - basis_stop_state is governed by the shared stop-state algebra
    - halt states may not produce a normal execution plan
    - states requiring human intervention may not proceed without explicit gate
    - steps may be empty, representing an explicit no-op / no-further-action plan
    """

    plan_record_id: str
    subject_id: str
    plan_type: str

    authority: AuthorityBinding
    evidence: EvidenceBinding
    determinism: DeterminismEnvelope

    basis_decision_record_id: str
    basis_stop_state: StopState

    steps: tuple[PlanStep, ...]

    summary: str
    rationale: str | None = None
    emitted_by: str | None = None
    human_authorized: bool = False

    def __post_init__(self) -> None:
        require_non_empty_str(
            self.plan_record_id,
            field_name="plan_record_id",
        )
        require_non_empty_str(
            self.subject_id,
            field_name="subject_id",
        )
        require_non_empty_str(
            self.plan_type,
            field_name="plan_type",
        )
        require_non_empty_str(
            self.basis_decision_record_id,
            field_name="basis_decision_record_id",
        )
        require_non_empty_str(
            self.summary,
            field_name="summary",
        )
        require_bool(
            self.human_authorized,
            field_name="human_authorized",
        )

        if self.rationale is not None:
            require_non_empty_str(
                self.rationale,
                field_name="rationale",
            )

        if self.emitted_by is not None:
            require_non_empty_str(
                self.emitted_by,
                field_name="emitted_by",
            )

        if not isinstance(self.authority, AuthorityBinding):
            raise PlanRecordError("authority must be an AuthorityBinding")

        if not isinstance(self.evidence, EvidenceBinding):
            raise PlanRecordError("evidence must be an EvidenceBinding")

        if not isinstance(self.determinism, DeterminismEnvelope):
            raise PlanRecordError(
                "determinism must be a DeterminismEnvelope"
            )

        if not isinstance(self.steps, tuple):
            raise PlanRecordError("steps must be a tuple[PlanStep, ...]")

        for index, step in enumerate(self.steps):
            if not isinstance(step, PlanStep):
                raise PlanRecordError(
                    f"steps[{index}] must be a PlanStep"
                )

        try:
            assert_decision_authority(self.authority)

            if (
                self.determinism.evidence_snapshot_id
                != self.evidence.evidence_snapshot_id
            ):
                raise PlanRecordError(
                    "determinism/evidence mismatch for evidence_snapshot_id"
                )

            if (
                self.determinism.policy_snapshot_id
                != self.evidence.policy_snapshot_id
            ):
                raise PlanRecordError(
                    "determinism/evidence mismatch for policy_snapshot_id"
                )

            enforce_stop_state_actionability(self.basis_stop_state)
            enforce_no_halt_progression(self.basis_stop_state)
            enforce_human_gate(
                self.basis_stop_state,
                human_authorized=self.human_authorized,
            )
        except (
            AuthorityError,
            EvidenceError,
            DeterminismError,
            StopStateError,
            ValidationError,
        ) as exc:
            raise PlanRecordError(
                f"plan record cross-module contract failed: {exc}"
            ) from exc

    @property
    def evidence_snapshot_id(self) -> str:
        return self.evidence.evidence_snapshot_id

    @property
    def policy_snapshot_id(self) -> str:
        return self.evidence.policy_snapshot_id

    @property
    def is_noop_plan(self) -> bool:
        return len(self.steps) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_record_id": self.plan_record_id,
            "subject_id": self.subject_id,
            "plan_type": self.plan_type,
            "authority": self.authority.to_dict(),
            "evidence": self.evidence.to_dict(),
            "determinism": self.determinism.to_dict(),
            "basis_decision_record_id": self.basis_decision_record_id,
            "basis_stop_state": self.basis_stop_state.value,
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary,
            "rationale": self.rationale,
            "emitted_by": self.emitted_by,
            "human_authorized": self.human_authorized,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlanRecord":
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

        steps_raw = data.get("steps", [])
        if not isinstance(steps_raw, list):
            raise PlanRecordError("steps must be a list in serialized form")

        try:
            steps = tuple(
                PlanStep.from_dict(
                    require_mapping(item, field_name="steps[]")
                )
                for item in steps_raw
            )

            basis_stop_state_raw = require_non_empty_str(
                data.get("basis_stop_state"),
                field_name="basis_stop_state",
            )

            return cls(
                plan_record_id=require_non_empty_str(
                    data.get("plan_record_id"),
                    field_name="plan_record_id",
                ),
                subject_id=require_non_empty_str(
                    data.get("subject_id"),
                    field_name="subject_id",
                ),
                plan_type=require_non_empty_str(
                    data.get("plan_type"),
                    field_name="plan_type",
                ),
                authority=AuthorityBinding.from_dict(authority_payload),
                evidence=EvidenceBinding.from_dict(evidence_payload),
                determinism=DeterminismEnvelope.from_dict(determinism_payload),
                basis_decision_record_id=require_non_empty_str(
                    data.get("basis_decision_record_id"),
                    field_name="basis_decision_record_id",
                ),
                basis_stop_state=StopState(basis_stop_state_raw),
                steps=steps,
                summary=require_non_empty_str(
                    data.get("summary"),
                    field_name="summary",
                ),
                rationale=_coerce_optional_non_empty_str(
                    data.get("rationale"),
                    field_name="rationale",
                ),
                emitted_by=_coerce_optional_non_empty_str(
                    data.get("emitted_by"),
                    field_name="emitted_by",
                ),
                human_authorized=require_bool(
                    data.get("human_authorized", False),
                    field_name="human_authorized",
                ),
            )
        except (
            AuthorityError,
            EvidenceError,
            DeterminismError,
            StopStateError,
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise PlanRecordError(
                f"invalid plan record payload: {exc}"
            ) from exc


def make_plan_record(
    *,
    plan_record_id: str,
    subject_id: str,
    plan_type: str,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    basis_decision_record_id: str,
    basis_stop_state: StopState,
    steps: tuple[PlanStep, ...],
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
    human_authorized: bool = False,
) -> PlanRecord:
    return PlanRecord(
        plan_record_id=plan_record_id,
        subject_id=subject_id,
        plan_type=plan_type,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id=basis_decision_record_id,
        basis_stop_state=basis_stop_state,
        steps=steps,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
        human_authorized=human_authorized,
    )


def assert_same_subject(
    left: PlanRecord,
    right: PlanRecord,
) -> None:
    if not isinstance(left, PlanRecord):
        raise PlanRecordError("left must be a PlanRecord")
    if not isinstance(right, PlanRecord):
        raise PlanRecordError("right must be a PlanRecord")

    if left.subject_id != right.subject_id:
        raise PlanRecordError(
            "plan records reference different subject_id values"
        )


def assert_same_plan_type(
    left: PlanRecord,
    right: PlanRecord,
) -> None:
    if not isinstance(left, PlanRecord):
        raise PlanRecordError("left must be a PlanRecord")
    if not isinstance(right, PlanRecord):
        raise PlanRecordError("right must be a PlanRecord")

    if left.plan_type != right.plan_type:
        raise PlanRecordError(
            "plan records reference different plan_type values"
        )


def _coerce_optional_non_empty_str(
    value: Any,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return require_non_empty_str(value, field_name=field_name)