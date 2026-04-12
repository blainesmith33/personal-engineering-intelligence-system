from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_execution_cli_end_to_end(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]

    plan_path = tmp_path / "plan.json"
    out_root = tmp_path / "out"

    plan_payload = {
        "schema_version": "1.0",
        "plan_record_id": "plan_cli_test",
        "subject_id": "subject_cli_test",
        "plan_type": "test",
        "basis_decision_record_id": "decision_cli_test",
        "basis_stop_state": "RESOLVED",
        "human_authorized": True,
        "summary": "cli test plan",
        "authority": {
            "authority_class": "authoritative",
            "evidence_role": "decision",
            "evidence_snapshot_id": "e1",
            "policy_snapshot_id": "p1",
            "source_label": "cli_test",
        },
        "evidence": {
            "evidence_snapshot_id": "e1",
            "policy_snapshot_id": "p1",
        },
        "determinism": {
            "file_hash": "fh1",
            "extractor_binary_hash": "ebh1",
            "extractor_config_hash": "ech1",
            "schema_version": "1.0",
            "policy_snapshot_id": "p1",
            "evidence_snapshot_id": "e1",
        },
        "steps": [
            {
                "step_id": "step1",
                "action_type": "noop",
                "description": "test step",
            }
        ],
    }

    plan_path.write_text(json.dumps(plan_payload), encoding="utf-8")

    env = dict(os.environ)
    existing_pythonpath = env.get("PYTHONPATH", "")
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else src_path
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "peis.execution.cli",
            "--plan",
            str(plan_path),
            "--out",
            str(out_root),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "ExecutionResultRecord written to:" in result.stdout

    stored_files = list((out_root / "execution_result_record").glob("execution_result_*.json"))
    assert len(stored_files) == 1

    payload = json.loads(stored_files[0].read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "execution_result_record"
    assert payload["plan_record_id"] == "plan_cli_test"
    assert payload["decision_record_id"] == "decision_cli_test"
    assert payload["subject_id"] == "subject_cli_test"
    assert payload["execution_status"] == "SUCCEEDED"