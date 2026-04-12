from __future__ import annotations

from peis.ids import (
    make_decision_id,
    make_evaluation_id,
    make_plan_id,
)

from peis.decision_record import DecisionRecord
from peis.evaluation_record import EvaluationRecord
from peis.plan_record import PlanRecord, PlanStep

from peis.core.authority import AuthorityBinding
from peis.core.evidence import EvidenceBinding
from peis.core.determinism import DeterminismEnvelope
from peis.core.stop_states import StopDecision, StopState


# -------------------------------------------------------
# Decision Builder
# -------------------------------------------------------


def build_decision_record(
    *,
    subject_id: str,
    decision_type: str,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    stop_decision: StopDecision,
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
) -> DecisionRecord:
    payload = {
        "subject_id": subject_id,
        "decision_type": decision_type,
        "stop_state": stop_decision.stop_state.value,
        "evidence_snapshot_id": evidence.evidence_snapshot_id,
        "policy_snapshot_id": evidence.policy_snapshot_id,
    }

    decision_record_id = make_decision_id(payload)

    return DecisionRecord(
        decision_record_id=decision_record_id,
        subject_id=subject_id,
        decision_type=decision_type,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        stop_decision=stop_decision,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )


# -------------------------------------------------------
# Evaluation Builder
# -------------------------------------------------------


def build_evaluation_record(
    *,
    subject_id: str,
    evaluation_type: str,
    input_authorities: tuple[AuthorityBinding, ...],
    input_evidence_bindings: tuple[EvidenceBinding, ...],
    input_determinism_envelopes: tuple[DeterminismEnvelope, ...],
    decision_record_id: str,
    result_stop_state: StopState,
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
) -> EvaluationRecord:
    payload = {
        "subject_id": subject_id,
        "evaluation_type": evaluation_type,
        "decision_record_id": decision_record_id,
        "result_stop_state": result_stop_state.value,
        "evidence_snapshot_id": input_evidence_bindings[0].evidence_snapshot_id,
        "policy_snapshot_id": input_evidence_bindings[0].policy_snapshot_id,
    }

    evaluation_record_id = make_evaluation_id(payload)

    return EvaluationRecord(
        evaluation_record_id=evaluation_record_id,
        subject_id=subject_id,
        evaluation_type=evaluation_type,
        input_authorities=input_authorities,
        input_evidence_bindings=input_evidence_bindings,
        input_determinism_envelopes=input_determinism_envelopes,
        decision_record_id=decision_record_id,
        result_stop_state=result_stop_state,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
    )


# -------------------------------------------------------
# Plan Builder
# -------------------------------------------------------


def build_plan_record(
    *,
    subject_id: str,
    plan_type: str,
    authority: AuthorityBinding,
    evidence: EvidenceBinding,
    determinism: DeterminismEnvelope,
    basis_decision_record_id: str,
    basis_stop_state: StopState,
    steps: tuple[PlanStep, ...],
    summary: str,
    rationale: str | None = None,
    emitted_by: str | None = None,
    human_authorized: bool = False,
) -> PlanRecord:
    payload = {
        "subject_id": subject_id,
        "plan_type": plan_type,
        "basis_decision_record_id": basis_decision_record_id,
        "basis_stop_state": basis_stop_state.value,
        "evidence_snapshot_id": evidence.evidence_snapshot_id,
        "policy_snapshot_id": evidence.policy_snapshot_id,
    }

    plan_record_id = make_plan_id(payload)

    return PlanRecord(
        plan_record_id=plan_record_id,
        subject_id=subject_id,
        plan_type=plan_type,
        authority=authority,
        evidence=evidence,
        determinism=determinism,
        basis_decision_record_id=basis_decision_record_id,
        basis_stop_state=basis_stop_state,
        steps=steps,
        summary=summary,
        rationale=rationale,
        emitted_by=emitted_by,
        human_authorized=human_authorized,
    )