from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class EvidenceError(ValueError):
    """Raised when evidence invariants are violated."""


# ---------------------------
# Core Snapshot Primitives
# ---------------------------


@dataclass(frozen=True, slots=True)
class EvidenceSnapshotRef:
    """
    Immutable reference to an evidence snapshot.

    This is the authoritative anchor for all evidence-derived decisions.
    """

    evidence_snapshot_id: str

    def __post_init__(self) -> None:
        _require_non_empty_str(
            self.evidence_snapshot_id,
            field_name="evidence_snapshot_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_snapshot_id": self.evidence_snapshot_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceSnapshotRef":
        if not isinstance(data, Mapping):
            raise EvidenceError("payload must be a mapping")

        return cls(
            evidence_snapshot_id=_coerce_required_str(
                data.get("evidence_snapshot_id"),
                field_name="evidence_snapshot_id",
            )
        )


@dataclass(frozen=True, slots=True)
class PolicySnapshotRef:
    """
    Immutable reference to a policy snapshot.

    This binds decisions to the exact policy state used.
    """

    policy_snapshot_id: str

    def __post_init__(self) -> None:
        _require_non_empty_str(
            self.policy_snapshot_id,
            field_name="policy_snapshot_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_snapshot_id": self.policy_snapshot_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PolicySnapshotRef":
        if not isinstance(data, Mapping):
            raise EvidenceError("payload must be a mapping")

        return cls(
            policy_snapshot_id=_coerce_required_str(
                data.get("policy_snapshot_id"),
                field_name="policy_snapshot_id",
            )
        )


# ---------------------------
# Combined Binding
# ---------------------------


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    """
    Combined evidence + policy binding.

    This is the canonical structure that all authoritative artifacts must carry.
    """

    evidence_snapshot_id: str
    policy_snapshot_id: str

    def __post_init__(self) -> None:
        _require_non_empty_str(
            self.evidence_snapshot_id,
            field_name="evidence_snapshot_id",
        )
        _require_non_empty_str(
            self.policy_snapshot_id,
            field_name="policy_snapshot_id",
        )

    @property
    def tuple(self) -> tuple[str, str]:
        return (self.evidence_snapshot_id, self.policy_snapshot_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "policy_snapshot_id": self.policy_snapshot_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceBinding":
        if not isinstance(data, Mapping):
            raise EvidenceError("payload must be a mapping")

        return cls(
            evidence_snapshot_id=_coerce_required_str(
                data.get("evidence_snapshot_id"),
                field_name="evidence_snapshot_id",
            ),
            policy_snapshot_id=_coerce_required_str(
                data.get("policy_snapshot_id"),
                field_name="policy_snapshot_id",
            ),
        )


# ---------------------------
# Invariants / Enforcement
# ---------------------------


def assert_same_binding(
    left: EvidenceBinding,
    right: EvidenceBinding,
) -> None:
    """
    Hard-fail unless two bindings are identical.

    This enforces determinism and prevents cross-snapshot mixing.
    """
    _require_binding(left, "left")
    _require_binding(right, "right")

    if left.tuple != right.tuple:
        raise EvidenceError(
            "evidence bindings must match exactly for deterministic operations"
        )


def assert_binding_present(binding: EvidenceBinding | None) -> None:
    """Hard-fail if binding is missing."""
    if binding is None:
        raise EvidenceError("evidence binding is required but missing")
    _require_binding(binding, "binding")


def assert_no_mixed_bindings(bindings: list[EvidenceBinding]) -> None:
    """
    Hard-fail if multiple different bindings are present.

    Used when evaluating sets of inputs that must share the same snapshot.
    """
    if not bindings:
        raise EvidenceError("bindings list must not be empty")

    first = bindings[0]
    _require_binding(first, "bindings[0]")

    for i, b in enumerate(bindings[1:], start=1):
        _require_binding(b, f"bindings[{i}]")
        if b.tuple != first.tuple:
            raise EvidenceError(
                "mixed evidence bindings detected within a single operation"
            )


def merge_binding(
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
) -> EvidenceBinding:
    """
    Explicit constructor for clarity at call sites.
    """
    return EvidenceBinding(
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
    )


# ---------------------------
# Determinism Envelope Helper
# ---------------------------


@dataclass(frozen=True, slots=True)
class DeterminismEnvelope:
    """
    Minimal determinism envelope.

    This will be expanded in determinism.py, but this version ensures that
    evidence + policy are always included.
    """

    evidence_snapshot_id: str
    policy_snapshot_id: str

    def __post_init__(self) -> None:
        _require_non_empty_str(
            self.evidence_snapshot_id,
            field_name="evidence_snapshot_id",
        )
        _require_non_empty_str(
            self.policy_snapshot_id,
            field_name="policy_snapshot_id",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "policy_snapshot_id": self.policy_snapshot_id,
        }

    @classmethod
    def from_binding(cls, binding: EvidenceBinding) -> "DeterminismEnvelope":
        _require_binding(binding, "binding")
        return cls(
            evidence_snapshot_id=binding.evidence_snapshot_id,
            policy_snapshot_id=binding.policy_snapshot_id,
        )


# ---------------------------
# Internal Helpers
# ---------------------------


def _require_binding(value: Any, name: str) -> EvidenceBinding:
    if not isinstance(value, EvidenceBinding):
        raise EvidenceError(f"{name} must be an EvidenceBinding")
    return value


def _coerce_required_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field_name} must be a non-empty string")
    return value.strip()


def _require_non_empty_str(value: str | None, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field_name} must be a non-empty string")