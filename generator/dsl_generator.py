from __future__ import annotations

from rich.console import Console

from config import AGENT_REGISTRY
from models import DifyNode, DifyWorkflowDSL, OrchestrationPlan, PlanStep

console = Console()

_FEATURES_DEFAULT = {
    "file_upload": {
        "allowed_file_extensions": [".JPG", ".JPEG", ".PNG", ".GIF", ".WEBP", ".SVG"],
        "allowed_file_types": ["image"],
        "allowed_file_upload_methods": ["local_file", "remote_url"],
        "enabled": False,
        "fileUploadConfig": {
            "attachment_image_file_size_limit": 2,
            "audio_file_size_limit": 50,
            "batch_count_limit": 5,
            "file_size_limit": 15,
            "file_upload_limit": 20,
            "image_file_batch_limit": 10,
            "image_file_size_limit": 10,
            "single_chunk_attachment_limit": 10,
            "video_file_size_limit": 100,
            "workflow_file_upload_limit": 10,
        },
        "image": {
            "enabled": False,
            "number_limits": 3,
            "transfer_methods": ["local_file", "remote_url"],
        },
        "number_limits": 3,
    },
    "opening_statement": "",
    "retriever_resource": {"enabled": True},
    "sensitive_word_avoidance": {"enabled": False},
    "speech_to_text": {"enabled": False},
    "suggested_questions": [],
    "suggested_questions_after_answer": {"enabled": False},
    "text_to_speech": {"enabled": False, "language": "", "voice": ""},
}


