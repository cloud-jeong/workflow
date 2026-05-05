from __future__ import annotations

import json

from anthropic import Anthropic
from rich.console import Console

from config import AGENT_REGISTRY
from models import OrchestrationPlan, PlanStep

console = Console()

PLANNER_SYSTEM_PROMPT = """You are an expert Workflow Planner for a semiconductor Yield Management System (YMS).

Available MCP Agents:
{agent_list}

Given a natural language request, analyze it and return ONLY a valid JSON object (no markdown, no extra text):
{{
  "reasoning": "brief reasoning in Korean (2-3 sentences)",
  "has_branch": false,
  "steps": [
    {{
      "step": 1,
      "agent_id": "agent_registry_key",
      "action": "Korean description of what this step does",
      "tools": ["tool_name_1", "tool_name_2"],
      "depends_on": [],
      "parallel": false,
      "condition": null
    }}
  ]
}}

Rules:
- Use only agents from the registry (use exact agent_id keys)
- steps with no depends_on or same depends_on as a sibling can be parallel=true
- set has_branch=true if the workflow has conditional branching
- condition field: use short English expression like "anomaly_detected == true"
- depends_on: list of step numbers this step must wait for
"""


class PlannerAgent:
    """Stage 1: 자연어 → OrchestrationPlan"""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def _build_system_prompt(self) -> str:
        agent_list = "\n".join(
            f'  - "{aid}" ({info["name"]}): {info["description"]}\n'
            f'    tools: {", ".join(info["tools"])}'
            for aid, info in AGENT_REGISTRY.items()
        )
        return PLANNER_SYSTEM_PROMPT.format(agent_list=agent_list)

    def plan(self, user_query: str) -> OrchestrationPlan:
        console.log("[bold cyan]Stage 1[/] Planner Agent 호출 중...")

        response = self.client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=self._build_system_prompt(),
            messages=[{"role": "user", "content": user_query}],
        )

        raw = response.content[0].text
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()

        data = json.loads(raw)

        steps = [
            PlanStep(
                step=s["step"],
                agent_id=s["agent_id"],
                action=s["action"],
                tools=s.get("tools", []),
                depends_on=s.get("depends_on", []),
                parallel=s.get("parallel", False),
                condition=s.get("condition"),
            )
            for s in data["steps"]
        ]

        plan = OrchestrationPlan(
            reasoning=data["reasoning"],
            steps=steps,
            has_branch=data.get("has_branch", False),
        )

        console.log(f"[green]✓[/] Plan 생성: {len(steps)}단계, 분기={'있음' if plan.has_branch else '없음'}")
        return plan
