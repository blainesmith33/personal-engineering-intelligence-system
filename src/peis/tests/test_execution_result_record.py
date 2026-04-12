from __future__ import annotations

import pytest

from peis.execution.result_record import (
    ARTIFACT_TYPE,
    SCHEMA_VERSION,
    ExecutionResultRecord,
    build_execution_result_record,
    make_execution_result_id,
)


def _authority() -> dict:
    return {
        "authority_type": "authoritative",
        "policy_snapshot_id": "policy_123",
    }


def _evidence() -> dict:
    return {
        "evidence_snapshot_id": "evidence_123",
        "policy_snapshot_id": "policy_123",
    }


def _determinism() -> dict:
    return {
        "envelope_id": "detenv_123",
        "inputs": {
            "policy_snapshot_id": "policy_123",
            "evidence_snapshot_id": "evidence_123",
            "toolchain_manifest_id": "toolchain_123",
        },
    }


def _step_result(
    *,
    step_index: int = 0,
    step_id: str = "step_001",
    action_type: str = "capability_call",
    status: str = "SUCCEEDED",
    input_payload: dict | None = None,
    output_payload: dict | None = None,
    error: dict | None = None,
) -> dict:
    return {
        "step_index": step_index,
        "step_id": step_id,
        "action_type": action_type,
        "status": status,
        "input_payload": input_payload if input_payload is not None else {"arg": "value"},
        "output_payload": output_payload if output_payload is not None else {"result": "ok"},
        "error": error,
    }


def _summary(
    *,
    steps_total: int = 1,
    steps_succeeded: int = 1,
    steps_failed: int = 0,
    steps_skipped: int = 0,
) -> dict:
    return {
        "steps_total": steps_total,
        "steps_succeeded": steps_succeeded,
        "steps_failed": steps_failed,
        "steps_skipped": steps_skipped,
    }


def _build_record(
    *,
    execution_status: str = "SUCCEEDED",
    step_results: list[dict] | None = None,
    summary: dict | None = None,
    rationale: str | None = None,
    emitted_by: str | None = None,
) -> ExecutionResultRecord:
    actual_step_results = step_results if step_results is not None else [_step_result()]
    actual_summary = summary if summary is not None else _summary()

    return build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan_123",
        decision_record_id="decision_123",
        subject_id="subject_123",
        execution_status=execution_status,
        step_results=actual_step_results,
        summary=actual_summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )


def test_build_execution_result_record_happy_path():
    record = _build_record(
        rationale="Executed approved plan.",
        emitted_by="executor_v1",
    )

    assert record.schema_version == SCHEMA_VERSION
    assert record.artifact_type == ARTIFACT_TYPE
    assert record.execution_result_record_id.startswith("execution_result_")

    assert record.plan_record_id == "plan_123"
    assert record.decision_record_id == "decision_123"
    assert record.subject_id == "subject_123"
    assert record.execution_status == "SUCCEEDED"

    assert len(record.step_results) == 1
    assert record.step_results[0]["step_index"] == 0
    assert record.step_results[0]["status"] == "SUCCEEDED"
    assert record.summary["steps_total"] == 1
    assert record.rationale == "Executed approved plan."
    assert record.emitted_by == "executor_v1"


def test_execution_result_record_round_trip_dict():
    record = _build_record(
        rationale="Round trip test.",
        emitted_by="executor_v1",
    )

    as_dict = record.to_dict()
    rebuilt = ExecutionResultRecord.from_dict(as_dict)

    assert rebuilt == record
    assert rebuilt.to_dict() == as_dict


def test_make_execution_result_id_is_deterministic_for_same_payload():
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "authority": _authority(),
        "evidence": _evidence(),
        "determinism": _determinism(),
        "plan_record_id": "plan_123",
        "decision_record_id": "decision_123",
        "subject_id": "subject_123",
        "execution_status": "SUCCEEDED",
        "step_results": [_step_result()],
        "summary": _summary(),
        "rationale": "Same payload",
        "emitted_by": "executor_v1",
    }

    result_1 = make_execution_result_id(payload)
    result_2 = make_execution_result_id(payload)

    assert result_1 == result_2
    assert result_1.startswith("execution_result_")


def test_build_execution_result_record_is_deterministic_for_same_inputs():
    record_1 = _build_record(
        rationale="Deterministic",
        emitted_by="executor_v1",
    )
    record_2 = _build_record(
        rationale="Deterministic",
        emitted_by="executor_v1",
    )

    assert record_1.execution_result_record_id == record_2.execution_result_record_id
    assert record_1.to_dict() == record_2.to_dict()


