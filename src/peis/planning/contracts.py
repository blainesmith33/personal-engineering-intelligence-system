from typing import Any, Dict, Set

from peis.execution.cli import _register_default_capabilities
from peis.execution.registry import CapabilityRegistry


def get_allowed_action_types(session_snapshot: Dict[str, Any]) -> Set[str]:
    """
    Resolve allowed action types from the currently used default execution
    capability surface.

    This binds planning legality to the same default capabilities that the
    execution CLI registers today.
    """

    registry = CapabilityRegistry()
    _register_default_capabilities(registry)
    return set(registry.list_action_types())