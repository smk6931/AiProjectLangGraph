import json
from app.clients.openai import client
from app.inquiry.state import InquiryState

async def answer_node(state: InquiryState) -> InquiryState:
    """
    [Answer Node]
    수집된 모든 정보(SQL 결과, RAG 문서, 웹 검색 등)를 종합하여 
    최종 답변을 JSON 형태로 생성합니다.
    """
    question = state["question"]
    category = state.get("category", "general")
    sales_data = state.get("sales_data", {})
    search_results = state.get("search_results", [])
    
    print(f"💬 [Answer] Generating response for {category}")

    # 컨텍스트 조립
    context_text = ""
    if category == "sales":
        context_text = f"SQL Result: {sales_data.get('sql_result', 'No Data')}\n"
        context_text += f"Reviews: {sales_data.get('recent_reviews', 'No Reviews')}"
    else:
        context_text = "\n".join(search_results)
        
    system_prompt = f"""
    당신은 유능한 프랜차이즈 매니저 AI입니다.
    제공된 [Context]를 바탕으로 사용자의 [Question]에 답변하세요.
    
    [Context]
    {context_text}
    
    [Output Format (JSON)]
    {{
        "answer": "친절하고 전문적인 답변 텍스트 (Markdown 지원)",
        "chart_data": [ {{ "label": "...", "value": 100 }} ], // (매출 질문 시 데이터)
        "key_metrics": [ {{ "label": "총 매출", "value": "1,000,000원", "delta": "+5%" }} ],
        "used_docs": [] // 참고한 문서 인덱스 (RAG인 경우)
    }}
    """
    
    final_answer = {}
    
    try:
        res = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        final_answer = json.loads(content)
        
    except Exception as e:
        print(f"❌ [Answer Error] {e}")
        final_answer = {
            "answer": "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다.",
            "chart_data": [],
            "key_metrics": []
        }
        
    return {"final_answer": final_answer}
