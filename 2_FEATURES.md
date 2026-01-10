# 🤖 AI Core Features Architecture

AI Store Manager의 핵심인 **Inquiry Agent**와 **Report Agent**의 아키텍처 및 구현 상세입니다.

---

## 💡 1. Inquiry Agent (지능형 매장 Q&A)
점주의 질문 의도를 파악하고, 사내 매뉴얼(RAG) 또는 외부 웹 검색(Google Grounding)을 통해 최적의 답변을 제공합니다.

### 🧠 Architecture Flow (LangGraph)
`Router` -> `Retrieve(Manual/Policy/Web)` -> `Analyze` -> `Answer`

1.  **Intent Classification (Router Node)**
    *   질문을 입력받아 **매출 분석(Sales)**, **매뉴얼 검색(Manual)**, **정책 확인(Policy)** 중 하나로 분류합니다.
    *   *Tech*: LLM 기반의 Zero-shot Classification.

2.  **Hybrid RAG System (Retrieval Node)**
    *   **Internal Data**: `pgvector`를 활용한 코사인 유사도 검색 (Manual/Policy DB).
    *   **External Data**: 내부 문서 유사도가 낮을 경우, **Google Search Grounding**으로 자동 전환하여 최신 웹 정보를 검색합니다.
    *   *Advantage*: "환불 규정" 같은 내부 정보와 "요즘 뜨는 메뉴" 같은 외부 정보를 하나의 에이전트가 처리 가능.

3.  **Context-Aware Answering (Answer Node)**
    *   검색된 정보(Context)와 질문을 결합하여 분석 보고서 형태의 답변을 생성합니다.
    *   **Citation Preservation**: 웹 검색 시 출처(URL)를 답변 하단에 `🌐 관련 링크` 섹션으로 자동 보존합니다.

---

## 📊 2. AI Strategy Report (주간 매출 분석)
매장의 매출 데이터를 심층 분석하고, 날씨/트렌드를 결합하여 구체적인 운영 전략을 제안합니다.

### 🧠 Logic Flow
1.  **Data Fetch & Integrity Check**
    *   DB(`sales_daily`)에서 매출 데이터를 조회하고, Python 레벨에서 주간 매출 합계를 재검증(`calculated_total_sales`)하여 데이터 정합성을 보장합니다.

2.  **Multi-Dimensional Analysis**
    *   **Growth Rate**: 전주 대비 성장률(WoW) 계산.
    *   **Menu Engineering**: 매출 상위(Top 5) 및 급락(Worst 5) 메뉴 도출.
    *   **Weather Correlation**: "비 오는 날 배달 매출 증가" 등 날씨와 매출의 상관관계를 분석.

3.  **AI Insight Generation (Gemini Pro)**
    *   수치 데이터 + 고객 리뷰 + 날씨 정보를 LLM에 주입하여 다음 4가지 섹션을 생성합니다:
        *   `<SALES_ANALYSIS>`: 수치적 근거 기반 분석
        *   `<STRATEGY>`: 다음 주 마케팅 전략
        *   `<IMPROVEMENT>`: 운영 개선점
        *   `<RISK>`: 리스크 점수 및 긴급 제언 (JSON Parsing)

4.  **Multi-Layer Caching Strategy**
    *   **L1 (Local Memory)**: 초고속 응답을 위한 인메모리 캐시.
    *   **L2 (Redis)**: 서버 재시작 후에도 유지되는 분산 캐시.
    *   **L3 (Persistent DB)**: 영구 보관을 위한 RDB 저장.
