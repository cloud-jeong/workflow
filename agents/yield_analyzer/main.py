"""Yield Analyzer Agent Service - port 8003."""
from __future__ import annotations

import sys
sys.path.insert(0, "..")

from _base import create_app
from tools import mcp_bin_analysis, mcp_calc_yield, mcp_wafer_map

TOOL_SPECS = {
    "mcp_calc_yield": {
        "name": "mcp_calc_yield",
        "description": "LOT 전체 웨이퍼의 수율(Yield %)을 계산합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":       {"type": "string"},
                "wafer_count":  {"type": "integer", "description": "웨이퍼 매수 (기본: 25)"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_bin_analysis": {
        "name": "mcp_bin_analysis",
        "description": "Bin별 불량 유형(Leakage, Open, Short, Parametric)을 분류하고 주요 원인을 분석합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id": {"type": "string"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_wafer_map": {
        "name": "mcp_wafer_map",
        "description": "웨이퍼 맵(다이 위치별 Pass/Fail)을 생성하고 불량 패턴을 분석합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":    {"type": "string"},
                "wafer_id":  {"type": "string", "description": "예: W01"},
            },
            "required": ["lot_id"],
        },
    },
}

SYSTEM_PROMPT = (
    "당신은 반도체 수율(Yield) 분석 전문 에이전트입니다. "
    "LOT 수율 계산, Bin 분석, 웨이퍼 맵 분석을 통해 "
    "수율 저하 원인과 불량 패턴을 한국어로 명확하게 보고하세요."
)


def dispatch(name: str, args: dict) -> dict:
    if name == "mcp_calc_yield":    return mcp_calc_yield(**args)
    if name == "mcp_bin_analysis":  return mcp_bin_analysis(**args)
    if name == "mcp_wafer_map":     return mcp_wafer_map(**args)
    return {"error": f"Unknown tool: {name}"}


app = create_app("yield_analyzer", TOOL_SPECS, dispatch, SYSTEM_PROMPT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
