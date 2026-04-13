from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from peis.execution.executor import execute_plan_record
from peis.execution.persist import persist_execution_result
from peis.execution.registry import Capability, CapabilityRegistry
from peis.execution.result_record import build_execution_result_record
from peis.plan_record import PlanRecord


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute a PlanRecord and persist results.")
    parser.add_argument("--plan", required=True, help="Path to plan_record.json")
    parser.add_argument("--out", required=True, help="Output root directory")

    args = parser.parse_args()

    plan_path = Path(args.plan).resolve()
    out_root = Path(args.out).resolve()

    if not plan_path.exists():
        raise SystemExit(f"Plan file not found: {plan_path}")

    plan_record = _load_plan(plan_path)
    repo_root = _resolve_repo_root(plan_path)

    registry = CapabilityRegistry()
    _register_default_capabilities(
        registry=registry,
        repo_root=repo_root,
    )

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


def _resolve_repo_root(plan_path: Path) -> Path:
    """
    Resolve the authoritative PEIS repo root deterministically.

    Priority:
    1. PEIS_REPO_ROOT environment override, if present and valid.
    2. Parent walk from the plan path for a directory containing src/peis.
    3. Parent walk from this file for a directory containing src/peis.
    """

    env_value = os.environ.get("PEIS_REPO_ROOT", "").strip()
    if env_value:
        candidate = Path(env_value).expanduser().resolve()
        if _looks_like_repo_root(candidate):
            return candidate
        raise SystemExit(
            f"PEIS_REPO_ROOT is set but invalid for this repo: {candidate}"
        )

    for candidate in [*plan_path.parents, *Path(__file__).resolve().parents]:
        if _looks_like_repo_root(candidate):
            return candidate.resolve()

    raise SystemExit(
        "Could not resolve PEIS repo root. Expected a parent directory containing src/peis."
    )


def _looks_like_repo_root(path: Path) -> bool:
    return (
        path.exists()
        and path.is_dir()
        and (path / "src").is_dir()
        and (path / "src" / "peis").is_dir()
    )


