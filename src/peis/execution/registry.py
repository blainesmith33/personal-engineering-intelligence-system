from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping

from peis.core.validation import (
    ValidationError,
    require_mapping,
    require_non_empty_str,
)


class ExecutionRegistryError(ValueError):
    """Raised when registry invariants are violated."""


# -------------------------------------------------------
# Capability Definition
# -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Capability:
    """
    A single executable capability.

    This is the ONLY allowed execution surface.
    """

    action_type: str
    handler: Callable[[Mapping[str, Any]], Mapping[str, Any]]
    requires_human_authorization: bool = False
    description: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_str(self.action_type, field_name="action_type")

        if not callable(self.handler):
            raise ExecutionRegistryError("handler must be callable")

        if self.description is not None:
            require_non_empty_str(
                self.description,
                field_name="description",
            )


# -------------------------------------------------------
# Registry
# -------------------------------------------------------


class CapabilityRegistry:
    """
    Deterministic registry of allowed execution capabilities.

    Properties:
    - Explicit allow-list only
    - No dynamic imports
    - No fallback execution
    - No implicit behavior
    """

    def __init__(self) -> None:
        self._capabilities: Dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if not isinstance(capability, Capability):
            raise ExecutionRegistryError(
                "capability must be a Capability"
            )

        action_type = capability.action_type

        if action_type in self._capabilities:
            raise ExecutionRegistryError(
                f"duplicate capability registration: {action_type}"
            )

        self._capabilities[action_type] = capability

    def get(self, action_type: str) -> Capability:
        action_type = require_non_empty_str(
            action_type,
            field_name="action_type",
        )

        capability = self._capabilities.get(action_type)

        if capability is None:
            raise ExecutionRegistryError(
                f"unknown action_type: {action_type}"
            )

        return capability

    def has(self, action_type: str) -> bool:
        return action_type in self._capabilities

    def list_action_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities.keys()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "capabilities": [
                {
                    "action_type": c.action_type,
                    "requires_human_authorization": c.requires_human_authorization,
                    "description": c.description,
                }
                for c in self._capabilities.values()
            ]
        }


# -------------------------------------------------------
# Execution
# -------------------------------------------------------


def execute_capability(
    *,
    registry: CapabilityRegistry,
    action_type: str,
    payload: Mapping[str, Any],
    human_authorized: bool,
) -> dict[str, Any]:
    """
    Execute a registered capability.

    Enforces:
    - capability existence
    - payload validity
    - human authorization (if required)
    - mapping-shaped result surface
    """
    if not isinstance(registry, CapabilityRegistry):
        raise ExecutionRegistryError("registry must be a CapabilityRegistry")

    capability = registry.get(action_type)

    try:
        require_mapping(payload, field_name="payload")
    except ValidationError as exc:
        raise ExecutionRegistryError("payload must be a mapping") from exc

    if capability.requires_human_authorization and not human_authorized:
        raise ExecutionRegistryError(
            f"capability requires human authorization: {action_type}"
        )

    try:
        result = capability.handler(payload)
    except Exception as exc:
        raise ExecutionRegistryError(
            f"capability execution failed: {action_type}"
        ) from exc

    try:
        require_mapping(result, field_name="result")
    except ValidationError as exc:
        raise ExecutionRegistryError(
            f"capability returned non-mapping result: {action_type}"
        ) from exc

    return dict(result)


# -------------------------------------------------------
# Default Safe Capability (for testing / baseline)
# -------------------------------------------------------


def noop_handler(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    Safe baseline capability.

    Does nothing except echo payload.
    """
    require_mapping(payload, field_name="payload")
    return {"status": "noop", "input": dict(payload)}


def build_default_registry() -> CapabilityRegistry:
    """
    Minimal registry with safe baseline capabilities.
    """
    registry = CapabilityRegistry()

    registry.register(
        Capability(
            action_type="noop",
            handler=noop_handler,
            requires_human_authorization=False,
            description="No-op capability for testing",
        )
    )

    return registry