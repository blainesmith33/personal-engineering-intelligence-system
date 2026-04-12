from peis.core.authority import (
    make_authoritative_binding,
    make_advisory_binding,
    assert_decision_authority,
    AuthorityError,
    EvidenceRole,
)


def test_authoritative_binding_allows_decision():
    binding = make_authoritative_binding(
        evidence_role=EvidenceRole.INPUT,
        evidence_snapshot_id="e1",
        policy_snapshot_id="p1",
        source_label="test",
    )

    assert_decision_authority(binding)


def test_advisory_binding_rejected_for_decision():
    binding = make_advisory_binding(
        evidence_role=EvidenceRole.INPUT,
        source_label="test",
    )

    try:
        assert_decision_authority(binding)
        assert False
    except AuthorityError:
        assert True