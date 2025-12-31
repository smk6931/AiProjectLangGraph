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
    category = Column(String(50), nullable=False)   # 예: 기기 관리, 위생 관리, 포스 운영
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # RAG 검색용 임베딩
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
