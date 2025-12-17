from pydantic import BaseModel

from sqlalchemy import Column, Integer, String, DateTime, func

from app.core.db import base


# ---------- API / JSON 용 Pydantic 스키마 ----------

class Users(BaseModel):
  email: str
  nickname: str
  password_hash: str


class UserLogin(BaseModel):
  email: str


# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------

class User(base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  email = Column(String, unique=True, nullable=False, index=True)
  password_hash = Column(String, nullable=False)
  nickname = Column(String, nullable=False)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
