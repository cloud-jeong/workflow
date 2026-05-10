from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from models import DifyWorkflowDSL, OrchestrationPlan, PlanStep
from generator.dsl_generator import WorkflowDSLGenerator

MOCK_REGISTRY = {
    "agent_a": {"name": "Agent A", "endpoint": "http://svc:8001"},
    "agent_b": {"name": "Agent B", "endpoint": "http://svc:8002"},
    "agent_c": {"name": "Agent C", "endpoint": "http://svc:8003"},
}


def make_step(step, agent_id, depends_on=None, condition=None, tools=None, parallel=False):
    return PlanStep(
        step=step,
        agent_id=agent_id,
        action=f"action for step {step}",
        tools=tools or [],
        depends_on=depends_on or [],
        parallel=parallel,
        condition=condition,
    )


def make_plan(*steps, reasoning="test"):
    return OrchestrationPlan(
        reasoning=reasoning,
        steps=list(steps),
        has_branch=any(s.condition for s in steps),
    )


def edges(dsl: DifyWorkflowDSL, src: str, tgt: str, handle: str = "source") -> list[dict]:
    return [
        e for e in dsl.edges
        if e["source"] == src and e["target"] == tgt and e["sourceHandle"] == handle
    ]


def node_ids(dsl: DifyWorkflowDSL) -> list[str]:
    return [n.id for n in dsl.nodes]


@pytest.fixture
def gen():
    with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
        yield WorkflowDSLGenerator()


# ──────────────────────────────────────────────
# _calc_layer
# ──────────────────────────────────────────────

class TestCalcLayer:
    def test_no_deps_is_layer_1(self, gen):
        s1 = make_step(1, "agent_a")
        assert gen._calc_layer(s1, [s1]) == 1

    def test_single_dep_is_layer_2(self, gen):
        s1 = make_step(1, "agent_a")
        s2 = make_step(2, "agent_b", depends_on=[1])
        assert gen._calc_layer(s2, [s1, s2]) == 2

    def test_chain_three_steps(self, gen):
        s1 = make_step(1, "agent_a")
        s2 = make_step(2, "agent_b", depends_on=[1])
        s3 = make_step(3, "agent_c", depends_on=[2])
        assert gen._calc_layer(s3, [s1, s2, s3]) == 3


# ──────────────────────────────────────────────
# _make_branch_node
# ──────────────────────────────────────────────

class TestMakeBranchNode:
    def test_condition_with_equals(self, gen):
        s = make_step(2, "agent_b", depends_on=[1], condition="anomaly_detected == true")
        node = gen._make_branch_node(s, "node_1_agent_a")
        cond = node.data["conditions"][0]
        assert node.type == "if-else"
        assert cond["variable_selector"] == ["node_1_agent_a", "anomaly_detected"]
        assert cond["value"] == "true"
        assert cond["comparison_operator"] == "=="

    def test_condition_without_equals_defaults_to_true(self, gen):
        s = make_step(2, "agent_b", depends_on=[1], condition="ooc_count")
        node = gen._make_branch_node(s, "node_1_agent_a")
        cond = node.data["conditions"][0]
        assert cond["variable_selector"] == ["node_1_agent_a", "ooc_count"]
        assert cond["value"] == "true"

    def test_source_node_is_dep_not_self(self, gen):
        s = make_step(3, "agent_c", depends_on=[2], condition="ok == true")
        node = gen._make_branch_node(s, "node_2_agent_b")
        assert node.data["conditions"][0]["variable_selector"][0] == "node_2_agent_b"

    def test_branch_id_uses_step_number(self, gen):
        s = make_step(5, "agent_a", condition="x == true")
        node = gen._make_branch_node(s, "node_4_agent_b")
        assert node.id == "branch_5"


# ──────────────────────────────────────────────
# _build_node_data
# ──────────────────────────────────────────────

class TestBuildNodeData:
    def test_type_is_http_request(self, gen):
        s = make_step(1, "agent_a", tools=["tool_x"])
        data = gen._build_node_data(s, MOCK_REGISTRY["agent_a"])
        assert data["type"] == "http-request"

    def test_url_appends_invoke(self, gen):
        s = make_step(1, "agent_a")
        data = gen._build_node_data(s, MOCK_REGISTRY["agent_a"])
        assert data["url"] == "http://svc:8001/invoke"

    def test_body_contains_tools(self, gen):
        s = make_step(1, "agent_a", tools=["tool_x", "tool_y"])
        data = gen._build_node_data(s, MOCK_REGISTRY["agent_a"])
        body = json.loads(data["body"]["data"])
        assert body["tools"] == ["tool_x", "tool_y"]

    def test_body_references_start_variables(self, gen):
        s = make_step(1, "agent_a")
        data = gen._build_node_data(s, MOCK_REGISTRY["agent_a"])
        body_str = data["body"]["data"]
        assert "{{#start.user_query#}}" in body_str
        assert "{{#start.lot_id#}}" in body_str


