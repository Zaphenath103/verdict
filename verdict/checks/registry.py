"""Check registry — discover, register, and manage verification checks."""

from __future__ import annotations

from verdict.checks.alignment import AlignmentCheck
from verdict.checks.correctness import CorrectnessCheck
from verdict.checks.regression import RegressionCheck
from verdict.checks.security import SecurityCheck
from verdict.core.verifier import BaseCheck


class CheckRegistry:
    """Registry for managing verification checks.

    Allows discovering available checks and creating configured instances.
    """

    def __init__(self) -> None:
        self._checks: dict[str, type[BaseCheck]] = {}

    def register(self, check_class: type[BaseCheck]) -> None:
        self._checks[check_class.name] = check_class

    def get(self, name: str) -> type[BaseCheck] | None:
        return self._checks.get(name)

    def list_checks(self) -> list[str]:
        return sorted(self._checks.keys())

    def create_all(self, **kwargs) -> list[BaseCheck]:
        """Instantiate all registered checks with optional kwargs."""
        instances = []
        for check_class in self._checks.values():
            try:
                instances.append(check_class(**kwargs))
            except TypeError:
                instances.append(check_class())
        return instances


# Default registry with built-in checks
_default_registry = CheckRegistry()
_default_registry.register(SecurityCheck)
_default_registry.register(CorrectnessCheck)
_default_registry.register(AlignmentCheck)
_default_registry.register(RegressionCheck)


def get_default_checks() -> list[BaseCheck]:
    """Get instances of all built-in checks with default configuration."""
    return [
        SecurityCheck(),
        CorrectnessCheck(),
        AlignmentCheck(),
        RegressionCheck(),
    ]


def get_registry() -> CheckRegistry:
    """Get the default check registry."""
    return _default_registry
