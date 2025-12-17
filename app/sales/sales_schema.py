from pydantic import BaseModel
from datetime import date
from sqlalchemy import Column, Integer, Date, Numeric, ForeignKey, UniqueConstraint
from app.core.db import base

# ---------- API / JSON 용 Pydantic 스키마 ----------


class SalesDailySchema(BaseModel):
    sales_id: int | None = None
    store_id: int
    sale_date: date
    total_sales: float
    total_orders: int

# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------


class SalesDaily(base):
    __tablename__ = "sales_daily"

    sales_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    sale_date = Column(Date, nullable=False)
    total_sales = Column(Numeric(15, 2), default=0)
    total_orders = Column(Integer, default=0)

    # 한 매장의 같은 날짜 데이터는 하나만 존재해야 함 (중복 방지)
    __table_args__ = (
        UniqueConstraint('store_id', 'sale_date', name='uix_store_date'),
    )
