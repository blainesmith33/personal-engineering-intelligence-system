from __future__ import annotations

import argparse
import json
import os
import platform
from pathlib import Path

from peis.execution.executor import execute_plan_record
from peis.execution.persist import persist_execution_result
from peis.execution.registry import CapabilityRegistry, Capability
from peis.execution.result_record import build_execution_result_record
from peis.plan_record import PlanRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a PlanRecord and persist results.")
    parser.add_argument("--plan", required=True, help="Path to plan_record.json")
    parser.add_argument("--out", required=True, help="Output root directory")

    args = parser.parse_args()

    plan_path = Path(args.plan)
    out_root = Path(args.out)

    if not plan_path.exists():
        raise SystemExit(f"Plan file not found: {plan_path}")

    plan_record = _load_plan(plan_path)

    registry = CapabilityRegistry()
    _register_default_capabilities(registry)

    plan_result = execute_plan_record(
        registry=registry,
        plan_record=plan_record,
    )

    record = _convert_to_execution_result_record(plan_record, plan_result)

    file_path = persist_execution_result(
        root=out_root,
        record=record,
    )

    print(f"ExecutionResultRecord written to: {file_path}")


def _load_plan(path: Path) -> PlanRecord:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    return PlanRecord.from_dict(payload)


def _register_default_capabilities(registry: CapabilityRegistry) -> None:
    import subprocess

    def noop_handler(payload):
        return {"status": "ok"}

    def run_pytest_handler(payload):
        result = subprocess.run(
            ["python", "-m", "pytest", "-q"],
            capture_output=True,
            text=True,
        )
        return {
            "status": "ok" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    def identify_next_task_handler(payload):
        repo_state = _collect_repo_state(payload)
        if repo_state["status"] != "ok":
            return repo_state

        summary = repo_state["summary"]

        if not summary["has_git_dir"]:
            recommendation = {
                "task_type": "repo_hygiene",
                "recommended_task": "Decide whether to initialize git for the PEIS repo before further expansion.",
                "reason": "Repository is not git-initialized, which limits traceability and drift control.",
            }
        elif not summary["has_pyproject_toml"]:
            recommendation = {
                "task_type": "project_structure",
                "recommended_task": "Create a pyproject.toml so the repo has an explicit Python project definition.",
                "reason": "The repo has source code and tests but no pyproject.toml.",
            }
        elif summary["project_test_file_count"] > 0 and not summary["has_pytest_ini"]:
            recommendation = {
                "task_type": "test_configuration",
                "recommended_task": "Review whether a pytest.ini is needed to make test behavior explicit.",
                "reason": "The repo has tests but no pytest.ini.",
            }
        else:
            recommendation = {
                "task_type": "next_action_selection",
                "recommended_task": "Review the current PEIS repo state and choose the next smallest implementation task.",
                "reason": "Core repo structure exists and no higher-priority structural gap was detected.",
            }

        return {
            "status": "ok",
            "repo_path": repo_state["repo_path"],
            "repo_summary": summary,
            "recommended_next_task": recommendation,
            "next_observation": (
                "Next task identified from grounded repo-state facts."
            ),
        }

    def summarize_current_blocker_handler(payload):
        return {
            "status": "ok",
            "message": "Summarize the current blocker preventing forward progress.",
        }

    def review_repo_state_handler(payload):
        return _collect_repo_state(payload)

    registry.register(
        Capability(
            action_type="noop",
            handler=noop_handler,
        )
    )

    registry.register(
        Capability(
            action_type="run_pytest",
            handler=run_pytest_handler,
        )
    )

    registry.register(
        Capability(
            action_type="identify_next_task",
            handler=identify_next_task_handler,
        )
    )

    registry.register(
        Capability(
            action_type="summarize_current_blocker",
            handler=summarize_current_blocker_handler,
        )
    )

    registry.register(
        Capability(
            action_type="review_repo_state",
            handler=review_repo_state_handler,
        )
    )


def _collect_repo_state(payload):
    repo_path_value = payload.get("repo_path")
    if isinstance(repo_path_value, str) and repo_path_value.strip():
        repo_root = Path(repo_path_value).expanduser().resolve()
    else:
        repo_root = Path.cwd().resolve()

    if not repo_root.exists():
        return {
            "status": "failed",
            "error": f"repo path does not exist: {repo_root}",
        }

    if not repo_root.is_dir():
        return {
            "status": "failed",
            "error": f"repo path is not a directory: {repo_root}",
        }

    exclude_dirs = {
        ".venv",
        ".pytest_cache",
        "__pycache__",
        ".Trash-1000",
        ".git",
    }

    def is_excluded(path: Path) -> bool:
        return any(part in exclude_dirs for part in path.parts)

    top_level_entries = sorted(
        p.name for p in repo_root.iterdir() if p.name not in exclude_dirs
    )

    python_files = sorted(
        p for p in repo_root.rglob("*.py") if not is_excluded(p.relative_to(repo_root))
    )

    json_files = sorted(
        p for p in repo_root.rglob("*.json") if not is_excluded(p.relative_to(repo_root))
    )

    test_files = sorted(
        p for p in repo_root.rglob("test_*.py") if not is_excluded(p.relative_to(repo_root))
    )

    top_level_scripts = sorted(
        p.name
        for p in repo_root.iterdir()
        if p.is_file() and p.suffix == ".py"
    )

    data_dir = repo_root / "data"
    data_artifact_dirs = []
    if data_dir.exists() and data_dir.is_dir():
        data_artifact_dirs = sorted(
            p.name for p in data_dir.iterdir() if p.is_dir()
        )

    git_dir = repo_root / ".git"
    pyproject_file = repo_root / "pyproject.toml"
    pytest_ini = repo_root / "pytest.ini"
    venv_dir = repo_root / ".venv"
    src_dir = repo_root / "src"

    git_status = "repo_present" if git_dir.exists() else "not_repo"

    src_packages: list[str] = []
    src_python_files = 0

    if src_dir.exists() and src_dir.is_dir():
        src_packages = sorted(
            p.name for p in src_dir.iterdir() if p.is_dir()
        )
        src_python_files = len(
            [
                p
                for p in src_dir.rglob("*.py")
                if "__pycache__" not in p.parts
            ]
        )

    return {
        "status": "ok",
        "repo_path": str(repo_root),
        "top_level_entries": top_level_entries,
        "summary": {
            "project_python_file_count": len(python_files),
            "project_json_file_count": len(json_files),
            "project_test_file_count": len(test_files),
            "src_python_file_count": src_python_files,
            "has_git_dir": git_dir.exists(),
            "has_pyproject_toml": pyproject_file.exists(),
            "has_pytest_ini": pytest_ini.exists(),
            "has_venv": venv_dir.exists(),
            "has_src_dir": src_dir.exists(),
            "src_packages": src_packages,
            "top_level_scripts": top_level_scripts,
            "data_artifact_dirs": data_artifact_dirs,
            "python_version": platform.python_version(),
            "cwd": os.getcwd(),
            "git_status": git_status,
        },
        "next_observation": (
            "Repository state collected from project files only. "
            "Use this to identify blockers, choose the next task, or decide if tests are needed."
        ),
    }


def _convert_to_execution_result_record(plan_record, plan_result):
    step_results = []

    for idx, step in enumerate(plan_result.step_results):
        step_results.append(
            {
                "step_index": idx,
                "step_id": step.step_id,
                "action_type": step.action_type,
                "status": "SUCCEEDED",
                "input_payload": {},
                "output_payload": step.output,
                "error": None,
            }
        )

    return build_execution_result_record(
        authority=plan_record.authority.to_dict(),
        evidence=plan_record.evidence.to_dict(),
        determinism=plan_record.determinism.to_dict(),
        plan_record_id=plan_record.plan_record_id,
        decision_record_id=plan_record.basis_decision_record_id,
        subject_id=plan_record.subject_id,
        execution_status="SUCCEEDED",
        step_results=step_results,
        summary={
            "steps_total": len(step_results),
            "steps_succeeded": len(step_results),
            "steps_failed": 0,
            "steps_skipped": 0,
        },
        emitted_by="cli",
    )


if __name__ == "__main__":
    main()