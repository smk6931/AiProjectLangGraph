from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel
from typing import Optional, List
from app.core.db import base

class Manual(base):
    __tablename__ = "manuals"

    manual_id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)   # 예: 위생, 레시피, 기기 등
    title = Column(String(200), nullable=False)     # 매뉴얼 제목
    content = Column(Text, nullable=False)          # 상세 내용
    
    # RAG 검색을 위한 벡터 데이터 (OpenAI Embedding: 1536 dim)
    embedding = Column(Vector(1536), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- Pydantic Models for API ---
class ManualCreate(BaseModel):
    category: str
    title: str
    content: str

class ManualResponse(ManualCreate):
    manual_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
