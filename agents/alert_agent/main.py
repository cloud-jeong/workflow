"""Alert Agent Service - port 8006."""
from __future__ import annotations

import sys
sys.path.insert(0, "..")

from _base import create_app
from tools import mcp_create_ticket, mcp_escalate, mcp_notify_slack

TOOL_SPECS = {
    "mcp_notify_slack": {
        "name": "mcp_notify_slack",
        "description": "Slack 채널에 공정 이상 알림을 발송합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":   {"type": "string"},
                "message":  {"type": "string", "description": "알림 메시지 (생략 시 자동 생성)"},
                "channel":  {"type": "string", "description": "Slack 채널 (기본: #yms-alerts)"},
                "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_create_ticket": {
        "name": "mcp_create_ticket",
        "description": "Jira에 공정 이상 티켓을 생성하고 담당자를 배정합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":   {"type": "string"},
                "title":    {"type": "string"},
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "assignee": {"type": "string"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_escalate": {
        "name": "mcp_escalate",
        "description": "심각도에 따라 상위 관리자에게 이슈를 에스컬레이션합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":    {"type": "string"},
                "ticket_id": {"type": "string"},
                "level":     {"type": "integer", "description": "에스컬레이션 레벨 1~3"},
            },
            "required": ["lot_id"],
        },
    },
}

SYSTEM_PROMPT = (
    "당신은 반도체 공정 이상 알림 전문 에이전트입니다. "
    "공정 이상이 감지된 경우 Slack 알림 발송 → Jira 티켓 생성 순서로 진행하세요. "
    "심각도가 HIGH이면 에스컬레이션도 수행하세요. "
    "모든 조치 결과를 한국어로 요약 보고하세요."
)


def dispatch(name: str, args: dict) -> dict:
    if name == "mcp_notify_slack":  return mcp_notify_slack(**args)
    if name == "mcp_create_ticket": return mcp_create_ticket(**args)
    if name == "mcp_escalate":      return mcp_escalate(**args)
    return {"error": f"Unknown tool: {name}"}


app = create_app("alert_agent", TOOL_SPECS, dispatch, SYSTEM_PROMPT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
