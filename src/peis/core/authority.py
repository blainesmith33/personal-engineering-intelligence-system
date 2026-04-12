from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class AuthorityError(ValueError):
    """Raised when authority rules are violated."""


class AuthorityClass(str, Enum):
    """
    System-wide authority classes.

    These classes are intentionally narrow and explicit. Any object that can
    influence interpretation, explanation, routing, or decision-making should
    be assigned exactly one authority class.
    """

    AUTHORITATIVE = "authoritative"
    DERIVED_AUTHORITATIVE = "derived_authoritative"
    ADVISORY = "advisory"
    DESCRIPTIVE = "descriptive"


class EvidenceRole(str, Enum):
    """
    Semantic role for a bound object.

    This is orthogonal to authority class. For example, an authoritative input
    and an authoritative decision artifact may both be authoritative, but they
    play different roles in the system.
    """

    INPUT = "input"
    SNAPSHOT = "snapshot"
    DECISION = "decision"
    OUTPUT = "output"
    EXPLANATION = "explanation"
    METADATA = "metadata"


@dataclass(frozen=True, slots=True)
class AuthorityBinding:
    """
    Immutable authority binding for an artifact, record, or decision.

    Required invariants:
    - Every bound object has exactly one authority class.
    - Advisory and descriptive content must not drive decisions.
    - Authoritative and derived-authoritative content must be traceable to
      immutable evidence and policy snapshots.
    """

    authority_class: AuthorityClass
    evidence_role: EvidenceRole
    evidence_snapshot_id: str | None
    policy_snapshot_id: str | None
    source_label: str
    advisory_note: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.source_label, field_name="source_label")

        if self.authority_class in {
            AuthorityClass.AUTHORITATIVE,
            AuthorityClass.DERIVED_AUTHORITATIVE,
        }:
            _require_non_empty_str(
                self.evidence_snapshot_id,
                field_name="evidence_snapshot_id",
            )
            _require_non_empty_str(
                self.policy_snapshot_id,
                field_name="policy_snapshot_id",
            )

        if self.authority_class in {
            AuthorityClass.ADVISORY,
            AuthorityClass.DESCRIPTIVE,
        }:
            if self.evidence_snapshot_id is not None:
                _require_non_empty_str(
                    self.evidence_snapshot_id,
                    field_name="evidence_snapshot_id",
                )
            if self.policy_snapshot_id is not None:
                _require_non_empty_str(
                    self.policy_snapshot_id,
                    field_name="policy_snapshot_id",
                )

        if self.authority_class == AuthorityClass.ADVISORY and self.advisory_note is not None:
            _require_non_empty_str(self.advisory_note, field_name="advisory_note")

        if self.authority_class != AuthorityClass.ADVISORY and self.advisory_note is not None:
            _require_non_empty_str(self.advisory_note, field_name="advisory_note")

    @property
    def is_decision_authoritative(self) -> bool:
        """
        Returns True only for classes permitted to participate in decisions.
        """
        return self.authority_class in {
            AuthorityClass.AUTHORITATIVE,
            AuthorityClass.DERIVED_AUTHORITATIVE,
        }

    @property
    def is_non_authoritative(self) -> bool:
        """
        Returns True for classes that must never drive decisions.
        """
        return self.authority_class in {
            AuthorityClass.ADVISORY,
            AuthorityClass.DESCRIPTIVE,
        }

    def to_dict(self) -> dict[str, Any]:
        """
        Stable serialization suitable for artifacts and logs.
        """
        return {
            "authority_class": self.authority_class.value,
            "evidence_role": self.evidence_role.value,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "policy_snapshot_id": self.policy_snapshot_id,
            "source_label": self.source_label,
            "advisory_note": self.advisory_note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuthorityBinding":
        """
        Parse and validate an AuthorityBinding from a mapping.
        """
        if not isinstance(data, Mapping):
            raise AuthorityError("authority binding payload must be a mapping")

        return cls(
            authority_class=_coerce_enum(
                AuthorityClass,
                data.get("authority_class"),
                field_name="authority_class",
            ),
            evidence_role=_coerce_enum(
                EvidenceRole,
                data.get("evidence_role"),
                field_name="evidence_role",
            ),
            evidence_snapshot_id=_coerce_optional_str(
                data.get("evidence_snapshot_id"),
                field_name="evidence_snapshot_id",
            ),
            policy_snapshot_id=_coerce_optional_str(
                data.get("policy_snapshot_id"),
                field_name="policy_snapshot_id",
            ),
            source_label=_coerce_required_str(
                data.get("source_label"),
                field_name="source_label",
            ),
            advisory_note=_coerce_optional_str(
                data.get("advisory_note"),
                field_name="advisory_note",
            ),
        )


def make_authoritative_binding(
    *,
    evidence_role: EvidenceRole,
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
    source_label: str,
) -> AuthorityBinding:
    """
    Construct a fully authoritative binding.

    Use this for objects directly grounded in authoritative evidence and policy.
    """
    return AuthorityBinding(
        authority_class=AuthorityClass.AUTHORITATIVE,
        evidence_role=evidence_role,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        source_label=source_label,
    )


def make_derived_authoritative_binding(
    *,
    evidence_role: EvidenceRole,
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
    source_label: str,
) -> AuthorityBinding:
    """
    Construct a derived-authoritative binding.

    Use this for outputs deterministically derived from authoritative inputs
    without introducing non-authoritative decision influence.
    """
    return AuthorityBinding(
        authority_class=AuthorityClass.DERIVED_AUTHORITATIVE,
        evidence_role=evidence_role,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        source_label=source_label,
    )


def make_advisory_binding(
    *,
    evidence_role: EvidenceRole,
    source_label: str,
    advisory_note: str | None = None,
    evidence_snapshot_id: str | None = None,
    policy_snapshot_id: str | None = None,
) -> AuthorityBinding:
    """
    Construct a non-authoritative advisory binding.

    Advisory content may reference authoritative context, but it must never
    become decision-driving merely because such references are attached.
    """
    return AuthorityBinding(
        authority_class=AuthorityClass.ADVISORY,
        evidence_role=evidence_role,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        source_label=source_label,
        advisory_note=advisory_note,
    )


def make_descriptive_binding(
    *,
    evidence_role: EvidenceRole,
    source_label: str,
    evidence_snapshot_id: str | None = None,
    policy_snapshot_id: str | None = None,
) -> AuthorityBinding:
    """
    Construct a descriptive binding.

    Descriptive data may be displayed or explained to users, but it must never
    drive comparisons, decisions, or stop-state transitions.
    """
    return AuthorityBinding(
        authority_class=AuthorityClass.DESCRIPTIVE,
        evidence_role=evidence_role,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        source_label=source_label,
    )


def assert_decision_authority(binding: AuthorityBinding) -> None:
    """
    Enforce that a binding is allowed to participate in decision logic.
    """
    if not isinstance(binding, AuthorityBinding):
        raise AuthorityError("binding must be an AuthorityBinding")

    if not binding.is_decision_authoritative:
        raise AuthorityError(
            "non-authoritative binding cannot participate in decision logic: "
            f"{binding.authority_class.value}"
        )


def assert_non_authoritative(binding: AuthorityBinding) -> None:
    """
    Enforce that a binding is advisory/descriptive only.
    """
    if not isinstance(binding, AuthorityBinding):
        raise AuthorityError("binding must be an AuthorityBinding")

    if not binding.is_non_authoritative:
        raise AuthorityError(
            "binding is authoritative and cannot be treated as purely "
            f"non-authoritative: {binding.authority_class.value}"
        )


def choose_more_authoritative(
    left: AuthorityBinding,
    right: AuthorityBinding,
) -> AuthorityBinding:
    """
    Return the more authoritative of two bindings.

    Ordering:
    authoritative > derived_authoritative > advisory > descriptive

    Ties are structural and therefore invalid to resolve here.
    """
    if not isinstance(left, AuthorityBinding):
        raise AuthorityError("left must be an AuthorityBinding")
    if not isinstance(right, AuthorityBinding):
        raise AuthorityError("right must be an AuthorityBinding")

    left_rank = _authority_rank(left.authority_class)
    right_rank = _authority_rank(right.authority_class)

    if left_rank > right_rank:
        return left
    if right_rank > left_rank:
        return right

    raise AuthorityError(
        "cannot resolve equal-authority bindings without domain-specific rules: "
        f"{left.authority_class.value}"
    )


def assert_no_descriptive_decision_input(bindings: list[AuthorityBinding]) -> None:
    """
    Hard-fail if any descriptive binding is presented as decision input.
    """
    for binding in bindings:
        if not isinstance(binding, AuthorityBinding):
            raise AuthorityError("all bindings must be AuthorityBinding instances")
        if binding.authority_class == AuthorityClass.DESCRIPTIVE:
            raise AuthorityError(
                "descriptive data must not be used as decision input"
            )


def assert_no_advisory_decision_input(bindings: list[AuthorityBinding]) -> None:
    """
    Hard-fail if any advisory binding is presented as decision input.
    """
    for binding in bindings:
        if not isinstance(binding, AuthorityBinding):
            raise AuthorityError("all bindings must be AuthorityBinding instances")
        if binding.authority_class == AuthorityClass.ADVISORY:
            raise AuthorityError(
                "advisory data must not be used as decision input"
            )


def _authority_rank(authority_class: AuthorityClass) -> int:
    """
    Internal total ordering for authority resolution.
    """
    match authority_class:
        case AuthorityClass.AUTHORITATIVE:
            return 4
        case AuthorityClass.DERIVED_AUTHORITATIVE:
            return 3
        case AuthorityClass.ADVISORY:
            return 2
        case AuthorityClass.DESCRIPTIVE:
            return 1

    raise AuthorityError(f"unsupported authority class: {authority_class!r}")


def _coerce_enum[T: Enum](
    enum_cls: type[T],
    value: Any,
    *,
    field_name: str,
) -> T:
    if isinstance(value, enum_cls):
        return value

    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"{field_name} must be a non-empty string")

    normalized = value.strip()
    try:
        return enum_cls(normalized)
    except ValueError as exc:
        raise AuthorityError(
            f"{field_name} has unsupported value: {normalized!r}"
        ) from exc


def _coerce_required_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"{field_name} must be a non-empty string")
    return value.strip()


def _coerce_optional_str(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"{field_name} must be None or a non-empty string")
    return value.strip()


def _require_non_empty_str(value: str | None, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityError(f"{field_name} must be a non-empty string")