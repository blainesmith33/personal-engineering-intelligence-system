from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from peis.core.validation import require_mapping, require_non_empty_str


class StorageError(ValueError):
    """Raised when storage invariants are violated."""


@dataclass(frozen=True, slots=True)
class StoredArtifactRef:
    """
    Immutable reference to a persisted artifact.

    This is the canonical return surface for storage writes.
    """

    artifact_id: str
    artifact_type: str
    path: str

    def __post_init__(self) -> None:
        require_non_empty_str(self.artifact_id, field_name="artifact_id")
        require_non_empty_str(self.artifact_type, field_name="artifact_type")
        require_non_empty_str(self.path, field_name="path")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "path": self.path,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StoredArtifactRef":
        require_mapping(data, field_name="data")
        return cls(
            artifact_id=require_non_empty_str(
                data.get("artifact_id"),
                field_name="artifact_id",
            ),
            artifact_type=require_non_empty_str(
                data.get("artifact_type"),
                field_name="artifact_type",
            ),
            path=require_non_empty_str(
                data.get("path"),
                field_name="path",
            ),
        )


def store_artifact(
    *,
    root_dir: str | Path,
    artifact_type: str,
    artifact_id: str,
    payload: Mapping[str, Any],
    overwrite: bool = False,
) -> StoredArtifactRef:
    """
    Persist a single artifact as JSON.

    Layout:
    <root_dir>/<artifact_type>/<artifact_id>.json

    Invariants:
    - artifact_type must be non-empty
    - artifact_id must be non-empty
    - payload must be a mapping
    - existing artifacts are immutable unless overwrite=True
    """
    root = _coerce_root_dir(root_dir)
    artifact_type = require_non_empty_str(
        artifact_type,
        field_name="artifact_type",
    )
    artifact_id = require_non_empty_str(
        artifact_id,
        field_name="artifact_id",
    )
    require_mapping(payload, field_name="payload")

    target_dir = root / artifact_type
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / f"{artifact_id}.json"

    if target_path.exists() and not overwrite:
        raise StorageError(
            f"artifact already exists and overwrite=False: {target_path}"
        )

    _write_json(target_path, payload)

    return StoredArtifactRef(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        path=str(target_path),
    )


def store_decision_record(
    *,
    root_dir: str | Path,
    record: Any,
    overwrite: bool = False,
) -> StoredArtifactRef:
    """
    Persist a DecisionRecord-like object exposing decision_record_id + to_dict().
    """
    artifact_id = _get_required_attr(
        record,
        attr_name="decision_record_id",
        field_name="decision_record_id",
    )
    payload = _get_payload(record)

    return store_artifact(
        root_dir=root_dir,
        artifact_type="decision_record",
        artifact_id=artifact_id,
        payload=payload,
        overwrite=overwrite,
    )


def store_evaluation_record(
    *,
    root_dir: str | Path,
    record: Any,
    overwrite: bool = False,
) -> StoredArtifactRef:
    """
    Persist an EvaluationRecord-like object exposing evaluation_record_id + to_dict().
    """
    artifact_id = _get_required_attr(
        record,
        attr_name="evaluation_record_id",
        field_name="evaluation_record_id",
    )
    payload = _get_payload(record)

    return store_artifact(
        root_dir=root_dir,
        artifact_type="evaluation_record",
        artifact_id=artifact_id,
        payload=payload,
        overwrite=overwrite,
    )


def store_plan_record(
    *,
    root_dir: str | Path,
    record: Any,
    overwrite: bool = False,
) -> StoredArtifactRef:
    """
    Persist a PlanRecord-like object exposing plan_record_id + to_dict().
    """
    artifact_id = _get_required_attr(
        record,
        attr_name="plan_record_id",
        field_name="plan_record_id",
    )
    payload = _get_payload(record)

    return store_artifact(
        root_dir=root_dir,
        artifact_type="plan_record",
        artifact_id=artifact_id,
        payload=payload,
        overwrite=overwrite,
    )


def store_pipeline_result(
    *,
    root_dir: str | Path,
    result: Any,
    overwrite: bool = False,
) -> dict[str, StoredArtifactRef]:
    """
    Persist a pipeline/orchestration result containing decision/evaluation/plan records.

    Expected attributes:
    - decision_record
    - evaluation_record
    - plan_record
    """
    decision_record = getattr(result, "decision_record", None)
    evaluation_record = getattr(result, "evaluation_record", None)
    plan_record = getattr(result, "plan_record", None)

    if decision_record is None:
        raise StorageError("result.decision_record is required")
    if evaluation_record is None:
        raise StorageError("result.evaluation_record is required")
    if plan_record is None:
        raise StorageError("result.plan_record is required")

    return {
        "decision_record": store_decision_record(
            root_dir=root_dir,
            record=decision_record,
            overwrite=overwrite,
        ),
        "evaluation_record": store_evaluation_record(
            root_dir=root_dir,
            record=evaluation_record,
            overwrite=overwrite,
        ),
        "plan_record": store_plan_record(
            root_dir=root_dir,
            record=plan_record,
            overwrite=overwrite,
        ),
    }


def _coerce_root_dir(root_dir: str | Path) -> Path:
    if isinstance(root_dir, Path):
        root = root_dir
    elif isinstance(root_dir, str) and root_dir.strip():
        root = Path(root_dir.strip())
    else:
        raise StorageError("root_dir must be a non-empty string or Path")

    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_required_attr(obj: Any, *, attr_name: str, field_name: str) -> str:
    value = getattr(obj, attr_name, None)
    return require_non_empty_str(value, field_name=field_name)


def _get_payload(obj: Any) -> dict[str, Any]:
    to_dict = getattr(obj, "to_dict", None)
    if not callable(to_dict):
        raise StorageError("record must expose a callable to_dict()")

    payload = to_dict()
    require_mapping(payload, field_name="payload")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        handle.write("\n")