"""Anomaly Detector Agent Service - port 8004."""
from __future__ import annotations

import sys
sys.path.insert(0, "..")

from _base import create_app
from tools import mcp_correlation_check, mcp_detect_drift, mcp_ml_predict

TOOL_SPECS = {
    "mcp_ml_predict": {
        "name": "mcp_ml_predict",
        "description": "ML 모델(Isolation Forest)로 공정 이상 여부를 예측하고 Anomaly Score를 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":   {"type": "string"},
                "features": {"type": "object", "description": "공정 파라미터 특성값 딕셔너리"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_detect_drift": {
        "name": "mcp_detect_drift",
        "description": "CUSUM 알고리즘으로 공정 파라미터 드리프트(방향·크기)를 탐지합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":    {"type": "string"},
                "parameter": {"type": "string", "description": "분석할 파라미터명"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_correlation_check": {
        "name": "mcp_correlation_check",
        "description": "공정 파라미터 간 상관관계를 분석하여 이상의 근본 원인을 파악합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id": {"type": "string"},
            },
            "required": ["lot_id"],
        },
    },
}

SYSTEM_PROMPT = (
    "당신은 반도체 공정 이상 탐지 전문 에이전트입니다. "
    "ML 예측, 드리프트 탐지, 상관관계 분석을 종합하여 "
    "공정 이상 여부를 최종 판정하고 근본 원인을 한국어로 보고하세요. "
    "anomaly_detected 필드를 반드시 결론에 포함하세요."
)


def dispatch(name: str, args: dict) -> dict:
    if name == "mcp_ml_predict":        return mcp_ml_predict(**args)
    if name == "mcp_detect_drift":      return mcp_detect_drift(**args)
    if name == "mcp_correlation_check": return mcp_correlation_check(**args)
    return {"error": f"Unknown tool: {name}"}


app = create_app("anomaly_detector", TOOL_SPECS, dispatch, SYSTEM_PROMPT)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
