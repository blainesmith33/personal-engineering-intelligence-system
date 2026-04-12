from peis.core.authority import EvidenceRole, make_authoritative_binding
from peis.core.determinism import build_minimal_envelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopState, make_stop_decision
from peis.plan_record import PlanStep
from peis.runtime.orchestrator import (
    OrchestratorError,
    build_inputs,
    orchestrate,
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


def test_build_inputs_success():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    inputs = build_inputs(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary="evaluation",
        decision_summary="decision",
        plan_summary="plan",
        steps=(),
    )

    assert inputs.subject_id == "s1"
    assert inputs.stop_decision.stop_state == StopState.RESOLVED


def test_orchestrate_success_with_noop_plan():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    inputs = build_inputs(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary="evaluation",
        decision_summary="decision",
        plan_summary="plan",
        steps=(),
    )

    result = orchestrate(inputs)

    assert result.subject_id == "s1"
    assert result.stop_state == StopState.RESOLVED
    assert result.plan_record.is_noop_plan is True
    assert result.decision_record.subject_id == "s1"
    assert result.evaluation_record.subject_id == "s1"


def test_orchestrate_success_with_plan_steps():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
    )

    inputs = build_inputs(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary="evaluation",
        decision_summary="decision",
        plan_summary="plan",
        steps=(step,),
    )

    result = orchestrate(inputs)

    assert len(result.plan_record.steps) == 1
    assert result.plan_record.is_noop_plan is False


def test_orchestrate_rejects_non_inputs_object():
    try:
        orchestrate("not-inputs")  # type: ignore[arg-type]
        assert False
    except OrchestratorError:
        assert True


def test_build_inputs_rejects_invalid_step_type():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    try:
        build_inputs(
            subject_id="s1",
            evaluation_type="eval",
            decision_type="decision",
            plan_type="plan",
            authority=authority,
            evidence=evidence,
            determinism=determinism,
            stop_decision=stop_decision,
            evaluation_summary="evaluation",
            decision_summary="decision",
            plan_summary="plan",
            steps=("not-a-step",),  # type: ignore[arg-type]
        )
        assert False
    except OrchestratorError:
        assert True


def test_orchestrate_rejects_halt_plan_generation():
    authority, evidence, determinism, _ = _make_valid_context()

    halt_decision = make_stop_decision(
        stop_state=StopState.HALT_CONFLICT,
        reason="halt",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    inputs = build_inputs(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=halt_decision,
        evaluation_summary="evaluation",
        decision_summary="decision",
        plan_summary="plan",
        steps=(),
    )

    try:
        orchestrate(inputs)
        assert False
    except Exception:
        assert True