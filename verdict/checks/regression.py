"""Regression verification checks.

Compares current trace against a baseline to detect behavioral regressions:
- New errors that didn't exist in baseline
- Increased action count (agent taking more steps)
- New tool usage (agent using tools it didn't before)
- Performance degradation
- Changed output patterns
"""

from __future__ import annotations

from verdict.core.tracer import Trace
from verdict.core.types import ActionType, Category, CheckResult, Severity
from verdict.core.verifier import BaseCheck


class RegressionCheck(BaseCheck):
    """Detects behavioral regressions by comparing against a baseline trace.

    Checks for:
    - New errors not present in baseline
    - Significant increase in action count
    - New tools used that weren't in baseline
    - Performance degradation (increased duration)
    """

    name = "regression"
    description = "Detects behavioral regressions against a baseline trace"
    category = Category.REGRESSION

    def __init__(
        self,
        baseline: Trace | None = None,
        action_count_threshold: float = 1.5,
        duration_threshold: float = 2.0,
    ):
        self.baseline = baseline
        self.action_count_threshold = action_count_threshold
        self.duration_threshold = duration_threshold

    def run(self, trace: Trace) -> list[CheckResult]:
        if self.baseline is None:
            return [CheckResult(
                check_name=self.name,
                category=self.category,
                passed=True,
                severity=Severity.INFO,
                message="No baseline provided — regression check skipped",
            )]

        results: list[CheckResult] = []

        results.extend(self._check_new_errors(trace))
        results.extend(self._check_action_count(trace))
        results.extend(self._check_new_tools(trace))
        results.extend(self._check_duration(trace))

        if not results:
            results.append(CheckResult(
                check_name=self.name,
                category=self.category,
                passed=True,
                severity=Severity.INFO,
                message="No regressions detected against baseline",
            ))

        return results

    def _check_new_errors(self, trace: Trace) -> list[CheckResult]:
        """Detect errors that weren't in the baseline."""
        assert self.baseline is not None
        results = []

        baseline_errors = {
            a.tool_result.error
            for a in self.baseline.actions
            if a.action_type == ActionType.TOOL_RESULT
            and a.tool_result
            and a.tool_result.error
        }

        for action in trace.actions:
            if (action.action_type == ActionType.TOOL_RESULT
                    and action.tool_result
                    and action.tool_result.error
                    and action.tool_result.error not in baseline_errors):
                results.append(CheckResult(
                    check_name=f"{self.name}/new_error",
                    category=self.category,
                    passed=False,
                    severity=Severity.HIGH,
                    message=f"New error not in baseline: {action.tool_result.error[:100]}",
                    details={"error": action.tool_result.error},
                    affected_actions=[action.id],
                    suggestion="This error is new — investigate the cause",
                ))

        return results

    def _check_action_count(self, trace: Trace) -> list[CheckResult]:
        """Check if action count increased significantly."""
        assert self.baseline is not None
        results = []

        baseline_count = len(self.baseline.actions)
        current_count = len(trace.actions)

        if baseline_count > 0:
            ratio = current_count / baseline_count
            if ratio > self.action_count_threshold:
                results.append(CheckResult(
                    check_name=f"{self.name}/action_count",
                    category=self.category,
                    passed=False,
                    severity=Severity.MEDIUM,
                    message=f"Action count increased {ratio:.1f}x ({baseline_count} -> {current_count})",
                    details={
                        "baseline": baseline_count,
                        "current": current_count,
                        "ratio": round(ratio, 2),
                        "threshold": self.action_count_threshold,
                    },
                    suggestion="Agent is taking significantly more steps — may be less efficient",
                ))

        return results

    def _check_new_tools(self, trace: Trace) -> list[CheckResult]:
        """Check if agent is using tools it didn't use in baseline."""
        assert self.baseline is not None
        results = []

        baseline_tools = {
            a.tool_call.name
            for a in self.baseline.actions
            if a.action_type == ActionType.TOOL_CALL and a.tool_call
        }

        current_tools = {
            a.tool_call.name
            for a in trace.actions
            if a.action_type == ActionType.TOOL_CALL and a.tool_call
        }

        new_tools = current_tools - baseline_tools
        if new_tools:
            results.append(CheckResult(
                check_name=f"{self.name}/new_tools",
                category=self.category,
                passed=False,
                severity=Severity.LOW,
                message=f"Agent using new tools not in baseline: {', '.join(sorted(new_tools))}",
                details={
                    "new_tools": sorted(new_tools),
                    "baseline_tools": sorted(baseline_tools),
                },
                suggestion="Review whether new tool usage is intentional",
            ))

        return results

    def _check_duration(self, trace: Trace) -> list[CheckResult]:
        """Check for performance degradation."""
        assert self.baseline is not None
        results = []

        if self.baseline.ended_at and self.baseline.started_at and trace.ended_at and trace.started_at:
            baseline_dur = (self.baseline.ended_at - self.baseline.started_at).total_seconds()
            current_dur = (trace.ended_at - trace.started_at).total_seconds()

            if baseline_dur > 0:
                ratio = current_dur / baseline_dur
                if ratio > self.duration_threshold:
                    results.append(CheckResult(
                        check_name=f"{self.name}/duration",
                        category=self.category,
                        passed=False,
                        severity=Severity.LOW,
                        message=f"Duration increased {ratio:.1f}x ({baseline_dur:.1f}s -> {current_dur:.1f}s)",
                        details={
                            "baseline_seconds": round(baseline_dur, 2),
                            "current_seconds": round(current_dur, 2),
                            "ratio": round(ratio, 2),
                        },
                        suggestion="Agent is running significantly slower",
                    ))

        return results
