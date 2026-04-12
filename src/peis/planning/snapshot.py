import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any


SCHEMA_VERSION = 1
ARTIFACT_TYPE = "planning_session_snapshot"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _blake3_like_hash(data: str) -> str:
    # Using sha256 as a placeholder for consistency if BLAKE3 is not yet standardized in your repo
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def make_planning_session_snapshot_id(canonical_body: Dict[str, Any]) -> str:
    """
    Deterministic ID derived from canonicalized snapshot contents.
    Excludes timestamp and ID itself.
    """
    canonical_str = _canonical_json(canonical_body)
    digest = _blake3_like_hash(canonical_str)[:16]
    return f"pss_{digest}"


def build_planning_session_snapshot(
    *,
    capability_inventory_snapshot_id: str,
    policy_snapshot_id: str,
    plan_schema_version: int,
    action_schema_version: int,
    prompt_pack_version: str,
    grounding_corpus_version: str,
    curated_examples_set_id: str,
    correction_cases_set_id: str,
    model_provider: str,
    model_id: str,
    session_id: str,
    startup_state_hash: str,
    created_reason: str = "startup",
    model_revision: Optional[str] = None,
    model_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a PlanningSessionSnapshot artifact.

    This function:
    - Constructs canonical snapshot body
    - Derives deterministic snapshot ID
    - Attaches timestamp
    """

    # --- Canonical body for ID generation (exclude ID + timestamp) ---
    canonical_body = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "capability_inventory_snapshot_id": capability_inventory_snapshot_id,
        "policy_snapshot_id": policy_snapshot_id,
        "plan_schema_version": plan_schema_version,
        "action_schema_version": action_schema_version,
        "prompt_pack_version": prompt_pack_version,
        "grounding_corpus_version": grounding_corpus_version,
        "curated_examples_set_id": curated_examples_set_id,
        "correction_cases_set_id": correction_cases_set_id,
        "model": {
            "provider": model_provider,
            "model_id": model_id,
            "model_revision": model_revision,
            "model_hash": model_hash,
        },
        "session": {
            "session_id": session_id,
            "startup_state_hash": startup_state_hash,
            "created_reason": created_reason,
        },
    }

    snapshot_id = make_planning_session_snapshot_id(canonical_body)

    # --- Final artifact ---
    snapshot = {
        **canonical_body,
        "planning_session_snapshot_id": snapshot_id,
        "created_at_utc": _utc_now_iso(),
    }

    return snapshot