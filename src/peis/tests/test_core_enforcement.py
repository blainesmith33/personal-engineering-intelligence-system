from peis.core.authority import (
    EvidenceRole,
    make_advisory_binding,
    make_authoritative_binding,
)
from peis.core.determinism import build_minimal_envelope
from peis.core.enforcement import (
    enforce_decision_contract,
    enforce_decision_set,
    enforce_human_gate,
    enforce_input_set,
    enforce_no_halt_progression,
    enforce_progress_allowed,
    enforce_stop_state_actionability,
)
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import (
    StopState,
    make_stop_decision,
)


def _make_valid_context():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.INPUT,
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
        source_label="test",
    )

    evidence = EvidenceBinding("e1", "p1")

    determinism = build_minimal_envelope(
        file_hash="f1",
        extractor_binary_hash="b1",
        extractor_config_hash="c1",
        schema_version="1",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    stop_decision = make_stop_decision(
        stop_state=StopState.RESOLVED,
        reason="ok",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    return authority, evidence, determinism, stop_decision


def test_enforce_decision_contract_success():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    enforce_decision_contract(
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        decision=stop_decision,
    )


def test_enforce_decision_contract_rejects_non_authoritative_binding():
    _, evidence, determinism, stop_decision = _make_valid_context()

    advisory = make_advisory_binding(
        evidence_role=EvidenceRole.INPUT,
        source_label="test",
    )

    try:
        enforce_decision_contract(
            authority=advisory,
            evidence=evidence,
            determinism=determinism,
            decision=stop_decision,
        )
        assert False
    except Exception:
        assert True


def test_enforce_input_set_success():
    authority, evidence, determinism, _ = _make_valid_context()

    enforce_input_set(
        authorities=(authority,),
        evidence_bindings=(evidence,),
        determinism_envelopes=(determinism,),
    )


def test_enforce_input_set_rejects_mixed_evidence():
    authority, evidence, determinism, _ = _make_valid_context()
    bad_evidence = EvidenceBinding("e2", "p1")

    try:
        enforce_input_set(
            authorities=(authority,),
            evidence_bindings=(evidence, bad_evidence),
            determinism_envelopes=(determinism, determinism),
        )
        assert False
    except Exception:
        assert True


def test_enforce_stop_state_actionability_accepts_valid_state():
    enforce_stop_state_actionability(StopState.RESOLVED)


def test_enforce_progress_allowed_accepts_resolved():
    enforce_progress_allowed(StopState.RESOLVED)


def test_enforce_progress_allowed_rejects_unknown():
    try:
        enforce_progress_allowed(StopState.UNKNOWN)
        assert False
    except Exception:
        assert True


def test_enforce_no_halt_progression_rejects_halt():
    try:
        enforce_no_halt_progression(StopState.HALT_STRUCTURAL)
        assert False
    except Exception:
        assert True


def test_enforce_human_gate_rejects_missing_authorization():
    try:
        enforce_human_gate(
            StopState.BLOCKED_HUMAN,
            human_authorized=False,
        )
        assert False
    except Exception:
        assert True


def test_enforce_human_gate_allows_authorized_blocked_human():
    enforce_human_gate(
        StopState.BLOCKED_HUMAN,
        human_authorized=True,
    )


def test_enforce_decision_set_success():
    _, evidence, determinism, stop_decision = _make_valid_context()

    enforce_decision_set(
        decisions=(stop_decision,),
        evidence=evidence,
        determinism=determinism,
    )


def test_enforce_decision_set_rejects_snapshot_mismatch():
    _, evidence, determinism, _ = _make_valid_context()

    bad_decision = make_stop_decision(
        stop_state=StopState.RESOLVED,
        reason="ok",
        evidence_snapshot_id="e2",
        policy_snapshot_id="p1",
    )

    try:
        enforce_decision_set(
            decisions=(bad_decision,),
            evidence=evidence,
            determinism=determinism,
        )
        assert False
    except Exception:
        assert True