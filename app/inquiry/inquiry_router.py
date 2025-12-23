from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.inquiry.inquiry_agent import process_inquiry
from app.inquiry.inquiry_schema import InquiryResponse

router = APIRouter(prefix="/inquiry", tags=["Inquiry"])


class InquiryRequest(BaseModel):
    """질문 요청 스키마"""
    store_id: int
    question: str


@router.post("/ask", response_model=dict)
async def ask_question(request: InquiryRequest):
    """
    가맹점 질문 처리 API
    LangGraph 에이전트가 질문을 분석하고, 적절한 데이터 소스(매출/매뉴얼/정책)에서
    정보를 검색하여 답변을 생성합니다.
    Args:
        request: 매장 ID와 질문 내용
    Returns:
        답변 및 메타데이터 (카테고리, inquiry_id 등)
    """
    try:
        result = await process_inquiry(
            store_id=request.store_id,
            question=request.question
        )
        
        return {
            "success": True,
            "data": result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"질문 처리 중 오류 발생: {str(e)}"
        )


@router.get("/history/{store_id}", response_model=list)
async def get_inquiry_history(store_id: int, limit: int = 10):
    """
    매장별 질문 이력 조회
    
    Args:
        store_id: 매장 ID
        limit: 조회할 개수 (기본 10개)
    
    Returns:
        질문/답변 이력 리스트
    """
    from app.core.db import fetch_all
    
    query = f"""
    SELECT inquiry_id, category, question, answer, created_at
    FROM store_inquiries
    WHERE store_id = {store_id}
    ORDER BY created_at DESC
    LIMIT {limit}
    """
    
    rows = await fetch_all(query)
    
    return [
        {
            "inquiry_id": row["inquiry_id"],
            "category": row["category"],
            "question": row["question"],
            "answer": row["answer"],
            "created_at": str(row["created_at"])
        }
        for row in rows
    ]
