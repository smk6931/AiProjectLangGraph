# LangChain vs LangGraph 사용 전략 가이드

## 📌 핵심 결론

**현재 프로젝트에서는 LangGraph를 주로 사용하고, LangChain은 보조적으로 사용하는 것이 최적입니다.**

---

## 🔍 언제 무엇을 쓸까?

### ✅ LangGraph를 사용해야 할 때

#### 1. **복잡한 워크플로우가 필요할 때**
- 여러 단계가 순차/병렬/조건부로 실행되어야 함
- 상태(State)를 명시적으로 관리해야 함
- 에이전트가 툴을 선택하며 실행해야 함

**예시:**
```python
# ✅ LangGraph가 적합
- 리포트 생성: fetch → analyze → validate → save (순차)
- 자율 에이전트: agent → tools → agent (루프)
- 조건부 분기: validate 실패 시 retry
```

#### 2. **에이전트 시스템**
- AI가 스스로 다음 행동을 결정해야 함
- 툴을 동적으로 선택해야 함
- 대화형 인터랙션이 필요함

**예시:**
```python
# ✅ report_autonomous.py - LangGraph Agent
- AI가 fetch_store_data 툴을 호출할지 판단
- AI가 save_strategic_report 툴을 호출할지 판단
- 툴 실행 후 다시 AI에게 돌아가서 다음 행동 결정
```

#### 3. **상태 관리가 중요한 경우**
- 각 단계에서 이전 결과를 누적해야 함
- 실행 로그를 추적해야 함
- 재시도 로직이 필요함

**예시:**
```python
# ✅ LangGraph State
class ReportState(TypedDict):
    store_id: int
    sales_data: List[Dict]
    execution_logs: List[str]  # 로그 누적
    retry_count: int  # 재시도 추적
```

---

### ✅ LangChain을 사용해야 할 때

#### 1. **단순한 LLM 호출**
- 프롬프트 → LLM → 파싱 같은 단순 파이프라인
- 복잡한 상태 관리가 필요 없음
- 조건부 분기나 루프가 없음

**예시:**
```python
# ✅ LangChain이 적합
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

chain = prompt_template | llm | parser
result = await chain.ainvoke({"input": "..."})
```

#### 2. **RAG (Retrieval-Augmented Generation)**
- 벡터 검색 → 컨텍스트 추가 → LLM 호출
- LangChain의 체인으로 충분히 구현 가능

**예시:**
```python
# ✅ LangChain RAG
retriever = vectorstore.as_retriever()
chain = retriever | format_docs | prompt | llm
```

#### 3. **프롬프트 체이닝**
- 여러 LLM 호출을 순차적으로 연결
- 중간 결과를 다음 프롬프트에 전달

**예시:**
```python
# ✅ LangChain Chain
step1 = prompt1 | llm1
step2 = prompt2 | llm2
chain = step1 | (lambda x: {"context": x}) | step2
```

---

## 🎯 현재 프로젝트 권장 전략

### 현재 구조 (권장 ✅)

```
app/report/
├── report_graph.py          # LangGraph (순차 워크플로우)
├── report_autonomous.py     # LangGraph (에이전트)
└── report_service.py         # 서비스 레이어
```

**이유:**
1. **report_graph.py**: 순차 실행이지만 상태 관리와 로그 추적이 중요 → LangGraph 적합
2. **report_autonomous.py**: 에이전트가 툴을 선택하며 실행 → LangGraph 필수
3. **LangChain은 내부적으로 사용**: LLM 호출 시 LangChain의 ChatGoogleGenerativeAI 사용

---

### 혼용 예시 (선택적)

만약 특정 부분에서 LangChain만으로 충분하다면:

```python
# app/report/report_service.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

async def simple_analysis(sales_data, reviews_data):
    """단순 분석만 필요한 경우 - LangChain으로 충분"""
    prompt = ChatPromptTemplate.from_template("...")
    llm = ChatGoogleGenerativeAI(...)
    parser = JsonOutputParser()
    
    chain = prompt | llm | parser
    return await chain.ainvoke({"sales": sales_data, "reviews": reviews_data})
```

하지만 **현재 프로젝트에서는 굳이 필요 없음**. LangGraph가 이미 잘 작동하고 있으므로.

---

## 📊 비교표

| 특징 | LangChain | LangGraph |
|------|-----------|-----------|
| **단순 파이프라인** | ✅ 적합 | ❌ 오버킬 |
| **복잡한 워크플로우** | ❌ 복잡함 | ✅ 적합 |
| **에이전트 시스템** | ❌ 어려움 | ✅ 필수 |
| **상태 관리** | ❌ 수동 관리 | ✅ 자동 관리 |
| **조건부 분기** | ❌ 복잡함 | ✅ 쉬움 |
| **루프/재시도** | ❌ 어려움 | ✅ 쉬움 |
| **실행 추적** | ❌ 어려움 | ✅ 내장 |
| **시각화** | ❌ 없음 | ✅ LangSmith 지원 |

---

## 💡 실무 관점

### 면접에서 어필할 포인트

**"LangGraph와 LangChain을 적절히 선택해서 사용했습니다"**

1. **LangGraph 사용 이유:**
   - "복잡한 AI 워크플로우를 체계적으로 관리하기 위해 LangGraph를 선택했습니다"
   - "에이전트가 툴을 동적으로 선택하며 실행하는 자율형 시스템을 구현했습니다"
   - "상태 관리와 실행 로그 추적이 중요해서 LangGraph의 StateGraph를 사용했습니다"

2. **LangChain 사용 이유:**
   - "단순한 LLM 호출은 LangChain의 Chain으로 처리했습니다"
   - "프롬프트 템플릿과 출력 파서를 LangChain으로 구성했습니다"

3. **혼용 전략:**
   - "각 도구의 장점을 살려서 적절히 선택했습니다"
   - "LangGraph는 워크플로우 오케스트레이션, LangChain은 LLM 호출에 사용했습니다"

---

## 🚀 결론

### 현재 프로젝트 권장사항

1. **주로 LangGraph 사용** ✅
   - 리포트 생성 워크플로우 (report_graph.py)
   - 자율형 에이전트 (report_autonomous.py)

2. **LangChain은 내부적으로 사용** ✅
   - LLM 호출 시 ChatGoogleGenerativeAI (이미 사용 중)
   - 필요시 프롬프트 템플릿, 출력 파서 등

3. **굳이 섞을 필요 없음** ❌
   - 현재 구조가 이미 최적
   - LangGraph 내부에서 LangChain을 사용하고 있음
   - 추가 복잡도만 증가

### 테스트 폴더의 목적

`tests/test_report_chain.py`는:
- **비교 목적**: LangGraph vs LangChain 차이를 보여주기 위함
- **학습 목적**: 두 방식의 차이를 이해하기 위함
- **포트폴리오**: "두 방식을 모두 이해하고 있다"는 것을 보여주기 위함

**하지만 실제 프로덕션 코드는 LangGraph를 계속 사용하는 것을 권장합니다.**

---

## 📝 추가 학습 자료

- **LangGraph 공식 문서**: https://langchain-ai.github.io/langgraph/
- **LangChain 공식 문서**: https://python.langchain.com/
- **언제 무엇을 쓸까**: https://langchain-ai.github.io/langgraph/tutorials/introduction/






