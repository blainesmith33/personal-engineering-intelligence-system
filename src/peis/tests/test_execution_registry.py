from peis.execution.registry import (
    Capability,
    CapabilityRegistry,
    ExecutionRegistryError,
    build_default_registry,
    execute_capability,
    noop_handler,
)


def _echo_handler(payload):
    return {
        "status": "ok",
        "echo": dict(payload),
    }


def _failing_handler(payload):
    raise RuntimeError("boom")


def test_capability_registry_register_and_get_success():
    registry = CapabilityRegistry()
    capability = Capability(
        action_type="echo",
        handler=_echo_handler,
        requires_human_authorization=False,
        description="Echo payload",
    )

    registry.register(capability)

    loaded = registry.get("echo")

    assert loaded is capability
    assert loaded.action_type == "echo"
    assert registry.has("echo") is True


def test_capability_registry_rejects_duplicate_registration():
    registry = CapabilityRegistry()
    capability = Capability(
        action_type="echo",
        handler=_echo_handler,
    )

    registry.register(capability)

    try:
        registry.register(capability)
        assert False
    except ExecutionRegistryError:
        assert True


def test_capability_registry_rejects_unknown_action_type():
    registry = CapabilityRegistry()

    try:
        registry.get("missing")
        assert False
    except ExecutionRegistryError:
        assert True


def test_capability_registry_lists_action_types_sorted():
    registry = CapabilityRegistry()

    registry.register(
        Capability(
            action_type="z_action",
            handler=_echo_handler,
        )
    )
    registry.register(
        Capability(
            action_type="a_action",
            handler=_echo_handler,
        )
    )

    assert registry.list_action_types() == ("a_action", "z_action")


def test_execute_capability_success():
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="echo",
            handler=_echo_handler,
        )
    )

    result = execute_capability(
        registry=registry,
        action_type="echo",
        payload={"x": 1},
        human_authorized=False,
    )

    assert result["status"] == "ok"
    assert result["echo"] == {"x": 1}


def test_execute_capability_rejects_missing_human_authorization():
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="sensitive",
            handler=_echo_handler,
            requires_human_authorization=True,
        )
    )

    try:
        execute_capability(
            registry=registry,
            action_type="sensitive",
            payload={"x": 1},
            human_authorized=False,
        )
        assert False
    except ExecutionRegistryError:
        assert True


def test_execute_capability_allows_human_authorization_when_required():
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="sensitive",
            handler=_echo_handler,
            requires_human_authorization=True,
        )
    )

    result = execute_capability(
        registry=registry,
        action_type="sensitive",
        payload={"x": 1},
        human_authorized=True,
    )

    assert result["status"] == "ok"


def test_execute_capability_rejects_handler_failure():
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="explode",
            handler=_failing_handler,
        )
    )

    try:
        execute_capability(
            registry=registry,
            action_type="explode",
            payload={"x": 1},
            human_authorized=False,
        )
        assert False
    except ExecutionRegistryError:
        assert True


def test_execute_capability_rejects_non_mapping_result():
    registry = CapabilityRegistry()

    def bad_handler(payload):
        return "not-a-mapping"

    registry.register(
        Capability(
            action_type="bad",
            handler=bad_handler,
        )
    )

    try:
        execute_capability(
            registry=registry,
            action_type="bad",
            payload={"x": 1},
            human_authorized=False,
        )
        assert False
    except ExecutionRegistryError:
        assert True


def test_noop_handler_returns_expected_shape():
    result = noop_handler({"x": 1})

    assert result["status"] == "noop"
    assert result["input"] == {"x": 1}


def test_build_default_registry_contains_noop():
    registry = build_default_registry()

    assert registry.has("noop") is True

    capability = registry.get("noop")
    assert capability.action_type == "noop"


def test_registry_to_dict_exposes_registered_capabilities():
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="echo",
            handler=_echo_handler,
            requires_human_authorization=False,
            description="Echo payload",
        )
    )

    payload = registry.to_dict()

    assert "capabilities" in payload
    assert len(payload["capabilities"]) == 1
    assert payload["capabilities"][0]["action_type"] == "echo"