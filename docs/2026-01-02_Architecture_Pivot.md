# 🏗️ Architecture Pivot: LangGraph Autonomous vs Human-in-the-Loop
**Date:** 2026-01-02  
**Author:** AI Project Team  

## 1. 배경 및 초기 설계 (The Problem)

### 초기 접근 방식: 완전 자동화 (Autonomous Agent)
초기에는 `LangGraph`를 사용하여 사용자 질문부터 최종 답변까지 **한 번에(End-to-End)** 실행되는 완전 자동화 파이프라인을 구축했습니다.
이 방식은 "사용자의 개입 없이(Autonomous)" 스스로 판단하고 행동한다는 점에서 이상적이었으나, **치명적인 단점**이 발견되었습니다.

### 발견된 문제점
1.  **환각(Hallucination) 위험**: LLM이 잘못된 매장을 선택하거나, 엉뚱한 문서를 참고해도 사용자가 이를 **중간에 바로잡을 수 없었습니다.**
2.  **민감한 데이터 접근**: 매출 데이터나 재무 분석의 경우, AI가 어떤 데이터를 보고 분석하는지 **사용자의 승인(Confirmation)** 절차가 필요했습니다.
3.  **UI 상호작용의 한계**: LangGraph의 실행 루프(`node` -> `edge` -> `node`) 중간에 웹 UI에서의 사용자 클릭 이벤트를 끼워넣는 것이 기술적으로 복잡했습니다. (`interrupt` 기능이 있으나 상태 관리가 까다로움)

---

## 2. 아키텍처 변경: Human-in-the-Loop (The Solution)

우리는 LangGraph의 그래프 **구조(Structure)는 유지하되**, 실행 방식(Execution)을 **단계별 수동 제어(Step-by-Step Manual Control)**로 변경했습니다.

### 변경된 흐름 비교

| 구분 | (Old) Autonomous Graph | (New) Sequential Checkpoint |
| :--- | :--- | :--- |
| **실행 방식** | `graph.invoke(input)` (Start -> End) | `API 1` (질문 분석) -> **STOP(UI)** -> `API 2` (답변 생성) |
| **사용자 개입** | 불가능 (결과 통보만 받음) | **가능 (검색 결과 확인 및 승인 후 진행)** |
| **안전성** | 낮음 (AI의 판단 미스 리스크) | **높음 (Human Check 도입)** |

### 구현 상세 (Sequential Logic)
`inquiry_agent.py`에서 단일 그래프 실행 로직을 제거하고, 두 개의 명시적 함수로 분리했습니다.

1.  **Phase 1: `run_search_check` (진단 및 검색)**
    *   질문을 분류(Router)하고 필요한 데이터를 수집합니다.
    *   **여기서 멈춤!** 수집된 데이터를 UI로 반환합니다.
2.  **Phase 2: `run_final_answer_stream` (최종 답변)**
    *   사용자가 UI에서 "분석 시작" 버튼을 누르면 실행됩니다.
    *   Phase 1의 상태를 이어받아 최종 분석 및 답변을 생성합니다.

---

## 3. 결론 및 인사이트 (Takeaways)

이 리팩토링 과정을 통해 얻은 핵심 교훈은 다음과 같습니다.

*   **"모든 것을 자동화하는 것이 정답은 아니다."** 
    *   특히 데이터 분석과 같이 **정확성**이 중요한 도메인에서는 AI와 사람이 협업하는 **Human-in-the-Loop** 설계가 필수적입니다.
*   **"유연한 아키텍처의 중요성"**
    *   LangGraph의 `Node` 기능을 모듈화해둔 덕분에, 그래프 실행 로직을 들어내고 순차 실행 로직으로 변경하는 과정이 매우 수월했습니다. (재사용성 입증)

> *기술적으로는 LangGraph의 `interrupt` 기능을 고도화하여 해결할 수도 있었으나, 현재의 웹 기반 아키텍처에서는 **API 엔드포인트를 분리하는 것**이 상태 관리(State Management) 측면에서 훨씬 안정적이고 직관적인 해결책이었습니다.*

---

## 4. 상세 UI/UX 플로우 및 설계 의도 (Implementation Details)

사용자(점주)가 AI를 신뢰하고 사용할 수 있도록 **3단계 상호작용 프로세스(3-Step Interaction Process)**를 설계했습니다.

