"""Tracer — captures every action an AI agent takes during execution.

The tracer is the foundation of Verdict. It wraps around any agent framework
and captures a structured trace of every tool call, decision, and output.
Traces are then passed to the Verifier for checking.

Usage:
    tracer = Tracer(agent_name="my-agent")
    with tracer.trace("deploy-task") as t:
        t.record_tool_call("bash", {"command": "npm run build"})
        t.record_tool_result(t.last_action_id, output="Build succeeded")
    report = Verifier().verify(t)
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

from verdict.core.types import (
    ActionType,
    AgentAction,
    ToolCall,
    ToolResult,
)


class Span:
    """A named span within a trace, grouping related actions."""

    def __init__(self, name: str, trace_id: str, parent_span_id: str | None = None):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        self.actions: list[AgentAction] = []
        self.started_at = datetime.now(timezone.utc)
        self.ended_at: datetime | None = None
        self.metadata: dict[str, Any] = {}

    def duration_ms(self) -> float:
        if self.ended_at is None:
            return 0.0
        delta = self.ended_at - self.started_at
        return delta.total_seconds() * 1000


class Trace:
    """A complete trace of an agent's execution.

    Captures every action — tool calls, results, decisions, file operations,
    shell commands, HTTP requests — in a structured, analyzable format.
    """

    def __init__(self, name: str, agent_name: str = "unknown"):
        self.id = uuid.uuid4().hex[:16]
        self.name = name
        self.agent_name = agent_name
        self.actions: list[AgentAction] = []
        self.spans: list[Span] = []
        self.started_at = datetime.now(timezone.utc)
        self.ended_at: datetime | None = None
        self.metadata: dict[str, Any] = {}
        self._active_span: Span | None = None
        self._tool_call_starts: dict[str, float] = {}

    @property
    def last_action_id(self) -> str:
        if not self.actions:
            raise ValueError("No actions recorded yet")
        return self.actions[-1].id

    def _add_action(self, action: AgentAction) -> str:
        self.actions.append(action)
        if self._active_span is not None:
            self._active_span.actions.append(action)
        return action.id

    def record_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record an agent invoking a tool."""
        tc = ToolCall(name=tool_name, arguments=arguments or {})
        self._tool_call_starts[tc.id] = time.monotonic()
        action = AgentAction(
            action_type=ActionType.TOOL_CALL,
            tool_call=tc,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_tool_result(
        self,
        tool_call_id: str,
        output: Any = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record the result of a tool invocation."""
        start = self._tool_call_starts.pop(tool_call_id, None)
        duration = (time.monotonic() - start) * 1000 if start else 0.0
        tr = ToolResult(
            tool_call_id=tool_call_id,
            output=output,
            error=error,
            duration_ms=duration,
        )
        action = AgentAction(
            action_type=ActionType.TOOL_RESULT,
            tool_result=tr,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_llm_request(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Record a request sent to an LLM."""
        action = AgentAction(
            action_type=ActionType.LLM_REQUEST,
            content=content,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_llm_response(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Record a response received from an LLM."""
        action = AgentAction(
            action_type=ActionType.LLM_RESPONSE,
            content=content,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_decision(self, content: str, metadata: dict[str, Any] | None = None) -> str:
        """Record an agent decision point."""
        action = AgentAction(
            action_type=ActionType.DECISION,
            content=content,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_file_write(
        self, path: str, content: str | None = None, metadata: dict[str, Any] | None = None
    ) -> str:
        """Record a file write operation."""
        action = AgentAction(
            action_type=ActionType.FILE_WRITE,
            content=path,
            metadata={"file_content": content, **(metadata or {})},
        )
        return self._add_action(action)

    def record_file_read(self, path: str, metadata: dict[str, Any] | None = None) -> str:
        """Record a file read operation."""
        action = AgentAction(
            action_type=ActionType.FILE_READ,
            content=path,
            metadata=metadata or {},
        )
        return self._add_action(action)

    def record_shell_exec(
        self,
        command: str,
        output: str | None = None,
        exit_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record a shell command execution."""
        action = AgentAction(
            action_type=ActionType.SHELL_EXEC,
            content=command,
            metadata={"output": output, "exit_code": exit_code, **(metadata or {})},
        )
        return self._add_action(action)

    def record_http_request(
        self,
        method: str,
        url: str,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Record an HTTP request."""
        action = AgentAction(
            action_type=ActionType.HTTP_REQUEST,
            content=f"{method} {url}",
            metadata={"status_code": status_code, **(metadata or {})},
        )
        return self._add_action(action)

    @contextmanager
    def span(self, name: str) -> Generator[Span, None, None]:
        """Create a named span grouping related actions."""
        parent = self._active_span
        s = Span(
            name=name,
            trace_id=self.id,
            parent_span_id=parent.id if parent else None,
        )
        self.spans.append(s)
        self._active_span = s
        try:
            yield s
        finally:
            s.ended_at = datetime.now(timezone.utc)
            self._active_span = parent

    def finalize(self) -> None:
        """Mark the trace as complete."""
        self.ended_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "action_count": len(self.actions),
            "span_count": len(self.spans),
            "actions": [a.model_dump(mode="json") for a in self.actions],
            "metadata": self.metadata,
        }


class Tracer:
    """Factory for creating and managing traces.

    Usage:
        tracer = Tracer(agent_name="my-agent")
        with tracer.trace("task-name") as t:
            t.record_tool_call("bash", {"command": "ls"})
            ...
    """

    def __init__(self, agent_name: str = "unknown"):
        self.agent_name = agent_name
        self.traces: list[Trace] = []

    @contextmanager
    def trace(self, name: str) -> Generator[Trace, None, None]:
        """Start a new trace for an agent task."""
        t = Trace(name=name, agent_name=self.agent_name)
        self.traces.append(t)
        try:
            yield t
        finally:
            t.finalize()

    def get_trace(self, trace_id: str) -> Trace | None:
        """Look up a trace by ID."""
        for t in self.traces:
            if t.id == trace_id:
                return t
        return None
