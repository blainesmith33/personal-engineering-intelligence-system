from __future__ import annotations

import os
from typing import Any, Dict

import requests
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

from peis.planning.artifact_store import ArtifactStore
from peis.planning.conversation_engine import ConversationEngine
from peis.planning.runtime import PlanningRuntime


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"
OPENAI_MODEL = os.environ.get("PEIS_OPENAI_MODEL", "gpt-5.4")


class PlanningRequestModel(BaseModel):
    objective: str


class SessionSnapshotModel(BaseModel):
    determinism_envelope: Dict[str, Any]
    prompt_pack_version: str


def _get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def _ollama_generate(
    *,
    prompt: str,
    timeout_seconds: int,
) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    data = response.json()
    model_output = data.get("response")

    if not isinstance(model_output, str):
        raise ValueError("Ollama response missing string field 'response'")

    return model_output.strip()


def local_ai_fn(payload: Dict[str, Any]) -> str:
    """
    Local AI behavior:
    - First turn: real qwen call
    - Later turns: deterministic reuse of last output
    """

    conversation_log = payload.get("conversation_log", [])
    if conversation_log:
        last_output = conversation_log[-1].get("output")
        if not isinstance(last_output, str):
            raise ValueError(
                "local_ai_fn expected last conversation output to be a string"
            )
        return last_output

    planning_request = payload.get("planning_request", payload)
    objective = planning_request.get("objective")

    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("local_ai_fn requires a non-empty objective")

    prompt = f"""
You are the local AI retrieval/suggestion layer inside a governed planning environment.

Objective:
{objective.strip()}

Rules:
- Return a short planning suggestion only.
- Do not explain limitations.
- Do not use markdown.
- Keep the response compact.
- Prefer action-oriented wording.
""".strip()

    return _ollama_generate(
        prompt=prompt,
        timeout_seconds=120,
    )


def chatgpt_fn(payload: Dict[str, Any]) -> str:
    """
    Real ChatGPT reasoning/adjudication layer.

    Input:
    - planning_request
    - conversation_log

    Output:
    - strict JSON only
    - target schema:
      {
        "objective": string,
        "steps": [{"action_type": string}]
      }
    """

    planning_request = payload.get("planning_request", payload)
    conversation_log = payload.get("conversation_log", [])

    objective = planning_request.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise ValueError("chatgpt_fn requires a non-empty objective")

    client = _get_openai_client()

    system_prompt = """
You are the reasoning/adjudication layer inside PEIS.

You are NOT the execution layer.
You are NOT allowed to explain your reasoning.
You MUST return ONLY valid JSON.

Required output schema:
{
  "objective": "string",
  "steps": [
    {
      "action_type": "string"
    }
  ]
}

Hard rules:
- Output ONLY JSON.
- No markdown.
- No commentary.
- No surrounding text.
- No extra fields.
- If local AI output is messy, repair it.
- If the simplest valid plan is obvious, return it directly.

Allowed action_type values:
- run_pytest
""".strip()

    user_payload = {
        "planning_request": planning_request,
        "conversation_log": conversation_log,
    }

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Repair/produce the final structured planning JSON for this input:\n"
                    f"{user_payload}"
                ),
            },
        ],
    )

    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("OpenAI response did not contain output_text")

    return output_text.strip()


def model_invoke_fn(prompt: str) -> str:
    """
    Final local planning model call used by the PEIS runtime.
    """
    return _ollama_generate(
        prompt=prompt,
        timeout_seconds=120,
    )


def adjudicate_fn(payload: Dict[str, Any]) -> str:
    """
    Real adjudication/repair path for invalid local-model output.

    Input payload is the escalation payload from PEIS.
    Output MUST be strict JSON only.
    """

    raw_output = payload.get("raw_output")
    validation_errors = payload.get("validation_errors", [])
    planning_request = payload.get("planning_request", {})
    session_snapshot = payload.get("session_snapshot", {})

    if not isinstance(raw_output, str):
        raise ValueError("adjudicate_fn requires raw_output string")

    client = _get_openai_client()

    system_prompt = """
You are the PEIS adjudication layer.

Your job is to repair invalid planning output into strict valid JSON.

You MUST return ONLY valid JSON.

Required schema:
{
  "objective": "string",
  "steps": [
    {
      "action_type": "string"
    }
  ]
}

Hard rules:
- Output ONLY JSON.
- No markdown.
- No explanations.
- No extra fields.
- Preserve intent when possible.
- Conform to allowed action types only.

Allowed action_type values:
- run_pytest
""".strip()

    user_payload = {
        "planning_request": planning_request,
        "session_snapshot": session_snapshot,
        "raw_output": raw_output,
        "validation_errors": validation_errors,
    }

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Repair this invalid planning output into valid final JSON:\n"
                    f"{user_payload}"
                ),
            },
        ],
    )

    output_text = getattr(response, "output_text", None)
    if not isinstance(output_text, str) or not output_text.strip():
        raise ValueError("OpenAI adjudication response did not contain output_text")

    return output_text.strip()


artifact_store = ArtifactStore(base_path="data/planning_artifacts")

runtime = PlanningRuntime(
    artifact_store=artifact_store,
    model_invoke_fn=model_invoke_fn,
    adjudicate_fn=adjudicate_fn,
)

engine = ConversationEngine(
    runtime=runtime,
    local_ai_fn=local_ai_fn,
    chatgpt_fn=chatgpt_fn,
)

app = FastAPI()


@app.post("/plan")
def run_plan(
    planning_request: PlanningRequestModel,
    session_snapshot: SessionSnapshotModel,
) -> Dict[str, Any]:
    result = engine.run(
        planning_request=planning_request.model_dump(),
        session_snapshot=session_snapshot.model_dump(),
    )
    return result