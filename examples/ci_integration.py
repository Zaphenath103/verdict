"""CI/CD integration example.

Shows how to use Verdict as a gate in your deployment pipeline.
Exit code 1 if the agent trace doesn't meet the threshold.
"""

import json
import sys

from verdict import Tracer, Verifier
from verdict.checks import get_default_checks
from verdict.core.scorer import TrustScorer


DEPLOY_THRESHOLD = 85.0


def simulate_agent_run() -> dict:
    """Simulate an agent run and return the trace data."""
    tracer = Tracer(agent_name="deploy-agent")

    with tracer.trace("production-deploy") as t:
        t.record_file_read("config/production.yml")
        t.record_shell_exec("docker build -t app:latest .", output="Built", exit_code=0)
        t.record_shell_exec("docker push app:latest", output="Pushed", exit_code=0)
        t.record_shell_exec(
            "kubectl apply -f k8s/deployment.yml",
            output="deployment.apps/app configured",
            exit_code=0,
        )
        t.record_http_request(
            "GET", "https://app.example.com/health", status_code=200
        )

    return t.to_dict(), t


def main():
    print("=== Verdict CI/CD Gate ===\n")

    trace_data, trace = simulate_agent_run()

    # Save trace for audit
    with open("trace.json", "w") as f:
        json.dump(trace_data, f, indent=2, default=str)
    print("Trace saved to trace.json")

    # Verify with custom threshold
    verifier = Verifier(scorer=TrustScorer(deploy_threshold=DEPLOY_THRESHOLD))
    for check in get_default_checks():
        verifier.add_check(check)

    report = verifier.verify(trace)

    print(f"Trust Score: {report.trust_score}/100 ({report.trust_grade})")
    print(f"Checks: {report.checks_passed}/{report.total_checks} passed")
    print(f"Threshold: {DEPLOY_THRESHOLD}")

    if report.trust_score >= DEPLOY_THRESHOLD and not report.has_critical():
        print("\nVERDICT: APPROVED - Proceeding with deployment")
        sys.exit(0)
    else:
        print("\nVERDICT: BLOCKED - Deployment halted")
        for f in report.critical_findings:
            print(f"  CRITICAL: {f.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
