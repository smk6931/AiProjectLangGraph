from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Numeric, JSON
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
    embedding = Column(Vector(1536), nullable=True)



