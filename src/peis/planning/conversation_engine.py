from __future__ import annotations

from typing import Any, Callable, Dict, List

from peis.planning.runtime import PlanningRuntime


class ConversationEngineError(RuntimeError):
    pass


class ConversationEngine:
    """
    Multi-agent conversation orchestrator.

    Enforces LOCK 15:

    Local AI → ChatGPT → Local AI → ChatGPT → PEIS

    - bounded turns (2 each)
    - no runaway loops
    - user interrupt respected
    """

    def __init__(
        self,
        *,
        runtime: PlanningRuntime,
        local_ai_fn: Callable[[Dict[str, Any]], str],
        chatgpt_fn: Callable[[Dict[str, Any]], str],
    ):
        self.runtime = runtime
        self.local_ai_fn = local_ai_fn
        self.chatgpt_fn = chatgpt_fn

    # -------------------------
    # PUBLIC ENTRY
    # -------------------------

    def run(
        self,
        *,
        planning_request: Dict[str, Any],
        session_snapshot: Dict[str, Any],
        user_control: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Execute full multi-agent loop.

        user_control may include:
        - stop: bool
        """

        if user_control and user_control.get("stop"):
            return self._halt("user_requested_stop")

        conversation_log: List[Dict[str, Any]] = []

        # -------------------------
        # TURN 1 — LOCAL AI
        # -------------------------

        local_1 = self._safe_call(self.local_ai_fn, planning_request)
        conversation_log.append({"agent": "local_ai", "output": local_1})

        # -------------------------
        # TURN 2 — CHATGPT
        # -------------------------

        chatgpt_1 = self._safe_call(
            self.chatgpt_fn,
            self._build_agent_input(planning_request, conversation_log),
        )
        conversation_log.append({"agent": "chatgpt", "output": chatgpt_1})

        # -------------------------
        # TURN 3 — LOCAL AI
        # -------------------------

        local_2 = self._safe_call(
            self.local_ai_fn,
            self._build_agent_input(planning_request, conversation_log),
        )
        conversation_log.append({"agent": "local_ai", "output": local_2})

        # -------------------------
        # TURN 4 — CHATGPT (FINAL)
        # -------------------------

        chatgpt_2 = self._safe_call(
            self.chatgpt_fn,
            self._build_agent_input(planning_request, conversation_log),
        )
        conversation_log.append({"agent": "chatgpt", "output": chatgpt_2})

        # -------------------------
        # FINAL → PEIS
        # -------------------------

        final_request = self._build_final_request(
            planning_request,
            chatgpt_2,
        )

        runtime_result = self.runtime.run(
            planning_request=final_request,
            session_snapshot=session_snapshot,
        )

        return {
            "conversation_log": conversation_log,
            "runtime_result": runtime_result,
        }

    # -------------------------
    # INTERNALS
    # -------------------------

    def _safe_call(
        self,
        fn: Callable[[Dict[str, Any]], str],
        payload: Dict[str, Any],
    ) -> str:
        try:
            result = fn(payload)

            if not isinstance(result, str):
                raise ConversationEngineError(
                    "agent output must be string"
                )

            return result

        except Exception as e:
            raise ConversationEngineError(str(e)) from e

    def _build_agent_input(
        self,
        planning_request: Dict[str, Any],
        conversation_log: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        return {
            "planning_request": planning_request,
            "conversation_log": conversation_log,
        }

    def _build_final_request(
        self,
        original_request: Dict[str, Any],
        chatgpt_output: str,
    ) -> Dict[str, Any]:
        """
        ChatGPT final output becomes the authoritative draft input.

        If ChatGPT output is invalid JSON, runtime will catch it.
        """

        return {
            "objective": original_request.get("objective"),
            "chatgpt_draft": chatgpt_output,
        }

    def _halt(self, reason: str) -> Dict[str, Any]:
        return {
            "status": "HALT",
            "reason": reason,
        }