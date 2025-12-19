import os
import json
from typing import Annotated, TypedDict, List, Dict, Any, Union
from datetime import date

# LangChain & LangGraph 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# 기존 프로젝트 서비스 및 모델 임포트
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store

# 1. 에이전트 상태(State) 정의
# messages: 대화 내역 (LLM의 판단과 툴 호출 결과가 누적됨)


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "Chat History"]
    store_id: int
    store_name: str

# 2. 자율적으로 실행될 툴(Tool) 정의


@tool
async def fetch_store_data(store_id: int):
    """
    지점의 최근 매출과 리뷰 데이터를 수집합니다.
    분석을 시작하기 위해 가장 먼저 호출해야 하는 툴입니다.
    """
    print(f"🛠️ [Tool] 지점 데이터 수집 중 (ID: {store_id})")
    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)

    # LLM이 읽기 좋게 요약해서 반환
    data_summary = {
        "sales": [{"date": str(s['order_date']), "revenue": float(s['daily_revenue'])} for s in sales[:7]],
        "reviews": [{"rating": r['rating'], "comment": r['review_text']} for r in reviews[:15]]
    }
    return json.dumps(data_summary, ensure_ascii=False)


@tool
async def save_strategic_report(
    store_id: int,
    summary: str,
    marketing_strategy: str,
    operational_improvement: str,
    risk_score: int
):
    """
    분석이 완료된 후 최종 리포트를 데이터베이스에 저장합니다.
    모든 분석이 끝난 후 마지막에 호출해야 합니다.
    """
    print(f"🛠️ [Tool] 분석 리포트 저장 중 (ID: {store_id})")

    db_report = StoreReport(
        store_id=store_id,
        report_date=date.today(),
        report_type="AI_AUTONOMOUS_REPORT",
        summary=summary,
        marketing_strategy=marketing_strategy,
        operational_improvement=operational_improvement,
        risk_assessment={"risk_score": risk_score,
                         "generated_at": str(date.today())}
    )

    try:
        with SessionLocal() as session:
            # 중복 방지를 위해 오늘자 기존 리포트 삭제
            session.query(StoreReport).filter_by(
                store_id=store_id, report_date=date.today()).delete()
            session.add(db_report)
            session.commit()
        return "성공적으로 리포트가 저장되었습니다."
    except Exception as e:
        return f"저장 중 오류 발생: {str(e)}"

# 3. 노드(Node) 정의


async def call_model(state: AgentState):
    """LLM이 현재 상태를 보고 다음 행동(툴 호출 혹은 답변)을 결정하는 노드"""
    prompt = f"""
    당신은 프랜차이즈 경영 전략 AI 에이전트입니다.
    매장명: {state['store_name']} (ID: {state['store_id']})
    
    작업 순서:
    1. fetch_store_data 툴을 호출하여 필요한 데이터를 가져옵니다.
    2. 수집된 데이터를 바탕으로 매출 추이와 고객 리뷰를 분석합니다.
    3. 분석 결과를 바탕으로 save_strategic_report 툴을 호출하여 저장합니다.
    4. 모든 작업이 완료되면 최종 완료 메시지를 작성합니다.
    """

    # 시스템 메시지 추가 (첫 호출시에만)
    messages = state["messages"]
    if not messages:
        messages = [SystemMessage(content=prompt)] + messages

    # LLM 설정 및 툴 바인딩
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )
    llm_with_tools = llm.bind_tools([fetch_store_data, save_strategic_report])

    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

# 4. 그래프(Graph) 빌드


def create_autonomous_report_graph():
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(
        [fetch_store_data, save_strategic_report]))

    # 시작점 설정
    workflow.set_entry_point("agent")

    # 조건부 엣지: LLM이 툴을 호출했으면 tools 노드로, 아니면 종료(END)로 이동
    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "tools"
        return END

    workflow.add_conditional_edges("agent", should_continue)

    # 툴 실행 후 다시 agent에게 판단을 맡김 (루프 형성)
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# 실행용 앱 객체 생성
autonomous_report_app = create_autonomous_report_graph()
