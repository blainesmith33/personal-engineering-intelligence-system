from __future__ import annotations

from pathlib import Path

from peis.execution.persist import persist_execution_result
from peis.execution.result_record import build_execution_result_record
from peis.storage.execution_result_record.store import (
    load_execution_result_record,
)


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


def test_execution_result_persist_and_load(tmp_path: Path):
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

    file_path = persist_execution_result(
        root=tmp_path,
        record=record,
    )

    assert file_path.exists()

    loaded = load_execution_result_record(
        root=tmp_path,
        execution_result_record_id=record.execution_result_record_id,
    )

    assert loaded.to_dict() == record.to_dict()