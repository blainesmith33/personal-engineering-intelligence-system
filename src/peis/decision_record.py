from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from peis.core.authority import (
    AuthorityBinding,
    AuthorityError,
)
from peis.core.determinism import (
    DeterminismEnvelope,
    DeterminismError,
)
from peis.core.enforcement import (
    enforce_decision_contract,
)
from peis.core.evidence import (
    EvidenceBinding,
    EvidenceError,
)
from peis.core.stop_states import (
    StopDecision,
    StopState,
    StopStateError,
)
from peis.core.validation import (
    ValidationError,
    require_mapping,
    require_non_empty_str,
)


class DecisionRecordError(ValueError):
    """Raised when DecisionRecord invariants are violated."""


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """
    Canonical authoritative decision artifact for PEIS.

    This is the first real artifact surface above core.

    Required invariants:
    - decision_record_id is present and non-empty
    - authority binding is decision-authoritative
    - evidence binding and determinism envelope are present
    - stop decision is present and governed
    - cross-module decision contract must pass
    """

    decision_record_id: str
    subject_id: str
    decision_type: str

    authority: AuthorityBinding
    evidence: EvidenceBinding
    determinism: DeterminismEnvelope
    stop_decision: StopDecision

    summary: str
    rationale: str | None = None
    emitted_by: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_str(
            self.decision_record_id,
            field_name="decision_record_id",
        )
        require_non_empty_str(
            self.subject_id,
            field_name="subject_id",
        )
        require_non_empty_str(
            self.decision_type,
            field_name="decision_type",
        )
        require_non_empty_str(
            self.summary,
            field_name="summary",
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
            raise DecisionRecordError("authority must be an AuthorityBinding")

        if not isinstance(self.evidence, EvidenceBinding):
            raise DecisionRecordError("evidence must be an EvidenceBinding")

        if not isinstance(self.determinism, DeterminismEnvelope):
            raise DecisionRecordError(
                "determinism must be a DeterminismEnvelope"
            )

        if not isinstance(self.stop_decision, StopDecision):
            raise DecisionRecordError("stop_decision must be a StopDecision")

        try:
            enforce_decision_contract(
                authority=self.authority,
                evidence=self.evidence,
                determinism=self.determinism,
                decision=self.stop_decision,
            )
        except (
            AuthorityError,
            EvidenceError,
            DeterminismError,
            StopStateError,
            ValidationError,
        ) as exc:
            raise DecisionRecordError(
                f"decision record cross-module contract failed: {exc}"
            ) from exc

    @property
    def stop_state(self) -> StopState:
        return self.stop_decision.stop_state

    @property
    def evidence_snapshot_id(self) -> str:
        return self.evidence.evidence_snapshot_id

    @property
    def policy_snapshot_id(self) -> str:
        return self.evidence.policy_snapshot_id

    @property
    def is_terminal(self) -> bool:
        return self.stop_decision.is_terminal

    @property
    def is_halt(self) -> bool:
        return self.stop_decision.is_halt

    @property
    def requires_human_intervention(self) -> bool:
        return self.stop_decision.requires_human_intervention

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_record_id": self.decision_record_id,
            "subject_id": self.subject_id,
            "decision_type": self.decision_type,
            "authority": self.authority.to_dict(),
            "evidence": self.evidence.to_dict(),
            "determinism": self.determinism.to_dict(),
            "stop_decision": self.stop_decision.to_dict(),
            "summary": self.summary,
            "rationale": self.rationale,
            "emitted_by": self.emitted_by,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DecisionRecord":
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

        try:
            return cls(
                decision_record_id=require_non_empty_str(
                    data.get("decision_record_id"),
                    field_name="decision_record_id",
                ),
                subject_id=require_non_empty_str(
                    data.get("subject_id"),
                    field_name="subject_id",
                ),
                decision_type=require_non_empty_str(
                    data.get("decision_type"),
                    field_name="decision_type",
                ),
                authority=AuthorityBinding.from_dict(authority_payload),
                evidence=EvidenceBinding.from_dict(evidence_payload),
                determinism=DeterminismEnvelope.from_dict(determinism_payload),
                stop_decision=StopDecision.from_dict(stop_decision_payload),
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
            )
        except (
            AuthorityError,
            EvidenceError,
            DeterminismError,
            StopStateError,
            ValidationError,
            TypeError,
        ) as exc:
            raise DecisionRecordError(
                f"invalid decision record payload: {exc}"
            ) from exc


def make_decision_record(
    *,
    decision_record_id: str,
    subject_id: str,
    decision_type: str,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    stop_decision: StopDecision,
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
) -> DecisionRecord:
    return DecisionRecord(
        decision_record_id=decision_record_id,
        subject_id=subject_id,
        decision_type=decision_type,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )


def assert_same_subject(
    left: DecisionRecord,
    right: DecisionRecord,
) -> None:
    if not isinstance(left, DecisionRecord):
        raise DecisionRecordError("left must be a DecisionRecord")
    if not isinstance(right, DecisionRecord):
        raise DecisionRecordError("right must be a DecisionRecord")

    if left.subject_id != right.subject_id:
        raise DecisionRecordError(
            "decision records reference different subject_id values"
        )


def assert_same_decision_type(
    left: DecisionRecord,
    right: DecisionRecord,
) -> None:
    if not isinstance(left, DecisionRecord):
        raise DecisionRecordError("left must be a DecisionRecord")
    if not isinstance(right, DecisionRecord):
        raise DecisionRecordError("right must be a DecisionRecord")

    if left.decision_type != right.decision_type:
        raise DecisionRecordError(
            "decision records reference different decision_type values"
        )


def _coerce_optional_non_empty_str(
    value: Any,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return require_non_empty_str(value, field_name=field_name)