# Dify Workflow DSL 구조 이해

## 노드 타입 필드

노드에는 타입 필드가 **두 곳**에 있습니다:

```yaml
# workflow_dsl.yaml:173-176
- type: custom          # ← React Flow 렌더러 타입 (항상 "custom")
  id: node_1_data_collector
  data:
    type: tool          # ← 실제 노드 기능 타입 (start/tool/if-else/end 등)
```

| 필드 | 위치 | 의미 |
|------|------|------|
| `type: custom` | 노드 최상위 | React Flow가 커스텀 컴포넌트로 렌더링하라는 지시 |
| `data.type` | `data` 블록 안 | 실제 노드의 기능/로직 타입 |

### 왜 항상 `custom`인가?

Dify는 React Flow 라이브러리로 그래프 UI를 구성하는데, React Flow의 기본 노드 타입(`input`, `output`, `default`)을 쓰지 않고 **모든 노드를 자체 커스텀 컴포넌트로 구현**했기 때문입니다.

즉, `type: custom`은 Dify가 자체 제작한 노드 UI 컴포넌트를 사용한다는 의미이고, 실제 노드 동작은 `data.type`으로 결정됩니다. DSL을 직접 작성할 때 `type: custom`은 항상 고정값으로 사용하면 됩니다.

---

## `data.type` 종류

| 타입 | 설명 |
|------|------|
| `start` | 워크플로우 시작점, 입력 변수 정의 |
| `end` | 워크플로우 종료, 출력 변수 정의 |
| `tool` | 외부 API/MCP 도구 호출 |
| `if-else` | 조건 분기 |
| `llm` | LLM 모델 직접 호출 |
| `code` | Python/JS 코드 실행 |
| `http-request` | HTTP REST API 호출 |
| `knowledge-retrieval` | 지식 베이스 검색 (RAG) |
| `question-classifier` | 질문 분류 |
| `template-transform` | Jinja2 템플릿 변환 |
| `variable-aggregator` | 변수 집계/병합 |
| `parameter-extractor` | LLM 기반 파라미터 추출 |
| `iteration` | 배열 순회 반복 |
| `loop` | 조건 기반 루프 (v0.6+) |
| `sub-workflow` | 서브 워크플로우 호출 |

---

## 변수/출력 데이터 타입

| 타입 | 설명 |
|------|------|
| `string` | 문자열 |
| `number` | 정수/실수 |
| `object` | JSON 객체 |
| `array[string]` | 문자열 배열 |
| `array[number]` | 숫자 배열 |
| `array[object]` | 객체 배열 |
| `file` | 단일 파일 |
| `array[file]` | 파일 목록 |

---

## Start 노드 입력 변수 타입

| 타입 | 설명 |
|------|------|
| `text-input` | 단일 라인 텍스트 |
| `paragraph` | 멀티라인 텍스트 |
| `number` | 숫자 입력 |
| `select` | 드롭다운 선택 |
| `file` | 단일 파일 업로드 |
| `file-list` | 다중 파일 업로드 |

---

## Tool Parameter 주입 방식

```yaml
# 다른 노드 출력값 참조
input:
  type: ref
  value: '{{#start.user_query#}}'

# 직접 값 지정
timeout:
  type: string
  value: "30"
```
