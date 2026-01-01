from typing import TypedDict, List, Dict, Any, Optional

# LangGraph에서 노드 간 데이터를 공유하기 위한 상태(State) 정의
class InquiryState(TypedDict):
    # 1. 입력 (Input)
    question: str              # 사용자의 질문
    store_id: int              # 매장 ID
    
    # 2. 분류 (Routing)
    category: str              # 질문 카테고리 (sales, manual, policy, general 등)
    requirements: dict         # 추출된 필요 정보 (날짜, 메뉴 등)
    
    # 3. 데이터 컨텍스트 (Data Context)
    date_range: Optional[str]  # 분석 기간 (예: BETWEEN '2024-01-01' AND '2024-01-07')
    sql_query: Optional[str]   # 생성된 SQL 쿼리
    sales_data: Dict[str, Any] # DB에서 가져온 매출/리뷰 데이터
    search_results: List[str]  # RAG 또는 웹 검색 결과 문서
    
    # 4. 검증 (Validation)
    is_relevant: bool          # 검색 결과 관련성 여부
    recommendation: Dict[str, Any] # AI 추천 여부 (웹 검색 등)
    
    # 5. 출력 (Output)
    final_answer: Dict[str, Any] # UI에 전달할 최종 JSON 응답
