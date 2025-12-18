from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Numeric, JSON
from sqlalchemy.orm import mapped_column
from pgvector.sqlalchemy import Vector
from app.core.db import base

# ---------- API / JSON 용 Pydantic 스키마 ----------


class ReviewSchema(BaseModel):
    review_id: int
    store_id: int
    menu_id: int
    rating: int
    review_text: str
    created_at: datetime
    delivery_app: str
    embedding: list[float] | None = None  # 1536 차원 임베딩


class ReviewAnalysisSchema(BaseModel):
    analysis_id: int
    review_id: int
    sentiment_score: float
    classification: list[str]  # JSON
    ai_reply: str
    model_version: str

# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------


class Review(base):
    __tablename__ = "reviews"

    review_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.order_id"),
                      nullable=True)  # 어떤 주문에 대한 리뷰인지 연결
    menu_id = Column(Integer, ForeignKey("menus.menu_id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1~5
    review_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    delivery_app = Column(String(50), nullable=True)  # 배민/쿠팡이츠 등

    # AI 검색(Semantic Search)을 위한 임베딩은 조회 빈도가 높으므로 본 테이블에 유지
    embedding = mapped_column(Vector(1536), nullable=True)


class ReviewAnalysis(base):
    __tablename__ = "review_analysis"

    analysis_id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey(
        "reviews.review_id"), unique=True, nullable=False)

    # 감정 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
    sentiment_score = Column(Numeric(3, 2), nullable=True)

    # 분류 태그 (JSON): ["맛", "양", "배달시간"]
    classification = Column(JSON, nullable=True)

    # AI 제안 답글
    ai_reply = Column(Text, nullable=True)

    # 분석에 사용된 모델 버전 (예: "gpt-4o", "gemini-1.5-pro")
    model_version = Column(String(50), nullable=True)

    analyzed_at = Column(DateTime, default=datetime.now)
