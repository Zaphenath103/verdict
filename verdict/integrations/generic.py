"""Generic integration — wraps any agent with Verdict tracing.

Works with any Python function or class. No framework dependency.

Usage:
    @verdict_traced("my-agent")
    def my_agent(task: str):
        # your agent logic
        return result

    # Or use the wrapper class:
    wrapper = VerdictWrapper("my-agent")
    with wrapper.trace("task-name") as ctx:
        ctx.record_tool_call("bash", {"command": "ls"})
        ctx.record_tool_result(ctx.last_action_id, output="file.txt")
    report = wrapper.verify()
"""

from __future__ import annotations

import functools
from typing import Any, Callable

from verdict.checks.registry import get_default_checks
from verdict.core.reporter import Reporter
from verdict.core.tracer import Trace, Tracer
from verdict.core.types import VerdictReport
from verdict.core.verifier import Verifier


class VerdictWrapper:
    """Wraps any agent with Verdict tracing and verification.

    Provides a simple API for recording agent actions and running
    verification at the end.
    """

    def __init__(
        self,
        agent_name: str = "unknown",
        verifier: Verifier | None = None,
        auto_register_defaults: bool = True,
    ):
        self.tracer = Tracer(agent_name=agent_name)
        self.verifier = verifier or Verifier()
        self._last_trace: Trace | None = None

        if auto_register_defaults and self.verifier.check_count == 0:
            for check in get_default_checks():
                self.verifier.add_check(check)

    def trace(self, name: str):
        """Start a new trace (use as context manager)."""
        return self.tracer.trace(name)

    def verify(self, trace: Trace | None = None) -> VerdictReport:
        """Run verification on the most recent trace (or a specific one)."""
        target = trace or self._last_trace
        if target is None and self.tracer.traces:
            target = self.tracer.traces[-1]
        if target is None:
            raise ValueError("No trace to verify")
        return self.verifier.verify(target)

    def verify_and_print(self, trace: Trace | None = None) -> VerdictReport:
        """Verify and print the report to terminal."""
        report = self.verify(trace)
        print(Reporter.to_terminal(report))
        return report


def verdict_traced(
    agent_name: str = "unknown",
    auto_verify: bool = True,
    print_report: bool = False,
) -> Callable:
    """Decorator that wraps a function with Verdict tracing.

    The decorated function receives a Trace object as its first argument.
    After execution, verification runs automatically.

    Usage:
        @verdict_traced("my-agent")
        def process_task(trace: Trace, task: str):
            trace.record_tool_call("bash", {"command": f"process {task}"})
            trace.record_tool_result(trace.last_action_id, output="done")
            return "completed"

        result, report = process_task("build the app")
    """

    def decorator(func: Callable) -> Callable:
        wrapper = VerdictWrapper(agent_name=agent_name)

        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> tuple[Any, VerdictReport | None]:
            with wrapper.trace(func.__name__) as t:
                result = func(t, *args, **kwargs)

            report = None
            if auto_verify:
                report = wrapper.verify(t)
                if print_report:
                    print(Reporter.to_terminal(report))

            return result, report

        wrapped.wrapper = wrapper  # type: ignore[attr-defined]
        return wrapped

    return decorator
