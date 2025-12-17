from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from app.core.db import base

# ---------- API / JSON 용 Pydantic 스키마 ----------


class OrderSchema(BaseModel):
    order_id: int
    store_id: int
    menu_id: int
    quantity: int
    total_price: float
    ordered_at: datetime

# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------


class Order(base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    menu_id = Column(Integer, ForeignKey("menus.menu_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    ordered_at = Column(DateTime, default=datetime.now, nullable=False)