class WorkflowDSLGenerator:
    """Stage 2: OrchestrationPlan → DifyWorkflowDSL"""

    _NODE_DATA_TEMPLATES: dict[str, dict] = {
        "start": {
            "type": "start",
            "variables": [
                {"variable": "user_query", "label": "사용자 요청", "type": "text-input", "required": True},
                {"variable": "lot_id", "label": "LOT ID", "type": "text-input", "required": False},
            ],
        },
        "end": {
            "type": "end",
            "outputs": [],
        },
        "http-request": {
            "type": "http-request",
            "method": "POST",
            "authorization": {"type": "no-auth"},
            "headers": "Content-Type: application/json",
            "params": "",
            "body": {"type": "json", "data": "{}"},
            "timeout": {"max_connect_timeout": 10, "max_read_timeout": 30, "max_write_timeout": 10},
        },
        "if-else": {
            "type": "if-else",
            "logical_operator": "and",
            "conditions": [],
        },
    }

    def generate(self, plan: OrchestrationPlan) -> DifyWorkflowDSL:
        console.log("[bold cyan]Stage 2[/] DSL 생성 중...")

        nodes: list[DifyNode] = []

        start_node = DifyNode(
            id="start",
            type="start",
            title="Start",
            layer=0,
            data=self._NODE_DATA_TEMPLATES["start"].copy(),
        )
        nodes.append(start_node)

        step_to_node_id: dict[int, str] = {}

        # First pass: create all agent nodes
        for step in plan.steps:
            node_id = f"node_{step.step}_{step.agent_id}"
            agent_info = AGENT_REGISTRY.get(step.agent_id, {})
            node_data = self._build_node_data(step, agent_info)
            node = DifyNode(
                id=node_id,
                type="http-request",
                title=agent_info.get("name", step.agent_id),
                agent_id=step.agent_id,
                tools=step.tools,
                layer=self._calc_layer(step, plan.steps),
                parallel=step.parallel,
                data=node_data,
            )
            nodes.append(node)
            step_to_node_id[step.step] = node_id

        # Second pass: create branch nodes, deduped by (dep_node, condition)
        seen_branches: dict[tuple, str] = {}  # (dep_node_id, condition) → branch_id
        step_to_branch: dict[int, str] = {}
        for step in plan.steps:
            if not step.condition or not step.depends_on:
                continue
            dep_node_id = step_to_node_id[step.depends_on[0]]
            branch_key = (dep_node_id, step.condition)
            if branch_key not in seen_branches:
                branch_id = f"branch_{step.step}"
                branch_node = self._make_branch_node(step, dep_node_id)
                nodes.append(branch_node)
                seen_branches[branch_key] = branch_id
            step_to_branch[step.step] = seen_branches[branch_key]

        # Find last layer to wire end node output
        if plan.steps:
            max_step_layer = max(self._calc_layer(s, plan.steps) for s in plan.steps)
            last_steps = [s for s in plan.steps if self._calc_layer(s, plan.steps) == max_step_layer]
            last_node_id = step_to_node_id[last_steps[0].step]
        else:
            max_step_layer = 0
            last_node_id = "start"

        end_node = DifyNode(
            id="end",
            type="end",
            title="End",
            layer=max_step_layer + 1,
            data={
                "type": "end",
                "outputs": [{
                    "variable": "result",
                    "value_selector": [last_node_id, "body"],
                    "value_type": "string",
                }],
            },
        )
        nodes.append(end_node)

        edges = self._build_edges(plan.steps, step_to_node_id, step_to_branch, nodes)

        console.log(f"[green]✓[/] DSL 생성: 노드 {len(nodes)}개, 엣지 {len(edges)}개")
        return DifyWorkflowDSL(nodes=nodes, edges=edges)

    def _build_node_data(self, step: PlanStep, agent_info: dict) -> dict:
        import json
        endpoint = agent_info.get("endpoint", "")
        body_payload = {
            "input": "{{#start.user_query#}}",
            "lot_id": "{{#start.lot_id#}}",
            "tools": step.tools,
        }
        return {
            "type": "http-request",
            "title": agent_info.get("name", step.agent_id),
            "desc": step.action,
            "method": "POST",
            "url": f"{endpoint}/invoke",
            "authorization": {"type": "no-auth"},
            "headers": "Content-Type: application/json",
            "params": "",
            "body": {
                "type": "json",
                "data": json.dumps(body_payload, ensure_ascii=False),
            },
            "timeout": {
                "max_connect_timeout": 10,
                "max_read_timeout": 30,
                "max_write_timeout": 10,
            },
        }

    def _make_branch_node(self, step: PlanStep, source_node_id: str) -> DifyNode:
        branch_id = f"branch_{step.step}"
        condition_var, condition_val = (
            step.condition.split("==") if "==" in step.condition else (step.condition, "true")
        )
        return DifyNode(
            id=branch_id,
            type="if-else",
            title=f"조건: {step.condition}",
            layer=step.step + 1,
            data={
                "type": "if-else",
                "title": f"조건 분기 (Step {step.step})",
                "logical_operator": "and",
                "conditions": [{
                    "variable_selector": [source_node_id, condition_var.strip()],
                    "comparison_operator": "==",
                    "value": condition_val.strip(),
                }],
            },
        )

    def _calc_layer(self, step: PlanStep, all_steps: list[PlanStep]) -> int:
        if not step.depends_on:
            return 1
        max_dep_layer = max(
            self._calc_layer(s, all_steps)
            for s in all_steps
            if s.step in step.depends_on
        )
        return max_dep_layer + 1

    def _build_edges(
        self,
        steps: list[PlanStep],
        step_to_node_id: dict[int, str],
        step_to_branch: dict[int, str],
        nodes: list[DifyNode],
    ) -> list[dict]:
        node_type_map = {n.id: n.data.get("type", n.type) for n in nodes}
        edges = []
        edge_counter = 0
        wired_dep_to_branch: set[tuple] = set()

        def make_edge(src: str, tgt: str, source_handle: str = "source") -> dict:
            nonlocal edge_counter
            edge_counter += 1
            return {
                "data": {
                    "isInIteration": False,
                    "isInLoop": False,
                    "sourceType": node_type_map.get(src, ""),
                    "targetType": node_type_map.get(tgt, ""),
                },
                "id": f"edge_{edge_counter}",
                "source": src,
                "sourceHandle": source_handle,
                "target": tgt,
                "targetHandle": "target",
                "type": "custom",
                "zIndex": 0,
            }

        # start → first-layer nodes (via branch if conditioned)
        for s in [step for step in steps if not step.depends_on]:
            node_id = step_to_node_id[s.step]
            if s.step in step_to_branch:
                branch_id = step_to_branch[s.step]
                edges.append(make_edge("start", branch_id))
                edges.append(make_edge(branch_id, node_id, source_handle="true"))
            else:
                edges.append(make_edge("start", node_id))

        # dependency → node edges (via branch if current step is conditioned)
        for step in steps:
            if not step.depends_on:
                continue
            node_id = step_to_node_id[step.step]
            for dep_step_num in step.depends_on:
                dep_node_id = step_to_node_id[dep_step_num]
                if step.step in step_to_branch:
                    branch_id = step_to_branch[step.step]
                    wire_key = (dep_node_id, branch_id)
                    if wire_key not in wired_dep_to_branch:
                        edges.append(make_edge(dep_node_id, branch_id))
                        wired_dep_to_branch.add(wire_key)
                    edges.append(make_edge(branch_id, node_id, source_handle="true"))
                else:
                    edges.append(make_edge(dep_node_id, node_id))

        # branch false → end
        branch_ids = {n.id for n in nodes if n.type == "if-else"}
        for branch_id in branch_ids:
            edges.append(make_edge(branch_id, "end", source_handle="false"))

        # last nodes → end (all leaf nodes regardless of condition)
        if steps:
            step_nums_as_dep = {dep for s in steps for dep in s.depends_on}
            leaf_steps = [s for s in steps if s.step not in step_nums_as_dep]
            for s in leaf_steps:
                edges.append(make_edge(step_to_node_id[s.step], "end"))

        return edges

    def to_dify_import_payload(
        self, dsl: DifyWorkflowDSL, name: str = "YMS Auto Workflow"
    ) -> dict:
        return {
            "app": {
                "description": "NL → Agent Orchestrator 자동 생성 워크플로우",
                "icon": "🤖",
                "icon_background": "#FFEAD5",
                "icon_type": "emoji",
                "mode": "workflow",
                "name": name,
                "use_icon_as_answer_icon": False,
            },
            "dependencies": [],
            "kind": "app",
            "version": "0.6.0",
            "workflow": {
                "conversation_variables": [],
                "environment_variables": [],
                "features": _FEATURES_DEFAULT,
                "graph": {
                    "edges": dsl.edges,
                    "nodes": [self._node_to_dict(n) for n in dsl.nodes],
                    "viewport": {"x": 0, "y": 0, "zoom": 1},
                },
                "rag_pipeline_variables": [],
            },
        }

    def _node_to_dict(self, node: DifyNode) -> dict:
        x = node.layer * 240 + 80
        y = 200
        # title and selected belong inside data per Dify's export format
        data = {**node.data, "title": node.title, "selected": False}
        return {
            "data": data,
            "height": 98,
            "id": node.id,
            "position": {"x": x, "y": y},
            "positionAbsolute": {"x": x, "y": y},
            "selected": False,
            "sourcePosition": "right",
            "targetPosition": "left",
            "type": "custom",
            "width": 244,
        }
