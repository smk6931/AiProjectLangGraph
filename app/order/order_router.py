from fastapi import APIRouter
from app.order.order_service import select_orders_by_store, select_daily_sales_by_store

router = APIRouter(prefix="/order", tags=["order"])


@router.get("/store/{store_id}")
async def get_orders_by_store(store_id: int):
    return await select_orders_by_store(store_id)


@router.get("/store/{store_id}/daily_sales")
async def get_daily_sales_by_store(store_id: int):
    return await select_daily_sales_by_store(store_id)
