from peis.evaluation_record import (
    EvaluationRecord,
    EvaluationRecordError,
    assert_same_evaluation_type,
    assert_same_subject,
    make_evaluation_record,
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

    return authority, evidence, determinism


def test_make_evaluation_record_success():
    authority, evidence, determinism = _make_valid_components()

    record = make_evaluation_record(
        evaluation_record_id="ev1",
        subject_id="s1",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d1",
        result_stop_state=StopState.RESOLVED,
        summary="done",
    )

    assert record.evaluation_record_id == "ev1"
    assert record.subject_id == "s1"
    assert record.decision_record_id == "d1"
    assert record.result_stop_state == StopState.RESOLVED
    assert record.evidence_snapshot_id == "e1"
    assert record.policy_snapshot_id == "p1"


def test_evaluation_record_to_dict_round_trip():
    authority, evidence, determinism = _make_valid_components()

    record = EvaluationRecord(
        evaluation_record_id="ev1",
        subject_id="s1",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d1",
        result_stop_state=StopState.RESOLVED,
        summary="done",
        rationale="because",
        emitted_by="tester",
    )

    payload = record.to_dict()
    restored = EvaluationRecord.from_dict(payload)

    assert restored == record


def test_evaluation_record_rejects_advisory_authority():
    _, evidence, determinism = _make_valid_components()

    advisory = make_advisory_binding(
        evidence_role=EvidenceRole.INPUT,
        source_label="test",
    )

    try:
        EvaluationRecord(
            evaluation_record_id="ev1",
            subject_id="s1",
            evaluation_type="classify",
            input_authorities=(advisory,),
            input_evidence_bindings=(evidence,),
            input_determinism_envelopes=(determinism,),
            decision_record_id="d1",
            result_stop_state=StopState.RESOLVED,
            summary="done",
        )
        assert False
    except EvaluationRecordError:
        assert True


def test_evaluation_record_rejects_mixed_evidence_bindings():
    authority, evidence, determinism = _make_valid_components()
    bad_evidence = EvidenceBinding("e2", "p1")

    try:
        EvaluationRecord(
            evaluation_record_id="ev1",
            subject_id="s1",
            evaluation_type="classify",
            input_authorities=(authority, authority),
            input_evidence_bindings=(evidence, bad_evidence),
            input_determinism_envelopes=(determinism, determinism),
            decision_record_id="d1",
            result_stop_state=StopState.RESOLVED,
            summary="done",
        )
        assert False
    except EvaluationRecordError:
        assert True


def test_evaluation_record_rejects_mixed_determinism_envelopes():
    authority, evidence, determinism = _make_valid_components()

    bad_determinism = build_minimal_envelope(
        file_hash="f2",
        extractor_binary_hash="b1",
        extractor_config_hash="c1",
        schema_version="1",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    try:
        EvaluationRecord(
            evaluation_record_id="ev1",
            subject_id="s1",
            evaluation_type="classify",
            input_authorities=(authority, authority),
            input_evidence_bindings=(evidence, evidence),
            input_determinism_envelopes=(determinism, bad_determinism),
            decision_record_id="d1",
            result_stop_state=StopState.RESOLVED,
            summary="done",
        )
        assert False
    except EvaluationRecordError:
        assert True


def test_assert_same_subject_passes():
    authority, evidence, determinism = _make_valid_components()

    left = make_evaluation_record(
        evaluation_record_id="ev1",
        subject_id="s1",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d1",
        result_stop_state=StopState.RESOLVED,
        summary="left",
    )

    right = make_evaluation_record(
        evaluation_record_id="ev2",
        subject_id="s1",
        evaluation_type="review",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d2",
        result_stop_state=StopState.UNKNOWN,
        summary="right",
    )

    assert_same_subject(left, right)


def test_assert_same_subject_fails():
    authority, evidence, determinism = _make_valid_components()

    left = make_evaluation_record(
        evaluation_record_id="ev1",
        subject_id="s1",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d1",
        result_stop_state=StopState.RESOLVED,
        summary="left",
    )

    right = make_evaluation_record(
        evaluation_record_id="ev2",
        subject_id="s2",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d2",
        result_stop_state=StopState.RESOLVED,
        summary="right",
    )

    try:
        assert_same_subject(left, right)
        assert False
    except EvaluationRecordError:
        assert True


def test_assert_same_evaluation_type_fails():
    authority, evidence, determinism = _make_valid_components()

    left = make_evaluation_record(
        evaluation_record_id="ev1",
        subject_id="s1",
        evaluation_type="classify",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d1",
        result_stop_state=StopState.RESOLVED,
        summary="left",
    )

    right = make_evaluation_record(
        evaluation_record_id="ev2",
        subject_id="s1",
        evaluation_type="review",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id="d2",
        result_stop_state=StopState.RESOLVED,
        summary="right",
    )

    try:
        assert_same_evaluation_type(left, right)
        assert False
    except EvaluationRecordError:
        assert True