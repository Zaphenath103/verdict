# VERDICT — Lead Dev Onboarding & Next Moves Brief

## Welcome, Lead Dev

You have been selected because you demonstrated the ability to ship working code
into this repo with no human intervention. This document is your operating manual.

---

## Your Authority

As Lead Dev, you can:
- Ship patch releases (0.1.x) autonomously
- Merge PRs that pass the full test suite
- Create GitHub Issues and assign them
- Make architectural decisions for components you own
- Publish weekly briefs to the Telegram channel

You cannot (without CEO approval):
- Change the trust scoring algorithm
- Remove or weaken security checks
- Ship minor/major releases
- Publish to PyPI
- Modify brand/pricing/licensing

---

## Architecture Quick Reference

```
verdict/
  core/           # Engine (DO NOT break these interfaces)
    types.py      # Pydantic models — the contract
    tracer.py     # Action capture — the foundation
    verifier.py   # Check orchestrator — the brain
    scorer.py     # Trust scoring — the judge
    reporter.py   # Output formatting — the voice
  checks/         # Verification checks (EXTEND these)
    security.py   # Dangerous patterns
    correctness.py # Outcome validation
    alignment.py  # Intent matching
    regression.py # Behavioral drift
    registry.py   # Check discovery
  integrations/   # Framework wrappers (ADD more)
    anthropic.py  # Claude
    openai.py     # GPT
    langchain.py  # LangChain
    generic.py    # Any agent
  cli/            # Terminal interface
    main.py       # Click commands
  dashboard/      # Web UI
    app.py        # FastAPI
  specs/          # Spec-driven verification (BUILD this out)
    schema.py     # AgentSpec model
tests/            # Everything must be tested
landing/          # verdict.zaphenath.app
.incubator/       # You are here
```

---

## Immediate Next Moves (Priority Order)

### P0 — Ship This Week
1. **Add more security patterns** — current: 7 dangerous commands, 8 sensitive data. Target: 20+ each
2. **Fix pyproject.toml build** — hatchling editable install fails on some systems, consider switching to setuptools
3. **Add python-multipart to dependencies** — dashboard needs it
4. **CLI: add `verdict checks --detail` subcommand** — show all patterns each check looks for

### P1 — Ship This Month
5. **Spec-driven verification** — load YAML spec files, auto-configure alignment checks from spec
6. **Persistent storage** — SQLite backend for dashboard reports
7. **Real-time streaming** — check actions AS they happen, not just after
8. **Baseline auto-learning** — save successful traces as baselines for regression checks
9. **Anthropic integration live test** — run against real Claude API, verify traces
10. **OpenAI integration live test** — same for GPT-4o

### P2 — Ship This Quarter
11. **Check marketplace** — community-contributed checks with versioning
12. **VS Code extension** — show Verdict results inline
13. **MCP integration** — trace Model Context Protocol tool calls natively
14. **Prometheus metrics** — export trust scores for monitoring dashboards
15. **GitHub Action** — `zaphenath/verdict-action@v1` for one-line CI integration

### P3 — Platform Play
16. **Verdict Cloud** — hosted SaaS version at verdict.zaphenath.app/cloud
17. **API endpoints** — verify traces via REST API
18. **Verdict Badge** — "Verified by Verdict" SVG badge for READMEs
19. **Certification program** — "Verdict-Certified Agent" for frameworks
20. **White-label SDK** — let platforms embed Verdict under their brand

---

## Code Standards

- **Tests:** Every feature needs tests. No exceptions. Target: 90%+ coverage.
- **Types:** Use Pydantic models for all data structures. Type hints everywhere.
- **Docs:** Every public function needs a docstring.
- **Naming:** snake_case for Python. Descriptive names. No abbreviations.
- **Commits:** Conventional commits (feat:, fix:, docs:, test:, refactor:)

---

## How to Report

Weekly brief format (Telegram or GitHub Discussion):

```
VERDICT WEEKLY — [date]

SHIPPED:
- [what was merged this week]

METRICS:
- GitHub stars: X
- pip installs: X
- Tests: X/X passing
- Coverage: X%

BLOCKED:
- [any blockers]

NEXT:
- [what's planned for next week]
```

---

## The Mission

Verdict becomes the industry standard for AI agent verification.
Every agent deployment runs through Verdict before reaching production.
You are building the seatbelt for the agentic era.

Ship fast. Ship safe. The world is watching.

— Zaphenath HQ
