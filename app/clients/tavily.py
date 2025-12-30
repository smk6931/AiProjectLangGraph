import os
from dotenv import load_dotenv
from app.util.decorators import perform_async_logging

# 환경 변수 로드
load_dotenv()

# Tavily API 키 (하드코딩 된 키가 있다면 우선순위 주의, 여기선 .env 사용 권장)
# .env에 TAVILY_API_KEY가 없으면 아래 하드코딩 된 키를 fallback으로 사용
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")

@perform_async_logging
async def tavily_search(query: str, max_results: int = 5):
    """
    Tavily API를 사용하여 웹 검색을 수행합니다.
    검색 결과가 없으면(Context 부족 시) 쿼리를 단순화하여 재시도(Self-Correction)합니다.
    
    Returns:
        str: 포맷팅된 검색 결과 문자열 (Title, Link, Snippet 포함)
    """
    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        
        # 1차 검색 시도 (구체적 쿼리)
        # 예: "카페 프랜차이즈 [질문]" 형태로 문맥 보강
        target_query = f"카페 프랜차이즈 {query}"
        response = tavily.search(query=target_query, search_depth="basic", max_results=max_results)
        raw_results = response.get('results', [])
        
        # 🔄 Self-Correction: 검색 결과가 없으면 쿼리 단순화 후 재시도
        if not raw_results:
            print(f"🔄 [Tavily Correction] '{target_query}' 결과 없음 -> '{query}' 재검색")
            # 접두사 제거하고 질문 자체로 검색
            response = tavily.search(query=query, search_depth="basic", max_results=max_results)
            raw_results = response.get('results', [])
        
        # 결과 포맷팅
        formatted_list = []
        for item in raw_results:
            title = item.get('title', '제목 없음')
            url = item.get('url', '#')
            content = item.get('content', '')
            formatted_list.append(f"Title: {title}\nLink: {url}\nSnippet: {content}\n")
        
        if not formatted_list:
             return "Tavily 검색 결과가 없습니다."
        else:
             return "[외부 웹 검색 결과 (Tavily)]\n" + "\n---\n".join(formatted_list)
             
    except Exception as e:
        print(f"❌ Tavily 검색 실패: {e}")
        return f"Tavily 검색 중 오류가 발생했습니다: {str(e)}"
