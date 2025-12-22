"""
LangChain만으로 리포트 생성 워크플로우 구현 (LangGraph 없이)

이 파일은 report_graph.py의 기능을 LangChain의 Chain만으로 구현한 버전입니다.
비교 목적으로 작성되었습니다.
"""
import json
import asyncio
from typing import Dict, Any, List
from datetime import date

# LangChain 관련 임포트
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# 프로젝트 모듈 임포트
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store
from app.clients.genai import genai_generate_text


# ========== 1. 각 단계를 Runnable로 구현 ==========

async def fetch_data_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """데이터 수집 단계"""
    store_id = inputs["store_id"]
    store_name = inputs["store_name"]
    
    print(f"📊 [LangChain] '{store_name}' 데이터 수집 시작")
    
    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)
    
    return {
        **inputs,
        "sales_data": sales[:7],
        "reviews_data": reviews[:15],
        "execution_logs": [f"✅ [LangChain] 데이터 수집 완료"]
    }


async def analyze_data_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """데이터 분석 단계 (LangChain LLM 사용)"""
    print("🧠 [LangChain] AI 분석 시작")
    
    sales_summary = [
        {"date": str(s['order_date']), "rev": float(s['daily_revenue'])} 
        for s in inputs["sales_data"]
    ]
    review_summary = [
        {"rate": r['rating'], "txt": r['review_text']} 
        for r in inputs["reviews_data"]
    ]
    
    # LangChain의 PromptTemplate 사용
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", "당신은 프랜차이즈 경영 전문가입니다."),
        ("user", """다음 데이터를 분석해주세요.
            매장: {store_name}
            매출현황: {sales_data}
            리뷰현황: {reviews_data}

            응답은 반드시 아래 JSON 형식으로만 할 것:
            {{
                "summary": "종합 분석 요약 (3줄)",
                "marketing_strategy": "마케팅 제안",
                "operational_improvement": "운영 개선 제안",
                "risk_assessment": {{"risk_score": 80, "main_risks": [], "suggestion": ""}}
            }}"""
        )
    ])
    
    # LLM 설정
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0
    )
    
    # JSON 파서
    parser = JsonOutputParser()
    
    # Chain 구성: Prompt → LLM → Parser
    chain = prompt_template | llm | parser
    
    # 실행
    report_dict = await chain.ainvoke({
        "store_name": inputs["store_name"],
        "sales_data": json.dumps(sales_summary),
        "reviews_data": json.dumps(review_summary, ensure_ascii=False)
    })
    
    return {
        **inputs,
        "final_report": report_dict,
        "execution_logs": inputs.get("execution_logs", []) + ["✅ [LangChain] 분석 완료"]
    }


async def save_report_step(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """리포트 저장 단계"""
    print("💾 [LangChain] 리포트 저장 중")
    
    report_dict = inputs["final_report"]
    
    db_report = StoreReport(
        store_id=inputs["store_id"],
        report_date=date.today(),
        report_type="AI_CHAIN_REPORT",  # LangChain 버전임을 표시
        summary=report_dict['summary'],
        marketing_strategy=report_dict['marketing_strategy'],
        operational_improvement=report_dict['operational_improvement'],
        risk_assessment=report_dict['risk_assessment']
    )
    
    with SessionLocal() as session:
        session.query(StoreReport).filter_by(
            store_id=inputs["store_id"], 
            report_date=date.today()
        ).delete()
        session.add(db_report)
        session.commit()
    
    return {
        **inputs,
        "execution_logs": inputs.get("execution_logs", []) + ["🏁 [LangChain] 프로세스 종료"]
    }


# ========== 2. Chain으로 순차 연결 ==========

def create_report_chain():
    """
    LangChain만으로 순차 실행 체인 구성
    
    LangGraph와 달리:
    - 상태 관리가 명시적이지 않음 (딕셔너리로 전달)
    - 조건부 분기나 루프가 복잡함
    - 각 단계가 독립적인 함수로 구현됨
    """
    
    # RunnableLambda로 각 단계를 Runnable로 변환
    fetch_chain = RunnableLambda(fetch_data_step)
    analyze_chain = RunnableLambda(analyze_data_step)
    save_chain = RunnableLambda(save_report_step)
    
    # 순차 연결: fetch → analyze → save
    full_chain = fetch_chain | analyze_chain | save_chain
    
    return full_chain


# ========== 3. 실행 함수 ==========

async def run_report_chain(store_id: int, store_name: str):
    """LangChain 체인 실행"""
    initial_input = {
        "store_id": store_id,
        "store_name": store_name,
        "execution_logs": []
    }
    
    chain = create_report_chain()
    result = await chain.ainvoke(initial_input)
    
    return result


# ========== 4. 테스트 실행 ==========

if __name__ == "__main__":
    async def test():
        result = await run_report_chain(store_id=1, store_name="테스트점")
        print("\n=== 최종 결과 ===")
        print(f"로그: {result['execution_logs']}")
        print(f"리포트: {result['final_report']}")
    
    asyncio.run(test())
