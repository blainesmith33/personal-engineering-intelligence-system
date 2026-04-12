from peis.decision_record import (
    DecisionRecord,
    DecisionRecordError,
    assert_same_decision_type,
    assert_same_subject,
    make_decision_record,
)

from peis.core.authority import (
    EvidenceRole,
    make_advisory_binding,
    make_authoritative_binding,
)
from peis.core.determinism import build_minimal_envelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopState, make_stop_decision


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

    stop_decision = make_stop_decision(
        stop_state=StopState.RESOLVED,
        reason="ok",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    return authority, evidence, determinism, stop_decision


def test_make_decision_record_success():
    authority, evidence, determinism, stop_decision = _make_valid_components()

    record = make_decision_record(
        decision_record_id="d1",
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="done",
    )

    assert record.decision_record_id == "d1"
    assert record.subject_id == "s1"
    assert record.stop_state == StopState.RESOLVED
    assert record.is_terminal is True
    assert record.is_halt is False


def test_decision_record_to_dict_round_trip():
    authority, evidence, determinism, stop_decision = _make_valid_components()

    record = DecisionRecord(
        decision_record_id="d1",
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="done",
        rationale="because",
        emitted_by="tester",
    )

    payload = record.to_dict()
    restored = DecisionRecord.from_dict(payload)

    assert restored == record


def test_decision_record_rejects_advisory_authority():
    _, evidence, determinism, stop_decision = _make_valid_components()

    advisory = make_advisory_binding(
        evidence_role=EvidenceRole.DECISION,
        source_label="test",
    )

    try:
        DecisionRecord(
            decision_record_id="d1",
            subject_id="s1",
            decision_type="classify",
            authority=advisory,
            evidence=evidence,
            determinism=determinism,
            stop_decision=stop_decision,
            summary="done",
        )
        assert False
    except DecisionRecordError:
        assert True


def test_decision_record_rejects_snapshot_mismatch():
    authority, evidence, determinism, _ = _make_valid_components()

    bad_stop_decision = make_stop_decision(
        stop_state=StopState.RESOLVED,
        reason="ok",
        evidence_snapshot_id="e2",
        policy_snapshot_id="p1",
    )

    try:
        DecisionRecord(
            decision_record_id="d1",
            subject_id="s1",
            decision_type="classify",
            authority=authority,
            evidence=evidence,
            determinism=determinism,
            stop_decision=bad_stop_decision,
            summary="done",
        )
        assert False
    except DecisionRecordError:
        assert True


def test_assert_same_subject_passes():
    authority, evidence, determinism, stop_decision = _make_valid_components()

    left = make_decision_record(
        decision_record_id="d1",
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="left",
    )

    right = make_decision_record(
        decision_record_id="d2",
        subject_id="s1",
        decision_type="review",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="right",
    )

    assert_same_subject(left, right)


def test_assert_same_subject_fails():
    authority, evidence, determinism, stop_decision = _make_valid_components()

    left = make_decision_record(
        decision_record_id="d1",
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="left",
    )

    right = make_decision_record(
        decision_record_id="d2",
        subject_id="s2",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="right",
    )

    try:
        assert_same_subject(left, right)
        assert False
    except DecisionRecordError:
        assert True


def test_assert_same_decision_type_fails():
    authority, evidence, determinism, stop_decision = _make_valid_components()

    left = make_decision_record(
        decision_record_id="d1",
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="left",
    )

    right = make_decision_record(
        decision_record_id="d2",
        subject_id="s1",
        decision_type="review",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="right",
    )

    try:
        assert_same_decision_type(left, right)
        assert False
    except DecisionRecordError:
        assert True