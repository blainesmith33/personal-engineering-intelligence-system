from peis.ids import (
    IdError,
    make_artifact_id,
    make_decision_id,
    make_evaluation_id,
    make_plan_id,
)


def test_make_artifact_id_is_deterministic_for_same_payload():
    payload = {
        "subject_id": "s1",
        "decision_type": "classify",
        "stop_state": "RESOLVED",
        "evidence_snapshot_id": "e1",
        "policy_snapshot_id": "p1",
    }

    first = make_artifact_id(prefix="decision", payload=payload)
    second = make_artifact_id(prefix="decision", payload=payload)

    assert first == second
    assert first.startswith("decision_")


def test_make_artifact_id_is_order_stable_for_same_mapping_contents():
    left = {
        "a": "1",
        "b": "2",
        "c": "3",
    }
    right = {
        "c": "3",
        "a": "1",
        "b": "2",
    }

    left_id = make_artifact_id(prefix="x", payload=left)
    right_id = make_artifact_id(prefix="x", payload=right)

    assert left_id == right_id


def test_make_artifact_id_changes_when_payload_changes():
    left = {
        "subject_id": "s1",
        "decision_type": "classify",
    }
    right = {
        "subject_id": "s2",
        "decision_type": "classify",
    }

    left_id = make_artifact_id(prefix="decision", payload=left)
    right_id = make_artifact_id(prefix="decision", payload=right)

    assert left_id != right_id


def test_make_artifact_id_rejects_empty_prefix():
    try:
        make_artifact_id(prefix="", payload={"a": 1})
        assert False
    except IdError:
        assert True


def test_make_artifact_id_rejects_non_mapping_payload():
    try:
        make_artifact_id(prefix="decision", payload="not-a-mapping")  # type: ignore[arg-type]
        assert False
    except IdError:
        assert True


def test_specific_id_builders_use_expected_prefixes():
    payload = {
        "subject_id": "s1",
        "evidence_snapshot_id": "e1",
        "policy_snapshot_id": "p1",
    }

    decision_id = make_decision_id(payload)
    evaluation_id = make_evaluation_id(payload)
    plan_id = make_plan_id(payload)

    assert decision_id.startswith("decision_")
    assert evaluation_id.startswith("evaluation_")
    assert plan_id.startswith("plan_")