# VERDICT INCUBATOR — Operating Rules

## Status: INCUBATING
**Incubator Entry Date:** 2026-04-02
**Launch Approval Required From:** CEO of Zaphenath
**Advisory Board:** Boris Cherny (verification), Thariq Shihipar (action design), Andrej Karpathy (agent safety)

---

## Workspace Rules

### 1. Autonomy
- Verdict operates in its own workspace at `ZAPHENATH/verdict/`
- Has its own git repo: `github.com/Zaphenath103/verdict`
- Has its own landing page: `verdict.zaphenath.app`
- Reports to Zaphenath HQ or allocated Telegram channel

### 2. Development Rules
- All code must pass the full test suite (49+ tests) before merge
- Every PR requires: tests, documentation, and changelog entry
- Security checks must never be weakened — only strengthened
- Trust scoring algorithm changes require CEO approval
- New integrations must include at least 3 tests

### 3. Release Process
- **Patch releases (0.1.x):** Lead Dev can ship autonomously
- **Minor releases (0.x.0):** Requires incubator review
- **Major releases (1.0.0):** Requires CEO approval (launch date)
- PyPI publishing requires CEO sign-off

### 4. Reporting
- Weekly brief to Zaphenath HQ (Telegram or allocated channel)
- Brief format: What shipped / What's blocked / Trust score of the week
- GitHub Issues used for all task tracking
- Milestones mapped to roadmap phases

### 5. No Human Intervention Mode
- The incubator workspace is open for autonomous contribution
- Any developer (human or AI) can pick up open issues
- First successful PR with passing tests earns Lead Dev consideration
- All contributions must follow CONTRIBUTING.md

### 6. Brand Rules
- Verdict always credits Zaphenath Labs as parent brand
- Landing page footer must link to zaphenath.app
- README must include "Built by Zaphenath Labs"
- Social media posts must tag @zaphenath

---

## Exit Criteria (Launch Readiness)

Verdict exits incubation when ALL of the following are met:

- [ ] 100+ GitHub stars
- [ ] PyPI package published and installable
- [ ] At least 2 real-world users running verification in CI/CD
- [ ] All 4 check categories have 10+ patterns each
- [ ] Anthropic + OpenAI integrations tested with live APIs
- [ ] Spec-driven verification (YAML specs) implemented
- [ ] Real-time streaming verification (check during execution)
- [ ] Dashboard deployed with persistent storage
- [ ] CEO of Zaphenath approves launch date
