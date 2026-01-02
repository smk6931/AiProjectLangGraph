import json
from app.clients.openai import client
from app.inquiry.state import InquiryState

async def router_node(state: InquiryState) -> InquiryState:
    """
    [Router Node]
    사용자의 질문 의도를 파악하여 적절한 카테고리(sales, manual, policy)로 분류합니다.
    """
    question = state["question"]
    
    system_prompt = """
    당신은 프랜차이즈 매장 관리 시스템의 '의도 분류기(Intent Classifier)'입니다.
    사용자의 질문을 분석하여 다음 카테고리 중 하나로 분류하고, 필요한 메타데이터를 추출하세요.

    [Categories]
    1. sales: 매출, 주문량, 인기 메뉴, 판매 추이, 리뷰 분석 등 데이터 기반 분석이 필요한 경우.
    2. manual: 레시피, 청소 방법, 기기 조작법 등 매장 운영 메뉴얼 관련.
    3. policy: 복장 규정, 급여, 근태, 본사 지침 등 규정 관련.
    4. general: 그 외 단순 인사말이나 일반적인 대화.

    [Output Format (JSON)]
    {
        "category": "sales" | "manual" | "policy" | "general",
        "reason": "분류 이유",
        "extracted_info": {
            "target_menu": [], // 언급된 메뉴명
            "period": "last_week" // 언급된 기간 (없으면 null)
        }
    }
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        category = parsed.get("category", "general")
        requirements = parsed.get("extracted_info", {})
        
        print(f"🔀 [Router] Category: {category} | Info: {requirements}")
        
    except Exception as e:
        print(f"⚠️ [Router Error] {e}")
        category = "general"
        requirements = {}

    return {
        "category": category,
        "requirements": requirements
    }
