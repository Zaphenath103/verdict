"""Basic Verdict verification example.

Shows how to trace an agent's actions and verify them.
"""

from verdict import Tracer, Verifier
from verdict.checks import get_default_checks
from verdict.core.reporter import Reporter


def main():
    # 1. Create a tracer for your agent
    tracer = Tracer(agent_name="my-coding-agent")

    # 2. Record agent actions within a trace
    with tracer.trace("deploy-task") as t:
        # Agent reads a file
        t.record_file_read("src/app.py")

        # Agent runs a build command
        t.record_shell_exec("npm run build", output="Build succeeded", exit_code=0)

        # Agent runs tests
        t.record_shell_exec("npm test", output="42 tests passed", exit_code=0)

        # Agent writes output
        t.record_file_write("dist/bundle.js", content="(function(){...})")

        # Agent makes an API call
        t.record_http_request("POST", "https://api.deploy.com/v1/deploy", status_code=200)

    # 3. Build a verifier with default checks
    verifier = Verifier()
    for check in get_default_checks():
        verifier.add_check(check)

    # 4. Verify the trace
    report = verifier.verify(t)

    # 5. Output the report
    print(Reporter.to_terminal(report))
    print(f"\nTrust Score: {report.trust_score}/100 ({report.trust_grade})")
    print(f"Deployable: {report.trust_score >= 80 and not report.has_critical()}")


if __name__ == "__main__":
    main()
