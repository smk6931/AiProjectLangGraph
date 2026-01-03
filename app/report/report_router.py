from fastapi import APIRouter, HTTPException
from app.report.report_schema import GenerateReportRequest
from app.report.report_service import generate_ai_store_report, select_latest_report

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate")
async def post_generate_report(request: GenerateReportRequest):
    """
    AI 전략 리포트 생성 요청 (Request Body 사용 - store_id 포함)
    """
    result = await generate_ai_store_report(request.store_id, request.store_name, request.mode, request.target_date)
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
        # 1. DB 삭제
        with SessionLocal() as session:
            # 해당 지점 리포트 전체 삭제
            session.query(StoreReport).filter(StoreReport.store_id == store_id).delete()
            session.commit()
            
        # 2. Redis 캐시 삭제 (동기화)
        from app.core.cache import get_redis
        client = await get_redis()
        if client:
            # 해당 store_id의 모든 리포트 키 스캔
            keys = await client.keys(f"report:{store_id}:*")
            if keys:
                await client.delete(*keys)
                print(f"🗑️ [Redis] {store_id}번 지점 관련 캐시 {len(keys)}개 삭제 완료")

        return {"status": "success", "message": f"{store_id}번 지점 리포트 초기화 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
