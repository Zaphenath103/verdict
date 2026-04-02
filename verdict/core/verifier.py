"""Verifier — the central orchestrator that runs checks against a trace.

The Verifier loads a set of checks (built-in + custom), runs them all
against a trace, collects results, computes a trust score, and produces
a VerdictReport.

Usage:
    verifier = Verifier()
    verifier.add_check(SecurityCheck())
    verifier.add_check(CorrectnessCheck())
    report = verifier.verify(trace)
    if report.trust_score < 80:
        print("BLOCKED: Trust score too low for deployment")
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from verdict.core.scorer import TrustScorer
from verdict.core.tracer import Trace
from verdict.core.types import (
    CheckResult,
    Severity,
    VerdictReport,
)


class BaseCheck(ABC):
    """Abstract base class for all verification checks.

    Implement `run()` to define custom verification logic.
    Each check receives the full trace and returns a list of CheckResults.
    """

    name: str = "unnamed_check"
    description: str = ""

    @abstractmethod
    def run(self, trace: Trace) -> list[CheckResult]:
        """Run this check against a trace. Return findings."""
        ...


class AsyncBaseCheck(ABC):
    """Async version of BaseCheck for checks that need I/O."""

    name: str = "unnamed_async_check"
    description: str = ""

    @abstractmethod
    async def run(self, trace: Trace) -> list[CheckResult]:
        """Run this check asynchronously."""
        ...


class VerificationResult:
    """Container for verification results before report generation."""

    def __init__(self, results: list[CheckResult], trace: Trace):
        self.results = results
        self.trace = trace
        self.passed = [r for r in results if r.passed]
        self.failed = [r for r in results if not r.passed]
        self.critical = [r for r in self.failed if r.severity == Severity.CRITICAL]
        self.high = [r for r in self.failed if r.severity == Severity.HIGH]

    @property
    def is_clean(self) -> bool:
        return len(self.failed) == 0

    @property
    def has_blockers(self) -> bool:
        return len(self.critical) > 0


class Verifier:
    """Central verification orchestrator.

    Registers checks, runs them against traces, and produces reports.
    """

    def __init__(
        self,
        scorer: TrustScorer | None = None,
        fail_fast: bool = False,
    ):
        self.scorer = scorer or TrustScorer()
        self.fail_fast = fail_fast
        self._sync_checks: list[BaseCheck] = []
        self._async_checks: list[AsyncBaseCheck] = []
        self._check_names: set[str] = set()

    def add_check(self, check: BaseCheck | AsyncBaseCheck) -> None:
        """Register a verification check."""
        name = check.name
        if name in self._check_names:
            raise ValueError(f"Check '{name}' is already registered")
        self._check_names.add(name)
        if isinstance(check, AsyncBaseCheck):
            self._async_checks.append(check)
        else:
            self._sync_checks.append(check)

    def add_checks(self, *checks: BaseCheck | AsyncBaseCheck) -> None:
        """Register multiple checks at once."""
        for check in checks:
            self.add_check(check)

    @property
    def check_count(self) -> int:
        return len(self._sync_checks) + len(self._async_checks)

    def verify(self, trace: Trace) -> VerdictReport:
        """Run all registered checks against a trace and produce a report.

        For async checks, runs them in an event loop.
        """
        all_results: list[CheckResult] = []

        # Run sync checks
        for check in self._sync_checks:
            try:
                results = check.run(trace)
                all_results.extend(results)
                if self.fail_fast and any(not r.passed for r in results):
                    break
            except Exception as exc:
                all_results.append(CheckResult(
                    check_name=check.name,
                    category=getattr(check, "category", __import__("verdict.core.types", fromlist=["Category"]).Category.CUSTOM),
                    passed=False,
                    severity=Severity.HIGH,
                    message=f"Check raised exception: {exc}",
                    details={"exception": str(exc), "type": type(exc).__name__},
                ))

        # Run async checks if any
        if self._async_checks and not self.fail_fast:
            async_results = self._run_async_checks(trace)
            all_results.extend(async_results)

        # Compute trust score
        trust = self.scorer.score(all_results)

        # Build report
        critical_findings = [
            r for r in all_results
            if not r.passed and r.severity in (Severity.CRITICAL, Severity.HIGH)
        ]

        report = VerdictReport(
            trace_id=trace.id,
            agent_name=trace.agent_name,
            started_at=trace.started_at,
            completed_at=datetime.now(timezone.utc),
            total_actions=len(trace.actions),
            total_checks=trust.total_checks,
            checks_passed=trust.passed,
            checks_failed=trust.failed,
            trust_score=trust.score,
            trust_grade=trust.grade,
            results=all_results,
            critical_findings=critical_findings,
            summary=self._generate_summary(trust, critical_findings),
        )

        return report

    def _run_async_checks(self, trace: Trace) -> list[CheckResult]:
        """Run async checks in an event loop."""
        results: list[CheckResult] = []

        async def _gather() -> list[CheckResult]:
            tasks = [check.run(trace) for check in self._async_checks]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(gathered):
                if isinstance(result, Exception):
                    results.append(CheckResult(
                        check_name=self._async_checks[i].name,
                        category=getattr(self._async_checks[i], "category", __import__("verdict.core.types", fromlist=["Category"]).Category.CUSTOM),
                        passed=False,
                        severity=Severity.HIGH,
                        message=f"Async check raised exception: {result}",
                    ))
                else:
                    results.extend(result)
            return results

        try:
            loop = asyncio.get_running_loop()
            # Already in an async context — use nest_asyncio pattern
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _gather())
                return future.result()
        except RuntimeError:
            return asyncio.run(_gather())

    @staticmethod
    def _generate_summary(trust: Any, critical_findings: list[CheckResult]) -> str:
        """Generate a human-readable summary."""
        parts = [f"Trust Score: {trust.score}/100 (Grade: {trust.grade})"]
        parts.append(f"Checks: {trust.passed} passed, {trust.failed} failed of {trust.total_checks} total")

        if critical_findings:
            parts.append(f"CRITICAL: {len(critical_findings)} blocking finding(s):")
            for f in critical_findings[:3]:
                parts.append(f"  - [{f.severity.value.upper()}] {f.check_name}: {f.message}")
        elif trust.failed > 0:
            parts.append("No critical findings, but some checks failed.")
        else:
            parts.append("All checks passed.")

        if trust.is_deployable:
            parts.append("VERDICT: APPROVED for deployment.")
        else:
            parts.append("VERDICT: BLOCKED — does not meet deployment threshold.")

        return "\n".join(parts)
