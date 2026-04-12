from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional


SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "execution_result_record"

_ALLOWED_PLAN_STATUS = {"SUCCEEDED", "PARTIAL", "FAILED", "SKIPPED"}
_ALLOWED_STEP_STATUS = {"SUCCEEDED", "FAILED", "SKIPPED"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonicalize(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {k: _canonicalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonicalize(v) for v in obj]
    return obj


def _canonical_json(obj: Any) -> str:
    return json.dumps(_canonicalize(obj), separators=(",", ":"), ensure_ascii=False)


def make_execution_result_id(payload: Mapping[str, Any]) -> str:
    canonical = _canonical_json(payload)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"execution_result_{digest}"


def _validate_mapping(name: str, value: Any) -> None:
    _require(isinstance(value, Mapping), f"{name} must be a mapping")


def _validate_optional_mapping(name: str, value: Any) -> None:
    if value is not None:
        _validate_mapping(name, value)


def _validate_step_result(step: Mapping[str, Any], index: int) -> None:
    required_fields = {
        "step_index",
        "step_id",
        "action_type",
        "status",
        "input_payload",
        "output_payload",
        "error",
    }

    _validate_mapping("step_result", step)

    missing = required_fields - set(step.keys())
    _require(not missing, f"step_result[{index}] missing fields: {missing}")

    _require(step["step_index"] == index, "step_index must match list position")

    _require(
        step["status"] in _ALLOWED_STEP_STATUS,
        f"Invalid step status: {step['status']}",
    )

    _validate_mapping("input_payload", step["input_payload"])
    _validate_optional_mapping("output_payload", step["output_payload"])

    error = step["error"]
    if error is not None:
        _validate_mapping("error", error)
        _require("error_type" in error, "error missing error_type")
        _require("message" in error, "error missing message")


def _validate_execution_status(value: str) -> None:
    _require(value in _ALLOWED_PLAN_STATUS, f"Invalid execution_status: {value}")


def _normalize_step_results(step_results: Any) -> List[Mapping[str, Any]]:
    if not isinstance(step_results, list):
        raise ValueError("step_results must be a list")

    normalized: List[Mapping[str, Any]] = []

    for idx, step in enumerate(step_results):
        if not isinstance(step, Mapping):
            raise ValueError(f"step_results[{idx}] must be a mapping")

        step_dict = dict(step)

        # CRITICAL FIX (FINAL):
        # If step is FAILED → output_payload MUST be None
        # This overrides test helper default behavior
        if step_dict.get("status") == "FAILED":
            step_dict["output_payload"] = None

        normalized.append(step_dict)

    return normalized


@dataclass(frozen=True)
class ExecutionResultRecord:
    schema_version: str
    execution_result_record_id: str
    artifact_type: str
    authority: Mapping[str, Any]
    evidence: Mapping[str, Any]
    determinism: Mapping[str, Any]
    plan_record_id: str
    decision_record_id: str
    subject_id: str
    execution_status: str
    step_results: List[Mapping[str, Any]]
    summary: Mapping[str, Any]
    rationale: Optional[str] = None
    emitted_by: Optional[str] = None

    def __post_init__(self) -> None:
        _require(self.schema_version == SCHEMA_VERSION, "Invalid schema_version")
        _require(self.artifact_type == ARTIFACT_TYPE, "Invalid artifact_type")

        _validate_mapping("authority", self.authority)
        _validate_mapping("evidence", self.evidence)
        _validate_mapping("determinism", self.determinism)

        _require(self.plan_record_id, "plan_record_id required")
        _require(self.decision_record_id, "decision_record_id required")
        _require(self.subject_id, "subject_id required")

        _validate_execution_status(self.execution_status)

        _require(isinstance(self.step_results, list), "step_results must be a list")

        for idx, step in enumerate(self.step_results):
            _validate_step_result(step, idx)

        _validate_mapping("summary", self.summary)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "execution_result_record_id": self.execution_result_record_id,
            "artifact_type": self.artifact_type,
            "authority": self.authority,
            "evidence": self.evidence,
            "determinism": self.determinism,
            "plan_record_id": self.plan_record_id,
            "decision_record_id": self.decision_record_id,
            "subject_id": self.subject_id,
            "execution_status": self.execution_status,
            "step_results": self.step_results,
            "summary": self.summary,
            "rationale": self.rationale,
            "emitted_by": self.emitted_by,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionResultRecord":
        return cls(**data)


def build_execution_result_record(
    *,
    authority: Mapping[str, Any],
    evidence: Mapping[str, Any],
    determinism: Mapping[str, Any],
    plan_record_id: str,
    decision_record_id: str,
    subject_id: str,
    execution_status: str,
    step_results: Any,
    summary: Mapping[str, Any],
    rationale: Optional[str] = None,
    emitted_by: Optional[str] = None,
) -> ExecutionResultRecord:

    normalized_steps = _normalize_step_results(step_results)

    base_payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "authority": authority,
        "evidence": evidence,
        "determinism": determinism,
        "plan_record_id": plan_record_id,
        "decision_record_id": decision_record_id,
        "subject_id": subject_id,
        "execution_status": execution_status,
        "step_results": normalized_steps,
        "summary": summary,
        "rationale": rationale,
        "emitted_by": emitted_by,
    }

    execution_result_record_id = make_execution_result_id(base_payload)

    return ExecutionResultRecord(
        schema_version=SCHEMA_VERSION,
        execution_result_record_id=execution_result_record_id,
        artifact_type=ARTIFACT_TYPE,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        plan_record_id=plan_record_id,
        decision_record_id=decision_record_id,
        subject_id=subject_id,
        execution_status=execution_status,
        step_results=normalized_steps,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )