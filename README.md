<p align="center">
  <h1 align="center">VERDICT</h1>
  <p align="center"><strong>The verification layer for AI agents.</strong></p>
  <p align="center">Intercept. Verify. Trust-score. Ship with confidence.</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/verdict-ai/"><img src="https://img.shields.io/pypi/v/verdict-ai?color=blue&label=pypi" alt="PyPI"></a>
  <a href="https://pypi.org/project/verdict-ai/"><img src="https://img.shields.io/pypi/pyversions/verdict-ai" alt="Python"></a>
  <a href="https://github.com/zaphenath/verdict/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"></a>
  <a href="https://github.com/zaphenath/verdict/actions"><img src="https://img.shields.io/github/actions/workflow/status/zaphenath/verdict/ci.yml?label=CI" alt="CI"></a>
  <a href="https://verdict.zaphenath.app"><img src="https://img.shields.io/badge/docs-verdict.zaphenath.app-cyan" alt="Docs"></a>
</p>

---

## The Problem

AI agents are shipping code, executing commands, and making decisions in production. **88% of organizations report agent security incidents.** Yet there is no universal way to verify what an agent actually did before it reaches production.

- **Boris Cherny** (Head of Claude Code): *"Verification loops are the single most important thing."*
- **Andrej Karpathy**: *"88% of organizations have reported AI agent security incidents."*
- **Thariq Shihipar** (Anthropic): *"Agent failures are tool-design problems, not model problems."*

**Verdict fills this gap.** It's the CI/CD gate for AI agents.

## What Verdict Does

```
Agent runs task  -->  Verdict traces every action  -->  Checks run  -->  Trust Score  -->  APPROVED / BLOCKED
```

Verdict intercepts every tool call, shell command, file write, and HTTP request your agent makes, runs a battery of verification checks (security, correctness, alignment, regression), and produces a **trust score** that gates deployment.

## Quick Start

```bash
pip install verdict-ai
```

### 1. Trace your agent

```python
from verdict import Tracer, Verifier
from verdict.checks import get_default_checks

tracer = Tracer(agent_name="my-agent")
with tracer.trace("deploy-task") as t:
    t.record_shell_exec("npm run build", output="ok", exit_code=0)
    t.record_shell_exec("npm test", output="42 passed", exit_code=0)
    t.record_file_write("dist/bundle.js")

verifier = Verifier()
for check in get_default_checks():
    verifier.add_check(check)

report = verifier.verify(t)
print(f"Trust Score: {report.trust_score}/100 ({report.trust_grade})")
# Trust Score: 100.0/100 (A+)
```

### 2. Catch dangerous actions

```python
with tracer.trace("risky-task") as t:
    t.record_shell_exec("rm -rf /", exit_code=0)  # CRITICAL
    t.record_tool_call("bash", {"command": "echo sk-proj-abc123..."})  # API key leak

report = verifier.verify(t)
print(f"Trust Score: {report.trust_score}/100 ({report.trust_grade})")
# Trust Score: 0.0/100 (F)
# VERDICT: BLOCKED
```

### 3. CLI usage

```bash
# Verify a trace file
verdict verify trace.json

# CI mode (exits 1 on failure)
verdict verify trace.json --ci --threshold 85

# Run the demo
verdict demo

# Launch the web dashboard
verdict dashboard
```

## Architecture

```
                    +------------------+
                    |   Your Agent     |
                    | (Claude, GPT,    |
                    |  LangChain, etc) |
                    +--------+---------+
                             |
                    +--------v---------+
                    |     TRACER       |  Captures every action:
                    |                  |  tool calls, shell execs,
                    |  trace.record_*  |  file ops, HTTP requests
                    +--------+---------+
                             |
                    +--------v---------+
                    |    VERIFIER      |  Runs all checks:
                    |                  |
                    |  Security        |  - Dangerous commands
                    |  Correctness     |  - Failed operations
                    |  Alignment       |  - Scope violations
                    |  Regression      |  - Behavioral drift
                    +--------+---------+
                             |
                    +--------v---------+
                    |   TRUST SCORER   |  0-100 score + letter grade
                    |                  |  Weighted by severity
                    |  A+ = ship it    |  Critical = instant block
                    |  F  = blocked    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |     REPORT       |  Terminal, JSON, Markdown,
                    |                  |  HTML, or Web Dashboard
                    +------------------+
```

## Built-in Checks

| Check | Category | What it catches |
|-------|----------|----------------|
| **Security** | `security` | Dangerous commands (`rm -rf /`), command injection, SQL injection, API key exposure, path traversal, private key leaks, JWT tokens |
| **Correctness** | `correctness` | Tool errors, non-zero exit codes, HTTP 4xx/5xx, orphaned tool calls, retry storms |
| **Alignment** | `alignment` | Unauthorized tool use, file writes outside scope, data exfiltration patterns, action budget exceeded, excessive side effects |
| **Regression** | `regression` | New errors vs baseline, increased action count, new tool usage, performance degradation |

## Framework Integrations

### Anthropic (Claude)

```python
from verdict.integrations.anthropic import TracedAnthropic

client = TracedAnthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Deploy the app"}],
    tools=[...],
)
report = client.verdict_verify()
```

### OpenAI

```python
from verdict.integrations.openai import TracedOpenAI

client = TracedOpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Deploy the app"}],
    tools=[...],
)
report = client.verdict_verify()
```

### Generic (any agent)

```python
from verdict.integrations.generic import verdict_traced

@verdict_traced("my-agent", auto_verify=True, print_report=True)
def my_agent(trace, task: str):
    trace.record_shell_exec(f"process {task}", output="done", exit_code=0)
    return "completed"

result, report = my_agent("build the app")
```

## Custom Checks

```python
from verdict.core.verifier import BaseCheck
from verdict.core.types import Category, CheckResult, Severity

class NoProdDatabaseCheck(BaseCheck):
    name = "no_prod_database"
    description = "Blocks direct production database access"
    category = Category.SECURITY

    def run(self, trace):
        for action in trace.actions:
            if "prod-db" in str(action.content or ""):
                return [CheckResult(
                    check_name=self.name,
                    category=self.category,
                    passed=False,
                    severity=Severity.CRITICAL,
                    message="Production database access detected",
                )]
        return [CheckResult(
            check_name=self.name,
            category=self.category,
            passed=True,
            severity=Severity.INFO,
            message="No production database access",
        )]

verifier.add_check(NoProdDatabaseCheck())
```

## Trust Scoring

The trust scorer uses a weighted algorithm:

- **Start at 100** (perfect trust)
- **Deduct per failure**, weighted by severity:
  - Critical: -30 pts (or instant 0 if `block_on_critical=True`)
  - High: -18 pts
  - Medium: -8 pts
  - Low: -3 pts
- **Category multipliers**: Security failures weigh 1.5x, correctness 1.2x
- **Coverage bonus**: More checks passing = higher confidence (up to +5)

| Grade | Score | Meaning |
|-------|-------|---------|
| A+ | 97-100 | Pristine. Ship it. |
| A | 90-96 | Excellent. Safe to deploy. |
| B | 80-89 | Good. Minor issues, deployable. |
| C | 70-79 | Concerning. Review before deploying. |
| D | 60-69 | Poor. Significant issues. |
| F | 0-59 | Blocked. Do not deploy. |

## CI/CD Integration

```yaml
# .github/workflows/agent-gate.yml
- name: Verify agent trace
  run: verdict verify trace.json --ci --threshold 85 --json-output
```

```python
# Or in Python:
report = verifier.verify(trace)
if report.trust_score < 85 or report.has_critical():
    sys.exit(1)  # Block deployment
```

## Web Dashboard

```bash
verdict dashboard --port 8741
```

Upload trace files, view reports, monitor trust scores — all in a sleek dark-mode UI.

## Why Verdict?

| Problem | Current State | With Verdict |
|---------|--------------|--------------|
| Agent security | 88% report incidents | Every action checked before deploy |
| Verification | Manual review or nothing | Automated, multi-dimensional checks |
| Trust | "It works on my machine" | Quantified 0-100 trust score |
| Compliance | No audit trail | Full trace of every agent action |
| CI/CD for agents | Doesn't exist | Drop-in gate with exit codes |
| Custom rules | DIY everything | Pluggable check system |

## Roadmap

- [ ] Async streaming verification (real-time checks during execution)
- [ ] Spec-driven verification (YAML spec files defining expected behavior)
- [ ] MCP (Model Context Protocol) integration
- [ ] Agent Capability Heat Maps (Karpathy's "jagged intelligence" visualized)
- [ ] Baseline learning (auto-generate baselines from successful runs)
- [ ] Team dashboards with historical trends
- [ ] PyPI package release
- [ ] VS Code extension

## Contributing

We welcome contributions. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/zaphenath/verdict.git
cd verdict
pip install -e ".[dev]"
pytest tests/ -v
```

## License

Apache 2.0 - See [LICENSE](LICENSE)

---

<p align="center">
  Built by <a href="https://zaphenath.app"><strong>Zaphenath Labs</strong></a><br>
  <sub>The verification layer the AI agent ecosystem has been waiting for.</sub>
</p>
