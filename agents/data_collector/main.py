"""DataCollector Agent Service - port 8001."""
from __future__ import annotations

import sys
sys.path.insert(0, "..")

from _base import create_app
from tools import mcp_fetch_equipment_log, mcp_fetch_sensor, mcp_query_db, mcp_read_file

TOOL_SPECS = {
    "mcp_query_db": {
        "name": "mcp_query_db",
        "description": "DB에서 LOT 공정 측정 데이터(산화막 두께, CD, 이온주입량 등)를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id": {"type": "string"},
                "query":  {"type": "string", "description": "조회 유형 (spc_measurements, process_history 등)"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_fetch_sensor": {
        "name": "mcp_fetch_sensor",
        "description": "장비 센서에서 온도/압력/가스 유량 등 실시간 데이터를 수집합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":       {"type": "string"},
                "equipment_id": {"type": "string"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_read_file": {
        "name": "mcp_read_file",
        "description": "레시피 또는 설정 파일을 읽습니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":    {"type": "string"},
                "file_type": {"type": "string", "description": "recipe | config | log"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_fetch_equipment_log": {
        "name": "mcp_fetch_equipment_log",
        "description": "장비 이벤트 로그(WARN/ERROR 포함)를 수집합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":       {"type": "string"},
                "equipment_id": {"type": "string"},
            },
            "required": ["lot_id"],
        },
    },
}

SYSTEM_PROMPT = (
    "당신은 반도체 공정 데이터 수집 전문 에이전트입니다. "
    "DB 조회, 센서 데이터, 장비 로그를 수집하여 이후 분석 단계에서 활용할 수 있도록 "
    "데이터를 정리하고 주요 이상 징후를 한국어로 간략히 요약하세요."
)


def dispatch(name: str, args: dict) -> dict:
    if name == "mcp_query_db":             return mcp_query_db(**args)
    if name == "mcp_fetch_sensor":         return mcp_fetch_sensor(**args)
    if name == "mcp_read_file":            return mcp_read_file(**args)
    if name == "mcp_fetch_equipment_log":  return mcp_fetch_equipment_log(**args)
    return {"error": f"Unknown tool: {name}"}


app = create_app("data_collector", TOOL_SPECS, dispatch, SYSTEM_PROMPT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
