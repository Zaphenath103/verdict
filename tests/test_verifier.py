"""Tests for the Verdict verifier and checks."""

from verdict.core.tracer import Trace
from verdict.core.types import Category, CheckResult, Severity
from verdict.core.verifier import BaseCheck, Verifier
from verdict.core.scorer import TrustScorer, TrustScore
from verdict.checks.security import SecurityCheck
from verdict.checks.correctness import CorrectnessCheck
from verdict.checks.alignment import AlignmentCheck
from verdict.checks.regression import RegressionCheck


class DummyPassCheck(BaseCheck):
    name = "dummy_pass"
    description = "Always passes"

    def run(self, trace: Trace) -> list[CheckResult]:
        return [CheckResult(
            check_name=self.name,
            category=Category.CUSTOM,
            passed=True,
            severity=Severity.INFO,
            message="All good",
        )]


class DummyFailCheck(BaseCheck):
    name = "dummy_fail"
    description = "Always fails"

    def run(self, trace: Trace) -> list[CheckResult]:
        return [CheckResult(
            check_name=self.name,
            category=Category.SECURITY,
            passed=False,
            severity=Severity.HIGH,
            message="Something bad",
        )]


class TestVerifier:
    def test_verify_empty_trace(self):
        v = Verifier()
        v.add_check(DummyPassCheck())
        t = Trace(name="empty")
        report = v.verify(t)
        assert report.trust_score > 0
        assert report.checks_passed >= 1

    def test_verify_with_failure(self):
        v = Verifier()
        v.add_check(DummyFailCheck())
        t = Trace(name="test")
        report = v.verify(t)
        assert report.checks_failed >= 1
        assert report.trust_score < 100

    def test_verify_mixed(self):
        v = Verifier()
        v.add_check(DummyPassCheck())
        v.add_check(DummyFailCheck())
        t = Trace(name="test")
        report = v.verify(t)
        assert report.checks_passed >= 1
        assert report.checks_failed >= 1

    def test_duplicate_check_raises(self):
        v = Verifier()
        v.add_check(DummyPassCheck())
        try:
            v.add_check(DummyPassCheck())
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestScorer:
    def test_perfect_score(self):
        scorer = TrustScorer()
        results = [CheckResult(
            check_name="test",
            category=Category.CUSTOM,
            passed=True,
            severity=Severity.INFO,
            message="ok",
        )]
        score = scorer.score(results)
        assert score.score >= 100.0
        assert score.grade == "A+"

    def test_critical_blocks(self):
        scorer = TrustScorer(block_on_critical=True)
        results = [CheckResult(
            check_name="test",
            category=Category.SECURITY,
            passed=False,
            severity=Severity.CRITICAL,
            message="critical issue",
        )]
        score = scorer.score(results)
        assert score.score == 0.0
        assert score.grade == "F"

    def test_empty_results(self):
        scorer = TrustScorer()
        score = scorer.score([])
        assert score.score == 100.0

    def test_severity_weighting(self):
        scorer = TrustScorer(block_on_critical=False)
        high_result = [CheckResult(
            check_name="high",
            category=Category.SECURITY,
            passed=False,
            severity=Severity.HIGH,
            message="high issue",
        )]
        low_result = [CheckResult(
            check_name="low",
            category=Category.CUSTOM,
            passed=False,
            severity=Severity.LOW,
            message="low issue",
        )]
        high_score = scorer.score(high_result)
        low_score = scorer.score(low_result)
        assert low_score.score > high_score.score


class TestSecurityCheck:
    def test_dangerous_command(self):
        check = SecurityCheck()
        t = Trace(name="test")
        t.record_shell_exec("rm -rf /", exit_code=0)
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0
        assert any(r.severity == Severity.CRITICAL for r in failed)

    def test_api_key_detection(self):
        check = SecurityCheck()
        t = Trace(name="test")
        t.record_tool_call("bash", {"command": "echo sk-proj-abcdef1234567890abcdefghijklmnop"})
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0

    def test_clean_trace(self):
        check = SecurityCheck()
        t = Trace(name="test")
        t.record_shell_exec("npm run build", output="ok", exit_code=0)
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0


class TestCorrectnessCheck:
    def test_tool_error(self):
        check = CorrectnessCheck()
        t = Trace(name="test")
        call_id = t.record_tool_call("bash", {"command": "bad command"})
        tc_id = t.actions[0].tool_call.id
        t.record_tool_result(tc_id, error="command not found")
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0

    def test_nonzero_exit(self):
        check = CorrectnessCheck()
        t = Trace(name="test")
        t.record_shell_exec("false", output="", exit_code=1)
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0

    def test_http_500(self):
        check = CorrectnessCheck()
        t = Trace(name="test")
        t.record_http_request("GET", "https://api.example.com", status_code=500)
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0


class TestAlignmentCheck:
    def test_tool_scope_violation(self):
        check = AlignmentCheck(allowed_tools=["read_file", "write_file"])
        t = Trace(name="test")
        t.record_tool_call("bash", {"command": "rm -rf ."})
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0

    def test_within_scope(self):
        check = AlignmentCheck(allowed_tools=["bash", "read_file"])
        t = Trace(name="test")
        t.record_tool_call("bash", {"command": "ls"})
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) == 0

    def test_action_budget_exceeded(self):
        check = AlignmentCheck(max_actions=5)
        t = Trace(name="test")
        for i in range(10):
            t.record_tool_call("bash", {"command": f"echo {i}"})
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0


class TestRegressionCheck:
    def test_no_baseline(self):
        check = RegressionCheck()
        t = Trace(name="test")
        results = check.run(t)
        assert all(r.passed for r in results)

    def test_new_error(self):
        baseline = Trace(name="baseline")
        baseline.record_tool_call("bash", {"command": "ls"})
        tc_id = baseline.actions[0].tool_call.id
        baseline.record_tool_result(tc_id, output="ok")
        baseline.finalize()

        check = RegressionCheck(baseline=baseline)
        t = Trace(name="current")
        t.record_tool_call("bash", {"command": "ls"})
        tc_id2 = t.actions[0].tool_call.id
        t.record_tool_result(tc_id2, error="permission denied")
        results = check.run(t)
        failed = [r for r in results if not r.passed]
        assert len(failed) > 0
