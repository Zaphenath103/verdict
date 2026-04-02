# Contributing to Verdict

Thanks for your interest in contributing to Verdict.

## Development Setup

```bash
git clone https://github.com/zaphenath/verdict.git
cd verdict
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

We use ruff for linting and formatting:

```bash
ruff check verdict/ tests/
ruff format verdict/ tests/
```

## Pull Requests

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a PR with a clear description

## Writing Custom Checks

See `examples/custom_checks.py` for how to write and register your own verification checks.

## Reporting Issues

Open an issue at https://github.com/zaphenath/verdict/issues with:
- Python version
- Verdict version
- Steps to reproduce
- Expected vs actual behavior
