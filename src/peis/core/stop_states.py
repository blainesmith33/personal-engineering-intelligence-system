from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class StopStateError(ValueError):
    """Raised when stop-state invariants are violated."""


class StopState(str, Enum):
    """
    Authoritative shared stop-state algebra for PEIS.

    These are the only permitted stop-states. No aliases, synonyms, or
    subsystem-local variants are allowed.
    """

    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    UNKNOWN_PENDING = "UNKNOWN_PENDING"
    BLOCKED_HUMAN = "BLOCKED_HUMAN"
    CONFLICT = "CONFLICT"
    HALT_CONFLICT = "HALT_CONFLICT"
    HALT_STRUCTURAL = "HALT_STRUCTURAL"


_TERMINAL_STATES: frozenset[StopState] = frozenset(
    {
        StopState.RESOLVED,
        StopState.UNKNOWN,
        StopState.BLOCKED_HUMAN,
        StopState.CONFLICT,
        StopState.HALT_CONFLICT,
        StopState.HALT_STRUCTURAL,
    }
)

_HALT_STATES: frozenset[StopState] = frozenset(
    {
        StopState.HALT_CONFLICT,
        StopState.HALT_STRUCTURAL,
    }
)

_NON_TERMINAL_STATES: frozenset[StopState] = frozenset(
    {
        StopState.UNKNOWN_PENDING,
    }
)


