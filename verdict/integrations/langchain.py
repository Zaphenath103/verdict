"""LangChain integration for Verdict.

Provides a callback handler that automatically traces all LangChain
agent actions and tool invocations.

Usage:
    from verdict.integrations.langchain import VerdictCallbackHandler

    handler = VerdictCallbackHandler()
    agent.run("do the task", callbacks=[handler])
    report = handler.verify()
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from verdict.core.tracer import Tracer
from verdict.core.types import VerdictReport
from verdict.core.verifier import Verifier
from verdict.checks.registry import get_default_checks


class VerdictCallbackHandler:
    """LangChain callback handler that traces agent actions for Verdict.

    Implements the LangChain callback interface to capture:
    - Tool starts and ends
    - LLM starts and ends
    - Chain starts and ends
    - Agent actions and decisions
    """

    def __init__(
        self,
        agent_name: str = "langchain-agent",
        verifier: Verifier | None = None,
    ):
        self._tracer = Tracer(agent_name=agent_name)
        self._verifier = verifier or Verifier()
        self._active_trace = None
        self._tool_call_map: dict[str, str] = {}

        if self._verifier.check_count == 0:
            for check in get_default_checks():
                self._verifier.add_check(check)

    def _ensure_trace(self) -> Any:
        if self._active_trace is None:
            t = self._tracer.tracer_trace_obj("langchain-run")
            self._active_trace = t
        return self._active_trace

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        trace = self._ensure_trace()
        content = prompts[0][:300] if prompts else ""
        trace.record_llm_request(content, metadata={"run_id": str(run_id)})

    def on_llm_end(self, response: Any, *, run_id: UUID, **kwargs: Any) -> None:
        trace = self._ensure_trace()
        text = ""
        if hasattr(response, "generations") and response.generations:
            gen = response.generations[0]
            if gen:
                text = gen[0].text[:300] if hasattr(gen[0], "text") else str(gen[0])[:300]
        trace.record_llm_response(text, metadata={"run_id": str(run_id)})

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        trace = self._ensure_trace()
        tool_name = serialized.get("name", "unknown_tool")
        action_id = trace.record_tool_call(
            tool_name,
            arguments={"input": input_str},
            metadata={"run_id": str(run_id)},
        )
        self._tool_call_map[str(run_id)] = action_id

    def on_tool_end(self, output: str, *, run_id: UUID, **kwargs: Any) -> None:
        trace = self._ensure_trace()
        action_id = self._tool_call_map.pop(str(run_id), "unknown")
        trace.record_tool_result(action_id, output=output[:500])

    def on_tool_error(self, error: BaseException, *, run_id: UUID, **kwargs: Any) -> None:
        trace = self._ensure_trace()
        action_id = self._tool_call_map.pop(str(run_id), "unknown")
        trace.record_tool_result(action_id, error=str(error))

    def verify(self) -> VerdictReport:
        """Run verification on the captured trace."""
        if self._active_trace:
            self._active_trace.finalize()
        if not self._tracer.traces:
            raise ValueError("No traces captured")
        return self._verifier.verify(self._tracer.traces[-1])

    @property
    def tracer(self) -> Tracer:
        return self._tracer
