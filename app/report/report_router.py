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
