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
from langgraph.graph.message import add_messages

# 기존 프로젝트 서비스 및 모델 임포트
from app.core.db import SessionLocal
from app.report.report_schema import StoreReport
from app.order.order_service import select_daily_sales_by_store
from app.review.review_service import select_reviews_by_store

# 1. 에이전트 상태(State) 정의
class AgentState(TypedDict):
    # add_messages 리듀서를 사용하여 메시지가 자동으로 누적되도록 합니다.
    messages: Annotated[List[BaseMessage], add_messages]
    store_id: int
    store_name: str

# 2. 자율적으로 실행될 툴(Tool) 정의

@tool
async def fetch_store_data(store_id: int):
    """지점의 최근 매출과 리뷰 데이터를 수집합니다. 분석을 위해 처음 실행해야 합니다."""
    print(f"🛠️ [Tool] 데이터 수집 중 (ID: {store_id})")
    sales = await select_daily_sales_by_store(store_id)
    reviews = await select_reviews_by_store(store_id)
    
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
    """분석이 완료된 전략 리포트를 DB에 저장합니다. 분석의 마지막 단계에 호출하세요."""
    print(f"🛠️ [Tool] 리포트 저장 중 (ID: {store_id})")
    
    db_report = StoreReport(
        store_id=store_id,
        report_date=date.today(),
        report_type="AI_AUTONOMOUS_REPORT",
        summary=summary,
        marketing_strategy=marketing_strategy,
        operational_improvement=operational_improvement,
        risk_assessment={"risk_score": risk_score, "generated_at": str(date.today())}
    )
    
    try:
        with SessionLocal() as session:
            session.query(StoreReport).filter_by(store_id=store_id, report_date=date.today()).delete()
            session.add(db_report)
            session.commit()
        return "성공적으로 저장되었습니다."
    except Exception as e:
        print(f"❌ [Tool] 저장 중 에러: {e}")
        return f"저장 실패: {str(e)}"

# 3. 노드(Node) 정의

async def call_model(state: AgentState):
    """LLM이 현재 상태를 보고 다음 행동을 결정하는 노드"""
    print("\n" + "═"*60)
    print(f"🤖 [Agent: Reasoning] '{state['store_name']}' 지점 분석 중...")
    
    messages = state.get("messages", [])
    
    # 1. AI가 읽을 이전 메시지 요약 로그
    if messages:
        last_msg = messages[-1]
        print(f"� [Input Context]: 마지막 메시지 타입 -> {type(last_msg).__name__}")
        if hasattr(last_msg, 'content') and last_msg.content:
            # 내용이 너무 길면 앞부분만 출력
            preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
            print(f"   내용 요약: {preview}")

    # 2. 초기 메시지 설정
    new_messages = []
    if not messages:
        print("🚩 [System] 분석 프로세스를 처음 시작합니다. 초기 지침 생성 중...")
        sys_msg = SystemMessage(content=f"당신은 '{state['store_name']}' 지점의 경영 전략가입니다. fetch_store_data로 데이터를 수집하고 분석한 뒤, 반드시 save_strategic_report로 리포트를 저장해야 합니다. 판단 근거를 한국어로 명확히 밝혀주세요.")
        prompt = HumanMessage(content="분석을 시작하고 리포트를 저장해주세요.")
        messages = [sys_msg, prompt]
        new_messages.extend(messages)

    # LLM 설정
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0
    )
    llm_with_tools = llm.bind_tools([fetch_store_data, save_strategic_report])
    
    # AI에게 생각 전개 요청
    response = await llm_with_tools.ainvoke(messages)
    
    # 3. AI의 생각(Thought) 출력
    if response.content:
        print(f"\n💡 [AI Thought]:\n{response.content}")
    
    # 4. AI가 결정한 툴 호출 및 매개변수 매핑 로그
    if response.tool_calls:
        print(f"\n🎯 [Tool Call Decision]:")
        for tool_call in response.tool_calls:
            print(f"   함수명: {tool_call['name']}")
            print(f"   매핑된 인자(Args): {json.dumps(tool_call['args'], indent=5, ensure_ascii=False)}")
    
    new_messages.append(response)
    print("═"*60)
    
    return {"messages": new_messages}

# 4. 그래프(Graph) 빌드

def create_autonomous_report_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode([fetch_store_data, save_strategic_report]))
    
    workflow.set_entry_point("agent")

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        # 툴 호출이 있으면 tools 노드로, 없으면 종료
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

# 실행용 전역 객체
autonomous_report_app = create_autonomous_report_graph()
