"""SPC Analyzer Agent Service - POST /invoke."""
from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from tools import mcp_calculate_cpk, mcp_detect_ooc, mcp_run_spc

load_dotenv()

app = FastAPI(title="SPC Analyzer Agent", version="0.1.0")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Tool 스펙 (Claude에게 노출할 JSON Schema) ──────────────────────────
TOOL_SPECS: dict[str, dict] = {
    "mcp_run_spc": {
        "name": "mcp_run_spc",
        "description": "LOT의 공정 파라미터 측정값으로 SPC 관리도를 분석하고 UCL/LCL/측정점을 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id":    {"type": "string", "description": "LOT ID"},
                "parameter": {"type": "string", "description": "측정 파라미터명 (기본: gate_oxide_thickness)"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_calculate_cpk": {
        "name": "mcp_calculate_cpk",
        "description": "공정 능력 지수(Cp, Cpk, Cpu, Cpl)를 계산하고 등급을 평가합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id": {"type": "string", "description": "LOT ID"},
                "usl":    {"type": "number", "description": "규격 상한 (기본: 108.0 Å)"},
                "lsl":    {"type": "number", "description": "규격 하한 (기본: 92.0 Å)"},
            },
            "required": ["lot_id"],
        },
    },
    "mcp_detect_ooc": {
        "name": "mcp_detect_ooc",
        "description": "Western Electric Rules를 적용해 OOC(Out of Control) 위반점을 탐지합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lot_id": {"type": "string", "description": "LOT ID"},
            },
            "required": ["lot_id"],
        },
    },
}

# ── Tool 실행 디스패처 ─────────────────────────────────────────────────
def dispatch_tool(name: str, args: dict) -> str:
    if name == "mcp_run_spc":
        result = mcp_run_spc(**args)
    elif name == "mcp_calculate_cpk":
        result = mcp_calculate_cpk(**args)
    elif name == "mcp_detect_ooc":
        result = mcp_detect_ooc(**args)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result, ensure_ascii=False)


# ── Request / Response 모델 ────────────────────────────────────────────
class InvokeRequest(BaseModel):
    input:   str
    lot_id:  str | None = None
    context: dict | None = None   # 이전 노드(data_collector) 출력
    tools:   list[str]            # Planner가 선택한 tool 목록


class InvokeResponse(BaseModel):
    output:  str
    lot_id:  str | None
    agent:   str = "spc_analyzer"


# ── /invoke 엔드포인트 ─────────────────────────────────────────────────
@app.post("/invoke", response_model=InvokeResponse)
async def invoke(req: InvokeRequest) -> InvokeResponse:
    # 요청된 tool 스펙만 Claude에 노출
    available_tools = [TOOL_SPECS[t] for t in req.tools if t in TOOL_SPECS]

    # 이전 노드 context를 user 메시지에 포함
    user_content = req.input
    if req.lot_id:
        user_content += f"\n\nLOT ID: {req.lot_id}"
    if req.context:
        user_content += f"\n\n[DataCollector 수집 결과]\n{json.dumps(req.context, ensure_ascii=False, indent=2)}"

    messages: list[dict] = [{"role": "user", "content": user_content}]

    # ── Claude Agent Loop ──────────────────────────────────────────────
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=(
                "당신은 반도체 공정 SPC(Statistical Process Control) 분석 전문 에이전트입니다. "
                "주어진 LOT의 SPC 분석, Cpk 계산, OOC 탐지를 수행하고 "
                "분석 결과를 간결하고 명확하게 한국어로 보고하세요."
            ),
            tools=available_tools,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return InvokeResponse(output=final_text, lot_id=req.lot_id)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     result_str,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user",      "content": tool_results})


# ── 헬스체크 ──────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "agent": "spc_analyzer"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
