import json
from datetime import datetime, date
from typing import Dict, Any, List

# External App Imports
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.inquiry.inquiry_schema import InquiryState

# ===== Step 6: Answer Synthesis Node (답변 생성 - Analytical) =====
async def answer_node_v2(state: InquiryState) -> InquiryState:
    """수집한 데이터를 바탕으로 '표(Table)' 중심의 심층 분석 보고서 생성"""
    question = state["question"]
    category = state["category"]
    
    # 1. 컨텍스트 구성
    context_text = ""
    if category == "sales":
        if "sales_data" in state and state["sales_data"]:
             context_text = state["sales_data"].get("summary_text", "")
    else:
        # manual / policy 데이터 통합
        docs = state.get("manual_data", []) + state.get("policy_data", [])
        context_text = "\n\n".join(docs)
    
    # 2. 시스템 프롬프트 (Markdown Table 강제 -> 상황에 따라 유연하게)
    system_prompt = (
        "당신은 프랜차이즈 수석 데이터 분석가(Chief Analyst)입니다. "
        "제공된 [분석용 데이터]를 기반으로 팩트에 입각한 인사이트를 제공하세요.\n\n"
        
        "[작성 규칙 - Strict Rules]\n"
        "1. **Reference Citation (출처 명시)**: 답변 시 반드시 **참고한 매뉴얼/규정의 제목**과 핵심 내용을 인용해서 답변하세요. 예: '참고하신 [환불 규정 가이드]에 따르면...'\n"
        "2. **Evidence Based**: [분석용 데이터]에 있는 내용을 최우선으로 근거로 삼으세요. 유사도가 높게 나온 문서가 있다면 해당 내용을 바탕으로 답변을 구성하세요.\n"
        "3. **Markdown Table 필수**: Best/Worst 메뉴, 지점 비교 등 리스트 형태의 데이터는 **반드시 Markdown 표(Table)**로 작성하여 가독성을 높이세요. (컬럼 예: 순위, 메뉴명, 판매량, 매출액가, 리뷰 요약)\n"
        "4. **화폐 단위**: 반드시 **원(KRW)**을 사용하세요.\n"
        "5. **원인 분석**: 추측이 아니라 데이터에 근거한 분석만 수행하세요."
    )
    
    # 메시지 구성
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"질문: {question}\n\n[분석용 데이터]\n{context_text}")
    ]
    
    # 3. LLM 호출
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    response = await llm.ainvoke(messages)
    
    # 4. 결과 저장 (Structured JSON 생성)
    # UI가 차트, 메트릭, 리뷰 근거를 렌더링할 수 있도록 JSON 구조화
    final_output = {
        "answer": response.content,
        "category": category
    }
    
    if category == "sales" and "sales_data" in state:
        sd = state["sales_data"]
        final_output["chart_data"] = sd.get("chart_data")
        final_output["chart_setup"] = sd.get("chart_setup")
        final_output["key_metrics"] = sd.get("key_metrics")
        
        # [Evidence] 분석에 사용된 리뷰 데이터 전달 (메뉴별 + 전체 최신)
        # 중복 제거를 위해 리스트 합치기
        all_reviews = sd.get("recent_reviews", []) + sd.get("menu_specific_reviews", [])
        # 간단한 중복 제거 (내용 기준)
        seen = set()
        unique_reviews = []
        for r in all_reviews:
            if r.get('review_text') and r['review_text'] not in seen:
                seen.add(r['review_text'])
                unique_reviews.append(r)
                
        final_output["used_reviews"] = unique_reviews
        
        # UI는 'summary' 키가 없으면 'answer'를 텍스트로 출력하지 않음? 
        # detail에 답변 내용 저장
        final_output["detail"] = response.content
    else:
        final_output["detail"] = response.content

    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    state["final_answer"] = json.dumps(final_output, ensure_ascii=False, default=json_serial)
    
    print(f"✅ [Analyst Answer] 분석 보고서 생성 완료 (Structured)")
    return state
