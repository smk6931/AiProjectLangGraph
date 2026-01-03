from fastapi import APIRouter, HTTPException
from app.report.report_service import generate_ai_store_report, select_latest_report

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate/{store_id}")
async def post_generate_report(store_id: int, store_name: str, mode: str = "sequential", target_date: str = None):
    """
    AI 전략 리포트 생성 요청 (mode: sequential, target_date: YYYY-MM-DD)
    """
    result = await generate_ai_store_report(store_id, store_name, mode, target_date)
    if not result:
        raise HTTPException(status_code=500, detail="리포트 생성에 실패했습니다.")
    return result


@router.get("/latest/{store_id}")
async def get_latest_report(store_id: int):
    """
    해당 지점의 가장 최근 리포트 조회
    """
    report = await select_latest_report(store_id)
    if not report:
        return None
    return report

@router.delete("/reset/{store_id}")
async def delete_reports(store_id: int):
    """
    해당 지점의 모든 AI 리포트 데이터 삭제 (초기화)
    """
    from app.core.db import SessionLocal
    from app.report.report_schema import StoreReport
    
    try:
        with SessionLocal() as session:
            # 해당 지점 리포트 전체 삭제
            session.query(StoreReport).filter(StoreReport.store_id == store_id).delete()
            session.commit()
        return {"status": "success", "message": f"{store_id}번 지점 리포트 초기화 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
