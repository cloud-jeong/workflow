from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DifyNode:
    id: str
    type: str
    title: str
    agent_id: str | None = None
    tools: list[str] = field(default_factory=list)
    layer: int = 1
    parallel: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class DifyWorkflowDSL:
    nodes: list[DifyNode]
    edges: list[dict]
