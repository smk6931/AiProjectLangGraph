from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel
from typing import Optional, List
from app.core.db import base

# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------
class Policy(base):
    __tablename__ = "policies"

    policy_id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)   # 예: 인사, 보안, 안전, 계약
    title = Column(String(200), nullable=False)     # 정책 제목
    content = Column(Text, nullable=False)          # 상세 정책 내용
    
    # RAG 검색을 위한 벡터 데이터 (OpenAI Embedding: 1536 dim)
    embedding = Column(Vector(1536), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# ---------- API / JSON 용 Pydantic 스키마 ----------
class PolicyCreate(BaseModel):
    category: str
    title: str
    content: str

class PolicyResponse(BaseModel):
    policy_id: int
    category: str
    title: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True
