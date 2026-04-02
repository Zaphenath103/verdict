"""OpenAI integration for Verdict.

Wraps the OpenAI Python SDK to trace all tool/function calls
in ChatGPT conversations, then verify the trace.

Usage:
    from verdict.integrations.openai import TracedOpenAI

    client = TracedOpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "List files"}],
        tools=[...],
    )
    report = client.verdict_verify()
"""

from __future__ import annotations

import json
from typing import Any

from verdict.core.tracer import Tracer
from verdict.core.types import VerdictReport
from verdict.core.verifier import Verifier
from verdict.checks.registry import get_default_checks


class TracedOpenAI:
    """Drop-in wrapper for the OpenAI client with Verdict tracing."""

    def __init__(
        self,
        api_key: str | None = None,
        verifier: Verifier | None = None,
        **client_kwargs: Any,
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install verdict-ai[openai]"
            )

        self._client = OpenAI(api_key=api_key, **client_kwargs)
        self._tracer = Tracer(agent_name="openai-gpt")
        self._verifier = verifier or Verifier()

        if self._verifier.check_count == 0:
            for check in get_default_checks():
                self._verifier.add_check(check)

        self.chat = _TracedChat(self._client.chat, self._tracer)

    def verdict_verify(self, trace_index: int = -1) -> VerdictReport:
        if not self._tracer.traces:
            raise ValueError("No traces recorded yet")
        trace = self._tracer.traces[trace_index]
        return self._verifier.verify(trace)

    @property
    def verdict_tracer(self) -> Tracer:
        return self._tracer

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _TracedChat:
    def __init__(self, chat: Any, tracer: Tracer):
        self._chat = chat
        self._tracer = tracer
        self.completions = _TracedCompletions(chat.completions, tracer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _TracedCompletions:
    def __init__(self, completions: Any, tracer: Tracer):
        self._completions = completions
        self._tracer = tracer

    def create(self, **kwargs: Any) -> Any:
        model = kwargs.get("model", "unknown")

        with self._tracer.trace(f"gpt-{model}") as trace:
            messages = kwargs.get("messages", [])
            user_msg = ""
            if messages:
                last = messages[-1]
                if isinstance(last.get("content"), str):
                    user_msg = last["content"][:200]
            trace.record_llm_request(user_msg, metadata={"model": model})

            response = self._completions.create(**kwargs)

            for choice in response.choices:
                msg = choice.message
                if msg.content:
                    trace.record_llm_response(msg.content[:500])
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        args = {}
                        if tc.function.arguments:
                            try:
                                args = json.loads(tc.function.arguments)
                            except json.JSONDecodeError:
                                args = {"raw": tc.function.arguments}
                        trace.record_tool_call(
                            tc.function.name,
                            arguments=args,
                            metadata={"openai_tool_call_id": tc.id},
                        )

            return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)
