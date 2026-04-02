"""Framework integrations for Verdict.

Provides drop-in wrappers for popular AI agent frameworks:
- Anthropic (Claude API)
- OpenAI (GPT API)
- LangChain
- Generic (any agent via decorators)
"""

from verdict.integrations.generic import VerdictWrapper, verdict_traced

__all__ = ["VerdictWrapper", "verdict_traced"]
