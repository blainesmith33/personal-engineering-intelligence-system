from peis.builders import (
    build_decision_record,
    build_evaluation_record,
    build_plan_record,
)

from peis.core.authority import (
    make_authoritative_binding,
    make_advisory_binding,
    EvidenceRole,
)

from peis.core.evidence import EvidenceBinding
from peis.core.determinism import build_minimal_envelope
from peis.core.stop_states import make_stop_decision, StopState
from peis.plan_record import PlanStep


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------


def _make_valid_context():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.INPUT,
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
        source_label="test",
    )

    evidence = EvidenceBinding("e1", "p1")

    determinism = build_minimal_envelope(
        file_hash="f",
        extractor_binary_hash="b",
        extractor_config_hash="c",
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


# -------------------------------------------------------
# Decision Builder
# -------------------------------------------------------


def test_build_decision_record_success():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    assert decision.subject_id == "s1"
    assert decision.stop_state == StopState.RESOLVED
    assert decision.decision_record_id.startswith("decision_")


def test_build_decision_record_rejects_advisory_authority():
    _, evidence, determinism, stop_decision = _make_valid_context()

    advisory = make_advisory_binding(
        evidence_role=EvidenceRole.INPUT,
        source_label="test",
    )

    try:
        build_decision_record(
            subject_id="s1",
            decision_type="classify",
            authority=advisory,
            evidence=evidence,
            determinism=determinism,
            stop_decision=stop_decision,
            summary="decision",
        )
        assert False
    except Exception:
        assert True


# -------------------------------------------------------
# Evaluation Builder
# -------------------------------------------------------


def test_build_evaluation_record_success():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    evaluation = build_evaluation_record(
        subject_id="s1",
        evaluation_type="eval",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id=decision.decision_record_id,
        result_stop_state=decision.stop_state,
        summary="eval",
    )

    assert evaluation.subject_id == "s1"
    assert evaluation.decision_record_id == decision.decision_record_id
    assert evaluation.evaluation_record_id.startswith("evaluation_")


def test_build_evaluation_record_rejects_mixed_evidence():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    bad_evidence = EvidenceBinding("e2", "p1")

    try:
        build_evaluation_record(
            subject_id="s1",
            evaluation_type="eval",
            input_authorities=(authority,),
            input_evidence_bindings=(evidence, bad_evidence),
            input_determinism_envelopes=(determinism, determinism),
            decision_record_id=decision.decision_record_id,
            result_stop_state=decision.stop_state,
            summary="eval",
        )
        assert False
    except Exception:
        assert True


# -------------------------------------------------------
# Plan Builder
# -------------------------------------------------------


def test_build_plan_record_success_with_steps():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
    )

    plan = build_plan_record(
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id=decision.decision_record_id,
        basis_stop_state=decision.stop_state,
        steps=(step,),
        summary="plan",
    )

    assert plan.subject_id == "s1"
    assert len(plan.steps) == 1
    assert plan.plan_record_id.startswith("plan_")


def test_build_plan_record_allows_empty_steps():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    plan = build_plan_record(
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id=decision.decision_record_id,
        basis_stop_state=decision.stop_state,
        steps=(),
        summary="plan",
    )

    assert plan.is_noop_plan
    assert len(plan.steps) == 0