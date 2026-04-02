"""Specification schema for defining expected agent behavior.

A spec file tells Verdict what the agent SHOULD do, so verification
can check alignment between intent and actual behavior.

Spec format (YAML):
    name: deploy-app
    description: Build and deploy the web application
    allowed_tools:
      - bash
      - read_file
      - write_file
    allowed_write_paths:
      - ./src/
      - ./dist/
    forbidden_patterns:
      - rm -rf /
      - DROP TABLE
    max_actions: 100
    required_steps:
      - name: build
        tool: bash
        args_contain: "npm run build"
      - name: test
        tool: bash
        args_contain: "npm test"
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RequiredStep(BaseModel):
    """A step that must appear in the trace."""
    name: str
    tool: str | None = None
    args_contain: str | None = None
    content_contain: str | None = None


class AgentSpec(BaseModel):
    """Specification of expected agent behavior."""

    name: str
    description: str = ""
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_tools: list[str] = Field(default_factory=list)
    allowed_write_paths: list[str] = Field(default_factory=list)
    allowed_read_paths: list[str] = Field(default_factory=list)
    allowed_hosts: list[str] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    max_actions: int = 500
    required_steps: list[RequiredStep] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
