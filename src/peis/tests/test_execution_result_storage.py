from __future__ import annotations

from peis.execution.result_record import build_execution_result_record


def _authority():
    return {
        "authority_type": "authoritative",
        "policy_snapshot_id": "p1",
    }


def _evidence():
    return {
        "evidence_snapshot_id": "e1",
        "policy_snapshot_id": "p1",
    }


def _determinism():
    return {
        "determinism_id": "d1",
    }


def _step():
    return {
        "step_index": 0,
        "step_id": "step1",
        "action_type": "noop",
        "status": "SUCCEEDED",
        "input_payload": {"x": 1},
        "output_payload": {"y": 2},
        "error": None,
    }


def _summary():
    return {
        "steps_total": 1,
        "steps_succeeded": 1,
        "steps_failed": 0,
        "steps_skipped": 0,
    }


def test_execution_result_record_to_from_dict_roundtrip():
    record = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan1",
        decision_record_id="decision1",
        subject_id="subject1",
        execution_status="SUCCEEDED",
        step_results=[_step()],
        summary=_summary(),
    )

    payload = record.to_dict()
    rebuilt = record.from_dict(payload)

    assert rebuilt.to_dict() == payload


def test_execution_result_record_deterministic_id_stable():
    record1 = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan1",
        decision_record_id="decision1",
        subject_id="subject1",
        execution_status="SUCCEEDED",
        step_results=[_step()],
        summary=_summary(),
    )

    record2 = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan1",
        decision_record_id="decision1",
        subject_id="subject1",
        execution_status="SUCCEEDED",
        step_results=[_step()],
        summary=_summary(),
    )

    assert record1.execution_result_record_id == record2.execution_result_record_id


def test_execution_result_record_deterministic_id_changes_on_payload_change():
    record1 = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan1",
        decision_record_id="decision1",
        subject_id="subject1",
        execution_status="SUCCEEDED",
        step_results=[_step()],
        summary=_summary(),
    )

    altered_step = _step()
    altered_step["input_payload"] = {"x": 999}

    record2 = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan1",
        decision_record_id="decision1",
        subject_id="subject1",
        execution_status="SUCCEEDED",
        step_results=[altered_step],
        summary=_summary(),
    )

    assert record1.execution_result_record_id != record2.execution_result_record_id