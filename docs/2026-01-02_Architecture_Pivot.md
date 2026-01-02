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