def test_build_execution_result_record_changes_id_when_payload_changes():
    record_1 = _build_record(
        rationale="Variant A",
        emitted_by="executor_v1",
    )
    record_2 = _build_record(
        rationale="Variant B",
        emitted_by="executor_v1",
    )

    assert record_1.execution_result_record_id != record_2.execution_result_record_id


@pytest.mark.parametrize(
    "execution_status",
    ["SUCCEEDED", "PARTIAL", "FAILED", "SKIPPED"],
)
def test_allowed_plan_level_execution_statuses(execution_status: str):
    record = _build_record(execution_status=execution_status)
    assert record.execution_status == execution_status


def test_invalid_plan_level_execution_status_raises():
    with pytest.raises(ValueError, match="Invalid execution_status"):
        _build_record(execution_status="BLOCKED")


def test_missing_plan_record_id_raises():
    with pytest.raises(ValueError, match="plan_record_id required"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_missing_decision_record_id_raises():
    with pytest.raises(ValueError, match="decision_record_id required"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_missing_subject_id_raises():
    with pytest.raises(ValueError, match="subject_id required"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_step_results_must_be_list():
    with pytest.raises(ValueError, match="step_results must be a list"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results={"not": "a list"},  # type: ignore[arg-type]
            summary=_summary(),
        )


def test_step_result_missing_required_field_raises():
    bad_step = _step_result()
    del bad_step["action_type"]

    with pytest.raises(ValueError, match="missing fields"):
        _build_record(step_results=[bad_step])


def test_step_index_must_match_list_position():
    bad_step = _step_result(step_index=1)

    with pytest.raises(ValueError, match="step_index must match list position"):
        _build_record(step_results=[bad_step])


@pytest.mark.parametrize("status", ["SUCCEEDED", "FAILED", "SKIPPED"])
def test_allowed_step_statuses(status: str):
    record = _build_record(
        step_results=[
            _step_result(
                status=status,
                output_payload={"result": "ok"} if status != "FAILED" else None,
                error=None if status != "FAILED" else {"error_type": "RuntimeError", "message": "boom"},
            )
        ],
        execution_status="SUCCEEDED" if status == "SUCCEEDED" else "FAILED",
        summary=_summary(
            steps_total=1,
            steps_succeeded=1 if status == "SUCCEEDED" else 0,
            steps_failed=1 if status == "FAILED" else 0,
            steps_skipped=1 if status == "SKIPPED" else 0,
        ),
    )
    assert record.step_results[0]["status"] == status


def test_invalid_step_status_raises():
    bad_step = _step_result(status="PARTIAL")

    with pytest.raises(ValueError, match="Invalid step status"):
        _build_record(step_results=[bad_step])


def test_input_payload_must_be_mapping():
    bad_step = _step_result(input_payload=["not", "mapping"])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="input_payload must be a mapping"):
        _build_record(step_results=[bad_step])


def test_output_payload_may_be_none():
    record = _build_record(
        step_results=[
            _step_result(
                status="FAILED",
                output_payload=None,
                error={"error_type": "RuntimeError", "message": "step failed"},
            )
        ],
        execution_status="FAILED",
        summary=_summary(steps_total=1, steps_succeeded=0, steps_failed=1, steps_skipped=0),
    )

    assert record.step_results[0]["output_payload"] is None


def test_output_payload_must_be_mapping_when_present():
    bad_step = _step_result(output_payload=["not", "mapping"])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="output_payload must be a mapping"):
        _build_record(step_results=[bad_step])


def test_error_may_be_none():
    record = _build_record(step_results=[_step_result(error=None)])
    assert record.step_results[0]["error"] is None


def test_error_must_be_mapping_when_present():
    bad_step = _step_result(error="boom")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="error must be a mapping"):
        _build_record(step_results=[bad_step])


def test_error_requires_error_type():
    bad_step = _step_result(
        status="FAILED",
        output_payload=None,
        error={"message": "boom"},
    )

    with pytest.raises(ValueError, match="error missing error_type"):
        _build_record(
            step_results=[bad_step],
            execution_status="FAILED",
            summary=_summary(steps_total=1, steps_succeeded=0, steps_failed=1, steps_skipped=0),
        )


