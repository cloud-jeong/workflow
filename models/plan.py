from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlanStep:
    step: int
    agent_id: str
    action: str
    tools: list[str]
    depends_on: list[int]
    parallel: bool = False
    condition: str | None = None


@dataclass
class OrchestrationPlan:
    reasoning: str
    steps: list[PlanStep]
    has_branch: bool = False
