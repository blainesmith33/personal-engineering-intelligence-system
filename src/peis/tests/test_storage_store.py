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
from peis.runtime.pipeline import build_pipeline_request, run_pipeline
from peis.storage.store import (
    StorageError,
    StoredArtifactRef,
    store_artifact,
    store_decision_record,
    store_evaluation_record,
    store_plan_record,
    store_pipeline_result,
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


def test_store_artifact_success(tmp_path: Path):
    ref = store_artifact(
        root_dir=tmp_path,
        artifact_type="decision_record",
        artifact_id="d1",
        payload={"a": 1, "b": "x"},
    )

    assert isinstance(ref, StoredArtifactRef)
    assert ref.artifact_id == "d1"
    assert ref.artifact_type == "decision_record"

    target = tmp_path / "decision_record" / "d1.json"
    assert target.exists()
    assert target.is_file()


def test_store_artifact_rejects_existing_without_overwrite(tmp_path: Path):
    store_artifact(
        root_dir=tmp_path,
        artifact_type="decision_record",
        artifact_id="d1",
        payload={"a": 1},
    )

    try:
        store_artifact(
            root_dir=tmp_path,
            artifact_type="decision_record",
            artifact_id="d1",
            payload={"a": 2},
            overwrite=False,
        )
        assert False
    except StorageError:
        assert True


def test_store_artifact_allows_overwrite_when_enabled(tmp_path: Path):
    store_artifact(
        root_dir=tmp_path,
        artifact_type="decision_record",
        artifact_id="d1",
        payload={"a": 1},
    )

    ref = store_artifact(
        root_dir=tmp_path,
        artifact_type="decision_record",
        artifact_id="d1",
        payload={"a": 2},
        overwrite=True,
    )

    assert ref.artifact_id == "d1"
    assert (tmp_path / "decision_record" / "d1.json").exists()


def test_store_decision_record_success(tmp_path: Path):
    decision, _, _ = _make_records()

    ref = store_decision_record(
        root_dir=tmp_path,
        record=decision,
    )

    assert ref.artifact_id == decision.decision_record_id
    assert ref.artifact_type == "decision_record"
    assert (tmp_path / "decision_record" / f"{decision.decision_record_id}.json").exists()


def test_store_evaluation_record_success(tmp_path: Path):
    _, evaluation, _ = _make_records()

    ref = store_evaluation_record(
        root_dir=tmp_path,
        record=evaluation,
    )

    assert ref.artifact_id == evaluation.evaluation_record_id
    assert ref.artifact_type == "evaluation_record"
    assert (tmp_path / "evaluation_record" / f"{evaluation.evaluation_record_id}.json").exists()


def test_store_plan_record_success(tmp_path: Path):
    _, _, plan = _make_records()

    ref = store_plan_record(
        root_dir=tmp_path,
        record=plan,
    )

    assert ref.artifact_id == plan.plan_record_id
    assert ref.artifact_type == "plan_record"
    assert (tmp_path / "plan_record" / f"{plan.plan_record_id}.json").exists()


def test_store_pipeline_result_success(tmp_path: Path):
    authority, evidence, determinism, stop_decision = _make_valid_context()

    request = build_pipeline_request(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary="evaluation",
        decision_summary="decision",
        plan_summary="plan",
        steps=(),
    )

    result = run_pipeline(request)

    refs = store_pipeline_result(
        root_dir=tmp_path,
        result=result.result,
    )

    assert set(refs.keys()) == {
        "decision_record",
        "evaluation_record",
        "plan_record",
    }
    assert (tmp_path / "decision_record").exists()
    assert (tmp_path / "evaluation_record").exists()
    assert (tmp_path / "plan_record").exists()


def test_store_pipeline_result_rejects_missing_components(tmp_path: Path):
    class BadResult:
        decision_record = None
        evaluation_record = None
        plan_record = None

    try:
        store_pipeline_result(
            root_dir=tmp_path,
            result=BadResult(),
        )
        assert False
    except StorageError:
        assert True


def test_store_artifact_rejects_invalid_payload(tmp_path: Path):
    try:
        store_artifact(
            root_dir=tmp_path,
            artifact_type="decision_record",
            artifact_id="d1",
            payload="not-a-mapping",  # type: ignore[arg-type]
        )
        assert False
    except Exception:
        assert True