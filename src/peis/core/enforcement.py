from __future__ import annotations

from collections.abc import Iterable

from peis.core.authority import AuthorityBinding, assert_decision_authority
from peis.core.determinism import (
    DeterminismEnvelope,
    assert_no_mixed_envelopes,
)
from peis.core.evidence import EvidenceBinding, assert_no_mixed_bindings
from peis.core.stop_states import (
    StopDecision,
    StopState,
    assert_no_custom_stop_state,
    can_progress,
    is_halt_state,
    requires_human_intervention,
)
from peis.core.validation import require


class EnforcementError(ValueError):
    """Raised when cross-module invariants are violated."""


def enforce_decision_contract(
    *,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    decision: StopDecision,
) -> None:
    """
    Enforce the minimum valid cross-module contract for a decision.

    Guarantees:
    - decision-driving authority is authoritative
    - stop-state is from the shared authoritative algebra
    - decision snapshot IDs match evidence binding
    - determinism envelope snapshot IDs match evidence binding
    """

    assert_decision_authority(authority)
    assert_no_custom_stop_state(decision.stop_state)

    require(
        decision.evidence_snapshot_id == evidence.evidence_snapshot_id,
        "decision evidence_snapshot_id mismatch",
    )
    require(
        decision.policy_snapshot_id == evidence.policy_snapshot_id,
        "decision policy_snapshot_id mismatch",
    )

    require(
        determinism.evidence_snapshot_id == evidence.evidence_snapshot_id,
        "determinism/evidence mismatch for evidence_snapshot_id",
    )
    require(
        determinism.policy_snapshot_id == evidence.policy_snapshot_id,
        "determinism/evidence mismatch for policy_snapshot_id",
    )


def enforce_input_set(
    *,
    authorities: Iterable[AuthorityBinding],
    evidence_bindings: Iterable[EvidenceBinding],
    determinism_envelopes: Iterable[DeterminismEnvelope],
) -> None:
    """
    Enforce that a set of decision inputs is structurally valid.

    Guarantees:
    - all authorities are allowed to drive decisions
    - all evidence bindings are identical
    - all determinism envelopes are identical
    - all envelopes agree with the shared evidence/policy binding
    """

    authority_list = list(authorities)
    evidence_list = list(evidence_bindings)
    envelope_list = list(determinism_envelopes)

    require(bool(authority_list), "authorities must not be empty")
    require(bool(evidence_list), "evidence_bindings must not be empty")
    require(bool(envelope_list), "determinism_envelopes must not be empty")

    for authority in authority_list:
        assert_decision_authority(authority)

    assert_no_mixed_bindings(evidence_list)
    assert_no_mixed_envelopes(envelope_list)

    canonical_binding = evidence_list[0]

    for envelope in envelope_list:
        require(
            envelope.evidence_snapshot_id == canonical_binding.evidence_snapshot_id,
            "determinism envelope evidence_snapshot_id does not match canonical evidence binding",
        )
        require(
            envelope.policy_snapshot_id == canonical_binding.policy_snapshot_id,
            "determinism envelope policy_snapshot_id does not match canonical evidence binding",
        )


def enforce_stop_state_actionability(stop_state: StopState) -> None:
    """
    Enforce that a stop-state is recognized and governed.

    This is the boundary check to prevent subsystem-local or ad hoc states.
    """

    assert_no_custom_stop_state(stop_state)


def enforce_progress_allowed(stop_state: StopState) -> None:
    """
    Hard-fail unless the stop-state allows normal forward progress.

    Current Phase 1 rule:
    - only RESOLVED allows normal progress
    """

    assert_no_custom_stop_state(stop_state)

    require(
        can_progress(stop_state),
        f"normal progress is not allowed for stop_state={stop_state.value}",
    )


def enforce_no_halt_progression(stop_state: StopState) -> None:
    """
    Hard-fail if a halt state is being treated as normally progressable.
    """

    assert_no_custom_stop_state(stop_state)

    require(
        not is_halt_state(stop_state),
        f"halt state cannot proceed normally: {stop_state.value}",
    )


def enforce_human_gate(stop_state: StopState, *, human_authorized: bool) -> None:
    """
    Enforce explicit human authorization where the stop-state requires it.
    """

    assert_no_custom_stop_state(stop_state)

    if requires_human_intervention(stop_state):
        require(
            human_authorized,
            f"human authorization required for stop_state={stop_state.value}",
        )


def enforce_decision_set(
    *,
    decisions: Iterable[StopDecision],
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
) -> None:
    """
    Enforce that a batch of decisions is internally consistent with the same
    evidence and determinism context.
    """

    decision_list = list(decisions)
    require(bool(decision_list), "decisions must not be empty")

    for decision in decision_list:
        assert_no_custom_stop_state(decision.stop_state)

        require(
            decision.evidence_snapshot_id == evidence.evidence_snapshot_id,
            "decision set contains mismatched evidence_snapshot_id",
        )
        require(
            decision.policy_snapshot_id == evidence.policy_snapshot_id,
            "decision set contains mismatched policy_snapshot_id",
        )

        require(
            determinism.evidence_snapshot_id == evidence.evidence_snapshot_id,
            "determinism/evidence mismatch for evidence_snapshot_id",
        )
        require(
            determinism.policy_snapshot_id == evidence.policy_snapshot_id,
            "determinism/evidence mismatch for policy_snapshot_id",
        )