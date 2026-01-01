import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.inquiry.state import InquiryState

llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=settings.OPENAI_API_KEY)

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
        
    # 프롬프트
    answer_prompt = ChatPromptTemplate.from_template("""
        SYSTEM: 당신은 유능한 프랜차이즈 매니저 AI입니다.
        제공된 [Context]를 바탕으로 사용자의 [Question]에 답변하세요.
        
        [Context]
        {context}
        
        [Output Requirements]
        - 반드시 아래 JSON 포맷을 준수하세요.
        - `answer`: 친절하고 전문적인 답변 텍스트 (Markdown 지원).
        - `chart_data`: (매출 질문인 경우) 차트에 사용할 데이터 리스트. 없으면 [].
        - `key_metrics`: (매출 질문인 경우) 강조할 숫자 지표.
        
        [JSON Format]
        {{
            "answer": "안녕하세요 점주님, 요청하신...",
            "chart_data": [ {{ "label": "...", "value": 100 }} ],
            "key_metrics": [ {{ "label": "총 매출", "value": "1,000,000원", "delta": "+5%" }} ],
            "used_docs": [] // 참고한 문서 인덱스 (RAG인 경우)
        }}
        
        USER: {question}
    """)
    
    chain = answer_prompt | llm
    res = await chain.ainvoke({"context": context_text, "question": question})
    
    try:
        clean_json = res.content.replace("```json", "").replace("```", "").strip()
        final_answer = json.loads(clean_json)
    except:
        final_answer = {
            "answer": res.content,
            "chart_data": [],
            "key_metrics": []
        }
        
    return {"final_answer": final_answer}
