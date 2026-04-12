from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class DeterminismError(ValueError):
    """Raised when determinism invariants are violated."""


# ---------------------------
# Determinism Envelope
# ---------------------------


@dataclass(frozen=True, slots=True)
class DeterminismEnvelope:
    """
    Full determinism envelope for PEIS.

    System outputs are guaranteed deterministic ONLY when all of the following
    inputs are identical.

    Any change to any field constitutes a new evaluation and MUST produce
    a new artifact identity.
    """

    file_hash: str
    extractor_binary_hash: str
    extractor_config_hash: str
    schema_version: str

    evidence_snapshot_id: str
    policy_snapshot_id: str

    model_hash: str | None = None
    advisory_retrieval_set_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.file_hash, "file_hash")
        _require_non_empty_str(self.extractor_binary_hash, "extractor_binary_hash")
        _require_non_empty_str(self.extractor_config_hash, "extractor_config_hash")
        _require_non_empty_str(self.schema_version, "schema_version")

        _require_non_empty_str(self.evidence_snapshot_id, "evidence_snapshot_id")
        _require_non_empty_str(self.policy_snapshot_id, "policy_snapshot_id")

        if self.model_hash is not None:
            _require_non_empty_str(self.model_hash, "model_hash")

        if self.advisory_retrieval_set_id is not None:
            _require_non_empty_str(
                self.advisory_retrieval_set_id,
                "advisory_retrieval_set_id",
            )

    # ---------------------------
    # Serialization
    # ---------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_hash": self.file_hash,
            "extractor_binary_hash": self.extractor_binary_hash,
            "extractor_config_hash": self.extractor_config_hash,
            "schema_version": self.schema_version,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "policy_snapshot_id": self.policy_snapshot_id,
            "model_hash": self.model_hash,
            "advisory_retrieval_set_id": self.advisory_retrieval_set_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DeterminismEnvelope":
        if not isinstance(data, Mapping):
            raise DeterminismError("payload must be a mapping")

        return cls(
            file_hash=_coerce_required_str(data.get("file_hash"), "file_hash"),
            extractor_binary_hash=_coerce_required_str(
                data.get("extractor_binary_hash"),
                "extractor_binary_hash",
            ),
            extractor_config_hash=_coerce_required_str(
                data.get("extractor_config_hash"),
                "extractor_config_hash",
            ),
            schema_version=_coerce_required_str(
                data.get("schema_version"),
                "schema_version",
            ),
            evidence_snapshot_id=_coerce_required_str(
                data.get("evidence_snapshot_id"),
                "evidence_snapshot_id",
            ),
            policy_snapshot_id=_coerce_required_str(
                data.get("policy_snapshot_id"),
                "policy_snapshot_id",
            ),
            model_hash=_coerce_optional_str(data.get("model_hash"), "model_hash"),
            advisory_retrieval_set_id=_coerce_optional_str(
                data.get("advisory_retrieval_set_id"),
                "advisory_retrieval_set_id",
            ),
        )

    # ---------------------------
    # Comparison
    # ---------------------------

    def equals(self, other: "DeterminismEnvelope") -> bool:
        _require_envelope(other, "other")
        return self.to_dict() == other.to_dict()

    def diff(self, other: "DeterminismEnvelope") -> dict[str, tuple[Any, Any]]:
        """
        Return field-level differences between two envelopes.
        """
        _require_envelope(other, "other")

        diff: dict[str, tuple[Any, Any]] = {}

        for key, value in self.to_dict().items():
            other_value = getattr(other, key)
            if value != other_value:
                diff[key] = (value, other_value)

        return diff


# ---------------------------
# Enforcement
# ---------------------------


def assert_same_envelope(
    left: DeterminismEnvelope,
    right: DeterminismEnvelope,
) -> None:
    """
    Hard-fail unless two envelopes are identical.
    """
    _require_envelope(left, "left")
    _require_envelope(right, "right")

    if not left.equals(right):
        raise DeterminismError(
            f"determinism envelope mismatch: {left.diff(right)}"
        )


def assert_envelope_present(envelope: DeterminismEnvelope | None) -> None:
    if envelope is None:
        raise DeterminismError("determinism envelope is required")
    _require_envelope(envelope, "envelope")


def assert_no_mixed_envelopes(envelopes: list[DeterminismEnvelope]) -> None:
    """
    Hard-fail if multiple different envelopes are used together.
    """
    if not envelopes:
        raise DeterminismError("envelopes list must not be empty")

    first = envelopes[0]
    _require_envelope(first, "envelopes[0]")

    for i, env in enumerate(envelopes[1:], start=1):
        _require_envelope(env, f"envelopes[{i}]")
        if not first.equals(env):
            raise DeterminismError(
                "mixed determinism envelopes detected in a single operation"
            )


def requires_new_artifact(
    previous: DeterminismEnvelope,
    current: DeterminismEnvelope,
) -> bool:
    """
    Returns True if ANY field differs.

    This is the canonical rule:
    ANY change → new evaluation → new artifact ID.
    """
    _require_envelope(previous, "previous")
    _require_envelope(current, "current")

    return not previous.equals(current)


# ---------------------------
# Builders
# ---------------------------


def build_minimal_envelope(
    *,
    file_hash: str,
    extractor_binary_hash: str,
    extractor_config_hash: str,
    schema_version: str,
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
) -> DeterminismEnvelope:
    """
    Minimal valid envelope (no advisory/model context).
    """
    return DeterminismEnvelope(
        file_hash=file_hash,
        extractor_binary_hash=extractor_binary_hash,
        extractor_config_hash=extractor_config_hash,
        schema_version=schema_version,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
    )


def build_full_envelope(
    *,
    file_hash: str,
    extractor_binary_hash: str,
    extractor_config_hash: str,
    schema_version: str,
    evidence_snapshot_id: str,
    policy_snapshot_id: str,
    model_hash: str | None = None,
    advisory_retrieval_set_id: str | None = None,
) -> DeterminismEnvelope:
    """
    Full envelope including model + advisory context.
    """
    return DeterminismEnvelope(
        file_hash=file_hash,
        extractor_binary_hash=extractor_binary_hash,
        extractor_config_hash=extractor_config_hash,
        schema_version=schema_version,
        evidence_snapshot_id=evidence_snapshot_id,
        policy_snapshot_id=policy_snapshot_id,
        model_hash=model_hash,
        advisory_retrieval_set_id=advisory_retrieval_set_id,
    )


# ---------------------------
# Internal Helpers
# ---------------------------


def _require_envelope(value: Any, name: str) -> DeterminismEnvelope:
    if not isinstance(value, DeterminismEnvelope):
        raise DeterminismError(f"{name} must be a DeterminismEnvelope")
    return value


def _coerce_required_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeterminismError(f"{field_name} must be a non-empty string")
    return value.strip()


def _coerce_optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise DeterminismError(
            f"{field_name} must be None or a non-empty string"
        )
    return value.strip()


def _require_non_empty_str(value: str | None, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DeterminismError(f"{field_name} must be a non-empty string")