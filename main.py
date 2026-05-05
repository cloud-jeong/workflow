"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workflow Orchestrator  —  3-Stage Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stage 1. Planner Agent   : 자연어 → Orchestration Plan (Claude API)
Stage 2. DSL Generator   : Plan → Dify Workflow Graph (nodes/edges)
Stage 3. Dify Executor   : DSL → Dify REST API (배포 or 실행)

실행:
    python main.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations

import json
import os

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import ANTHROPIC_API_KEY, DIFY_API_KEY, DIFY_BASE_URL
from dify import DifyWorkflowClient
from generator import WorkflowDSLGenerator
from models import DifyWorkflowDSL, OrchestrationPlan
from planner import PlannerAgent

console = Console()


class WorkflowOrchestrator:
    """3단계 파이프라인 실행"""

    def __init__(self):
        self.planner   = PlannerAgent(api_key=ANTHROPIC_API_KEY)
        self.generator = WorkflowDSLGenerator()
        self.dify      = DifyWorkflowClient(
            base_url=DIFY_BASE_URL,
            app_api_key=DIFY_API_KEY,
            console_token=os.getenv("DIFY_CONSOLE_TOKEN"),
        )

    def run(
        self,
        user_query: str,
        execute: bool = False,
        export_yaml: bool = True,
        export_json: bool = True,
    ) -> dict:
        console.rule("[bold] MES Workflow Orchestrator")

        plan = self.planner.plan(user_query)
        self._print_plan(plan)

        dsl = self.generator.generate(plan)
        import_payload = self.generator.to_dify_import_payload(dsl)
        self._print_dsl(dsl)

        if export_json:
            path = "result_dsl.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(import_payload, f, ensure_ascii=False, indent=2)
            console.log(f"[dim]→ JSON 저장: {path}[/]")

        if export_yaml:
            path = "result_dsl.yaml"
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(import_payload, f, allow_unicode=True, sort_keys=False)
            console.log(f"→ YAML 저장: {path}")

        run_result = None
        if execute:
            run_result = self._execute(user_query, dsl, import_payload)

        console.rule("[bold green]완료")
        return {
            "plan": plan,
            "dsl": dsl,
            "import_payload": import_payload,
            "run_result": run_result,
        }

    def _execute(self, query: str, dsl: DifyWorkflowDSL, payload: dict) -> dict:
        console.log("[bold cyan]Stage 3[/] Dify 실행 전략 결정 중...")

        if os.getenv("DIFY_CONSOLE_TOKEN"):
            console.log("→ 전략 1: Console API로 신규 앱 생성")
            app = self.dify.import_app_from_dsl(payload)
            app_id = app["id"]
            self.dify.publish_workflow(app_id)
            console.log(f"[green]✓[/] 배포 완료 — app_id: {app_id}")

        console.log("→ 전략 2: 기존 배포 앱 실행")
        inputs = {"user_query": query, "lot_id": ""}
        return self.dify.run_workflow(inputs=inputs)

    def _print_plan(self, plan: OrchestrationPlan):
        console.print(Panel(plan.reasoning, title="[cyan]Planner 추론[/]", border_style="cyan"))
        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("Step", width=6)
        table.add_column("Agent", width=22)
        table.add_column("Action", width=38)
        table.add_column("Tools", width=30)
        table.add_column("Flags", width=12)
        for s in plan.steps:
            flags = []
            if s.parallel:   flags.append("[yellow]⇉ PARALLEL[/]")
            if s.condition:  flags.append(f"[magenta]⎇ {s.condition}[/]")
            table.add_row(
                str(s.step),
                s.agent_id,
                s.action[:36],
                "\n".join(s.tools[:3]),
                " ".join(flags) or "—",
            )
        console.print(table)

    def _print_dsl(self, dsl: DifyWorkflowDSL):
        console.print(Panel(
            f"노드: [bold]{len(dsl.nodes)}[/]  엣지: [bold]{len(dsl.edges)}[/]\n"
            + "\n".join(
                f"  {'⇉' if n.parallel else '→'} [{n.type:8}] {n.title}"
                for n in dsl.nodes
            ),
            title="[green]생성된 Workflow DSL[/]",
            border_style="green",
        ))


if __name__ == "__main__":
    orchestrator = WorkflowOrchestrator()

    query = (
        "어제 LOT-2024-0812의 SPC 데이터를 분석하고, "
        "이상 공정이 감지되면 슬랙 알림과 PDF 리포트를 동시에 생성해줘."
    )

    result = orchestrator.run(
        user_query=query,
        execute=False,
        export_yaml=True,
        export_json=True,
    )

    # 이미 배포된 워크플로우 직접 실행
    # client = DifyWorkflowClient(DIFY_BASE_URL, DIFY_API_KEY)
    # result = client.run_workflow(
    #     inputs={"user_query": query, "lot_id": "LOT-2024-0812"},
    # )
    # print(result)

    # SSE 스트리밍 실행
    # client = DifyWorkflowClient(DIFY_BASE_URL, DIFY_API_KEY)
    # for event in client.run_workflow_stream({"user_query": query}):
    #     evt_type = event.get("event")
    #     if evt_type == "node_finished":
    #         print(f"[{event['data']['title']}] 완료")
    #     elif evt_type == "workflow_finished":
    #         print("최종 결과:", event["data"]["outputs"])
    #         break
