import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.inquiry.state import InquiryState

# LLM 설정
llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=settings.OPENAI_API_KEY)

async def router_node(state: InquiryState) -> InquiryState:
    """
    [Router Node]
    사용자의 질문 의도를 파악하여 적절한 카테고리(sales, manual, policy)로 분류합니다.
    """
    question = state["question"]
    
    # 프롬프트: 질문 분류가 핵심
    router_prompt = ChatPromptTemplate.from_template("""
        SYSTEM: 당신은 프랜차이즈 매장 관리 시스템의 '의도 분류기(Intent Classifier)'입니다.
        사용자의 질문을 분석하여 다음 카테고리 중 하나로 분류하고, 필요한 메타데이터를 추출하세요.

        [Categories]
        1. sales: 매출, 주문량, 인기 메뉴, 판매 추이, 리뷰 분석 등 데이터 기반 분석이 필요한 경우.
        2. manual: 레시피, 청소 방법, 기기 조작법 등 매장 운영 메뉴얼 관련.
        3. policy: 복장 규정, 급여, 근태, 본사 지침 등 규정 관련.
        4. general: 그 외 단순 인사말이나 일반적인 대화.

        [Output Format (JSON)]
        {{
            "category": "sales" | "manual" | "policy" | "general",
            "reason": "분류 이유",
            "extracted_info": {{
                "target_menu": [], // 언급된 메뉴명
                "period": "last_week" // 언급된 기간 (없으면 null)
            }}
        }}

        USER: {question}
    """)
    
    # LLM 호출
    chain = router_prompt | llm
    response = await chain.ainvoke({"question": question})
    
    try:
        # JSON 파싱
        cleaned_text = response.content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned_text)
        
        category = parsed.get("category", "general")
        requirements = parsed.get("extracted_info", {})
        
        print(f"🔀 [Router] Category: {category} | Info: {requirements}")
        
        # State 업데이트
        return {
            "category": category,
            "requirements": requirements
        }
        
    except Exception as e:
        print(f"⚠️ [Router Error] {e}")
        return {"category": "general", "requirements": {}}