### 🔄 Flow Overview
1.  **Phase 1: Intent & Check (의도 파악 및 초동 조사)**
    *   **User Action**: 프롬프트 입력 (`/inquiry/check`)
    *   **System**: 유저 질문을 백엔드로 전송하여 **Router(분류)** 및 **Diagnosis/Retrieval(데이터 조회)** 수행.
    *   **Why?**: AI가 질문을 제대로 이해했는지, 어떤 데이터를 볼 것인지 **미리 보여주기 위함**입니다. 답변부터 바로 생성하면 나중에 "어? 이 데이터 아닌데?" 하고 되돌릴 수 없기 때문입니다.

2.  **Phase 2: Human Verification (사용자 검증 및 선택)**
    *   **User Action**: AI가 제안한 **분석 계획(Plan)** 또는 **참고 문서(Candidate Docs)** 확인.
        *   *Sales*: 분석할 지점과 데이터 소스 확인 -> "분석 시작" 클릭.
        *   *Manual*: 검색된 매뉴얼 중 엉뚱한 문서 체크 해제 -> "답변 생성" 클릭.
    *   **Why?**: **환각(Hallucination) 방지의 핵심 단계**입니다. AI가 잘못된 문서를 참고하려 할 때, 사용자가 이를 사전에 차단(Filtering)할 수 있어 최종 답변의 품질이 비약적으로 상승합니다.

3.  **Phase 3: Execution & Streaming (최종 실행 및 응답)**
    *   **User Action**: 최종 승인 버튼 클릭 (`/inquiry/generate/stream`)
    *   **System**: Phase 1에서 확보한 데이터(Context)를 재사용하여 **LLM이 최종 답변을 스트리밍(`yield`)** 방식으로 생성.
    *   **Why?**: 
        *   **성능 최적화**: Phase 1에서 이미 가져온 데이터를 Phase 3로 넘겨주어(`Context Reuse`), 무거운 DB 조회를 두 번 하지 않도록 설계했습니다. (속도 2배 향상)
        *   **사용자 경험(UX)**: 긴 생성 시간을 견디지 않도록 실시간으로 토큰을 뿌려주어(Streaming) 체감 대기 시간을 줄였습니다.

---

## 5. 백엔드 서비스 구조 설계 (Data Access Strategy with CQRS)

AI 에이전트의 데이터 접근 로직을 기존 서비스 계층과 분리하여 **CQRS(Command Query Responsibility Segregation)** 패턴을 일부 차용했습니다.

### 🏗️ 구조적 분리 (Separation of Concerns)

| 구분 | **운영 서비스 (`app/service/*.py`)** | **AI 에이전트 노드 (`app/inquiry/nodes/*.py`)** |
| :--- | :--- | :--- |
| **주요 역할** | **Command (쓰기/수정) & Simple Query** | **Complex Query (복합 조회/분석)** |
| **사용 사례** | 주문 생성, 메뉴 등록, 단일 조회 | "지난주 대비 매출 추이는?", "비 오는 날 인기 메뉴는?" |
| **구현 방식** | ORM 기반의 단순 CRUD 메소드 | Raw SQL 기반의 복잡한 집계(Aggregation) 및 조인(Join) |

### 💡 설계 의도 (Design Rationale)
1.  **성능 최적화 (Performance)**: 
    *   기존 ORM 객체를 재사용할 경우, 분석에 불필요한 필드까지 모두 로딩하는 **Over-fetching** 문제가 발생합니다.
    *   AI 에이전트는 통계 데이터(Sum, Count, Group By)가 주로 필요하므로, 이에 최적화된 **전용 SQL**을 작성하여 조회 속도를 높였습니다.
2.  **의존성 분리 (Decoupling)**:
    *   운영 로직(주문 처리 등)이 변경되더라도, AI 분석 로직은 영향을 받지 않도록 격리했습니다.
    *   반대로 AI를 위해 조회 로직을 수정해도, 핵심 운영 서비스의 안정성은 보장됩니다.
3.  **유연한 질의 (Flexible Querying)**:
    *   LLM이 필요로 하는 데이터 형태(JSON, Markdown Summary)로 DB에서 바로 가공하여 가져오기 위해, 서비스 계층을 거치지 않고 직접 데이터에 접근하는 방식이 훨씬 효율적이었습니다.
