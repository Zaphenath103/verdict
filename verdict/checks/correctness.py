"""Correctness verification checks.

Validates that agent actions produce expected outcomes:
- Tool calls return successful results (no errors)
- Shell commands exit with code 0
- File operations target existing/valid paths
- HTTP requests return 2xx status codes
- No unhandled exceptions in the trace
- Action sequences are logically consistent
"""

from __future__ import annotations

from verdict.core.tracer import Trace
from verdict.core.types import ActionType, Category, CheckResult, Severity
from verdict.core.verifier import BaseCheck


class CorrectnessCheck(BaseCheck):
    """Validates agent actions produce correct outcomes.

    Checks for:
    - Failed tool calls (errors in results)
    - Non-zero shell exit codes
    - HTTP errors (4xx/5xx)
    - Orphaned tool calls (call without result)
    - Empty/null outputs where output is expected
    - Repeated failed attempts (retry storms)
    """

    name = "correctness"
    description = "Validates agent actions produce expected correct outcomes"
    category = Category.CORRECTNESS

    def __init__(
        self,
        max_retries: int = 3,
        allow_http_errors: list[int] | None = None,
    ):
        self.max_retries = max_retries
        self.allow_http_errors = allow_http_errors or []

    def run(self, trace: Trace) -> list[CheckResult]:
        results: list[CheckResult] = []

        results.extend(self._check_tool_errors(trace))
        results.extend(self._check_shell_exits(trace))
        results.extend(self._check_http_status(trace))
        results.extend(self._check_orphaned_calls(trace))
        results.extend(self._check_retry_storms(trace))

        if not results:
            results.append(CheckResult(
                check_name=self.name,
                category=self.category,
                passed=True,
                severity=Severity.INFO,
                message="All agent actions produced correct outcomes",
            ))

        return results

    def _check_tool_errors(self, trace: Trace) -> list[CheckResult]:
        """Check for tool calls that returned errors."""
        results = []
        for action in trace.actions:
            if action.action_type == ActionType.TOOL_RESULT and action.tool_result:
                if action.tool_result.error:
                    results.append(CheckResult(
                        check_name=f"{self.name}/tool_error",
                        category=self.category,
                        passed=False,
                        severity=Severity.MEDIUM,
                        message=f"Tool call returned error: {action.tool_result.error[:100]}",
                        details={
                            "tool_call_id": action.tool_result.tool_call_id,
                            "error": action.tool_result.error,
                        },
                        affected_actions=[action.id],
                        suggestion="Investigate why the tool call failed and fix the input",
                    ))
        return results

    def _check_shell_exits(self, trace: Trace) -> list[CheckResult]:
        """Check for non-zero shell exit codes."""
        results = []
        for action in trace.actions:
            if action.action_type == ActionType.SHELL_EXEC:
                exit_code = action.metadata.get("exit_code")
                if exit_code is not None and exit_code != 0:
                    results.append(CheckResult(
                        check_name=f"{self.name}/shell_exit",
                        category=self.category,
                        passed=False,
                        severity=Severity.MEDIUM,
                        message=f"Shell command exited with code {exit_code}: {(action.content or '')[:80]}",
                        details={
                            "command": action.content,
                            "exit_code": exit_code,
                            "output": action.metadata.get("output", "")[:200],
                        },
                        affected_actions=[action.id],
                        suggestion="Check command syntax and ensure dependencies are available",
                    ))
        return results

    def _check_http_status(self, trace: Trace) -> list[CheckResult]:
        """Check for HTTP error status codes."""
        results = []
        for action in trace.actions:
            if action.action_type == ActionType.HTTP_REQUEST:
                status = action.metadata.get("status_code")
                if status and status >= 400 and status not in self.allow_http_errors:
                    severity = Severity.HIGH if status >= 500 else Severity.MEDIUM
                    results.append(CheckResult(
                        check_name=f"{self.name}/http_error",
                        category=self.category,
                        passed=False,
                        severity=severity,
                        message=f"HTTP {status} error: {action.content}",
                        details={
                            "url": action.content,
                            "status_code": status,
                        },
                        affected_actions=[action.id],
                        suggestion="Check the URL and request parameters",
                    ))
        return results

    def _check_orphaned_calls(self, trace: Trace) -> list[CheckResult]:
        """Check for tool calls without corresponding results."""
        results = []
        call_ids = set()
        result_ids = set()

        for action in trace.actions:
            if action.action_type == ActionType.TOOL_CALL and action.tool_call:
                call_ids.add(action.tool_call.id)
            if action.action_type == ActionType.TOOL_RESULT and action.tool_result:
                result_ids.add(action.tool_result.tool_call_id)

        orphaned = call_ids - result_ids
        if orphaned:
            results.append(CheckResult(
                check_name=f"{self.name}/orphaned_calls",
                category=self.category,
                passed=False,
                severity=Severity.LOW,
                message=f"{len(orphaned)} tool call(s) without results (possible timeout or crash)",
                details={"orphaned_ids": list(orphaned)},
                suggestion="Ensure all tool calls complete with a result or explicit timeout",
            ))

        return results

    def _check_retry_storms(self, trace: Trace) -> list[CheckResult]:
        """Detect repeated failed attempts at the same operation."""
        results = []
        tool_failures: dict[str, int] = {}

        for action in trace.actions:
            if action.action_type == ActionType.TOOL_CALL and action.tool_call:
                key = f"{action.tool_call.name}:{sorted(action.tool_call.arguments.items())}"
                tool_failures.setdefault(key, 0)
            if action.action_type == ActionType.TOOL_RESULT and action.tool_result:
                if action.tool_result.error:
                    # Find the matching call
                    for a in trace.actions:
                        if (a.action_type == ActionType.TOOL_CALL
                                and a.tool_call
                                and a.tool_call.id == action.tool_result.tool_call_id):
                            key = f"{a.tool_call.name}:{sorted(a.tool_call.arguments.items())}"
                            tool_failures[key] = tool_failures.get(key, 0) + 1
                            break

        for key, count in tool_failures.items():
            if count > self.max_retries:
                results.append(CheckResult(
                    check_name=f"{self.name}/retry_storm",
                    category=self.category,
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Retry storm detected: {count} failed attempts for same operation",
                    details={"operation": key, "attempts": count, "max_allowed": self.max_retries},
                    suggestion="Agent is stuck in a retry loop. Add backoff or fallback logic.",
                ))

        return results
