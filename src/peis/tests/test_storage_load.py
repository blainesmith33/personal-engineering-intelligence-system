import json
from pathlib import Path

from peis.builders import (
    build_decision_record,
    build_evaluation_record,
    build_plan_record,
)
from peis.core.authority import EvidenceRole, make_authoritative_binding
from peis.core.determinism import build_minimal_envelope
from peis.core.evidence import EvidenceBinding
from peis.core.stop_states import StopState, make_stop_decision
from peis.storage.load import (
    StorageLoadError,
    load_artifact,
    load_decision_record,
    load_evaluation_record,
    load_plan_record,
)
from peis.storage.store import (
    store_decision_record,
    store_evaluation_record,
    store_plan_record,
)


def _make_valid_context():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.INPUT,
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

    stop_decision = make_stop_decision(
        stop_state=StopState.RESOLVED,
        reason="ok",
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
    )

    return authority, evidence, determinism, stop_decision


def _make_records():
    authority, evidence, determinism, stop_decision = _make_valid_context()

    decision = build_decision_record(
        subject_id="s1",
        decision_type="classify",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary="decision",
    )

    evaluation = build_evaluation_record(
        subject_id="s1",
        evaluation_type="eval",
        input_authorities=(authority,),
        input_evidence_bindings=(evidence,),
        input_determinism_envelopes=(determinism,),
        decision_record_id=decision.decision_record_id,
        result_stop_state=decision.stop_state,
        summary="evaluation",
    )

    plan = build_plan_record(
        subject_id="s1",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id=decision.decision_record_id,
        basis_stop_state=decision.stop_state,
        steps=(),
        summary="plan",
    )

    return decision, evaluation, plan


def test_load_artifact_success(tmp_path: Path):
    target_dir = tmp_path / "decision_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    payload = {"a": 1, "b": "x"}
    target_path = target_dir / "d1.json"
    target_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_artifact(
        root_dir=tmp_path,
        artifact_type="decision_record",
        artifact_id="d1",
    )

    assert loaded == payload


def test_load_artifact_rejects_missing_file(tmp_path: Path):
    try:
        load_artifact(
            root_dir=tmp_path,
            artifact_type="decision_record",
            artifact_id="missing",
        )
        assert False
    except StorageLoadError:
        assert True


def test_load_artifact_rejects_invalid_json(tmp_path: Path):
    target_dir = tmp_path / "decision_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / "d1.json"
    target_path.write_text("{not-valid-json}", encoding="utf-8")

    try:
        load_artifact(
            root_dir=tmp_path,
            artifact_type="decision_record",
            artifact_id="d1",
        )
        assert False
    except StorageLoadError:
        assert True


def test_load_artifact_rejects_non_mapping_payload(tmp_path: Path):
    target_dir = tmp_path / "decision_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / "d1.json"
    target_path.write_text(json.dumps(["not", "a", "mapping"]), encoding="utf-8")

    try:
        load_artifact(
            root_dir=tmp_path,
            artifact_type="decision_record",
            artifact_id="d1",
        )
        assert False
    except Exception:
        assert True


def test_load_decision_record_round_trip(tmp_path: Path):
    decision, _, _ = _make_records()

    store_decision_record(
        root_dir=tmp_path,
        record=decision,
    )

    loaded = load_decision_record(
        root_dir=tmp_path,
        decision_record_id=decision.decision_record_id,
    )

    assert loaded == decision


def test_load_evaluation_record_round_trip(tmp_path: Path):
    _, evaluation, _ = _make_records()

    store_evaluation_record(
        root_dir=tmp_path,
        record=evaluation,
    )

    loaded = load_evaluation_record(
        root_dir=tmp_path,
        evaluation_record_id=evaluation.evaluation_record_id,
    )

    assert loaded == evaluation


def test_load_plan_record_round_trip(tmp_path: Path):
    _, _, plan = _make_records()

    store_plan_record(
        root_dir=tmp_path,
        record=plan,
    )

    loaded = load_plan_record(
        root_dir=tmp_path,
        plan_record_id=plan.plan_record_id,
    )

    assert loaded == plan


def test_load_decision_record_rejects_invalid_payload_shape(tmp_path: Path):
    target_dir = tmp_path / "decision_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    bad_payload = {
        "decision_record_id": "d1",
        "subject_id": "s1",
        # missing required fields
    }

    target_path = target_dir / "d1.json"
    target_path.write_text(json.dumps(bad_payload), encoding="utf-8")

    try:
        load_decision_record(
            root_dir=tmp_path,
            decision_record_id="d1",
        )
        assert False
    except StorageLoadError:
        assert True


def test_load_evaluation_record_rejects_invalid_payload_shape(tmp_path: Path):
    target_dir = tmp_path / "evaluation_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    bad_payload = {
        "evaluation_record_id": "ev1",
        "subject_id": "s1",
    }

    target_path = target_dir / "ev1.json"
    target_path.write_text(json.dumps(bad_payload), encoding="utf-8")

    try:
        load_evaluation_record(
            root_dir=tmp_path,
            evaluation_record_id="ev1",
        )
        assert False
    except StorageLoadError:
        assert True


def test_load_plan_record_rejects_invalid_payload_shape(tmp_path: Path):
    target_dir = tmp_path / "plan_record"
    target_dir.mkdir(parents=True, exist_ok=True)

    bad_payload = {
        "plan_record_id": "p1",
        "subject_id": "s1",
    }

    target_path = target_dir / "p1.json"
    target_path.write_text(json.dumps(bad_payload), encoding="utf-8")

    try:
        load_plan_record(
            root_dir=tmp_path,
            plan_record_id="p1",
        )
        assert False
    except StorageLoadError:
        assert True