from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence


class ValidationError(ValueError):
    """Raised when validation invariants are violated."""


# ---------------------------
# Core Primitives
# ---------------------------


def require(condition: bool, message: str) -> None:
    """
    Generic hard assertion.

    Always use this instead of inline asserts to ensure consistent failure mode.
    """
    if not condition:
        raise ValidationError(message)


def require_type(value: Any, expected_type: type, *, field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{field_name} must be of type {expected_type.__name__}"
        )


def require_one_of(
    value: Any,
    allowed: Iterable[Any],
    *,
    field_name: str,
) -> None:
    if value not in allowed:
        raise ValidationError(
            f"{field_name} must be one of {list(allowed)}, got {value!r}"
        )


# ---------------------------
# String Validation
# ---------------------------


def require_non_empty_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def require_optional_str(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"{field_name} must be None or a non-empty string"
        )
    return value.strip()


# ---------------------------
# Boolean / Numeric
# ---------------------------


def require_bool(value: Any, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{field_name} must be a bool")
    return value


def require_int(value: Any, *, field_name: str) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an int")
    return value


def require_positive_int(value: Any, *, field_name: str) -> int:
    require_int(value, field_name=field_name)
    if value <= 0:
        raise ValidationError(f"{field_name} must be > 0")
    return value


# ---------------------------
# Collection Validation
# ---------------------------


def require_list(value: Any, *, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list")
    return value


def require_non_empty_list(value: Any, *, field_name: str) -> list[Any]:
    require_list(value, field_name=field_name)
    if not value:
        raise ValidationError(f"{field_name} must not be empty")
    return value


def require_sequence(value: Any, *, field_name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence):
        raise ValidationError(f"{field_name} must be a sequence")
    return value


def require_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{field_name} must be a mapping")
    return value


def require_keys(
    mapping: Mapping[str, Any],
    *,
    required_keys: Iterable[str],
) -> None:
    for key in required_keys:
        if key not in mapping:
            raise ValidationError(f"missing required key: {key}")


def require_no_extra_keys(
    mapping: Mapping[str, Any],
    *,
    allowed_keys: Iterable[str],
) -> None:
    allowed = set(allowed_keys)
    for key in mapping:
        if key not in allowed:
            raise ValidationError(f"unexpected key: {key}")


# ---------------------------
# Structural Validation
# ---------------------------


def require_same_length(
    a: Sequence[Any],
    b: Sequence[Any],
    *,
    field_name_a: str,
    field_name_b: str,
) -> None:
    if len(a) != len(b):
        raise ValidationError(
            f"{field_name_a} and {field_name_b} must have same length"
        )


def require_unique(
    values: Sequence[Any],
    *,
    field_name: str,
) -> None:
    if len(values) != len(set(values)):
        raise ValidationError(f"{field_name} must contain unique values")


# ---------------------------
# Enum / Literal Coercion
# ---------------------------


def coerce_enum(
    enum_cls: type,
    value: Any,
    *,
    field_name: str,
):
    if isinstance(value, enum_cls):
        return value

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")

    normalized = value.strip()

    try:
        return enum_cls(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"{field_name} has unsupported value: {normalized!r}"
        ) from exc


# ---------------------------
# Bulk Guards
# ---------------------------


def require_all(
    values: Iterable[Any],
    predicate,
    *,
    field_name: str,
) -> None:
    for i, v in enumerate(values):
        if not predicate(v):
            raise ValidationError(
                f"{field_name}[{i}] failed validation: {v!r}"
            )


def require_none(
    values: Iterable[Any],
    predicate,
    *,
    field_name: str,
) -> None:
    for i, v in enumerate(values):
        if predicate(v):
            raise ValidationError(
                f"{field_name}[{i}] must not satisfy predicate: {v!r}"
            )