from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.db import get_db
from app.manual.manual_schema import Manual, ManualResponse

router = APIRouter(prefix="/manual", tags=["Manual"])

@router.get("/get", response_model=List[ManualResponse])
def get_manuals(db: Session = Depends(get_db)):
    """모든 매뉴얼 조회"""
    results = db.query(Manual).all()
    # Pydantic 모델(ManualResponse)로 자동 변환되어 리턴됨 (Vector 등 제외됨)
    return results
