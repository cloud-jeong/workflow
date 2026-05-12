"""공통 Agent 베이스 - Claude loop + FastAPI app factory."""
from __future__ import annotations

import json
import os
from collections.abc import Callable

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()
_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))


class InvokeRequest(BaseModel):
    input:   str
    lot_id:  str | None = None
    context: dict | None = None
    tools:   list[str]


class InvokeResponse(BaseModel):
    output: str
    lot_id: str | None
    agent:  str


def create_app(
    agent_id:      str,
    tool_specs:    dict[str, dict],
    dispatch_fn:   Callable[[str, dict], dict],
    system_prompt: str,
) -> FastAPI:
    app = FastAPI(title=f"{agent_id} Agent", version="0.1.0")

    @app.post("/invoke", response_model=InvokeResponse)
    async def invoke(req: InvokeRequest) -> InvokeResponse:
        available = [tool_specs[t] for t in req.tools if t in tool_specs]

        content = req.input
        if req.lot_id:
            content += f"\n\nLOT ID: {req.lot_id}"
        if req.context:
            content += (
                f"\n\n[이전 분석 결과]\n"
                f"{json.dumps(req.context, ensure_ascii=False, indent=2)}"
            )

        messages: list[dict] = [{"role": "user", "content": content}]

        while True:
            response = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system_prompt,
                tools=available,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                return InvokeResponse(output=text, lot_id=req.lot_id, agent=agent_id)

            if response.stop_reason == "tool_use":
                results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = dispatch_fn(block.name, block.input)
                        results.append({
                            "type":        "tool_result",
                            "tool_use_id": block.id,
                            "content":     json.dumps(result, ensure_ascii=False),
                        })
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user",      "content": results})

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "agent": agent_id}

    return app
