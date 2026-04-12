from peis.planning.artifact_store import ArtifactStore
from peis.planning.runtime import PlanningRuntime
from peis.planning.snapshot import build_planning_session_snapshot
from peis.server import model_invoke_fn, adjudicate_fn

artifact_store = ArtifactStore("data/planning_artifacts")

runtime = PlanningRuntime(
    artifact_store=artifact_store,
    model_invoke_fn=model_invoke_fn,
    adjudicate_fn=adjudicate_fn,
)

session_snapshot = build_planning_session_snapshot(
    capability_inventory_snapshot_id="manual_test_capabilities",
    policy_snapshot_id="manual_test_policy",
    plan_schema_version=1,
    action_schema_version=1,
    prompt_pack_version="manual_test_prompt_pack",
    grounding_corpus_version="manual_test_grounding",
    curated_examples_set_id="manual_test_examples",
    correction_cases_set_id="manual_test_corrections",
    model_provider="ollama",
    model_id="qwen2.5:3b",
    session_id="manual_test_session",
    startup_state_hash="manual_test_startup",
)

session_snapshot["determinism_envelope"] = {
    "policy_snapshot_id": session_snapshot["policy_snapshot_id"],
    "capability_inventory_snapshot_id": session_snapshot["capability_inventory_snapshot_id"],
    "prompt_pack_version": session_snapshot["prompt_pack_version"],
    "model_id": session_snapshot["model"]["model_id"],
    "session_id": session_snapshot["session"]["session_id"],
}

result = runtime.run(
    planning_request={
        "objective": "I need one concrete next step for PEIS today"
    },
    session_snapshot=session_snapshot,
)

print(result)
