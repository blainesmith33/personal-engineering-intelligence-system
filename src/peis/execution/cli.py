from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
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
        elif (
            summary["has_review_runtime_surface_capability"]
            and summary["runtime_surface_has_launcher_mismatch"]
        ):
            recommendation = {
                "task_type": "runtime_alignment",
                "recommended_task": (
                    "Reconcile the current server launch script with the runtime gateway surface so "
                    "the documented launcher and the canonical gateway entrypoint are aligned."
                ),
                "reason": (
                    "The repo has a gateway runtime surface, but the current server launch script targets "
                    "a different app/module or port than the gateway defaults."
                ),
            }
        elif (
            summary["has_review_runtime_surface_capability"]
            and summary["runtime_surface_requires_openai_api_key"]
        ):
            recommendation = {
                "task_type": "runtime_env_hardening",
                "recommended_task": (
                    "Make runtime-readiness expectations explicit by documenting and/or validating the "
                    "required OPENAI_API_KEY before gateway startup."
                ),
                "reason": (
                    "Gateway config requires OPENAI_API_KEY, so runtime readiness depends on environment "
                    "state in addition to repo file presence."
                ),
            }
        elif summary["has_runtime_modules"] and summary["grounded_execution_capability_count"] <= 6:
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
                    "Run grounded runtime and artifact inspection capabilities, then use their persisted "
                    "results to select the next implementation-hardening task from actual execution evidence."
                ),
                "reason": (
                    "Core repo structure and grounded inspection capabilities exist, and no higher-priority "
                    "structural gap was detected from current repo facts."
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

    def review_runtime_surface_handler(payload: dict[str, Any]) -> dict[str, Any]:
        runtime_state = _collect_runtime_surface_state(
            payload,
            repo_root=repo_root,
            repo_python=repo_python,
        )
        if runtime_state["status"] != "ok":
            return runtime_state

        summary = runtime_state["runtime_summary"]

        if summary["runtime_surface_has_launcher_mismatch"]:
            recommendation = {
                "task_type": "runtime_alignment",
                "recommended_task": (
                    "Reconcile the current server launch script with the runtime gateway surface so "
                    "the documented launcher and the canonical gateway entrypoint are aligned."
                ),
                "reason": (
                    "The current launch script targets a different app/module or port than the "
                    "runtime gateway defaults."
                ),
            }
        elif summary["runtime_surface_requires_openai_api_key"]:
            recommendation = {
                "task_type": "runtime_env_hardening",
                "recommended_task": (
                    "Make runtime-readiness expectations explicit by documenting and/or validating "
                    "the required OPENAI_API_KEY before gateway startup."
                ),
                "reason": (
                    "Gateway config hard-requires OPENAI_API_KEY, so runtime readiness depends on "
                    "environment state in addition to file presence."
                ),
            }
        elif not summary["gateway_health_endpoint_present"]:
            recommendation = {
                "task_type": "runtime_observability",
                "recommended_task": (
                    "Add or harden a gateway health/readiness endpoint so runtime inspection can "
                    "distinguish process liveness from usable gateway readiness."
                ),
                "reason": (
                    "Runtime health inspection should expose meaningful readiness facts, not just "
                    "basic process availability."
                ),
            }
        else:
            recommendation = {
                "task_type": "runtime_surface_verified",
                "recommended_task": (
                    "Use the grounded runtime surface facts to choose the next runtime-hardening or "
                    "execution-surface expansion task."
                ),
                "reason": (
                    "Runtime entrypoints, config surface, and launch paths were inspected from repo facts."
                ),
            }

        return {
            "status": "ok",
            "repo_path": str(repo_root),
            "runtime_summary": summary,
            "recommended_next_task": recommendation,
            "next_observation": "Runtime/API readiness inspected from grounded repo-state facts.",
        }

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

    registry.register(
        Capability(
            action_type="review_runtime_surface",
            handler=review_runtime_surface_handler,
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
    runtime_surface_summary = _collect_runtime_surface_summary(repo_root)

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
            "runtime_surface_requires_openai_api_key": runtime_surface_summary["runtime_surface_requires_openai_api_key"],
            "runtime_surface_has_launcher_mismatch": runtime_surface_summary["runtime_surface_has_launcher_mismatch"],
        },
        "next_observation": (
            "Repository state collected from authoritative repo files and artifact directories only. "
            "Use this to identify blockers, choose the next task, or decide if tests are needed."
        ),
    }


def _collect_runtime_surface_state(
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

    if not repo_root.exists() or not repo_root.is_dir():
        return {
            "status": "failed",
            "error": f"repo path is invalid: {repo_root}",
        }

    runtime_summary = _collect_runtime_surface_summary(repo_root)
    runtime_summary["repo_python_executable"] = str(repo_python)

    return {
        "status": "ok",
        "repo_path": str(repo_root),
        "runtime_summary": runtime_summary,
        "next_observation": (
            "Runtime/API surface collected from gateway modules and launch scripts only."
        ),
    }


def _collect_runtime_surface_summary(repo_root: Path) -> dict[str, Any]:
    gateway_dir = repo_root / "src" / "peis" / "runtime" / "gateway"
    main_path = gateway_dir / "main.py"
    api_path = gateway_dir / "api.py"
    config_path = gateway_dir / "config.py"
    schemas_path = gateway_dir / "schemas.py"
    orchestrator_path = gateway_dir / "orchestrator.py"
    run_server_script = repo_root / "run_peis_server.sh"
    start_peis_script = repo_root / "start_peis.sh"

    has_gateway_main = main_path.exists()
    has_gateway_api = api_path.exists()
    has_gateway_config = config_path.exists()
    has_gateway_schemas = schemas_path.exists()
    has_gateway_orchestrator = orchestrator_path.exists()
    has_run_peis_server_script = run_server_script.exists()
    has_start_peis_script = start_peis_script.exists()

    config_source = _safe_read_text(config_path)
    api_source = _safe_read_text(api_path)
    run_server_source = _safe_read_text(run_server_script)
    start_peis_source = _safe_read_text(start_peis_script)

    gateway_requires_openai_api_key = "OPENAI_API_KEY" in config_source
    default_ollama_base_url = _extract_python_constant(
        config_source,
        "DEFAULT_OLLAMA_BASE_URL",
    )
    default_gateway_host = _extract_python_constant(
        config_source,
        "DEFAULT_HOST",
    )
    default_gateway_port = _extract_python_constant(
        config_source,
        "DEFAULT_PORT",
    )

    gateway_health_endpoint_present = (
        '@app.get("/health")' in api_source
        or "@app.get('/health')" in api_source
    )

    gateway_import_initializes_orchestrator = (
        "_config = load_gateway_config()" in api_source
        and "_orchestrator = GatewayOrchestrator(_config)" in api_source
    )

    run_script_targets_peis_server_app = "uvicorn peis.server:app" in run_server_source
    run_script_targets_gateway_main = (
        "peis.runtime.gateway.main" in run_server_source
        or "uvicorn peis.runtime.gateway" in run_server_source
        or "uvicorn peis.runtime.gateway.api:app" in run_server_source
    )

    run_script_host = _extract_shell_assignment(run_server_source, "HOST")
    run_script_port = _extract_shell_assignment(run_server_source, "PORT")
    start_script_activates_venv = "source .venv/bin/activate" in start_peis_source

    launcher_mismatch = False
    mismatch_reasons: list[str] = []

    if has_gateway_main and has_run_peis_server_script:
        if run_script_targets_peis_server_app and not run_script_targets_gateway_main:
            launcher_mismatch = True
            mismatch_reasons.append(
                "run_peis_server.sh launches peis.server:app instead of the gateway runtime surface"
            )

    if default_gateway_port is not None and run_script_port is not None:
        if str(default_gateway_port) != str(run_script_port):
            launcher_mismatch = True
            mismatch_reasons.append(
                f"gateway default port is {default_gateway_port} but run_peis_server.sh uses {run_script_port}"
            )

    if has_gateway_main and not has_run_peis_server_script:
        mismatch_reasons.append("gateway runtime exists but no server launch script was found")

    readiness_summary = _build_runtime_readiness_summary(
        has_gateway_main=has_gateway_main,
        has_gateway_api=has_gateway_api,
        has_gateway_config=has_gateway_config,
        has_gateway_schemas=has_gateway_schemas,
        has_gateway_orchestrator=has_gateway_orchestrator,
        gateway_requires_openai_api_key=gateway_requires_openai_api_key,
        launcher_mismatch=launcher_mismatch,
    )

    return {
        "has_gateway_main": has_gateway_main,
        "has_gateway_api": has_gateway_api,
        "has_gateway_config": has_gateway_config,
        "has_gateway_schemas": has_gateway_schemas,
        "has_gateway_orchestrator": has_gateway_orchestrator,
        "has_run_peis_server_script": has_run_peis_server_script,
        "has_start_peis_script": has_start_peis_script,
        "gateway_requires_openai_api_key": gateway_requires_openai_api_key,
        "runtime_surface_requires_openai_api_key": gateway_requires_openai_api_key,
        "default_ollama_base_url": default_ollama_base_url,
        "default_gateway_host": default_gateway_host,
        "default_gateway_port": default_gateway_port,
        "gateway_health_endpoint_present": gateway_health_endpoint_present,
        "gateway_import_initializes_orchestrator": gateway_import_initializes_orchestrator,
        "run_script_targets_peis_server_app": run_script_targets_peis_server_app,
        "run_script_targets_gateway_runtime": run_script_targets_gateway_main,
        "run_script_host": run_script_host,
        "run_script_port": run_script_port,
        "start_script_activates_venv": start_script_activates_venv,
        "server_script_targets_gateway_runtime": run_script_targets_gateway_main,
        "runtime_surface_has_launcher_mismatch": launcher_mismatch,
        "launcher_mismatch_reasons": mismatch_reasons,
        "runtime_readiness_summary": readiness_summary,
    }


def _build_runtime_readiness_summary(
    *,
    has_gateway_main: bool,
    has_gateway_api: bool,
    has_gateway_config: bool,
    has_gateway_schemas: bool,
    has_gateway_orchestrator: bool,
    gateway_requires_openai_api_key: bool,
    launcher_mismatch: bool,
) -> str:
    if not all(
        [
            has_gateway_main,
            has_gateway_api,
            has_gateway_config,
            has_gateway_schemas,
            has_gateway_orchestrator,
        ]
    ):
        return (
            "Runtime gateway surface is incomplete from repo facts; one or more required "
            "gateway modules are missing."
        )

    if launcher_mismatch:
        return (
            "Runtime gateway surface exists, but the current launch path appears misaligned "
            "with the gateway entrypoint and/or default port."
        )

    if gateway_requires_openai_api_key:
        return (
            "Runtime gateway surface exists and is structurally present, but readiness still "
            "depends on required environment configuration such as OPENAI_API_KEY."
        )

    return (
        "Runtime gateway surface appears structurally present from repo facts."
    )


def _safe_read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_python_constant(source: str, constant_name: str) -> str | int | float | bool | None:
    if not source.strip():
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == constant_name:
                    value_node = node.value
                    if isinstance(value_node, ast.Constant):
                        return value_node.value

        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == constant_name:
                value_node = node.value
                if isinstance(value_node, ast.Constant):
                    return value_node.value

    return None


def _extract_shell_assignment(source: str, variable_name: str) -> str | None:
    if not source.strip():
        return None

    pattern = rf'^\s*{re.escape(variable_name)}="([^"]+)"\s*$'
    match = re.search(pattern, source, flags=re.MULTILINE)
    if match is None:
        return None
    return match.group(1)


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