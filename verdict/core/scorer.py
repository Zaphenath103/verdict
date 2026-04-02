"""TrustScorer — produces a trust score and grade for an agent trace.

The scoring algorithm is weighted by severity and category, producing a
0-100 score and letter grade (A+ through F). Scores below configurable
thresholds can gate deployment in CI/CD pipelines.

Algorithm:
    1. Start at 100 (perfect trust)
    2. Deduct points per failed check, weighted by severity
    3. Apply category multipliers (security failures weight more)
    4. Bonus for comprehensive coverage (more checks = more confidence)
    5. Floor at 0
"""

from __future__ import annotations

from dataclasses import dataclass, field

from verdict.core.types import Category, CheckResult, Severity


# Severity deduction weights (how many points lost per failure)
SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 30.0,
    Severity.HIGH: 18.0,
    Severity.MEDIUM: 8.0,
    Severity.LOW: 3.0,
    Severity.INFO: 0.5,
}

# Category multipliers (security failures are weighted heavier)
CATEGORY_MULTIPLIERS: dict[Category, float] = {
    Category.SECURITY: 1.5,
    Category.CORRECTNESS: 1.2,
    Category.ALIGNMENT: 1.1,
    Category.REGRESSION: 1.0,
    Category.PERFORMANCE: 0.8,
    Category.CUSTOM: 1.0,
}

# Grade thresholds
GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (97, "A+"),
    (93, "A"),
    (90, "A-"),
    (87, "B+"),
    (83, "B"),
    (80, "B-"),
    (77, "C+"),
    (73, "C"),
    (70, "C-"),
    (67, "D+"),
    (63, "D"),
    (60, "D-"),
    (0, "F"),
]


@dataclass
class TrustScore:
    """A computed trust score with breakdown."""

    score: float
    grade: str
    total_checks: int
    passed: int
    failed: int
    deductions: list[dict[str, float]] = field(default_factory=list)
    coverage_bonus: float = 0.0

    @property
    def is_passing(self) -> bool:
        return self.score >= 70.0

    @property
    def is_deployable(self) -> bool:
        return self.score >= 80.0 and self.failed == 0


class TrustScorer:
    """Computes trust scores from verification check results.

    Configurable thresholds:
        deploy_threshold: minimum score to allow deployment (default 80)
        block_on_critical: if True, any critical finding = score 0 (default True)
    """

    def __init__(
        self,
        deploy_threshold: float = 80.0,
        block_on_critical: bool = True,
        severity_weights: dict[Severity, float] | None = None,
        category_multipliers: dict[Category, float] | None = None,
    ):
        self.deploy_threshold = deploy_threshold
        self.block_on_critical = block_on_critical
        self.severity_weights = severity_weights or SEVERITY_WEIGHTS.copy()
        self.category_multipliers = category_multipliers or CATEGORY_MULTIPLIERS.copy()

    def score(self, results: list[CheckResult]) -> TrustScore:
        """Compute a trust score from verification results."""
        if not results:
            return TrustScore(
                score=100.0,
                grade="A+",
                total_checks=0,
                passed=0,
                failed=0,
            )

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed]
        has_critical = any(r.severity == Severity.CRITICAL for r in failed)

        # If blocking on critical and we have one, score is 0
        if self.block_on_critical and has_critical:
            return TrustScore(
                score=0.0,
                grade="F",
                total_checks=len(results),
                passed=len(passed),
                failed=len(failed),
                deductions=[
                    {
                        "check": r.check_name,
                        "severity": r.severity.value,
                        "category": r.category.value,
                        "points": 100.0,
                    }
                    for r in failed
                    if r.severity == Severity.CRITICAL
                ],
            )

        # Calculate deductions
        base_score = 100.0
        deductions: list[dict[str, float]] = []

        for r in failed:
            weight = self.severity_weights.get(r.severity, 5.0)
            multiplier = self.category_multipliers.get(r.category, 1.0)
            deduction = weight * multiplier
            deductions.append({
                "check": r.check_name,
                "severity": r.severity.value,
                "category": r.category.value,
                "points": round(deduction, 2),
            })
            base_score -= deduction

        # Coverage bonus: more checks = higher confidence (up to +5)
        coverage_bonus = min(5.0, len(results) * 0.25)
        if len(failed) == 0:
            base_score += coverage_bonus

        final_score = max(0.0, min(100.0, base_score))
        grade = self._compute_grade(final_score)

        return TrustScore(
            score=round(final_score, 2),
            grade=grade,
            total_checks=len(results),
            passed=len(passed),
            failed=len(failed),
            deductions=deductions,
            coverage_bonus=coverage_bonus if len(failed) == 0 else 0.0,
        )

    @staticmethod
    def _compute_grade(score: float) -> str:
        for threshold, grade in GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "F"
