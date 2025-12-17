from pydantic import BaseModel
from datetime import date
from sqlalchemy import Column, Integer, String, Float, Date, Numeric
from app.core.db import base

# ---------- API / JSON 용 Pydantic 스키마 ----------


class StoreSchema(BaseModel):
    store_id: int
    store_name: str
    region: str
    city: str
    lat: float
    lon: float
    population_density_index: float | None = None
    open_date: date | None = None
    franchise_type: str | None = None


# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------

class Store(base):
    __tablename__ = "stores"

    store_id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)           # 서울 / 대구 / 강원
    city = Column(String(50), nullable=False)             # UI·지도 표시용
    # 위도 (DOUBLE PRECISION)
    lat = Column(Float, nullable=False)
    # 경도 (DOUBLE PRECISION)
    lon = Column(Float, nullable=False)
    population_density_index = Column(Float, nullable=True)  # 도심 대비 인구밀도 지수
    open_date = Column(Date, nullable=True)
    franchise_type = Column(String(20), nullable=True)    # 직영 / 가맹
