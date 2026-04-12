from peis.plan_record import (
    PlanRecord,
    PlanRecordError,
    PlanStep,
    assert_same_plan_type,
    assert_same_subject,
    make_plan_record,
)

from peis.core.authority import (
    EvidenceRole,
    make_advisory_binding,
    make_authoritative_binding,
)
from peis.core.determinism import build_minimal_envelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopState


def _make_valid_components():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.DECISION,
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

    return authority, evidence, determinism


def test_plan_step_round_trip():
    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
        requires_human_authorization=False,
        metadata={"k": "v"},
    )

    payload = step.to_dict()
    restored = PlanStep.from_dict(payload)

    assert restored == step


def test_make_plan_record_success_with_steps():
    authority, evidence, determinism = _make_valid_components()

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
    )

    record = make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(step,),
        summary="done",
    )

    assert record.plan_record_id == "p1"
    assert record.subject_id == "s1"
    assert record.basis_stop_state == StopState.RESOLVED
    assert len(record.steps) == 1
    assert record.is_noop_plan is False


def test_plan_record_allows_empty_steps_as_noop_plan():
    authority, evidence, determinism = _make_valid_components()

    record = make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="noop",
    )

    assert record.is_noop_plan is True
    assert len(record.steps) == 0


def test_plan_record_to_dict_round_trip():
    authority, evidence, determinism = _make_valid_components()

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
    )

    record = PlanRecord(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(step,),
        summary="done",
        rationale="because",
        emitted_by="tester",
        human_authorized=False,
    )

    payload = record.to_dict()
    restored = PlanRecord.from_dict(payload)

    assert restored == record


def test_plan_record_rejects_advisory_authority():
    _, evidence, determinism = _make_valid_components()

    advisory = make_advisory_binding(
        evidence_role=EvidenceRole.DECISION,
        source_label="test",
    )

    try:
        PlanRecord(
            plan_record_id="p1",
            subject_id="s1",
            plan_type="plan",
            authority=advisory,
            evidence=evidence,
            determinism=determinism,
            basis_decision_record_id="d1",
            basis_stop_state=StopState.RESOLVED,
            steps=(),
            summary="done",
        )
        assert False
    except PlanRecordError:
        assert True


def test_plan_record_rejects_determinism_evidence_mismatch():
    authority, evidence, _ = _make_valid_components()

    bad_determinism = build_minimal_envelope(
        file_hash="f1",
        extractor_binary_hash="b1",
        extractor_config_hash="c1",
        schema_version="1",
        evidence_snapshot_id="e2",
        policy_snapshot_id="p1",
    )

    try:
        PlanRecord(
            plan_record_id="p1",
            subject_id="s1",
            plan_type="plan",
            authority=authority,
            evidence=evidence,
            determinism=bad_determinism,
            basis_decision_record_id="d1",
            basis_stop_state=StopState.RESOLVED,
            steps=(),
            summary="done",
        )
        assert False
    except PlanRecordError:
        assert True


def test_plan_record_rejects_halt_state():
    authority, evidence, determinism = _make_valid_components()

    try:
        PlanRecord(
            plan_record_id="p1",
            subject_id="s1",
            plan_type="plan",
            authority=authority,
            evidence=evidence,
            determinism=determinism,
            basis_decision_record_id="d1",
            basis_stop_state=StopState.HALT_CONFLICT,
            steps=(),
            summary="done",
        )
        assert False
    except PlanRecordError:
        assert True


def test_plan_record_requires_human_authorization_for_blocked_human():
    authority, evidence, determinism = _make_valid_components()

    try:
        PlanRecord(
            plan_record_id="p1",
            subject_id="s1",
            plan_type="plan",
            authority=authority,
            evidence=evidence,
            determinism=determinism,
            basis_decision_record_id="d1",
            basis_stop_state=StopState.BLOCKED_HUMAN,
            steps=(),
            summary="done",
            human_authorized=False,
        )
        assert False
    except PlanRecordError:
        assert True


def test_plan_record_allows_human_gated_blocked_human_plan():
    authority, evidence, determinism = _make_valid_components()

    record = PlanRecord(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.BLOCKED_HUMAN,
        steps=(),
        summary="done",
        human_authorized=True,
    )

    assert record.human_authorized is True
    assert record.basis_stop_state == StopState.BLOCKED_HUMAN


def test_assert_same_subject_passes():
    authority, evidence, determinism = _make_valid_components()

    left = make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="left",
    )

    right = make_plan_record(
        plan_record_id="p2",
        subject_id="s1",
        plan_type="review",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d2",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="right",
    )

    assert_same_subject(left, right)


def test_assert_same_subject_fails():
    authority, evidence, determinism = _make_valid_components()

    left = make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="left",
    )

    right = make_plan_record(
        plan_record_id="p2",
        subject_id="s2",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d2",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="right",
    )

    try:
        assert_same_subject(left, right)
        assert False
    except PlanRecordError:
        assert True


def test_assert_same_plan_type_fails():
    authority, evidence, determinism = _make_valid_components()

    left = make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="left",
    )

    right = make_plan_record(
        plan_record_id="p2",
        subject_id="s1",
        plan_type="review",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d2",
        basis_stop_state=StopState.RESOLVED,
        steps=(),
        summary="right",
    )

    try:
        assert_same_plan_type(left, right)
        assert False
    except PlanRecordError:
        assert True