def _resolve_repo_python(repo_root: Path) -> Path:
    """
    Resolve the authoritative Python interpreter for PEIS execution.

    Prefer the repo-local venv interpreter path exactly as it exists on disk.
    Do not resolve the symlink target when returning it, because the venv path
    itself is the meaningful deterministic execution surface.

    Fall back to the current interpreter only if it is already being invoked
    from the repo-local venv path.
    """

    candidates = [
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "bin" / "python3",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    current_python = Path(sys.executable)
    repo_venv_bin = repo_root / ".venv" / "bin"

    try:
        current_python.parent.relative_to(repo_venv_bin)
    except ValueError:
        raise SystemExit(
            "Could not resolve a repo-local Python interpreter. "
            f"Checked: {[str(p) for p in candidates]}. "
            f"Current interpreter is not inside {repo_venv_bin}: {current_python}"
        ) from None

    return current_python


def _register_default_capabilities(
    registry: CapabilityRegistry,
    *,
    repo_root: Path,
) -> None:
    repo_python = _resolve_repo_python(repo_root)

    def noop_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "ok",
            "repo_path": str(repo_root),
            "next_observation": "No-op capability executed.",
        }

    def run_pytest_handler(payload: dict[str, Any]) -> dict[str, Any]:
        result = subprocess.run(
            [str(repo_python), "-m", "pytest", "-q"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        return {
            "status": "ok" if result.returncode == 0 else "failed",
            "repo_path": str(repo_root),
            "python_executable": str(repo_python),
            "cwd": str(repo_root),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "next_observation": (
                "Pytest executed with the repo-local interpreter from the authoritative repo root."
            ),
        }

    def identify_next_task_handler(payload: dict[str, Any]) -> dict[str, Any]:
        repo_state = _collect_repo_state(payload, repo_root=repo_root, repo_python=repo_python)
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
        elif summary["has_runtime_gateway"] and not summary["has_review_runtime_surface_capability"]:
            recommendation = {
                "task_type": "execution_capability_expansion",
                "recommended_task": (
                    "Add a grounded execution capability to inspect runtime/API readiness, "
                    "including gateway entrypoints, provider configuration surface, and launch scripts."
                ),
                "reason": (
                    "The repo contains runtime gateway code, provider modules, and startup scripts, "
                    "but the grounded execution surface cannot yet inspect that runtime layer directly."
                ),
            }
        elif summary["has_execution_artifacts"] and not summary["has_review_recent_artifacts_capability"]:
            recommendation = {
                "task_type": "artifact_aware_execution",
                "recommended_task": (
                    "Add a grounded execution capability that reads recent PEIS execution artifacts "
                    "and summarizes the latest concrete outcomes, blockers, and next actions."
                ),
                "reason": (
                    "PEIS is already persisting execution artifacts, but the execution surface cannot "
                    "yet use those persisted results as grounded input for recommendations."
                ),
            }
        elif summary["has_runtime_modules"] and summary["grounded_execution_capability_count"] <= 5:
            recommendation = {
                "task_type": "execution_surface_growth",
                "recommended_task": (
                    "Expand grounded execution capability coverage before widening orchestration, "
                    "starting with runtime inspection and artifact review."
                ),
                "reason": (
                    "The repo already includes planning, runtime, orchestration, storage, and tests, "
                    "but the grounded execution capability surface remains narrow."
                ),
            }
        else:
            recommendation = {
                "task_type": "implementation_progression",
                "recommended_task": (
                    "Run the grounded test capability and use the result artifact to select the next "
                    "implementation-hardening task from actual execution evidence."
                ),
                "reason": (
                    "Core repo structure and initial grounded execution capabilities exist, and no "
                    "higher-priority structural gap was detected from current repo facts."
                ),
            }

        return {
            "status": "ok",
            "repo_path": repo_state["repo_path"],
            "repo_summary": summary,
            "recommended_next_task": recommendation,
            "next_observation": "Next task identified from grounded repo-state facts.",
        }

    def summarize_current_blocker_handler(payload: dict[str, Any]) -> dict[str, Any]:
        repo_state = _collect_repo_state(payload, repo_root=repo_root, repo_python=repo_python)
        if repo_state["status"] != "ok":
            return repo_state

        summary = repo_state["summary"]

        if not summary["has_git_dir"]:
            blocker = {
                "blocker_type": "repo_hygiene",
                "blocker_summary": "The PEIS repo was not initialized as a git repository.",
                "reason": "Without git history, drift detection, rollback, and change review are weakened.",
                "recommended_resolution": "Initialize git and commit the current PEIS baseline.",
            }
        elif not summary["has_pyproject_toml"]:
            blocker = {
                "blocker_type": "project_structure",
                "blocker_summary": "The repo has Python source and tests but no pyproject.toml.",
                "reason": "Project packaging and tool configuration are still implicit.",
                "recommended_resolution": "Create a pyproject.toml to define the Python project explicitly.",
            }
        elif summary["project_test_file_count"] > 0 and not summary["has_pytest_ini"]:
            blocker = {
                "blocker_type": "test_configuration",
                "blocker_summary": "The repo contains tests but no pytest.ini.",
                "reason": "Test behavior is not yet explicitly configured at the repo level.",
                "recommended_resolution": "Decide whether pytest.ini is needed and add it if PEIS needs stable test configuration.",
            }
        else:
            blocker = {
                "blocker_type": "no_structural_blocker_detected",
                "blocker_summary": "No major structural blocker was detected from repo-state facts.",
                "reason": "The repo has git, explicit project structure, source code, and no obvious missing structural prerequisite.",
                "recommended_resolution": "Move to the next grounded implementation task based on current PEIS priorities.",
            }

        return {
            "status": "ok",
            "repo_path": repo_state["repo_path"],
            "repo_summary": summary,
            "current_blocker": blocker,
            "next_observation": "Current blocker summarized from grounded repo-state facts.",
        }

    def review_repo_state_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return _collect_repo_state(payload, repo_root=repo_root, repo_python=repo_python)

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


def _collect_repo_state(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    repo_python: Path,
) -> dict[str, Any]:
    payload_repo_path = payload.get("repo_path")
    if isinstance(payload_repo_path, str) and payload_repo_path.strip():
        requested_repo_root = Path(payload_repo_path).expanduser().resolve()
        if requested_repo_root != repo_root:
            return {
                "status": "failed",
                "error": (
                    f"repo path override does not match authoritative repo root: "
                    f"requested={requested_repo_root} authoritative={repo_root}"
                ),
            }

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
    data_artifact_dirs: list[str] = []
    if data_dir.exists() and data_dir.is_dir():
        data_artifact_dirs = sorted(
            p.name for p in data_dir.iterdir() if p.is_dir()
        )

    git_dir = repo_root / ".git"
    pyproject_file = repo_root / "pyproject.toml"
    pytest_ini = repo_root / "pytest.ini"
    venv_dir = repo_root / ".venv"
    src_dir = repo_root / "src"
    peis_dir = src_dir / "peis"
    execution_cli = peis_dir / "execution" / "cli.py"
    runtime_gateway_main = peis_dir / "runtime" / "gateway" / "main.py"
    runtime_dir = peis_dir / "runtime"
    orchestration_dir = peis_dir / "orchestration"
    storage_dir = peis_dir / "storage"
    execution_artifacts_dir = data_dir / "execution_artifacts"
    planning_artifacts_dir = data_dir / "planning_artifacts"

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

    grounded_actions = _extract_grounded_action_types(execution_cli)
    recent_execution_artifacts = _list_recent_json_files(execution_artifacts_dir, limit=5)
    recent_planning_artifacts = _list_recent_json_files(planning_artifacts_dir, limit=5)

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
            "repo_python_executable": str(repo_python),
            "cwd": str(repo_root),
            "git_status": git_status,
            "has_runtime_modules": runtime_dir.exists() and runtime_dir.is_dir(),
            "has_runtime_gateway": runtime_gateway_main.exists(),
            "has_orchestration_modules": orchestration_dir.exists() and orchestration_dir.is_dir(),
            "has_storage_modules": storage_dir.exists() and storage_dir.is_dir(),
            "has_execution_artifacts": execution_artifacts_dir.exists() and execution_artifacts_dir.is_dir(),
            "has_planning_artifacts": planning_artifacts_dir.exists() and planning_artifacts_dir.is_dir(),
            "grounded_execution_action_types": grounded_actions,
            "grounded_execution_capability_count": len(grounded_actions),
            "has_review_runtime_surface_capability": "review_runtime_surface" in grounded_actions,
            "has_review_recent_artifacts_capability": "review_recent_artifacts" in grounded_actions,
            "recent_execution_artifacts": recent_execution_artifacts,
            "recent_planning_artifacts": recent_planning_artifacts,
        },
        "next_observation": (
            "Repository state collected from authoritative repo files and artifact directories only. "
            "Use this to identify blockers, choose the next task, or decide if tests are needed."
        ),
    }


