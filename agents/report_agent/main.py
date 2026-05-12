"""Report Agent Service - port 8005."""
from __future__ import annotations

import sys
sys.path.insert(0, "..")

from _base import create_app
from tools import mcp_export_pdf, mcp_gen_report, mcp_send_email

TOOL_SPECS = {
    "mcp_gen_report": {
        "name": "mcp_gen_report",
        "description": "SPC/Yield/Anomaly 분석 결과를 종합한 공정 리포트를 생성합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":  {"type": "string"},
                "context": {"type": "object", "description": "이전 분석 결과 딕셔너리"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_export_pdf": {
        "name": "mcp_export_pdf",
        "description": "생성된 리포트를 PDF 파일로 내보냅니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "report_id": {"type": "string"},
                "lot_id":    {"type": "string"},
            },
            "required": ["report_id", "lot_id"],
        },
    },
    "mcp_send_email": {
        "name": "mcp_send_email",
        "description": "PDF 리포트를 담당자에게 이메일로 발송합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":     {"type": "string"},
                "report_id":  {"type": "string"},
                "recipients": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["lot_id", "report_id"],
        },
    },
}

SYSTEM_PROMPT = (
    "당신은 반도체 공정 리포트 생성 전문 에이전트입니다. "
    "분석 결과를 종합하여 리포트를 생성하고 PDF로 내보낸 후 담당자에게 발송하세요. "
    "리포트 생성 → PDF 변환 → 이메일 발송 순서로 진행하세요."
)


def dispatch(name: str, args: dict) -> dict:
    if name == "mcp_gen_report":  return mcp_gen_report(**args)
    if name == "mcp_export_pdf":  return mcp_export_pdf(**args)
    if name == "mcp_send_email":  return mcp_send_email(**args)
    return {"error": f"Unknown tool: {name}"}


app = create_app("report_agent", TOOL_SPECS, dispatch, SYSTEM_PROMPT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
