# Dify Workflow DSL 생성

## `data.type` 종류

| 타입                  | 설명                              |
| --------------------- | --------------------------------- |
| `start`               | 워크플로우 시작점, 입력 변수 정의 |
| `end`                 | 워크플로우 종료, 출력 변수 정의   |
| `tool`                | 외부 API/MCP 도구 호출            |
| `if-else`             | 조건 분기                         |
| `llm`                 | LLM 모델 직접 호출                |
| `code`                | Python/JS 코드 실행               |
| `http-request`        | HTTP REST API 호출                |
| `knowledge-retrieval` | 지식 베이스 검색 (RAG)            |
| `question-classifier` | 질문 분류                         |
| `template-transform`  | Jinja2 템플릿 변환                |
| `variable-aggregator` | 변수 집계/병합                    |
| `parameter-extractor` | LLM 기반 파라미터 추출            |
| `iteration`           | 배열 순회 반복                    |
| `loop`                | 조건 기반 루프 (v0.6+)            |
| `sub-workflow`        | 서브 워크플로우 호출              |

```
    - id: node_1_data_collector
      width: 244
      height: 98
      position:         # 부모 컨테이너 기준 상대 좌표
        x: 360
        y: 200
      positionAbsolute:  # 항상 캔버스 좌상단 원점(0,0) 기준 실제 위치
        x: 360
        y: 200
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom      # dify애서는 react flow 기본 제공 node type이 아닌 custom 임
      data:
        type: http-request
        title: DataCollector Agent
        desc: LOT-2024-0812의 어제 SPC 데이터 및 장비 로그 수집
        method: POST
        url: http://agent-svc:8001/invoke
        authorization:
          type: no-auth
        headers: 'Content-Type: application/json'
        params: ''
        body:
          type: json
          data: '{"input": "{{#start.user_query#}}", "lot_id": "{{#start.lot_id#}}",
            "tools": ["mcp_query_db", "mcp_fetch_equipment_log"]}'
        timeout:
          max_connect_timeout: 10
          max_read_timeout: 30
          max_write_timeout: 10
        selected: false

```