def _extract_grounded_action_types(cli_path: Path) -> list[str]:
    if not cli_path.exists() or not cli_path.is_file():
        return []

    try:
        source = cli_path.read_text(encoding="utf-8")
    except OSError:
        return []

    try:
        tree = ast.parse(source, filename=str(cli_path))
    except SyntaxError:
        return []

    action_types: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        if not isinstance(func, ast.Name) or func.id != "Capability":
            continue

        for keyword in node.keywords:
            if keyword.arg != "action_type":
                continue

            value_node = keyword.value
            if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
                action_type = value_node.value.strip()
                if action_type and action_type not in action_types:
                    action_types.append(action_type)

    return sorted(action_types)


def _list_recent_json_files(directory: Path, *, limit: int) -> list[str]:
    if not directory.exists() or not directory.is_dir():
        return []

    files = [
        p for p in directory.rglob("*.json")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return [str(p) for p in files[:limit]]


def _convert_to_execution_result_record(plan_record, plan_result):
    step_results = []

    for idx, step in enumerate(plan_result.step_results):
        normalized_status = "SUCCEEDED"
        if step.status.strip().lower() in {"failed", "error"}:
            normalized_status = "FAILED"

        step_results.append(
            {
                "step_index": idx,
                "step_id": step.step_id,
                "action_type": step.action_type,
                "status": normalized_status,
                "input_payload": {},
                "output_payload": step.output,
                "error": None if normalized_status == "SUCCEEDED" else step.output.get("error"),
            }
        )

    steps_failed = sum(1 for s in step_results if s["status"] == "FAILED")
    execution_status = "SUCCEEDED" if steps_failed == 0 else "FAILED"

    return build_execution_result_record(
        authority=plan_record.authority.to_dict(),
        evidence=plan_record.evidence.to_dict(),
        determinism=plan_record.determinism.to_dict(),
        plan_record_id=plan_record.plan_record_id,
        decision_record_id=plan_record.basis_decision_record_id,
        subject_id=plan_record.subject_id,
        execution_status=execution_status,
        step_results=step_results,
        summary={
            "steps_total": len(step_results),
            "steps_succeeded": len(step_results) - steps_failed,
            "steps_failed": steps_failed,
            "steps_skipped": 0,
        },
        emitted_by="cli",
    )


if __name__ == "__main__":
    main()