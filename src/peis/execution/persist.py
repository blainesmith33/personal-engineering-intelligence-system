from __future__ import annotations

from pathlib import Path
from typing import Union

from peis.execution.result_record import ExecutionResultRecord
from peis.storage.execution_result_record.store import (
    store_execution_result_record,
)


def persist_execution_result(
    *,
    root: Union[str, Path],
    record: ExecutionResultRecord,
):
    """
    Persist an ExecutionResultRecord using the canonical storage layer.

    This function is the execution-layer entry point for persistence.
    It must remain a thin wrapper to preserve determinism and separation of concerns.
    """
    if not isinstance(record, ExecutionResultRecord):
        raise ValueError("record must be an ExecutionResultRecord")

    return store_execution_result_record(
        root=root,
        record=record,
    )