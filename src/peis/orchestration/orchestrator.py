from typing import Dict, Any

import requests
from openai import OpenAI

from peis.orchestration.types import OrchestrationInput, OrchestrationResult


# ======================
# CONFIG (keep minimal)
# ======================

OLLAMA_URL = "http://192.168.1.253:11434/api/generate"
LOCAL_MODEL = "qwen2.5:3b"
CHATGPT_MODEL = "gpt-5.4"

client = OpenAI()


# ======================
# LOCAL MODEL
# ======================

def _call_local_model(prompt: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": LOCAL_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    res.raise_for_status()
    return res.json()["response"].strip()


# ======================
# CHATGPT ADJUDICATOR
# ======================

def _call_chatgpt_adjudicator(user_input: str, local_output: str) -> str:
    response = client.responses.create(
        model=CHATGPT_MODEL,
        input=[
            {
                "role": "system",
                "content": "You repair invalid plans. Output ONLY valid JSON.",
            },
            {
                "role": "user",
                "content": f"""
User request:
{user_input}

Local model draft:
{local_output}

Fix and return a VALID plan JSON.
""",
            },
        ],
    )
    return response.output_text.strip()


# ======================
# VALIDATION HOOK
# ======================

def _validate_plan(plan_str: str) -> Dict[str, Any]:
    """
    Replace this with your real validator import once wired.
    """
    import json

    try:
        parsed = json.loads(plan_str)
    except Exception:
        return {"status": "INVALID", "errors": ["invalid_json"]}

    if "steps" not in parsed:
        return {"status": "INVALID", "errors": ["missing_steps"]}

    return {"status": "VALID", "plan": parsed}


# ======================
# ESCALATION BUILDER
# ======================

def _build_escalation(user_input: str, local_output: str, errors: Any) -> Dict[str, Any]:
    return {
        "artifact_type": "planning_escalation_payload",
        "reason": "invalid_after_local_generation",
        "user_input": user_input,
        "local_output": local_output,
        "errors": errors,
    }


# ======================
# MAIN ORCHESTRATOR
# ======================

def run_orchestration(input_data: OrchestrationInput) -> OrchestrationResult:
    user_input = input_data["planning_request"]["objective"]

    # ---- STEP 1: LOCAL MODEL ----
    local_output = _call_local_model(user_input)

    # ---- STEP 2: VALIDATE ----
    validation = _validate_plan(local_output)

    if validation["status"] == "VALID":
        return {
            "status": "VALID",
            "plan": validation["plan"],
        }

    # ---- STEP 3: ESCALATION BUILD ----
    escalation_payload = _build_escalation(
        user_input,
        local_output,
        validation.get("errors", []),
    )

    # ---- STEP 4: CHATGPT ADJUDICATION ----
    repaired_output = _call_chatgpt_adjudicator(
        user_input,
        local_output,
    )

    # ---- STEP 5: FINAL VALIDATION ----
    final_validation = _validate_plan(repaired_output)

    if final_validation["status"] == "VALID":
        return {
            "status": "VALID",
            "plan": final_validation["plan"],
        }

    # ---- STEP 6: HARD ESCALATION ----
    return {
        "status": "ESCALATED",
        "escalation_payload": escalation_payload,
    }
