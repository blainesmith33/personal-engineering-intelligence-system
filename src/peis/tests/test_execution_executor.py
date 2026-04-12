from peis.core.authority import EvidenceRole, make_authoritative_binding
from peis.core.determinism import build_minimal_envelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopState
from peis.execution.executor import (
    ExecutionError,
    execute_plan_record,
)
from peis.execution.registry import (
    Capability,
    CapabilityRegistry,
    build_default_registry,
)
from peis.plan_record import PlanStep, make_plan_record


def _make_valid_context():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.DECISION,
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
        source_label="test",
    )

    evidence = EvidenceBinding("e1", "p1")

    determinism = build_minimal_envelope(
        file_hash="f1",
        extractor_binary_hash="b1",
        extractor_config_hash="c1",
        schema_version="1",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    return authority, evidence, determinism


def _make_plan_record(
    *,
    steps: tuple[PlanStep, ...],
    human_authorized: bool = False,
) -> object:
    authority, evidence, determinism = _make_valid_context()

    return make_plan_record(
        plan_record_id="p1",
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id="d1",
        basis_stop_state=StopState.RESOLVED,
        steps=steps,
        summary="plan",
        human_authorized=human_authorized,
    )


def test_execute_plan_record_noop_plan_success():
    registry = build_default_registry()
    plan_record = _make_plan_record(steps=())

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert result.plan_record_id == "p1"
    assert result.subject_id == "s1"
    assert result.executed is True
    assert result.is_noop_execution is True
    assert result.step_results == ()


def test_execute_plan_record_single_noop_step_success():
    registry = build_default_registry()

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="do nothing",
    )
    plan_record = _make_plan_record(steps=(step,))

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert result.executed is True
    assert result.is_noop_execution is False
    assert len(result.step_results) == 1

    step_result = result.step_results[0]
    assert step_result.step_id == "step1"
    assert step_result.action_type == "noop"
    assert step_result.status == "noop"
    assert step_result.output["status"] == "noop"


def test_execute_plan_record_multiple_steps_success():
    registry = build_default_registry()

    steps = (
        PlanStep(
            step_id="step1",
            action_type="noop",
            description="first",
        ),
        PlanStep(
            step_id="step2",
            action_type="noop",
            description="second",
        ),
    )
    plan_record = _make_plan_record(steps=steps)

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert len(result.step_results) == 2
    assert result.step_results[0].step_id == "step1"
    assert result.step_results[1].step_id == "step2"


def test_execute_plan_record_rejects_non_registry():
    plan_record = _make_plan_record(steps=())

    try:
        execute_plan_record(
            registry="not-a-registry",  # type: ignore[arg-type]
            plan_record=plan_record,
        )
        assert False
    except ExecutionError:
        assert True


def test_execute_plan_record_rejects_non_plan_record():
    registry = build_default_registry()

    try:
        execute_plan_record(
            registry=registry,
            plan_record="not-a-plan-record",  # type: ignore[arg-type]
        )
        assert False
    except ExecutionError:
        assert True


def test_execute_plan_record_rejects_unknown_action_type():
    registry = build_default_registry()

    step = PlanStep(
        step_id="step1",
        action_type="missing_action",
        description="unknown",
    )
    plan_record = _make_plan_record(steps=(step,))

    try:
        execute_plan_record(
            registry=registry,
            plan_record=plan_record,
        )
        assert False
    except ExecutionError:
        assert True


def test_execute_plan_record_rejects_registry_execution_failure():
    registry = CapabilityRegistry()

    def failing_handler(payload):
        raise RuntimeError("boom")

    registry.register(
        Capability(
            action_type="explode",
            handler=failing_handler,
        )
    )

    step = PlanStep(
        step_id="step1",
        action_type="explode",
        description="explode",
    )
    plan_record = _make_plan_record(steps=(step,))

    try:
        execute_plan_record(
            registry=registry,
            plan_record=plan_record,
        )
        assert False
    except ExecutionError:
        assert True


def test_execute_plan_record_enforces_capability_human_authorization():
    registry = CapabilityRegistry()

    def ok_handler(payload):
        return {"status": "ok"}

    registry.register(
        Capability(
            action_type="sensitive",
            handler=ok_handler,
            requires_human_authorization=True,
        )
    )

    step = PlanStep(
        step_id="step1",
        action_type="sensitive",
        description="sensitive action",
    )
    plan_record = _make_plan_record(
        steps=(step,),
        human_authorized=False,
    )

    try:
        execute_plan_record(
            registry=registry,
            plan_record=plan_record,
        )
        assert False
    except ExecutionError:
        assert True


def test_execute_plan_record_allows_capability_human_authorization():
    registry = CapabilityRegistry()

    def ok_handler(payload):
        return {"status": "ok", "seen": payload["step_id"]}

    registry.register(
        Capability(
            action_type="sensitive",
            handler=ok_handler,
            requires_human_authorization=True,
        )
    )

    step = PlanStep(
        step_id="step1",
        action_type="sensitive",
        description="sensitive action",
        requires_human_authorization=True,
    )
    plan_record = _make_plan_record(
        steps=(step,),
        human_authorized=True,
    )

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert len(result.step_results) == 1
    assert result.step_results[0].status == "ok"
    assert result.step_results[0].output["seen"] == "step1"


def test_execute_plan_record_includes_expected_payload_fields():
    captured = {}

    def capture_handler(payload):
        captured.update(payload)
        return {"status": "ok"}

    registry = CapabilityRegistry()
    registry.register(
        Capability(
            action_type="capture",
            handler=capture_handler,
        )
    )

    step = PlanStep(
        step_id="step1",
        action_type="capture",
        description="capture payload",
        metadata={"x": 1},
    )
    plan_record = _make_plan_record(steps=(step,))

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert len(result.step_results) == 1
    assert captured["plan_record_id"] == "p1"
    assert captured["subject_id"] == "s1"
    assert captured["plan_type"] == "plan"
    assert captured["basis_decision_record_id"] == "d1"
    assert captured["basis_stop_state"] == "RESOLVED"
    assert captured["step_id"] == "step1"
    assert captured["action_type"] == "capture"
    assert captured["description"] == "capture payload"
    assert captured["requires_human_authorization"] is False
    assert captured["metadata"] == {"x": 1}


def test_step_execution_result_defaults_status_to_completed_when_missing():
    registry = CapabilityRegistry()

    def no_status_handler(payload):
        return {"value": 123}

    registry.register(
        Capability(
            action_type="nostatus",
            handler=no_status_handler,
        )
    )

    step = PlanStep(
        step_id="step1",
        action_type="nostatus",
        description="no status",
    )
    plan_record = _make_plan_record(steps=(step,))

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    assert len(result.step_results) == 1
    assert result.step_results[0].status == "completed"
    assert result.step_results[0].output["value"] == 123


def test_plan_execution_result_to_dict_shape():
    registry = build_default_registry()

    step = PlanStep(
        step_id="step1",
        action_type="noop",
        description="serialize",
    )
    plan_record = _make_plan_record(steps=(step,))

    result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    payload = result.to_dict()

    assert payload["plan_record_id"] == "p1"
    assert payload["subject_id"] == "s1"
    assert payload["executed"] is True
    assert isinstance(payload["step_results"], list)
    assert payload["step_results"][0]["step_id"] == "step1"