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

---

## `_build_edges()` 상세 설명

[dsl_generator.py:223-293](../generator/dsl_generator.py)

### 함수 시그니처

```python
def _build_edges(
    self,
    steps: list[PlanStep],           # 오케스트레이션 플랜의 모든 스텝
    step_to_node_id: dict[int, str], # step 번호 → 노드 ID 매핑
    step_to_branch: dict[int, str],  # step 번호 → 브랜치 노드 ID 매핑 (조건 있는 스텝만)
    nodes: list[DifyNode],           # 생성된 모든 노드 목록
) -> list[dict]:
```

### 초기화 (230–233)

| 라인 | 코드 | 설명 |
|------|------|------|
| 230 | `node_type_map = {n.id: n.data.get("type", n.type) for n in nodes}` | 노드 ID → 타입 조회 딕셔너리. `make_edge`에서 `sourceType`/`targetType` 채울 때 사용 |
| 231 | `edges = []` | 최종 반환할 엣지 리스트 |
| 232 | `edge_counter = 0` | 엣지 ID `"edge_1"`, `"edge_2"`, ... 생성용 순번 |
| 233 | `wired_dep_to_branch: set[tuple] = set()` | `(dep_node_id, branch_id)` 중복 방지 집합. 여러 스텝이 같은 브랜치로 연결될 때 dep→branch 엣지 중복 생성 방지 |

### 내부 헬퍼: `make_edge` (235–252)

`nonlocal edge_counter`로 호출마다 카운터를 1씩 증가시켜 고유 ID를 부여한다.

```python
{
    "data": {
        "isInIteration": False,    # 이터레이션 블록 안에 있는지 (항상 False)
        "isInLoop": False,         # 루프 블록 안에 있는지 (항상 False)
        "sourceType": ...,         # node_type_map으로 조회한 출발 노드 타입
        "targetType": ...,         # node_type_map으로 조회한 도착 노드 타입
    },
    "id": f"edge_{edge_counter}",  # 고유 ID
    "source": src,                 # 출발 노드 ID
    "sourceHandle": source_handle, # 기본값 "source"; 브랜치는 "true"/"false"
    "target": tgt,                 # 도착 노드 ID
    "targetHandle": "target",      # 항상 "target" (Dify 스펙)
    "type": "custom",
    "zIndex": 0,
}
```

`sourceHandle`이 핵심 — Dify의 `if-else` 노드는 출력 핸들이 `"true"` / `"false"` / `"source"`로 구분됨

### 구간 1: start → 첫 번째 레이어 노드 연결 (255–262)

`depends_on`이 없는 스텝(최초 레이어)만 필터링하여 처리한다.

- **조건 있는 경우** (`s.step in step_to_branch`):
  ```
  start → branch_N → (sourceHandle="true") → node_id
  ```
- **조건 없는 경우**:
  ```
  start → node_id  (sourceHandle="source")
  ```

### 구간 2: 의존 노드 → 현재 노드 연결 (265–279)

`depends_on`이 있는 스텝만 처리한다. 의존하는 스텝이 여러 개일 수 있으므로 `for dep_step_num in step.depends_on`으로 반복한다.

- **현재 스텝에 조건이 있는 경우**:
  ```
  dep_node → branch  (wire_key로 중복 검사 후 skip)
  branch → node      (sourceHandle="true")
  ```
- **조건 없는 경우**:
  ```
  dep_node → node  (sourceHandle="source")
  ```

### 구간 3: 브랜치 false 경로 → end (282–284)

모든 `if-else` 노드를 찾아 `"false"` 핸들에서 `end`로 연결한다.  
조건 불만족 시 즉시 워크플로우 종료.

```python
branch_ids = {n.id for n in nodes if n.type == "if-else"}
for branch_id in branch_ids:
    edges.append(make_edge(branch_id, "end", source_handle="false"))
```

### 구간 4: 리프 노드 → end (287–291)

어떤 스텝에도 `depends_on`으로 참조되지 않는 "말단 스텝"을 찾아 `end`로 연결한다.

```python
step_nums_as_dep = {dep for s in steps for dep in s.depends_on}
leaf_steps = [s for s in steps if s.step not in step_nums_as_dep]
for s in leaf_steps:
    edges.append(make_edge(step_to_node_id[s.step], "end"))
```

### 전체 엣지 흐름 요약

```
start
  ├── (조건 없음) ──────────────► node_A
  └── (조건 있음) ── branch_N ──► node_B  (true 경로)
                         └──────► end     (false 경로)

node_A ──► node_C  (A에 의존)
node_B ──► node_C  (B에 의존)

node_C ──► end     (리프 노드)
```

---

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
