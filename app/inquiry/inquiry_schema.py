from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from pydantic import BaseModel
from app.core.db import base
from typing import TypedDict, List, Dict, Any

# --- LangGraph State ---
class InquiryState(TypedDict):
    """에이전트 상태 관리"""
    store_id: int
    question: str
    category: str  # Router가 분류한 카테고리
    
    # 각 노드에서 수집한 데이터
    sales_data: Dict[str, Any]
    manual_data: List[str]
    policy_data: List[str]
    
    # 최종 결과
    final_answer: str
    inquiry_id: int
    diagnosis_result: str # 진단 결과 요약 (새로 추가)


class StoreInquiry(base):
    __tablename__ = "store_inquiries"

    inquiry_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    
    # 카테고리 (예: "sales", "manual", "policy") - 라우터가 분류한 값
    category = Column(String(50), nullable=False)
    
    # 질문과 답변 (상세 내용이므로 Text 타입 사용)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# --- Pydantic Models for API ---
class InquiryCreate(BaseModel):
    store_id: int
    question: str

class InquiryResponse(BaseModel):
    inquiry_id: int
    store_id: int
    category: str
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True


