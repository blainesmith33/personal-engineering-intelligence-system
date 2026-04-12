from __future__ import annotations

import hashlib
from typing import Mapping, Any


class IdError(ValueError):
    """Raised when ID generation invariants are violated."""


# -------------------------------------------------------
# Core ID Generation
# -------------------------------------------------------


def _stable_serialize(data: Mapping[str, Any]) -> bytes:
    """
    Deterministic serialization (order-stable).
    """
    if not isinstance(data, Mapping):
        raise IdError("data must be a mapping")

    items = sorted(data.items(), key=lambda x: x[0])

    parts: list[str] = []

    for key, value in items:
        if isinstance(value, Mapping):
            value_str = _stable_serialize(value).decode()
        else:
            value_str = repr(value)

        parts.append(f"{key}={value_str}")

    return "|".join(parts).encode("utf-8")


def _blake3_like_hash(data: bytes) -> str:
    """
    Using SHA256 as a stand-in for deterministic hashing.
    """
    return hashlib.sha256(data).hexdigest()


def make_artifact_id(
    *,
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    """
    Deterministic artifact ID.

    prefix examples:
    - decision
    - evaluation
    - plan

    ID format:
    <prefix>_<hash>
    """
    if not isinstance(prefix, str) or not prefix:
        raise IdError("prefix must be a non-empty string")

    serialized = _stable_serialize(payload)
    digest = _blake3_like_hash(serialized)

    return f"{prefix}_{digest[:16]}"


# -------------------------------------------------------
# Specific ID Builders
# -------------------------------------------------------


def make_decision_id(payload: Mapping[str, Any]) -> str:
    return make_artifact_id(prefix="decision", payload=payload)


def make_evaluation_id(payload: Mapping[str, Any]) -> str:
    return make_artifact_id(prefix="evaluation", payload=payload)


def make_plan_id(payload: Mapping[str, Any]) -> str:
    return make_artifact_id(prefix="plan", payload=payload)