import json
from typing import Dict, Any, List

# External App Imports
from app.clients.genai import genai_generate_with_grounding
from app.core.db import fetch_all
from app.inquiry.inquiry_schema import InquiryState

# ===== Step 4: Manual RAG Node (매뉴얼 검색) =====
async def manual_node(state: InquiryState) -> InquiryState:
    """매뉴얼 DB에서 관련 문서 검색 (Vector Search)"""
    if state["category"] != "manual":
        return state
    
    question = state["question"]
    
    # OpenAI Embeddings로 질문 벡터화
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = embeddings_model.embed_query(question)
    
    # pgvector 유사도 검색 (코사인 거리 기준 Top 3)
    # distance가 0에 가까울수록 유사함
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM manuals
    ORDER BY distance
    LIMIT 5
    """
    
    rows = await fetch_all(query)
    
    # 검색 결과 및 최소 거리 저장
    min_distance = 1.0 # 기본값 (불일치)
    if rows:
        min_distance = min([r['distance'] for r in rows])
        
    state["manual_data"] = [
        f"[{row['title']}] (유사도: {1 - row['distance']:.2f})\n{row['content']}"
        for row in rows
    ]
    
    if "search_meta" not in state: state["search_meta"] = {}
    state["search_meta"] = {"min_distance": min_distance, "source": "manual_db"}
    
    print(f"📖 [Manual] 검색 완료 (Min Distance: {min_distance:.4f})")
    return state


# ===== Step 5: Policy RAG Node (정책 검색) =====
async def policy_node(state: InquiryState) -> InquiryState:
    """운영 정책 매뉴얼 검색 (Policies 테이블 조회)"""
    if state["category"] != "policy":
        return state
    
    question = state["question"]
    
    from langchain_openai import OpenAIEmbeddings
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    question_vector = embeddings_model.embed_query(question)
    
    query = f"""
    SELECT title, content, category,
           embedding <=> '{question_vector}'::vector AS distance
    FROM policies
    ORDER BY distance
    LIMIT 5
    """
    
    rows = await fetch_all(query)
    
    min_distance = 1.0
    if rows:
        min_distance = min([r['distance'] for r in rows])
        
    state["policy_data"] = [
        f"[{row['title']}] (유사도: {1 - row['distance']:.2f})\n{row['content']}"
        for row in rows
    ]
    
    state["search_meta"] = {"min_distance": min_distance, "source": "policy_db"}
    
    print(f"📜 [Policy] 검색 완료 (Min Distance: {min_distance:.4f})")
    return state


# ===== Step 5.5: Web Search Node (외부 검색 - Google Grounding) =====
async def web_search_node(state: InquiryState) -> InquiryState:
    """내부 DB 검색 실패 시 외부 웹 검색 수행 (Google Gemini Grounding)"""
    question = state["question"]
    print(f"🌐 [Google Grounding] 내부 문서 부족 -> 구글 검색 수행: {question}")
    
    try:
        # 구글 검색 Grounding을 통한 답변 생성
        grounded_response = await genai_generate_with_grounding(question)
        
        # 결과 저장
        state["manual_data"] = [f"[Google 검색 결과 기반 답변]\n{grounded_response}"]
        state["search_meta"] = {"source": "web_search", "min_distance": 0.0}
        
    except Exception as e:
        print(f"❌ Google Grounding 실패: {e}")
        state["manual_data"] = [f"외부 검색 연결에 실패했습니다. (Error: {str(e)})"]
        
    return state
