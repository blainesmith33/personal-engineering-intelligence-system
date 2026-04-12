from peis.core.determinism import (
    build_minimal_envelope,
    requires_new_artifact,
)


def test_same_envelope_no_new_artifact():
    a = build_minimal_envelope(
        file_hash="f",
        extractor_binary_hash="b",
        extractor_config_hash="c",
        schema_version="1",
        evidence_snapshot_id="e",
        policy_snapshot_id="p",
    )

    b = a

    assert not requires_new_artifact(a, b)


def test_different_envelope_requires_new():
    a = build_minimal_envelope(
        file_hash="f",
        extractor_binary_hash="b",
        extractor_config_hash="c",
        schema_version="1",
        evidence_snapshot_id="e",
        policy_snapshot_id="p",
    )

    b = build_minimal_envelope(
        file_hash="f2",
        extractor_binary_hash="b",
        extractor_config_hash="c",
        schema_version="1",
        evidence_snapshot_id="e",
        policy_snapshot_id="p",
    )

    assert requires_new_artifact(a, b)