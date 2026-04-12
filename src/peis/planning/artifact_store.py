from __future__ import annotations

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List


class ArtifactStoreError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _hash(data: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(data).encode()).hexdigest()


class ArtifactStore:
    """
    Deterministic artifact store for planning subsystem.
    """

    def __init__(self, base_path: str):
        self.base = Path(base_path)

        self.validated_path = self.base / "validated_plans"
        self.failure_path = self.base / "failure_cases"
        self.correction_path = self.base / "correction_cases"

        for p in [
            self.validated_path,
            self.failure_path,
            self.correction_path,
        ]:
            p.mkdir(parents=True, exist_ok=True)

    # -------------------------
    # WRITE METHODS
    # -------------------------

    def write_validated_plan(self, payload: Dict[str, Any]) -> str:
        self._require_fields(payload, ["plan", "validation_result", "determinism_envelope"])

        content_hash = _hash(payload)
        artifact_id = f"vplan_{content_hash}"

        payload["validated_plan_id"] = artifact_id
        payload["created_at_utc"] = _utc_now()

        self._write(self.validated_path, artifact_id, payload)
        return artifact_id

    def write_failure_case(self, payload: Dict[str, Any]) -> str:
        self._require_fields(payload, ["raw_output", "validation_errors", "determinism_envelope"])

        content_hash = _hash(payload)
        artifact_id = f"pfail_{content_hash}"

        payload["failure_case_id"] = artifact_id
        payload["created_at_utc"] = _utc_now()

        self._write(self.failure_path, artifact_id, payload)
        return artifact_id

    def write_correction_case(self, payload: Dict[str, Any]) -> str:
        self._require_fields(payload, ["original_output", "corrected_output", "determinism_envelope"])

        content_hash = _hash(payload)
        artifact_id = f"pcorr_{content_hash}"

        payload["correction_case_id"] = artifact_id
        payload["created_at_utc"] = _utc_now()

        self._write(self.correction_path, artifact_id, payload)
        return artifact_id

    # -------------------------
    # READ METHODS
    # -------------------------

    def get_validated_plans(self) -> List[Dict[str, Any]]:
        return self._read_all(self.validated_path)

    def get_failure_cases(self) -> List[Dict[str, Any]]:
        return self._read_all(self.failure_path)

    def get_correction_cases(self) -> List[Dict[str, Any]]:
        return self._read_all(self.correction_path)

    # -------------------------
    # INTERNALS
    # -------------------------

    def _write(self, path: Path, artifact_id: str, payload: Dict[str, Any]) -> None:
        file_path = path / f"{artifact_id}.json"

        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

    def _read_all(self, path: Path) -> List[Dict[str, Any]]:
        results = []

        for file in path.glob("*.json"):
            with open(file) as f:
                results.append(json.load(f))

        return results

    def _require_fields(self, payload: Dict[str, Any], fields: List[str]) -> None:
        for f in fields:
            if f not in payload:
                raise ArtifactStoreError(f"missing required field: {f}")