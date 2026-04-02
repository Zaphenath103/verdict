"""Core type definitions for the Verdict verification engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for verification findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Categories of verification checks."""

    SECURITY = "security"
    CORRECTNESS = "correctness"
    ALIGNMENT = "alignment"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


class ActionType(str, Enum):
    """Types of agent actions."""

    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    DECISION = "decision"
    FILE_WRITE = "file_write"
    FILE_READ = "file_read"
    SHELL_EXEC = "shell_exec"
    HTTP_REQUEST = "http_request"
    MESSAGE_SEND = "message_send"


class ToolCall(BaseModel):
    """Represents a single tool invocation by an agent."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolResult(BaseModel):
    """Represents the result of a tool invocation."""

    tool_call_id: str
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentAction(BaseModel):
    """A single action taken by an agent during execution."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_type: ActionType
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_id: str | None = None


class CheckResult(BaseModel):
    """Result of running a single verification check."""

    check_name: str
    category: Category
    passed: bool
    severity: Severity = Severity.INFO
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    affected_actions: list[str] = Field(default_factory=list)
    suggestion: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerdictReport(BaseModel):
    """Complete verification report for an agent trace."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str
    agent_name: str = "unknown"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_actions: int = 0
    total_checks: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    trust_score: float = 0.0
    trust_grade: str = "F"
    results: list[CheckResult] = Field(default_factory=list)
    critical_findings: list[CheckResult] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.checks_passed / self.total_checks

    def has_critical(self) -> bool:
        return len(self.critical_findings) > 0

    def has_failures(self) -> bool:
        return self.checks_failed > 0
