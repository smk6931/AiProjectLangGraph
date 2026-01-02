import json
from datetime import datetime, date
from typing import Dict, Any, List

# External App Imports
from app.clients.genai import genai_generate_text
from app.inquiry.inquiry_schema import InquiryState

# ===== Router Node (질문 분류) =====
async def router_node(state: InquiryState) -> InquiryState:
    """
    질문을 분석하여 카테고리 분류
    - sales: 매출, 성과, 통계 관련
    - manual: 기기 사용법, 레시피, 기술 지원
    - policy: 운영 규정, 고객 응대, 본사 정책
    """
    question = state["question"]
    
    prompt = f"""
    당신은 프랜차이즈 매장 질문 분류 AI입니다. 
    질문의 핵심 의도를 파악하여 다음 3가지 중 하나로 분류하세요.

    질문: "{question}"

    1. sales (매출/데이터):
       - 매출, 판매량, 주문 건수, 메뉴별 성과, 통계
       - "지난주 매출 어때?", "가장 많이 팔린 메뉴는?"

    2. manual (매뉴얼/기술):
       - 기기 조작, 고장 수리, 청소 방법, 레시피
       - "커피머신 청소 어떻게 해?", "와이파이 연결법"

    3. policy (정책/외부정보):
       - 매장 운영 규정, 환불/반품 정책, 고객 응대 매뉴얼
       - **[중요]**: "맛집 추천", "날씨", "뉴스", "주변 상권" 등 외부 정보 검색이 필요한 경우도 'policy'로 분류

    [Output Format]
    JSON으로만 응답하세요:
    {{"category": "sales" | "manual" | "policy", "reason": "분류 이유"}}
    """ 
    
    # LLM 호출 (Gemini로 간소화)
    try:
        # 가볍고 빠른 gemai 사용
        response = await genai_generate_text(prompt)
        
        # JSON 파싱
        content = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        category = data.get("category", "policy") # 기본값 policy
        reason = data.get("reason", "")
    except Exception as e:
        print(f"⚠️ [Router] 분류 오류 (Fallback to policy): {e}")
        category = "policy"
        reason = "Error Parsing"
        data = {}

    print(f"🔀 [Router] Category Decision: {category} (Reason: {reason})")
    
    # State 업데이트
    state["category"] = category
    return state
