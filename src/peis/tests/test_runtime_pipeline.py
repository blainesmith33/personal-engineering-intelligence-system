from peis.runtime.pipeline import build_pipeline_request, run_pipeline
from peis.core.authority import make_authoritative_binding, EvidenceRole
from peis.core.evidence import EvidenceBinding
from peis.core.determinism import build_minimal_envelope
from peis.core.stop_states import make_stop_decision, StopState


def test_pipeline_end_to_end():
    authority = make_authoritative_binding(
        evidence_role=EvidenceRole.INPUT,
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
        source_label="test",
    )

    evidence = EvidenceBinding("e1", "p1")

    determinism = build_minimal_envelope(
        file_hash="f",
        extractor_binary_hash="b",
        extractor_config_hash="c",
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

    request = build_pipeline_request(
        subject_id="s1",
        evaluation_type="eval",
        decision_type="decision",
        plan_type="plan",
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        evaluation_summary="eval",
        decision_summary="decision",
        plan_summary="plan",
        steps=(),
    )

    result = run_pipeline(request)

    assert result.subject_id == "s1"
    assert result.stop_state == StopState.RESOLVED