from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.inquiry.inquiry_agent import run_search_check, run_final_answer_stream
from app.inquiry.inquiry_schema import InquiryResponse

router = APIRouter(prefix="/inquiry", tags=["Inquiry"])


class InquiryRequest(BaseModel):
    """질문 요청 스키마"""
    store_id: int
    question: str


@router.post("/check", response_model=dict)
async def check_database_search(request: InquiryRequest):
    """
    [Steps 1] DB 검색 & 유사도 확인 API
    질문을 받아 내부 DB(매뉴얼/정책)를 검색하고, 
    가장 유사한 문서와 점수를 반환합니다. (답변 생성 X)
    """
    from app.inquiry.inquiry_agent import run_search_check
    
    result = await run_search_check(request.store_id, request.question)
    return {
        "success": True,
        "data": result
    }


class GenerateRequest(BaseModel):
    store_id: int
    question: str
    category: str
    mode: str # 'db' or 'web'
    context_data: list = [] # DB 모드일 때 사용할 검색 결과 리스트


@router.post("/generate/stream")
async def generate_answer_stream(request: GenerateRequest):
    """
    [Steps 2] 최종 답변 생성 (Streaming)
    사용자가 선택한 모드(DB or Web)에 따라 최종 답변을 스트리밍합니다.
    """
    from fastapi.responses import StreamingResponse
    from app.inquiry.inquiry_agent import run_final_answer_stream
    
    return StreamingResponse(
        run_final_answer_stream(
            request.store_id, 
            request.question, 
            request.category, 
            request.mode, 
            request.context_data
        ),
        media_type="application/x-ndjson"
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
