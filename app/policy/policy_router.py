from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.db import get_db
from app.policy.policy_schema import Policy, PolicyResponse

router = APIRouter(prefix="/policy", tags=["Policy"])

@router.get("/get", response_model=List[PolicyResponse])
def get_policies(db: Session = Depends(get_db)):
    """모든 정책/규정 조회"""
    results = db.query(Policy).all()
    # Pydantic 모델(PolicyResponse)로 자동 변환 (임베딩 필드 제외)
    return results