# ──────────────────────────────────────────────
# generate() — node structure
# ──────────────────────────────────────────────

class TestGenerateNodes:
    def test_empty_plan_has_start_and_end_only(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan())
        ids = node_ids(dsl)
        assert ids == ["start", "end"]

    def test_linear_plan_node_count(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1]),
            ))
        # start, node_1_agent_a, node_2_agent_b, end
        assert len(dsl.nodes) == 4
        assert "node_1_agent_a" in node_ids(dsl)
        assert "node_2_agent_b" in node_ids(dsl)

    def test_linear_plan_has_no_branch_nodes(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1]),
            ))
        branch_nodes = [n for n in dsl.nodes if n.type == "if-else"]
        assert branch_nodes == []

    def test_conditional_step_creates_branch_node(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="ok == true"),
            ))
        # start, node_1_agent_a, node_2_agent_b, branch_2, end
        assert len(dsl.nodes) == 5
        assert "branch_2" in node_ids(dsl)

    def test_branch_checks_dep_node_output(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="flag == true"),
            ))
        branch = next(n for n in dsl.nodes if n.id == "branch_2")
        selector = branch.data["conditions"][0]["variable_selector"]
        assert selector[0] == "node_1_agent_a"
        assert selector[1] == "flag"

    def test_same_condition_same_dep_deduplicates_branch(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="ok == true"),
                make_step(3, "agent_c", depends_on=[1], condition="ok == true"),
            ))
        branch_nodes = [n for n in dsl.nodes if n.type == "if-else"]
        assert len(branch_nodes) == 1

    def test_end_node_references_last_node_body(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1]),
            ))
        end_node = next(n for n in dsl.nodes if n.id == "end")
        selector = end_node.data["outputs"][0]["value_selector"]
        assert selector == ["node_2_agent_b", "body"]


# ──────────────────────────────────────────────
# generate() — edge structure
# ──────────────────────────────────────────────

class TestGenerateEdges:
    def test_linear_edges(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1]),
            ))
        assert len(edges(dsl, "start", "node_1_agent_a")) == 1
        assert len(edges(dsl, "node_1_agent_a", "node_2_agent_b")) == 1
        assert len(edges(dsl, "node_2_agent_b", "end")) == 1

    def test_branch_edges_true_and_false(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="ok == true"),
            ))
        assert len(edges(dsl, "node_1_agent_a", "branch_2")) == 1
        assert len(edges(dsl, "branch_2", "node_2_agent_b", handle="true")) == 1
        assert len(edges(dsl, "branch_2", "end", handle="false")) == 1
        assert len(edges(dsl, "node_2_agent_b", "end")) == 1

    def test_dedup_branch_gets_two_true_edges(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="ok == true"),
                make_step(3, "agent_c", depends_on=[1], condition="ok == true"),
            ))
        branch_id = next(n.id for n in dsl.nodes if n.type == "if-else")
        true_edges = [e for e in dsl.edges
                      if e["source"] == branch_id and e["sourceHandle"] == "true"]
        assert len(true_edges) == 2
        targets = {e["target"] for e in true_edges}
        assert "node_2_agent_b" in targets
        assert "node_3_agent_c" in targets

    def test_dedup_branch_dep_wired_once(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan(
                make_step(1, "agent_a"),
                make_step(2, "agent_b", depends_on=[1], condition="ok == true"),
                make_step(3, "agent_c", depends_on=[1], condition="ok == true"),
            ))
        branch_id = next(n.id for n in dsl.nodes if n.type == "if-else")
        dep_to_branch = edges(dsl, "node_1_agent_a", branch_id)
        assert len(dep_to_branch) == 1

    def test_empty_plan_has_no_edges(self, gen):
        with patch("generator.dsl_generator.AGENT_REGISTRY", MOCK_REGISTRY):
            dsl = gen.generate(make_plan())
        assert dsl.edges == []
