from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class DifyNode:
    id: str
    type: str
    title: str
    agent_id: str | None = None
    tools: list[str] = field(default_factory=list) # 각 인스턴스가 고유한 딕셔너리 객체를 생성하도록 보장하여, 모든 인스턴스가 하나의 딕셔너리를 공유하는 문제를 방지합니다.
    layer: int = 1              # node의 x좌표 계산, end node의 layer 결정
    parallel: bool = False
    data: dict = field(default_factory=dict)


@dataclass
class DifyWorkflowDSL:
    nodes: list[DifyNode]
    edges: list[dict]
