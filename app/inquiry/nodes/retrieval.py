import json
from app.clients.openai import openai_create_embedding
from app.clients.genai import genai_generate_with_grounding
from app.core.db import fetch_all
from app.inquiry.state import InquiryState

async def retrieval_node(state: InquiryState) -> InquiryState:
    """
    [Retrieval Node]
    Manual/Policy 질문에 대해 PostgreSQL(pgvector) 검색 및 Web Search Fallback을 수행합니다.
    """
    question = state["question"]
    category = state["category"] # manual or policy
    
    print(f"📘 [Retrieval] Searching for category: {category} (using pgvector)")
    
    search_results = []
    is_relevant = True
    recommendation = {"indices": [], "comment": ""}

    try:
        # 1. Query Embedding 생성
        query_vector = await openai_create_embedding(question)
        
        # 2. SQL Vector Search
        # 카테고리에 따라 테이블 분기 (policy -> policies, manual -> manuals)
        table_name = "policies" if category == "policy" else "manuals"
        
        # pgvector: <=> (Cosine Distance), <-> (L2 Distance), <#> (Inner Product)
        # Cosine Distance 사용: 0(identical) ~ 2(opposite)
        sql = f"""
            SELECT content, (embedding <=> $1) as distance
            FROM {table_name}
            ORDER BY distance ASC
            LIMIT 3
        """
        
        # pgvector 쿼리 시 벡터 리스트를 문자열로 변환하여 전달
        rows = await fetch_all(sql, str(query_vector))
        
        # 3. 결과 처리
        if rows:
            for row in rows:
                dist = row['distance']
                content = row['content']
                search_results.append(f"[Distance: {dist:.4f}] {content}")
                
            # Distance Threshold (유사도 판단 기준)
            # 0.5 이상이면 거리가 멀다고 판단 (상황에 따라 조절 필요)
            if rows[0]['distance'] > 0.5:
                is_relevant = False
                recommendation["comment"] = "⚠️ 내부 문서와 유사도가 낮습니다."
        else:
            is_relevant = False
            recommendation["comment"] = "관련된 내부 문서를 찾지 못했습니다."

        # 4. Web Search Fallback (관련성 낮을 때)
        if not is_relevant:
            print("🌐 [Web Search] Triggering Gemini Grounding...")
            web_res = await genai_generate_with_grounding(question)
            search_results.append(f"====== [Web Search Result] ======\n{web_res}")

    except Exception as e:
        print(f"❌ [Retrieval Error] {e}")
        # DB 검색 실패 시에도 Web Search 시도
        web_res = await genai_generate_with_grounding(question)
        search_results.append(f"====== [Fallback Result] ======\n{web_res}")

    return {
        "search_results": search_results,
        "is_relevant": is_relevant,
        "recommendation": recommendation
    }
