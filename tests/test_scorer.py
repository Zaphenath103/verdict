"""Tests for the trust scorer."""

from verdict.core.scorer import TrustScorer
from verdict.core.types import Category, CheckResult, Severity


class TestTrustScorer:
    def test_all_passing(self):
        scorer = TrustScorer()
        results = [
            CheckResult(check_name="a", category=Category.SECURITY, passed=True, severity=Severity.INFO, message="ok"),
            CheckResult(check_name="b", category=Category.CORRECTNESS, passed=True, severity=Severity.INFO, message="ok"),
            CheckResult(check_name="c", category=Category.ALIGNMENT, passed=True, severity=Severity.INFO, message="ok"),
        ]
        score = scorer.score(results)
        assert score.score >= 100.0
        assert score.grade == "A+"
        assert score.is_passing
        assert score.is_deployable

    def test_critical_failure_blocks(self):
        scorer = TrustScorer(block_on_critical=True)
        results = [
            CheckResult(check_name="a", category=Category.SECURITY, passed=True, severity=Severity.INFO, message="ok"),
            CheckResult(check_name="b", category=Category.SECURITY, passed=False, severity=Severity.CRITICAL, message="bad"),
        ]
        score = scorer.score(results)
        assert score.score == 0.0
        assert score.grade == "F"
        assert not score.is_passing
        assert not score.is_deployable

    def test_medium_deduction(self):
        scorer = TrustScorer()
        results = [
            CheckResult(check_name="a", category=Category.CORRECTNESS, passed=False, severity=Severity.MEDIUM, message="warning"),
        ]
        score = scorer.score(results)
        assert 80 < score.score < 100

    def test_multiple_failures(self):
        scorer = TrustScorer(block_on_critical=False)
        results = [
            CheckResult(check_name="a", category=Category.SECURITY, passed=False, severity=Severity.HIGH, message="bad"),
            CheckResult(check_name="b", category=Category.CORRECTNESS, passed=False, severity=Severity.HIGH, message="bad"),
            CheckResult(check_name="c", category=Category.ALIGNMENT, passed=False, severity=Severity.MEDIUM, message="meh"),
        ]
        score = scorer.score(results)
        assert score.score < 70
        assert score.failed == 3

    def test_grade_thresholds(self):
        scorer = TrustScorer()
        # Test grade boundaries
        assert scorer._compute_grade(97) == "A+"
        assert scorer._compute_grade(93) == "A"
        assert scorer._compute_grade(83) == "B"
        assert scorer._compute_grade(73) == "C"
        assert scorer._compute_grade(50) == "F"
