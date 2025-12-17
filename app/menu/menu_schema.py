from pydantic import BaseModel

from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.orm import mapped_column
from pgvector.sqlalchemy import Vector

from app.core.db import base


# ---------- API / JSON 용 Pydantic 스키마 ----------

class MenuSchema(BaseModel):
    menu_id: int | None = None
    menu_name: str
    category: str
    base_price: float | None = None
    cost_price: float | None = None
    list_price: float | None = None
    main_ingredient: str | None = None
    is_seasonal: bool = False


# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------

class Menu(base):
    __tablename__ = "menus"

    menu_id = Column(Integer, primary_key=True, index=True)
    menu_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)   # coffee / dessert
    is_seasonal = Column(Boolean, default=False)

    cost_price = Column(Numeric(10, 2), nullable=True)       # 원가
    list_price = Column(Numeric(10, 2), nullable=True)       # 정가
    main_ingredient = Column(String(100), nullable=True)     # 주재료

    description = Column(String(500), nullable=True)         # 메뉴 설명 (임베딩 대상)
    embedding = mapped_column(Vector(1536), nullable=True)   # 메뉴 추천/검색용 임베딩
