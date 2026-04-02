# VERDICT — Improvements & Technical Debt

## Critical Improvements (Must Fix Before v0.2.0)

### 1. Build System
- **Issue:** `hatchling` editable install fails on some Python 3.11 setups
- **Fix:** Add `python-multipart` to core dependencies, consider `setuptools` fallback
- **Impact:** Blocks `pip install -e .` for contributors

### 2. Security Patterns Are Too Few
- **Current:** 7 dangerous commands, 8 sensitive data patterns
- **Target:** 25+ dangerous, 20+ sensitive, 10+ injection
- **Missing patterns:** Terraform destroy, kubectl delete, git push --force, npm publish, Docker privileged, Azure/GCP keys, Stripe keys, database connection strings

### 3. Async Check Execution
- **Issue:** Async checks use a ThreadPoolExecutor workaround
- **Fix:** Proper `asyncio.run()` with `nest_asyncio` for nested loops
- **Impact:** Async checks may fail in already-async contexts

### 4. Dashboard Persistence
- **Issue:** Reports are in-memory only, lost on restart
- **Fix:** Add SQLite storage with migration support
- **Impact:** Dashboard is demo-only without persistence

### 5. LangChain Integration Bug
- **Issue:** `_ensure_trace` calls `self._tracer.tracer_trace_obj` which doesn't exist
- **Fix:** Should create trace via `Trace()` directly
- **Impact:** LangChain integration will crash on first use

---

## Architecture Improvements

### 6. Plugin System for Checks
- Current: checks are imported directly
- Better: entry_points-based plugin system so third parties can `pip install verdict-check-aws` and it auto-registers

### 7. Streaming Verification
- Current: verify after trace completes
- Better: `StreamingVerifier` that checks actions in real-time as they're recorded
- Enables: blocking dangerous actions BEFORE they execute

### 8. Spec-Driven Verification
- Schema exists (`specs/schema.py`) but no loader or check generator
- Need: YAML/JSON spec loader that auto-creates AlignmentCheck instances
- Enables: declarative verification ("this agent should only use these tools")

### 9. Trace Storage Format
- Current: custom JSON via `.to_dict()`
- Better: OpenTelemetry-compatible trace format
- Enables: integration with existing observability infrastructure

### 10. Check Composition
- Current: checks are flat, independent
- Better: check pipelines (if security passes, run alignment; if alignment fails, skip regression)
- Enables: smarter, faster verification

---

## Performance Improvements

### 11. Lazy Check Loading
- Don't import all checks at startup
- Use lazy imports for framework-specific integrations
- Reduces startup time for CLI

### 12. Parallel Check Execution
- Run all sync checks in parallel using ThreadPoolExecutor
- Currently sequential — slows down with many checks

### 13. Trace Compression
- Large traces (1000+ actions) consume memory
- Add trace compaction (merge repeated similar actions)
- Add streaming trace writer (write to disk as actions are recorded)

---

## Quality Improvements

### 14. Test Coverage
- Current: 49 tests, estimated 75% coverage
- Target: 100+ tests, 90%+ coverage
- Missing: reporter format edge cases, error paths, concurrent access

### 15. Type Safety
- Run mypy strict mode across codebase
- Fix any type: ignore comments
- Add runtime type validation for public APIs

### 16. Documentation
- Generate API docs from docstrings (Sphinx/mkdocs)
- Add architecture decision records (ADRs)
- Add cookbook with 10+ real-world examples