def test_error_requires_message():
    bad_step = _step_result(
        status="FAILED",
        output_payload=None,
        error={"error_type": "RuntimeError"},
    )

    with pytest.raises(ValueError, match="error missing message"):
        _build_record(
            step_results=[bad_step],
            execution_status="FAILED",
            summary=_summary(steps_total=1, steps_succeeded=0, steps_failed=1, steps_skipped=0),
        )


def test_failed_step_supports_structured_error_with_optional_details():
    record = _build_record(
        step_results=[
            _step_result(
                status="FAILED",
                output_payload=None,
                error={
                    "error_type": "CapabilityExecutionError",
                    "message": "capability failed",
                    "details": {"code": "E_FAIL"},
                },
            )
        ],
        execution_status="FAILED",
        summary=_summary(steps_total=1, steps_succeeded=0, steps_failed=1, steps_skipped=0),
    )

    error = record.step_results[0]["error"]
    assert error["error_type"] == "CapabilityExecutionError"
    assert error["message"] == "capability failed"
    assert error["details"] == {"code": "E_FAIL"}


def test_partial_execution_result_supports_executed_steps_only():
    record = _build_record(
        execution_status="PARTIAL",
        step_results=[
            _step_result(
                step_index=0,
                step_id="step_001",
                status="SUCCEEDED",
                input_payload={"value": 1},
                output_payload={"value": 2},
                error=None,
            ),
            _step_result(
                step_index=1,
                step_id="step_002",
                status="FAILED",
                input_payload={"value": 2},
                output_payload=None,
                error={"error_type": "RuntimeError", "message": "failure on step 2"},
            ),
        ],
        summary=_summary(steps_total=2, steps_succeeded=1, steps_failed=1, steps_skipped=0),
    )

    assert record.execution_status == "PARTIAL"
    assert len(record.step_results) == 2
    assert record.step_results[0]["status"] == "SUCCEEDED"
    assert record.step_results[1]["status"] == "FAILED"


def test_skipped_execution_result_is_allowed():
    record = _build_record(
        execution_status="SKIPPED",
        step_results=[],
        summary=_summary(steps_total=0, steps_succeeded=0, steps_failed=0, steps_skipped=0),
    )

    assert record.execution_status == "SKIPPED"
    assert record.step_results == []


def test_authority_must_be_mapping():
    with pytest.raises(ValueError, match="authority must be a mapping"):
        build_execution_result_record(
            authority="bad",  # type: ignore[arg-type]
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_evidence_must_be_mapping():
    with pytest.raises(ValueError, match="evidence must be a mapping"):
        build_execution_result_record(
            authority=_authority(),
            evidence="bad",  # type: ignore[arg-type]
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_determinism_must_be_mapping():
    with pytest.raises(ValueError, match="determinism must be a mapping"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism="bad",  # type: ignore[arg-type]
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary=_summary(),
        )


def test_summary_must_be_mapping():
    with pytest.raises(ValueError, match="summary must be a mapping"):
        build_execution_result_record(
            authority=_authority(),
            evidence=_evidence(),
            determinism=_determinism(),
            plan_record_id="plan_123",
            decision_record_id="decision_123",
            subject_id="subject_123",
            execution_status="SUCCEEDED",
            step_results=[_step_result()],
            summary="bad",  # type: ignore[arg-type]
        )


def test_executor_style_multi_step_construction_path():
    step_results = [
        _step_result(
            step_index=0,
            step_id="step_prepare",
            action_type="capability_call",
            status="SUCCEEDED",
            input_payload={"path": "/tmp/input.txt"},
            output_payload={"prepared": True},
            error=None,
        ),
        _step_result(
            step_index=1,
            step_id="step_run",
            action_type="capability_call",
            status="SUCCEEDED",
            input_payload={"command": "process"},
            output_payload={"exit_code": 0, "result": "done"},
            error=None,
        ),
    ]

    summary = _summary(steps_total=2, steps_succeeded=2, steps_failed=0, steps_skipped=0)

    record = build_execution_result_record(
        authority=_authority(),
        evidence=_evidence(),
        determinism=_determinism(),
        plan_record_id="plan_abc",
        decision_record_id="decision_abc",
        subject_id="subject_abc",
        execution_status="SUCCEEDED",
        step_results=step_results,
        summary=summary,
        rationale="Executor integration path test.",
        emitted_by="executor_v1",
    )

    assert record.plan_record_id == "plan_abc"
    assert record.decision_record_id == "decision_abc"
    assert record.subject_id == "subject_abc"
    assert record.execution_status == "SUCCEEDED"
    assert len(record.step_results) == 2
    assert record.step_results[1]["output_payload"]["exit_code"] == 0