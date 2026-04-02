"""Verdict — The verification layer for AI agents."""

__version__ = "0.1.0"

from verdict.core.tracer import Tracer, Trace, Span
from verdict.core.verifier import Verifier, VerificationResult
from verdict.core.scorer import TrustScorer, TrustScore
from verdict.core.types import (
    AgentAction,
    ToolCall,
    ToolResult,
    Severity,
    CheckResult,
    VerdictReport,
)

__all__ = [
    "Tracer",
    "Trace",
    "Span",
    "Verifier",
    "VerificationResult",
    "TrustScorer",
    "TrustScore",
    "AgentAction",
    "ToolCall",
    "ToolResult",
    "Severity",
    "CheckResult",
    "VerdictReport",
]