@dataclass(frozen=True, slots=True)
class StopDecision:
    """
    Immutable stop-state decision artifact.

    Required invariants:
    - Every decision must declare exactly one authoritative stop-state.
    - Every decision must include a non-empty reason.
    - Decisions tied to authoritative evaluation must bind immutable evidence
      and policy snapshot identifiers.
    - Halt states may not be marked resumable within the same decision artifact.
    """

    stop_state: StopState
    reason: str
    evidence_snapshot_id: str
    policy_snapshot_id: str
    details: str | None = None
    resumable: bool = False

    def __post_init__(self) -> None:
        _require_non_empty_str(self.reason, field_name="reason")
        _require_non_empty_str(
            self.evidence_snapshot_id,
            field_name="evidence_snapshot_id",
        )
        _require_non_empty_str(
            self.policy_snapshot_id,
            field_name="policy_snapshot_id",
        )

        if self.details is not None:
            _require_non_empty_str(self.details, field_name="details")

        if is_halt_state(self.stop_state) and self.resumable:
            raise StopStateError(
                "halt states may not be marked resumable in the same decision"
            )

    @property
    def is_terminal(self) -> bool:
        """Return True when this decision is terminal."""
        return is_terminal_state(self.stop_state)

    @property
    def is_halt(self) -> bool:
        """Return True when this decision is a halt condition."""
        return is_halt_state(self.stop_state)

    @property
    def requires_human_intervention(self) -> bool:
        """
        Return True when the state requires explicit human action before
        normal forward progress may continue.
        """
        return self.stop_state in {
            StopState.BLOCKED_HUMAN,
            StopState.CONFLICT,
            StopState.HALT_CONFLICT,
            StopState.HALT_STRUCTURAL,
        }

    def to_dict(self) -> dict[str, Any]:
        """Stable serialization suitable for logs and artifacts."""
        return {
            "stop_state": self.stop_state.value,
            "reason": self.reason,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "policy_snapshot_id": self.policy_snapshot_id,
            "details": self.details,
            "resumable": self.resumable,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StopDecision":
        """Parse and validate a StopDecision from a mapping."""
        if not isinstance(data, Mapping):
            raise StopStateError("stop decision payload must be a mapping")

        return cls(
            stop_state=_coerce_stop_state(
                data.get("stop_state"),
                field_name="stop_state",
            ),
            reason=_coerce_required_str(
                data.get("reason"),
                field_name="reason",
            ),
            evidence_snapshot_id=_coerce_required_str(
                data.get("evidence_snapshot_id"),
                field_name="evidence_snapshot_id",
            ),
            policy_snapshot_id=_coerce_required_str(
                data.get("policy_snapshot_id"),
                field_name="policy_snapshot_id",
            ),
            details=_coerce_optional_str(
                data.get("details"),
                field_name="details",
            ),
            resumable=_coerce_bool(
                data.get("resumable", False),
                field_name="resumable",
            ),
        )


def make_stop_decision(
    *,
    stop_state: StopState,
    reason: str,
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
    details: str | None = None,
    resumable: bool = False,
) -> StopDecision:
    """Construct a validated stop decision."""
    return StopDecision(
        stop_state=stop_state,
        reason=reason,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        details=details,
        resumable=resumable,
    )


def is_valid_stop_state(value: Any) -> bool:
    """Return True only if value is a supported stop-state."""
    try:
        _coerce_stop_state(value, field_name="stop_state")
    except StopStateError:
        return False
    return True


def is_terminal_state(stop_state: StopState) -> bool:
    """Return True when the state is terminal."""
    _require_stop_state(stop_state, field_name="stop_state")
    return stop_state in _TERMINAL_STATES


def is_non_terminal_state(stop_state: StopState) -> bool:
    """Return True when the state is explicitly non-terminal."""
    _require_stop_state(stop_state, field_name="stop_state")
    return stop_state in _NON_TERMINAL_STATES


def is_halt_state(stop_state: StopState) -> bool:
    """Return True when the state is a halt condition."""
    _require_stop_state(stop_state, field_name="stop_state")
    return stop_state in _HALT_STATES


def assert_valid_stop_state(value: Any) -> StopState:
    """Coerce and validate a stop-state value."""
    return _coerce_stop_state(value, field_name="stop_state")


def assert_terminal_state(stop_state: StopState) -> None:
    """Hard-fail unless the stop-state is terminal."""
    _require_stop_state(stop_state, field_name="stop_state")
    if not is_terminal_state(stop_state):
        raise StopStateError(
            f"stop_state must be terminal, got: {stop_state.value}"
        )


def assert_non_terminal_state(stop_state: StopState) -> None:
    """Hard-fail unless the stop-state is non-terminal."""
    _require_stop_state(stop_state, field_name="stop_state")
    if not is_non_terminal_state(stop_state):
        raise StopStateError(
            f"stop_state must be non-terminal, got: {stop_state.value}"
        )


def assert_not_halt_state(stop_state: StopState) -> None:
    """Hard-fail if the stop-state is a halt condition."""
    _require_stop_state(stop_state, field_name="stop_state")
    if is_halt_state(stop_state):
        raise StopStateError(
            f"halt stop_state cannot proceed normally: {stop_state.value}"
        )


def assert_no_custom_stop_state(value: Any) -> None:
    """
    Hard-fail unless the value is one of the shared authoritative stop-states.

    This exists to make the contract explicit at subsystem boundaries.
    """
    _coerce_stop_state(value, field_name="stop_state")


def choose_more_severe_state(left: StopState, right: StopState) -> StopState:
    """
    Return the more severe of two stop-states using the shared ordering.

    Severity ordering:
    HALT_STRUCTURAL > HALT_CONFLICT > CONFLICT > BLOCKED_HUMAN
    > UNKNOWN_PENDING > UNKNOWN > RESOLVED

    Equal severity is treated as structurally ambiguous here and must be
    resolved by the caller with domain-specific context.
    """
    _require_stop_state(left, field_name="left")
    _require_stop_state(right, field_name="right")

    left_rank = _severity_rank(left)
    right_rank = _severity_rank(right)

    if left_rank > right_rank:
        return left
    if right_rank > left_rank:
        return right

    raise StopStateError(
        "cannot resolve equally severe stop-states without domain-specific rules: "
        f"{left.value} vs {right.value}"
    )


def can_progress(stop_state: StopState) -> bool:
    """
    Return True only when normal forward progress is allowed.

    UNKNOWN_PENDING is non-terminal but still indicates unresolved work.
    This function treats it as progress-blocking.
    """
    _require_stop_state(stop_state, field_name="stop_state")
    return stop_state == StopState.RESOLVED


def requires_human_intervention(stop_state: StopState) -> bool:
    """Return True when explicit human intervention is required."""
    _require_stop_state(stop_state, field_name="stop_state")
    return stop_state in {
        StopState.BLOCKED_HUMAN,
        StopState.CONFLICT,
        StopState.HALT_CONFLICT,
        StopState.HALT_STRUCTURAL,
    }


def _severity_rank(stop_state: StopState) -> int:
    match stop_state:
        case StopState.HALT_STRUCTURAL:
            return 7
        case StopState.HALT_CONFLICT:
            return 6
        case StopState.CONFLICT:
            return 5
        case StopState.BLOCKED_HUMAN:
            return 4
        case StopState.UNKNOWN_PENDING:
            return 3
        case StopState.UNKNOWN:
            return 2
        case StopState.RESOLVED:
            return 1

    raise StopStateError(f"unsupported stop_state: {stop_state!r}")


def _require_stop_state(value: Any, *, field_name: str) -> StopState:
    return _coerce_stop_state(value, field_name=field_name)


def _coerce_stop_state(value: Any, *, field_name: str) -> StopState:
    if isinstance(value, StopState):
        return value

    if not isinstance(value, str) or not value.strip():
        raise StopStateError(f"{field_name} must be a non-empty string")

    normalized = value.strip()
    try:
        return StopState(normalized)
    except ValueError as exc:
        raise StopStateError(
            f"{field_name} has unsupported value: {normalized!r}"
        ) from exc


def _coerce_required_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StopStateError(f"{field_name} must be a non-empty string")
    return value.strip()


def _coerce_optional_str(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise StopStateError(f"{field_name} must be None or a non-empty string")
    return value.strip()


def _coerce_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise StopStateError(f"{field_name} must be a bool")
    return value


def _require_non_empty_str(value: str | None, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StopStateError(f"{field_name} must be a non-empty string")