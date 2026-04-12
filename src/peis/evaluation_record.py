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
    enforce_input_set,
)
from peis.core.evidence import (
    EvidenceBinding,
    EvidenceError,
)
from peis.core.stop_states import (
    StopState,
    StopStateError,
    assert_no_custom_stop_state,
)
from peis.core.validation import (
    ValidationError,
    require_mapping,
    require_non_empty_list,
    require_non_empty_str,
)


class EvaluationRecordError(ValueError):
    """Raised when EvaluationRecord invariants are violated."""


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    """
    Canonical evaluation artifact for PEIS.

    This records the evaluated subject, the bounded input context used for the
    evaluation, and the resulting decision record identity produced from that
    evaluation context.

    Required invariants:
    - evaluation_record_id is present and non-empty
    - subject_id is present and non-empty
    - evaluation_type is present and non-empty
    - all input authorities are decision-authoritative
    - all evidence bindings are identical
    - all determinism envelopes are identical
    - result_stop_state is governed by the shared stop-state algebra
    - decision_record_id is present and non-empty
    """

    evaluation_record_id: str
    subject_id: str
    evaluation_type: str

    input_authorities: tuple[AuthorityBinding, ...]
    input_evidence_bindings: tuple[EvidenceBinding, ...]
    input_determinism_envelopes: tuple[DeterminismEnvelope, ...]

    decision_record_id: str
    result_stop_state: StopState

    summary: str
    rationale: str | None = None
    emitted_by: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_str(
            self.evaluation_record_id,
            field_name="evaluation_record_id",
        )
        require_non_empty_str(
            self.subject_id,
            field_name="subject_id",
        )
        require_non_empty_str(
            self.evaluation_type,
            field_name="evaluation_type",
        )
        require_non_empty_str(
            self.decision_record_id,
            field_name="decision_record_id",
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

        if not isinstance(self.input_authorities, tuple):
            raise EvaluationRecordError(
                "input_authorities must be a tuple[AuthorityBinding, ...]"
            )
        if not isinstance(self.input_evidence_bindings, tuple):
            raise EvaluationRecordError(
                "input_evidence_bindings must be a tuple[EvidenceBinding, ...]"
            )
        if not isinstance(self.input_determinism_envelopes, tuple):
            raise EvaluationRecordError(
                "input_determinism_envelopes must be a tuple[DeterminismEnvelope, ...]"
            )

        if not self.input_authorities:
            raise EvaluationRecordError("input_authorities must not be empty")
        if not self.input_evidence_bindings:
            raise EvaluationRecordError(
                "input_evidence_bindings must not be empty"
            )
        if not self.input_determinism_envelopes:
            raise EvaluationRecordError(
                "input_determinism_envelopes must not be empty"
            )

        try:
            enforce_input_set(
                authorities=self.input_authorities,
                evidence_bindings=self.input_evidence_bindings,
                determinism_envelopes=self.input_determinism_envelopes,
            )
            assert_no_custom_stop_state(self.result_stop_state)
        except (
            AuthorityError,
            EvidenceError,
            DeterminismError,
            StopStateError,
            ValidationError,
        ) as exc:
            raise EvaluationRecordError(
                f"evaluation record cross-module contract failed: {exc}"
            ) from exc

    @property
    def evidence_snapshot_id(self) -> str:
        return self.input_evidence_bindings[0].evidence_snapshot_id

    @property
    def policy_snapshot_id(self) -> str:
        return self.input_evidence_bindings[0].policy_snapshot_id

    @property
    def canonical_evidence_binding(self) -> EvidenceBinding:
        return self.input_evidence_bindings[0]

    @property
    def canonical_determinism_envelope(self) -> DeterminismEnvelope:
        return self.input_determinism_envelopes[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_record_id": self.evaluation_record_id,
            "subject_id": self.subject_id,
            "evaluation_type": self.evaluation_type,
            "input_authorities": [
                authority.to_dict() for authority in self.input_authorities
            ],
            "input_evidence_bindings": [
                binding.to_dict() for binding in self.input_evidence_bindings
            ],
            "input_determinism_envelopes": [
                envelope.to_dict()
                for envelope in self.input_determinism_envelopes
            ],
            "decision_record_id": self.decision_record_id,
            "result_stop_state": self.result_stop_state.value,
            "summary": self.summary,
            "rationale": self.rationale,
            "emitted_by": self.emitted_by,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvaluationRecord":
        require_mapping(data, field_name="data")

        authorities_payload = require_non_empty_list(
            data.get("input_authorities"),
            field_name="input_authorities",
        )
        evidence_payload = require_non_empty_list(
            data.get("input_evidence_bindings"),
            field_name="input_evidence_bindings",
        )
        envelopes_payload = require_non_empty_list(
            data.get("input_determinism_envelopes"),
            field_name="input_determinism_envelopes",
        )

        try:
            input_authorities = tuple(
                AuthorityBinding.from_dict(
                    require_mapping(item, field_name="input_authorities[]")
                )
                for item in authorities_payload
            )
            input_evidence_bindings = tuple(
                EvidenceBinding.from_dict(
                    require_mapping(
                        item,
                        field_name="input_evidence_bindings[]",
                    )
                )
                for item in evidence_payload
            )
            input_determinism_envelopes = tuple(
                DeterminismEnvelope.from_dict(
                    require_mapping(
                        item,
                        field_name="input_determinism_envelopes[]",
                    )
                )
                for item in envelopes_payload
            )

            return cls(
                evaluation_record_id=require_non_empty_str(
                    data.get("evaluation_record_id"),
                    field_name="evaluation_record_id",
                ),
                subject_id=require_non_empty_str(
                    data.get("subject_id"),
                    field_name="subject_id",
                ),
                evaluation_type=require_non_empty_str(
                    data.get("evaluation_type"),
                    field_name="evaluation_type",
                ),
                input_authorities=input_authorities,
                input_evidence_bindings=input_evidence_bindings,
                input_determinism_envelopes=input_determinism_envelopes,
                decision_record_id=require_non_empty_str(
                    data.get("decision_record_id"),
                    field_name="decision_record_id",
                ),
                result_stop_state=assert_no_custom_stop_state(
                    data.get("result_stop_state")
                ) or StopState(data.get("result_stop_state")),
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
            ValueError,
        ) as exc:
            raise EvaluationRecordError(
                f"invalid evaluation record payload: {exc}"
            ) from exc


def make_evaluation_record(
    *,
    evaluation_record_id: str,
    subject_id: str,
    evaluation_type: str,
    input_authorities: tuple[AuthorityBinding, ...],
    input_evidence_bindings: tuple[EvidenceBinding, ...],
    input_determinism_envelopes: tuple[DeterminismEnvelope, ...],
    decision_record_id: str,
    result_stop_state: StopState,
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
) -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_record_id=evaluation_record_id,
        subject_id=subject_id,
        evaluation_type=evaluation_type,
        input_authorities=input_authorities,
        input_evidence_bindings=input_evidence_bindings,
        input_determinism_envelopes=input_determinism_envelopes,
        decision_record_id=decision_record_id,
        result_stop_state=result_stop_state,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )


def assert_same_subject(
    left: EvaluationRecord,
    right: EvaluationRecord,
) -> None:
    if not isinstance(left, EvaluationRecord):
        raise EvaluationRecordError("left must be an EvaluationRecord")
    if not isinstance(right, EvaluationRecord):
        raise EvaluationRecordError("right must be an EvaluationRecord")

    if left.subject_id != right.subject_id:
        raise EvaluationRecordError(
            "evaluation records reference different subject_id values"
        )


def assert_same_evaluation_type(
    left: EvaluationRecord,
    right: EvaluationRecord,
) -> None:
    if not isinstance(left, EvaluationRecord):
        raise EvaluationRecordError("left must be an EvaluationRecord")
    if not isinstance(right, EvaluationRecord):
        raise EvaluationRecordError("right must be an EvaluationRecord")

    if left.evaluation_type != right.evaluation_type:
        raise EvaluationRecordError(
            "evaluation records reference different evaluation_type values"
        )


def _coerce_optional_non_empty_str(
    value: Any,
    *,
    field_name: str,
) -> str | None:
    if value is None:
        return None
    return require_non_empty_str(value, field_name=field_name)