import json
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from app.clients.genai import genai_generate_with_grounding # Gemini Grounding
from app.core.config import settings
from app.inquiry.state import InquiryState

# 벡터 DB 설정 (임시 경로, 실제 경로에 맞게 수정 필요)
persist_directory = "./chroma_db" 
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=settings.OPENAI_API_KEY)

async def retrieval_node(state: InquiryState) -> InquiryState:
    """
    [Retrieval Node]
    Manual/Policy 질문에 대해 Vector DB 검색 및 Web Search Fallback을 수행합니다.
    """
    question = state["question"]
    category = state["category"] # manual or policy
    
    print(f"📘 [Retrieval] Searching for category: {category}")
    
    search_results = []
    is_relevant = True
    recommendation = {"indices": [], "comment": ""}

    try:
        # 1. RAG Vector Search
        # (실제 구현 시엔 collection_name을 category에 따라 분기)
        collection_name = "manual_collection" if category == "manual" else "policy_collection"
        
        # Chroma DB가 없거나 로드 실패 시 에러 처리 필요
        try:
            vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings, collection_name=collection_name)
            docs = vectorstore.similarity_search_with_score(question, k=3)
            
            # 검색 결과 가공
            for doc, score in docs:
                # score가 낮으면(거리가 멀면) 관련성 낮음으로 판단 (예: score > 0.5)
                # Chroma는 L2 distance를 쓸 경우 0에 가까울수록 유사함
                search_results.append(f"[Score: {score:.4f}] {doc.page_content}")
                
            # 가장 가까운 문서의 거리가 너무 멀면 Web Search 추천
            if docs and docs[0][1] > 0.6: # Threshold
                is_relevant = False
                recommendation["comment"] = "⚠️ 내부 문서와 유사도가 낮습니다. 웹 검색을 추천합니다."
                
        except Exception as e:
            print(f"⚠️ [VecDB Error] {e}")
            is_relevant = False # DB 에러 시 웹 검색 유도

        # 2. Web Search (Fallback or Recommendation)
        # 만약 관련성이 낮다고 판단되면 Gemini Grounding 실행 (Optional)
        # 여기서는 추천 메시지만 남기고, 실제 실행은 Answer 단계나 UI 선택에 맡길 수도 있음.
        # 하지만 Auto-Feedback 루프라면 여기서 바로 Web Search를 돌릴 수도 있음.
        
        if not is_relevant:
            print("🌐 [Web Search] Triggering Gemini Grounding...")
            web_res = await genai_generate_with_grounding(question)
            search_results.append(f"====== [Web Search Result] ======\n{web_res}")

    except Exception as e:
        print(f"❌ [Retrieval Error] {e}")

    return {
        "search_results": search_results,
        "is_relevant": is_relevant,
        "recommendation": recommendation
    }
