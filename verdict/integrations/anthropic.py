"""Anthropic (Claude) integration for Verdict.

Wraps the Anthropic Python SDK to automatically trace all tool use
in Claude conversations, then verify the trace.

Usage:
    from verdict.integrations.anthropic import TracedAnthropic

    client = TracedAnthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "List files in /tmp"}],
        tools=[...],
    )
    report = client.verdict_verify()
"""

from __future__ import annotations

from typing import Any

from verdict.core.tracer import Tracer
from verdict.core.types import VerdictReport
from verdict.core.verifier import Verifier
from verdict.checks.registry import get_default_checks


class TracedAnthropic:
    """Drop-in wrapper for the Anthropic client with Verdict tracing.

    Intercepts messages.create() calls, traces tool use blocks
    in responses, and provides verification.
    """

    def __init__(
        self,
        api_key: str | None = None,
        verifier: Verifier | None = None,
        **client_kwargs: Any,
    ):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install verdict-ai[anthropic]"
            )

        self._client = Anthropic(api_key=api_key, **client_kwargs)
        self._tracer = Tracer(agent_name="anthropic-claude")
        self._verifier = verifier or Verifier()

        if self._verifier.check_count == 0:
            for check in get_default_checks():
                self._verifier.add_check(check)

        # Proxy the messages interface
        self.messages = _TracedMessages(self._client.messages, self._tracer)

    def verdict_verify(self, trace_index: int = -1) -> VerdictReport:
        """Verify the most recent (or specified) trace."""
        if not self._tracer.traces:
            raise ValueError("No traces recorded yet")
        trace = self._tracer.traces[trace_index]
        return self._verifier.verify(trace)

    @property
    def verdict_tracer(self) -> Tracer:
        return self._tracer

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the underlying client."""
        return getattr(self._client, name)


class _TracedMessages:
    """Proxies messages.create() with automatic tracing."""

    def __init__(self, messages: Any, tracer: Tracer):
        self._messages = messages
        self._tracer = tracer

    def create(self, **kwargs: Any) -> Any:
        """Traced version of messages.create()."""
        model = kwargs.get("model", "unknown")

        with self._tracer.trace(f"claude-{model}") as trace:
            # Record the request
            messages = kwargs.get("messages", [])
            user_msg = ""
            if messages:
                last = messages[-1]
                if isinstance(last.get("content"), str):
                    user_msg = last["content"][:200]
            trace.record_llm_request(user_msg, metadata={"model": model})

            # Make the actual API call
            response = self._messages.create(**kwargs)

            # Trace the response
            for block in response.content:
                if block.type == "text":
                    trace.record_llm_response(block.text[:500])
                elif block.type == "tool_use":
                    call_id = trace.record_tool_call(
                        block.name,
                        arguments=dict(block.input) if block.input else {},
                        metadata={"anthropic_tool_use_id": block.id},
                    )

            return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)
