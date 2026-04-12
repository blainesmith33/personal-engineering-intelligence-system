from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from peis.core.validation import require_mapping, require_non_empty_str
from peis.decision_record import DecisionRecord
from peis.evaluation_record import EvaluationRecord
from peis.plan_record import PlanRecord


class StorageLoadError(ValueError):
    """Raised when stored artifacts cannot be loaded safely."""


def load_artifact(
    *,
    root_dir: str | Path,
    artifact_type: str,
    artifact_id: str,
) -> dict[str, Any]:
    """
    Load a single stored artifact JSON payload.

    Expected layout:
    <root_dir>/<artifact_type>/<artifact_id>.json
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

    target_path = root / artifact_type / f"{artifact_id}.json"

    if not target_path.exists():
        raise StorageLoadError(f"artifact not found: {target_path}")

    if not target_path.is_file():
        raise StorageLoadError(f"artifact path is not a file: {target_path}")

    try:
        with target_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise StorageLoadError(
            f"artifact JSON is invalid: {target_path}"
        ) from exc

    require_mapping(payload, field_name="payload")
    return dict(payload)


def load_decision_record(
    *,
    root_dir: str | Path,
    decision_record_id: str,
) -> DecisionRecord:
    payload = load_artifact(
        root_dir=root_dir,
        artifact_type="decision_record",
        artifact_id=decision_record_id,
    )

    try:
        return DecisionRecord.from_dict(payload)
    except Exception as exc:
        raise StorageLoadError(
            f"failed to load DecisionRecord: {decision_record_id}"
        ) from exc


def load_evaluation_record(
    *,
    root_dir: str | Path,
    evaluation_record_id: str,
) -> EvaluationRecord:
    payload = load_artifact(
        root_dir=root_dir,
        artifact_type="evaluation_record",
        artifact_id=evaluation_record_id,
    )

    try:
        return EvaluationRecord.from_dict(payload)
    except Exception as exc:
        raise StorageLoadError(
            f"failed to load EvaluationRecord: {evaluation_record_id}"
        ) from exc


def load_plan_record(
    *,
    root_dir: str | Path,
    plan_record_id: str,
) -> PlanRecord:
    payload = load_artifact(
        root_dir=root_dir,
        artifact_type="plan_record",
        artifact_id=plan_record_id,
    )

    try:
        return PlanRecord.from_dict(payload)
    except Exception as exc:
        raise StorageLoadError(
            f"failed to load PlanRecord: {plan_record_id}"
        ) from exc


def _coerce_root_dir(root_dir: str | Path) -> Path:
    if isinstance(root_dir, Path):
        return root_dir
    if isinstance(root_dir, str) and root_dir.strip():
        return Path(root_dir.strip())
    raise StorageLoadError("root_dir must be a non-empty string or Path")