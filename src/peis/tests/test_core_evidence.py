from peis.core.evidence import (
    EvidenceBinding,
    assert_same_binding,
    EvidenceError,
)


def test_same_binding_passes():
    a = EvidenceBinding("e1", "p1")
    b = EvidenceBinding("e1", "p1")

    assert_same_binding(a, b)


def test_mismatch_binding_fails():
    a = EvidenceBinding("e1", "p1")
    b = EvidenceBinding("e2", "p1")

    try:
        assert_same_binding(a, b)
        assert False
    except EvidenceError:
        assert True