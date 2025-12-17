from pydantic import BaseModel
from datetime import date, datetime
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, JSON
from sqlalchemy.orm import mapped_column
from app.core.db import base

# ---------- API / JSON 용 Pydantic 스키마 ----------


class StoreReportSchema(BaseModel):
    report_id: int
    store_id: int
    report_date: date
    report_type: str  # DAILY, WEEKLY, MONTHLY

    summary: str
    marketing_strategy: str
    operational_improvement: str
    risk_assessment: Dict[str, Any] | None = None  # JSON 데이터

# ---------- Alembic / DB 매핑용 SQLAlchemy 모델 ----------


class StoreReport(base):
    __tablename__ = "store_reports"

    report_id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    report_date = Column(Date, default=date.today, nullable=False)

    # 리포트 유형: DAILY(일간), WEEKLY(주간), MONTHLY(월간)
    report_type = Column(String(20), nullable=False)

    # 🤖 AI 분석 결과 저장 영역
    summary = Column(Text, nullable=True)                   # 종합 3줄 요약
    # 마케팅 제안 (타겟팅, 프로모션 등)
    marketing_strategy = Column(Text, nullable=True)
    operational_improvement = Column(
        Text, nullable=True)   # 운영 개선 제안 (인력 배치, 재고 관리 등)

    # 구조화된 분석 데이터 (JSON)
    # 예: {"risk_score": 85, "churn_prediction": "high", "top_keywords": ["친절", "느림"]}
    risk_assessment = Column(JSON, nullable=True)

    created_at = Column(Date, default=datetime.now)
