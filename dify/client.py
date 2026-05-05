from __future__ import annotations

import json

import httpx
import yaml
from rich.console import Console

console = Console()


class DifyWorkflowClient:
    """
    Dify Workflow REST API 래퍼

    ─ 공개 App API (DIFY_API_KEY = App API Key) ─────────────────
    POST /v1/workflows/run          → 배포된 워크플로우 실행
    GET  /v1/workflows/run/{run_id} → 실행 결과 조회

    ─ Console API (별도 인증 필요) ──────────────────────────────
    POST /console/api/apps/import   → DSL YAML로 새 앱 생성
    POST /console/api/apps/{id}/workflows/draft → 드래프트 업데이트
    POST /console/api/apps/{id}/workflows/publish → 워크플로우 배포

    ※ Console API는 Dify 자체 계정 세션 인증이 필요합니다.
       Self-hosted 환경에서는 DIFY_CONSOLE_TOKEN 환경변수 사용.
    """

    def __init__(
        self,
        base_url: str,
        app_api_key: str,
        console_token: str | None = None,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.console_base = self.base_url.replace("/v1", "")
        self.app_api_key = app_api_key
        self.console_token = console_token
        self.timeout = timeout

    @property
    def _app_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.app_api_key}",
            "Content-Type": "application/json",
        }

    @property
    def _console_headers(self) -> dict:
        if not self.console_token:
            raise RuntimeError("Console API는 console_token이 필요합니다.")
        return {
            "Authorization": f"Bearer {self.console_token}",
            "Content-Type": "application/json",
        }

    def run_workflow(
        self,
        inputs: dict,
        user: str = "orchestrator",
        response_mode: str = "blocking",
    ) -> dict:
        url = f"{self.base_url}/workflows/run"
        payload = {
            "inputs": inputs,
            "response_mode": response_mode,
            "user": user,
        }

        console.log(f"[bold cyan]Stage 3[/] 워크플로우 실행 요청: [dim]{url}[/]")

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._app_headers, json=payload)
            resp.raise_for_status()
            result = resp.json()

        console.log(f"[green]✓[/] 실행 완료 — task_id: {result.get('task_id', 'N/A')}")
        return result

    def get_run_result(self, workflow_run_id: str) -> dict:
        url = f"{self.base_url}/workflows/run/{workflow_run_id}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, headers=self._app_headers)
            resp.raise_for_status()
        return resp.json()

    def import_app_from_dsl(self, payload: dict) -> dict:
        yaml_content = yaml.dump(payload, allow_unicode=True, sort_keys=False)
        url = f"{self.console_base}/console/api/apps/import"

        console.log(f"[bold cyan]Stage 3[/] Console API 앱 Import: [dim]{url}[/]")

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                url,
                headers={**self._console_headers, "Content-Type": "application/x-yaml"},
                content=yaml_content.encode("utf-8"),
            )
            resp.raise_for_status()
            result = resp.json()

        console.log(f"[green]✓[/] 앱 생성 완료 — app_id: {result.get('id')}")
        return result

    def update_draft(self, app_id: str, graph: dict) -> dict:
        url = f"{self.console_base}/console/api/apps/{app_id}/workflows/draft"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._console_headers, json={"graph": graph})
            resp.raise_for_status()
        return resp.json()

    def publish_workflow(self, app_id: str) -> dict:
        url = f"{self.console_base}/console/api/apps/{app_id}/workflows/publish"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=self._console_headers)
            resp.raise_for_status()
        return resp.json()

    def run_workflow_stream(self, inputs: dict, user: str = "orchestrator"):
        url = f"{self.base_url}/workflows/run"
        payload = {"inputs": inputs, "response_mode": "streaming", "user": user}

        with httpx.Client(timeout=None) as client:
            with client.stream("POST", url, headers=self._app_headers, json=payload) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        try:
                            yield json.loads(line[6:])
                        except json.JSONDecodeError:
                            pass
