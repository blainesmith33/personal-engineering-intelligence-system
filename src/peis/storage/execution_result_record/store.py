from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from peis.execution.result_record import ExecutionResultRecord


def store_execution_result_record(
    *,
    root: Union[str, Path],
    record: ExecutionResultRecord,
) -> Path:
    """
    Persist an ExecutionResultRecord deterministically.

    Path:
        <root>/execution_result_record/<execution_result_record_id>.json
    """
    if not isinstance(record, ExecutionResultRecord):
        raise ValueError("record must be an ExecutionResultRecord")

    root_path = Path(root)
    dir_path = root_path / "execution_result_record"
    dir_path.mkdir(parents=True, exist_ok=True)

    file_path = dir_path / f"{record.execution_result_record_id}.json"

    payload = record.to_dict()

    # Deterministic write
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, sort_keys=True, separators=(",", ":"))

    return file_path


def load_execution_result_record(
    *,
    root: Union[str, Path],
    execution_result_record_id: str,
) -> ExecutionResultRecord:
    """
    Load an ExecutionResultRecord from storage.
    """
    if not isinstance(execution_result_record_id, str) or not execution_result_record_id.strip():
        raise ValueError("execution_result_record_id must be a non-empty string")

    root_path = Path(root)
    file_path = root_path / "execution_result_record" / f"{execution_result_record_id}.json"

    if not file_path.exists():
        raise FileNotFoundError(f"ExecutionResultRecord not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    return ExecutionResultRecord.from_dict(payload)